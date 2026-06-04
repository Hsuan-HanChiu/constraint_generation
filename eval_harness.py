#!/usr/bin/env python
"""Evaluation harness for the constraint-generation dataset.

Runs a chat LLM over every record (across ALL datasets/*.jsonl by default),
asks it to generate the Pyomo constraint(s) from the plain-language
description + component list, and grades each generation by Z3 LOGICAL
EQUIVALENCE against the ground truth.

It talks to any OpenAI-compatible endpoint, so it works with:
  - a vLLM OpenAI server  (python -m vllm.entrypoints.openai.api_server ...)
  - TGI / SGLang OpenAI shims
  - the real OpenAI API   (--base-url https://api.openai.com/v1)

It REUSES grade_harness.py and does not touch it:
  gh.grade(problem_id, generated, expected_pyomo)  -> {"equivalent": True/False/None, ...}
  gh.build_user_prompt(record) / gh.system_prompt() / gh._strip_fences() / gh.constraint_names()

Run inside the `opti` conda env (pyomo + z3-solver + openai). The model itself
is served separately (e.g. vLLM in its own env); this script is just the client
+ grader.

Examples
--------
  # smoke test against a local vLLM server, 5 records:
  python eval_harness.py --model Qwen/Qwen3.5-9B-Instruct \
      --base-url http://localhost:8000/v1 --limit 5

  # full eval, greedy (pass@1):
  python eval_harness.py --model Qwen/Qwen3.5-9B-Instruct \
      --base-url http://localhost:8000/v1 --out eval_qwen.jsonl

  # pass@5 with sampling:
  python eval_harness.py --model ... --n 5 --temperature 0.7
"""
import argparse, glob, json, os, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grade_harness as gh  # noqa: E402


def collect_records(glob_pat):
    """Load every record across the matched dataset files, tagging each with
    its source dataset stem (problem_id is what actually resolves the base)."""
    files = sorted(glob.glob(os.path.join(HERE, glob_pat)))
    recs = []
    for fp in files:
        stem = os.path.basename(fp).replace("_constraint_gen.jsonl", "")
        with open(fp) as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    r["_dataset"] = stem
                    recs.append(r)
    return recs, files


def kind_of(r):
    names = gh.constraint_names(r["expected_pyomo"])
    return "whole-set" if len(names) > 1 else "per-constraint"


def _is_openai_reasoning(model):
    """OpenAI reasoning models (gpt-5 family, o-series) reject `temperature` and
    `max_tokens` and instead want `max_completion_tokens` (+ optional reasoning_effort).
    vLLM-served open models (Qwen etc.) take the normal params, so this only
    triggers on the OpenAI names."""
    m = model.lower()
    return m.startswith(("gpt-5", "o1", "o3", "o4"))


def _generate(client, model, system, user, temperature, max_tokens, reasoning_effort=None):
    kwargs = {"model": model,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]}
    if _is_openai_reasoning(model):
        kwargs["max_completion_tokens"] = max_tokens   # must be large enough for reasoning + answer
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
    else:
        kwargs["temperature"] = temperature
        kwargs["max_tokens"] = max_tokens
    resp = client.chat.completions.create(**kwargs)
    return gh._strip_fences(resp.choices[0].message.content or "")


def eval_one(idx, r, client, model, system, n, temperature, max_tokens, reasoning_effort=None):
    """Generate n samples for one record and grade each. pass@k = any sample EQUIVALENT."""
    user = gh.build_user_prompt(r)
    samples, verdicts = [], []
    for _ in range(n):
        try:
            g = _generate(client, model, system, user, temperature, max_tokens, reasoning_effort)
            v = gh.grade(r["problem_id"], g, r["expected_pyomo"])
        except Exception as e:
            g, v = None, {"equivalent": None, "error": f"{type(e).__name__}: {e}"}
        samples.append(g)
        verdicts.append({"equivalent": v.get("equivalent"), "error": v.get("error")})
    passed = any(v["equivalent"] is True for v in verdicts)
    all_err = all(v["equivalent"] is None for v in verdicts)
    return {
        "idx": idx,
        "problem_id": r["problem_id"],
        "dataset": r.get("_dataset"),
        "kind": kind_of(r),
        "description": r["description"][:140],
        "passed": passed,
        "all_error": all_err,
        "verdicts": verdicts,
        "samples": samples,
    }


def summarize(results, model, n):
    def rate(sub):
        return sum(1 for x in sub if x["passed"]), len(sub)
    e, t = rate(results)
    print("\n===== EVAL SUMMARY =====")
    print(f"model: {model}  |  records: {t}  |  metric: pass@{n}")
    print(f"OVERALL : {e}/{t} = {e / max(1, t):.1%}")
    for k in ("per-constraint", "whole-set"):
        ke, kt = rate([x for x in results if x["kind"] == k])
        if kt:
            print(f"  {k:14}: {ke}/{kt} = {ke / kt:.1%}")
    nerr = sum(1 for x in results if x["all_error"])
    print(f"  unparseable/grade-error records (all samples): {nerr}/{t}")
    by = defaultdict(lambda: [0, 0])
    for x in results:
        by[x["dataset"]][1] += 1
        by[x["dataset"]][0] += 1 if x["passed"] else 0
    worst = sorted(by.items(), key=lambda kv: kv[1][0] / max(1, kv[1][1]))[:12]
    print("  12 hardest models (pass rate):")
    for name, (me, mt) in worst:
        print(f"    {name:24} {me}/{mt} = {me / mt:.0%}")


def main():
    ap = argparse.ArgumentParser(description="Eval an LLM on the constraint-gen dataset (Z3-graded).")
    ap.add_argument("--model", required=True, help="served model id / HF repo / local path")
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "http://localhost:8000/v1"),
                    help="OpenAI-compatible endpoint (vLLM default :8000/v1)")
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "EMPTY"),
                    help="any non-empty string for vLLM")
    ap.add_argument("--dataset-glob", default="datasets/*_constraint_gen.jsonl",
                    help="which dataset files to evaluate (default: all)")
    ap.add_argument("--n", type=int, default=1, help="samples per record (pass@k)")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=1024,
                    help="for OpenAI reasoning models this maps to max_completion_tokens; "
                         "bump to >=4096 so reasoning+answer fit")
    ap.add_argument("--reasoning-effort", default=None,
                    choices=[None, "minimal", "low", "medium", "high"],
                    help="OpenAI gpt-5/o-series only; 'low' keeps cost down for this mechanical task")
    ap.add_argument("--limit", type=int, default=None, help="cap #records (smoke test)")
    ap.add_argument("--workers", type=int, default=8, help="concurrent request+grade threads")
    ap.add_argument("--out", default="eval_results.jsonl")
    args = ap.parse_args()

    from openai import OpenAI
    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    system = gh.system_prompt()
    recs, files = collect_records(args.dataset_glob)
    if args.limit:
        recs = recs[:args.limit]
    print(f"loaded {len(recs)} records from {len(files)} dataset files")
    print(f"model={args.model}  base_url={args.base_url}  n={args.n}  T={args.temperature}  workers={args.workers}")

    results = []
    t0 = time.time()
    out_path = args.out if os.path.isabs(args.out) else os.path.join(HERE, args.out)
    with open(out_path, "w") as fout, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(eval_one, i, r, client, args.model, system,
                          args.n, args.temperature, args.max_tokens, args.reasoning_effort): i
                for i, r in enumerate(recs)}
        done = 0
        for fut in as_completed(futs):
            res = fut.result()
            results.append(res)
            fout.write(json.dumps(res, ensure_ascii=False) + "\n")
            fout.flush()
            done += 1
            if done % 25 == 0 or done == len(recs):
                npass = sum(1 for x in results if x["passed"])
                print(f"  {done}/{len(recs)}  pass={npass}  ({time.time() - t0:.0f}s)")

    results.sort(key=lambda x: x["idx"])
    summarize(results, args.model, args.n)
    print(f"\nwrote {out_path}  ({time.time() - t0:.0f}s elapsed)")


if __name__ == "__main__":
    main()
