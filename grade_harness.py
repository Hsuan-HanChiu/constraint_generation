#!/usr/bin/env python
"""
Constraint-generation checking harness.

Loads the constraint-generation dataset (one record = system context +
description + ground-truth Pyomo), optionally calls an LLM (OpenAI API) to
generate a constraint from the description, and grades the generated Pyomo
against the ground truth for LOGICAL EQUIVALENCE using OptiChat's Z3 checker
(benchmarking/z3_constraint_checker.compare_added_constraints).

Run inside the `opti` conda env (has pyomo 6.9.5, z3-solver, openai):
    conda run --no-capture-output -n opti python grade_harness.py --help

Two ways to use it:

  1) Grade an output you already have (no API call) — the manual path:
       python grade_harness.py grade --record 0 --generated /path/to/output.py
     ...or paste-grade from stdin:
       python grade_harness.py grade --record 0 --generated -

  2) Generate with the API and grade in one shot:
       export OPENAI_API_KEY=sk-...
       python grade_harness.py api --model gpt-5.5 --record 0
       python grade_harness.py api --model gpt-5.5 --all --out results.jsonl

Records are indexed 0..14 for agreste (0-13 = per-constraint, 14 = whole set).
The target constraint name(s) are parsed from each record's expected_pyomo, so
the harness knows which constraint(s) to strip from the base before grading.
"""
from __future__ import annotations
import argparse, copy, importlib.util, json, os, re, sys, time
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                      # .../OptiChat_test
OPTICHAT = ROOT / "optichat_org" / "OptiChat"
Z3CHECKER = OPTICHAT / "benchmarking" / "z3_constraint_checker.py"
SYSTEM_PROMPT_FILE = HERE / "constraint_gen_system_prompt.txt"
DATASETS_DIR = HERE / "datasets"            # all constraint-gen JSONL datasets
REDUCED_DIR = HERE / "reduced_data"         # small grading instances for MIPs
MODEL_LIBRARY = OPTICHAT / "model_library" / "feas_model"   # canonical paired source (.py + _data.json)
DATASET = DATASETS_DIR / "agreste_lp293_constraint_gen.jsonl"

# Per-problem base model + data registry. Add new models here as the dataset grows.
MODEL_REGISTRY = {
    "agreste_lp293": {
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "agreste_lp293.py",
        "data_json": ROOT / "GAMSConversion" / "data_json" / "agreste.json",
    },
    "binpacking_mip": {
        # Small instance (6 items, 3 bins) for FAST, reliable Z3 grading — the
        # constraint STRUCTURE is identical to the full 60x20 instance, so an
        # equivalence check on the small one is valid and far quicker (the full
        # instance's 1200 binaries time out Z3's counterexample search).
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "binpacking_mip.py",
        "data_json": REDUCED_DIR / "binpacking_small.json",
    },
    "tsp1_mip": {
        # TSP with Miller-Tucker-Zemlin subtour elimination. The full instance
        # defines x over ii x ii (17x17 = 289 binaries); a small instance (5
        # candidate cities, 4 toured, preserving the ii > i quirk) keeps Z3 fast.
        # The constraint STRUCTURE is instance-independent, so the equivalence
        # check on the small instance is valid (validated FAITHFUL vs the 17x6).
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "tsp1_mip.py",
        "data_json": REDUCED_DIR / "tsp1_small.json",
    },
    # ---- batch 2 (2026-06-02): distinct constraint families ----
    "gussex1_lp": {  # transportation: supply capacity, demand satisfaction, flow cost
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "gussex1_lp.py",
        "data_json": ROOT / "GAMSConversion" / "data_json" / "gussex1.json",
    },
    "blend_lp57": {  # blending: proportion/quality, material balance, accounting
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "blend_lp57.py",
        "data_json": ROOT / "GAMSConversion" / "data_json" / "blend.json",
    },
    "decomp_lp97": {  # transshipment: node flow balance with intermediate tanks
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "decomp_lp97.py",
        "data_json": ROOT / "GAMSConversion" / "data_json" / "decomp.json",
    },
    "csp_mip": {  # closest string problem (NOT cutting stock): one-char-per-position + min-max Hamming
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "csp_mip.py",
        "data_json": REDUCED_DIR / "csp_small.json",  # full has 156 binaries; reduced 12, validated faithful
    },
    "flowshop_mip": {  # permutation flow-shop: position assignment + completion-time recursion
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "flowshop_mip.py",
        "data_json": ROOT / "GAMSConversion" / "data_json" / "flowshop.json",  # 36 binaries, grades in 20ms
    },
    "fawley_lp": {  # refinery blending/operations: multi-stream balance + quality pooling
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "fawley_lp.py",
        "data_json": ROOT / "GAMSConversion" / "data_json" / "fawley.json",
    },
    "nurses_mip": {  # nurse rostering: cost/time accounting, shift coverage, overlap/incompat/assoc, skill, fairness
        # Full instance has 54 nurses x 54 shift-combos = ~2916 binaries -> Z3 times out.
        # Reduced instance (3 nurses x 4 shift-combos = 12 binaries) keeps the constraint
        # STRUCTURE identical while grading in ms.
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "nurses_mip.py",
        "data_json": REDUCED_DIR / "nurses_small.json",
    },
    "orani_lp": {  # CGE / input-output economics: market clearing + price identities (LP, full data)
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "orani_lp.py",
        "data_json": ROOT / "GAMSConversion" / "data_json" / "orani.json",
    },
    "poutil_mip": {  # power-plant unit commitment: temporal stage/startup linking, load-following tiers
        # Full instance ~771 binaries (8 stages x 96 periods) -> Z3 times out.
        # Reduced instance (5 periods, 4 stages = 23 binaries) keeps structure, grades in ms.
        "base_py": ROOT / "LLMDatasets" / "pyomo2training_data" / "training_dataset" / "poutil_mip.py",
        "data_json": REDUCED_DIR / "poutil_small.json",
    },
    # ---- batch 3 (2026-06-02): sourced from optichat model_library (module-script .py) ----
    "lands_stoc_lp": {  # two-stage stochastic LP: scenario recourse, capacity/budget, demand balance
        "base_py": MODEL_LIBRARY / "lands_stoc_lp.py",
        "data_json": MODEL_LIBRARY / "lands_stoc_lp_data.json",
    },
    "korpet_mip": {  # petrochemical complex: mass balance, quality bounds, capacity, investment, accounting
        # Full instance ~108 binaries -> reduced (8 binaries) keeps structure, grades < 120ms.
        "base_py": MODEL_LIBRARY / "korpet_mip.py",
        "data_json": REDUCED_DIR / "korpet_small.json",
    },
    "mesc_lp": {  # multi-echelon supply chain LP: lead-time-shifted inventory/pipeline balance,
        # sales/reorder coupling across stages, backlog accounting, discounted per-period profit.
        # All 9 constraint families are LINEAR (dis**n is a param^const coefficient); full data grades fast.
        "base_py": MODEL_LIBRARY / "mesc_lp.py",
        "data_json": MODEL_LIBRARY / "mesc_lp_data.json",
    },
    "cubesoln_mip": {  # 3x3x3 cube line-cover MIP: exact-count cell selection, data-driven
        # line-cover bracketing (ldef walks core cells via df offsets), total aggregation.
        # Only 27 binaries -> full data grades in ~35ms, no reduced instance needed.
        "base_py": MODEL_LIBRARY / "cubesoln_mip.py",
        "data_json": MODEL_LIBRARY / "cubesoln_mip_data.json",
    },
    "multipleMB_mip": {  # multi-machine scheduling MIP: release/due/makespan timing, one-machine
        # assignment, and disjunctive big-M sequencing (d1/d2) gated by assignment + order indicators.
        # 56 binaries (z + y) but full data grades in < 45ms, no reduced instance needed.
        "base_py": MODEL_LIBRARY / "multipleMB_mip.py",
        "data_json": MODEL_LIBRARY / "multipleMB_mip_data.json",
    },
    "maintenance_mip": {  # preventive-maintenance scheduling MIP: rolling-window coverage (mtn),
        # big-M shutdown gating of events (shd), pullback-window shutdown spacing (shw), cost accounting.
        # Window constraints are guarded (skip rows running past horizon), keeping the binary count
        # Z3-tractable -> full data grades in ~216ms, no reduced instance needed.
        "base_py": MODEL_LIBRARY / "maintenance_mip.py",
        "data_json": MODEL_LIBRARY / "maintenance_mip_data.json",
    },
}

# ----------------------------------------------------------------------------
# .env loading (zero-dependency; does not override already-set env vars)
# ----------------------------------------------------------------------------
def _load_dotenv():
    for env_path in (HERE / ".env", Path.cwd() / ".env"):
        if not env_path.is_file():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            if key.startswith("export "):
                key = key[len("export "):].strip()
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)

_load_dotenv()

# ----------------------------------------------------------------------------
# Import the Z3 checker standalone
# ----------------------------------------------------------------------------
def _load_z3_checker():
    spec = importlib.util.spec_from_file_location("z3cc", str(Z3CHECKER))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["z3cc"] = mod            # register before exec so @dataclass resolves __module__
    spec.loader.exec_module(mod)
    return mod

Z3CC = _load_z3_checker()
import pyomo.environ as pyo

# ----------------------------------------------------------------------------
# Data loading + base model construction
# ----------------------------------------------------------------------------
def _conv_key(k: str):
    parts = k.split("|")
    out = [int(x) if x.lstrip("-").isdigit() else x for x in parts]
    return out[0] if len(out) == 1 else tuple(out)

def _tuplize_members(members):
    """A set's members may be 1-D (scalars) or multi-D (lists/pairs). Pyomo's Set
    needs multi-dim members as tuples, so convert any inner list to a tuple."""
    return [tuple(m) if isinstance(m, list) else m for m in members]

def _load_data(data_json: Path) -> dict:
    """Build the data dict for build_model(data). Handles two on-disk shapes:
      (1) structured: {sets, scalar_params, indexed_params}
      (2) flat: top-level keys map directly to set lists / scalars / indexed dicts
    Multi-dim sets are tuple-ized; indexed-param pipe-keys are split + int-coerced.
    Unused keys are harmless (build_model reads only what it needs), so we no longer
    special-case agreste's ps/sp — they pass through and are ignored."""
    raw = json.load(open(data_json))
    data = {}
    if "sets" in raw and ("indexed_params" in raw or "scalar_params" in raw):
        for s, members in raw.get("sets", {}).items():
            data[s] = _tuplize_members(members) if isinstance(members, list) else members
        for k, v in raw.get("scalar_params", {}).items():
            data[k] = v
        for k, v in raw.get("indexed_params", {}).items():
            data[k] = {_conv_key(kk): vv for kk, vv in v.items()} if isinstance(v, dict) else v
    else:                                            # flat format (e.g. poutil, korpet)
        for k, v in raw.items():
            if isinstance(v, dict):
                data[k] = {_conv_key(kk): vv for kk, vv in v.items()}
            elif isinstance(v, list):
                data[k] = _tuplize_members(v)
            else:
                data[k] = v
    return data

def _exec_base(base_py: Path, data: dict):
    """Build a base model from a model .py, supporting BOTH interfaces:
      (A) LLMDatasets style: the module defines `build_model(data)` -> model.
      (B) model_library style: the module is a SCRIPT that reads a `data` global
          (injected here) and builds `model` at module scope.
    We inject `data` into the exec namespace and exec the source; if a build_model
    function is defined we call it, otherwise we return the module-level `model`."""
    src = Path(base_py).read_text()
    g = {"data": data, "__name__": f"_base_{Path(base_py).stem}"}
    exec(compile(src, str(base_py), "exec"), g)        # noqa: S102 (trusted local corpus)
    if callable(g.get("build_model")):
        return g["build_model"](data)
    if "model" in g:
        return g["model"]
    raise RuntimeError(f"{base_py.name}: no build_model() and no module-level `model`")

def _resolve_reg(problem_id: str) -> dict:
    """Return {base_py, data_json} for a problem_id. Explicit MODEL_REGISTRY entries
    win; otherwise fall back to the model_library convention:
      base_py  = MODEL_LIBRARY/<id>.py
      data_json= reduced_data/<id>_small.json if it exists, else MODEL_LIBRARY/<id>_data.json
    So any model_library model graded with a reduced instance just needs its
    reduced_data/<id>_small.json present — no registry edit required."""
    if problem_id in MODEL_REGISTRY:
        return MODEL_REGISTRY[problem_id]
    base_py = MODEL_LIBRARY / f"{problem_id}.py"
    reduced = REDUCED_DIR / f"{problem_id}_small.json"
    data_json = reduced if reduced.exists() else MODEL_LIBRARY / f"{problem_id}_data.json"
    if not base_py.exists():
        raise KeyError(f"no registry entry and no model_library .py for problem_id={problem_id!r}")
    return {"base_py": base_py, "data_json": data_json}

_BASE_CACHE: dict = {}
def build_base(problem_id: str):
    """Build the FULL base model (all native constraints present)."""
    if problem_id in _BASE_CACHE:
        return _BASE_CACHE[problem_id]
    reg = _resolve_reg(problem_id)
    base = _exec_base(Path(reg["base_py"]), _load_data(reg["data_json"]))
    _BASE_CACHE[problem_id] = base
    return base

def constraint_names(pyomo_code: str) -> list[str]:
    """Parse `model.<name> = Constraint(...)` target names from a code block."""
    return re.findall(r"model\.(\w+)\s*=\s*Constraint", pyomo_code)

def build_base_explicit(base_py: Path, data_json: Path):
    """Build a base model from EXPLICIT base_py + data_json paths (no registry).
    Parallel-safe: lets a worker validate a model that isn't registered yet."""
    return _exec_base(Path(base_py), _load_data(Path(data_json)))

def build_base_from(problem_id: str, data_json: Path):
    """Build a base model from an EXPLICIT data file (bypasses the registry/cache).
    Used to grade the same constraint on a different-sized instance."""
    reg = _resolve_reg(problem_id)
    return _exec_base(Path(reg["base_py"]), _load_data(Path(data_json)))

def grade_on_base(base_full, generated_code: str, expected_code: str, timeout_ms: int):
    """Grade against a pre-built base model with an explicit Z3 timeout."""
    target_names = constraint_names(expected_code)
    if not target_names:
        return {"equivalent": None, "reason": "no_target_constraint_name_parsed"}
    base = copy.deepcopy(base_full)
    for name in target_names:
        if name in [c.name for c in base.component_objects(pyo.Constraint, active=True)]:
            base.del_component(name)
    actual = copy.deepcopy(base)
    ok_a, err_a = _exec_constraint(actual, generated_code)
    if not ok_a:
        return {"equivalent": None, "reason": f"generated_exec_error:{err_a}"}
    expected = copy.deepcopy(base)
    ok_e, err_e = _exec_constraint(expected, expected_code)
    if not ok_e:
        return {"equivalent": None, "reason": f"expected_exec_error:{err_e}"}
    rep = Z3CC.compare_added_constraints(base, actual, expected, timeout_ms=timeout_ms)
    return {"equivalent": rep.equivalent, "reason": rep.reason}

def _exec_constraint(model, code: str):
    g = {"model": model, "Constraint": pyo.Constraint, "sum": sum, "pyo": pyo,
         "value": pyo.value, "quicksum": sum}
    try:
        exec(code, g)
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

# ----------------------------------------------------------------------------
# Grading
# ----------------------------------------------------------------------------
def grade(problem_id: str, generated_code: str, expected_code: str) -> dict:
    """
    Build base, strip the target constraint(s) so both sides ADD them fresh,
    exec generated + expected, run the Z3 equivalence check.
    Returns a dict verdict.
    """
    base_full = build_base(problem_id)
    target_names = constraint_names(expected_code)
    if not target_names:
        return {"equivalent": None, "reason": "no_target_constraint_name_parsed"}

    base = copy.deepcopy(base_full)
    for name in target_names:
        if name in [c.name for c in base.component_objects(pyo.Constraint, active=True)]:
            base.del_component(name)

    actual = copy.deepcopy(base)
    ok_a, err_a = _exec_constraint(actual, generated_code)
    if not ok_a:
        return {"equivalent": None, "reason": f"generated_exec_error:{err_a}",
                "target_names": target_names}

    expected = copy.deepcopy(base)
    ok_e, err_e = _exec_constraint(expected, expected_code)
    if not ok_e:
        return {"equivalent": None, "reason": f"expected_exec_error:{err_e}",
                "target_names": target_names}

    report = Z3CC.compare_added_constraints(base, actual, expected)
    return {
        "equivalent": report.equivalent,
        "reason": report.reason,
        "target_names": target_names,
        "actual_added": report.actual_added,
        "expected_added": report.expected_added,
        "counterexample": getattr(report, "counterexample", None),
    }

# ----------------------------------------------------------------------------
# Prompt assembly
# ----------------------------------------------------------------------------
def _fmt_components(c: dict) -> str:
    lines = []
    lines.append("SETS:")
    for s in c.get("sets", []):
        mem = s.get("members", [])
        mem_str = ", ".join(map(str, mem)) if len(mem) <= 20 else ", ".join(map(str, mem[:20])) + f", ... ({len(mem)} total)"
        lines.append(f"  - {s['name']}: {s.get('doc','')} | members: {{{mem_str}}}")
    lines.append("PARAMETERS:")
    for p in c.get("params", []):
        idx = f"[{p['index']}]" if p.get("index") else ""
        lines.append(f"  - {p['name']}{idx}: {p.get('doc','')}")
    lines.append("VARIABLES:")
    for v in c.get("vars", []):
        idx = f"[{v['index']}]" if v.get("index") else ""
        dom = f" ({v['domain']})" if v.get("domain") else ""
        lines.append(f"  - {v['name']}{idx}{dom}: {v.get('doc','')}")
    obj = c.get("objective", {})
    if obj:
        lines.append(f"OBJECTIVE: {obj.get('sense','')} {obj.get('expr_var','')}")
    return "\n".join(lines)

def build_user_prompt(record: dict) -> str:
    return (
        f"MODEL NARRATIVE:\n{record['model_narrative']}\n\n"
        f"COMPONENTS:\n{_fmt_components(record['components'])}\n\n"
        f"DESCRIPTION:\n{record['description']}"
    )

def system_prompt() -> str:
    return SYSTEM_PROMPT_FILE.read_text()

# ----------------------------------------------------------------------------
# OpenAI generation
# ----------------------------------------------------------------------------
def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```$", "", t)
    return t.strip()

def generate_openai(system: str, user: str, model: str, api_key: str | None = None) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    # Minimal, model-agnostic call: no temperature / max_tokens (newer models reject them).
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return _strip_fences(resp.choices[0].message.content)

# ----------------------------------------------------------------------------
# Records
# ----------------------------------------------------------------------------
def load_records(dataset_path=None) -> list[dict]:
    if dataset_path is None:
        path = DATASET
    else:
        path = Path(dataset_path)
        if not path.exists():            # allow a bare filename → resolve under datasets/
            path = DATASETS_DIR / dataset_path
    return [json.loads(l) for l in open(path) if l.strip()]

# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def cmd_list(args):
    for i, r in enumerate(load_records(args.dataset)):
        names = constraint_names(r["expected_pyomo"])
        kind = "whole-set" if len(names) > 1 else "per-constraint"
        desc = r["description"][:70].replace("\n", " ")
        print(f"[{i:2}] {r['problem_id']} | {kind} | {len(names)} constraint(s): {names if len(names)<=3 else names[:3]+['...']}")
        print(f"     desc: {desc}...")

def cmd_grade(args):
    records = load_records(args.dataset)
    r = records[args.record]
    if args.generated == "-":
        generated = sys.stdin.read()
    else:
        generated = Path(args.generated).read_text()
    generated = _strip_fences(generated)
    verdict = grade(r["problem_id"], generated, r["expected_pyomo"])
    _print_verdict(args.record, r, verdict)

def cmd_api(args):
    records = load_records(args.dataset)
    targets = list(range(len(records))) if args.all else [args.record]
    sysp = system_prompt()
    # JSONL when the path ends in .jsonl (streamed, crash-safe); otherwise a
    # single JSON document with a summary block written at the end.
    jsonl_mode = bool(args.out) and args.out.endswith(".jsonl")
    out_f = open(args.out, "w") if jsonl_mode else None
    results = []
    n_eq = n_neq = n_err = 0
    for i in targets:
        r = records[i]
        user = build_user_prompt(r)
        try:
            generated = generate_openai(sysp, user, args.model, args.api_key)
        except Exception as e:
            print(f"[{i:2}] API ERROR: {type(e).__name__}: {e}")
            n_err += 1
            entry = {"record": i, "problem_id": r["problem_id"], "model": args.model,
                     "generated": None, "verdict": None,
                     "error": f"{type(e).__name__}: {e}"}
            results.append(entry)
            if out_f:
                out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            continue
        verdict = grade(r["problem_id"], generated, r["expected_pyomo"])
        _print_verdict(i, r, verdict, generated=generated, show_gen=args.show_generated)
        if verdict["equivalent"] is True: n_eq += 1
        elif verdict["equivalent"] is False: n_neq += 1
        else: n_err += 1
        entry = {"record": i, "problem_id": r["problem_id"], "model": args.model,
                 "generated": generated, "verdict": verdict}
        results.append(entry)
        if out_f:
            out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    summary = {"model": args.model, "total": len(targets),
               "equivalent": n_eq, "not_equivalent": n_neq, "errors": n_err}
    if len(targets) > 1:
        print(f"\n===== SUMMARY ({args.model}) =====")
        print(f"  equivalent : {n_eq}/{len(targets)}")
        print(f"  not equiv  : {n_neq}/{len(targets)}")
        print(f"  errors/skip: {n_err}/{len(targets)}")
    if out_f:
        out_f.close()
        print(f"  wrote {args.out}")
    elif args.out:
        with open(args.out, "w") as f:
            json.dump({"summary": summary, "results": results}, f,
                      ensure_ascii=False, indent=2)
        print(f"  wrote {args.out}")

def _perturb(code: str):
    """Flip the first relational operator to make a (usually) NON-equivalent control."""
    for a, b in (("<=", ">="), (">=", "<="), ("==", "<=")):
        if a in code:
            return code.replace(a, b, 1)
    return None

def cmd_calibrate(args):
    """
    Answer 'is this instance the right size for Z3?' by MEASURING: for each
    per-constraint record, time the self-grade (must be True) and an auto-
    perturbed negative control (relation flipped, should be False). If anything
    returns z3_unknown/timeout, the instance is too big; if everything is fast
    and the controls are caught, it's well-sized.
    """
    records = load_records(args.dataset)
    print(f"{'rec':>3}  {'target':<12} {'self(ms)':>9} {'self':>6}  {'ctrl(ms)':>9} {'ctrl':>6}")
    worst = 0.0; any_unknown = False; n = 0
    for i, r in enumerate(records):
        names = constraint_names(r["expected_pyomo"])
        if len(names) != 1:
            continue                              # skip whole-set
        n += 1
        exp = r["expected_pyomo"]
        t0 = time.perf_counter()
        v_self = grade(r["problem_id"], exp, exp)
        t_self = (time.perf_counter() - t0) * 1000
        pert = _perturb(exp)
        t_ctrl = float("nan"); v_ctrl = {"equivalent": None, "reason": "no_relop"}
        if pert:
            t1 = time.perf_counter()
            v_ctrl = grade(r["problem_id"], pert, exp)
            t_ctrl = (time.perf_counter() - t1) * 1000
        worst = max(worst, t_self, 0 if pert is None else t_ctrl)
        if v_self["reason"] == "z3_unknown_or_timeout" or v_ctrl.get("reason") == "z3_unknown_or_timeout":
            any_unknown = True
        sd = {True: "OK", False: "FAIL", None: "?"}
        print(f"{i:>3}  {names[0]:<12} {t_self:>9.0f} {sd[v_self['equivalent']]:>6}  "
              f"{t_ctrl:>9.0f} {sd[v_ctrl['equivalent']]:>6}")
    print(f"\nworst single-grade: {worst:.0f} ms  (Z3 budget is {Z3CC.Z3_TIMEOUT_MS} ms)")
    if any_unknown:
        print("VERDICT: instance is TOO BIG — Z3 hit unknown/timeout. Shrink the index sets or raise the timeout.")
    else:
        bad = [1 for r in records if len(constraint_names(r['expected_pyomo']))==1]
        print("VERDICT: instance is well-sized — all grades resolved cleanly within budget.")
        print("         (self-grades must be OK; ctrl should be FAIL — if a ctrl is OK, that constraint")
        print("          has no relational operator to flip or is symmetric; not a sizing problem.)")

def _battery(expected: str):
    """A small battery of test constraints: the correct one (should be EQUIV) plus
    perturbations that are generically NON-equivalent. The validation cares about
    AGREEMENT between instances, not the specific verdict."""
    cases = [("correct", expected)]
    flip = _perturb(expected)
    if flip and flip != expected:
        cases.append(("relop-flip", flip))
    if "sum(" in expected:                       # double one term group -> changes coefficients
        cases.append(("2x-scale", expected.replace("sum(", "2 * sum(", 1)))
    return cases

def cmd_validate_instance(args):
    """
    Empirically confirm the reduced instance grades IDENTICALLY to the full one.
    For each per-constraint record, grade a battery (correct + perturbations) on
    BOTH the small instance (registry data) and the full instance (--full-data,
    long timeout), and check the verdicts MATCH. Any DISAGREEMENT means the small
    instance is too degenerate (e.g. coincidental parameter values let a wrong
    constraint pass) and must be enlarged. Inconclusive = full instance timed out
    even at the long budget.
    """
    records = load_records(args.dataset)
    problem_id = records[0]["problem_id"]
    small_base = build_base(problem_id)                              # registry (reduced) instance
    full_base = build_base_from(problem_id, Path(args.full_data))    # full instance
    print(f"problem={problem_id}  small={MODEL_REGISTRY[problem_id]['data_json'].name}  "
          f"full={Path(args.full_data).name}  full-timeout={args.timeout_large}ms\n")
    n_cases = n_agree = n_disagree = n_inconc = 0
    for i, r in enumerate(records):
        names = constraint_names(r["expected_pyomo"])
        if len(names) != 1:
            continue
        exp = r["expected_pyomo"]
        for label, cand in _battery(exp):
            vs = grade_on_base(small_base, cand, exp, Z3CC.Z3_TIMEOUT_MS)
            vl = grade_on_base(full_base, cand, exp, args.timeout_large)
            n_cases += 1
            es, el = vs["equivalent"], vl["equivalent"]
            if el is None:
                tag = "INCONCLUSIVE (full timed out)"; n_inconc += 1
            elif es == el:
                tag = f"agree ({es})"; n_agree += 1
            else:
                tag = f"*** DISAGREE small={es} full={el} ***"; n_disagree += 1
            print(f"  {names[0]:<10} {label:<11} small={str(es):<5} full={str(el):<5}  {tag}")
    print(f"\ncases={n_cases}  agree={n_agree}  disagree={n_disagree}  inconclusive={n_inconc}")
    if n_disagree == 0 and n_inconc == 0:
        print("VERDICT: reduced instance is FAITHFUL — identical verdicts to the full instance on every case.")
    elif n_disagree == 0:
        print("VERDICT: no disagreements, but some full-instance cases timed out — raise --timeout-large to fully confirm.")
    else:
        print("VERDICT: NOT faithful — the reduced instance disagrees with the full one. Enlarge it (more/less-degenerate members).")

def cmd_selfcheck(args):
    """
    Parallel-safe validation via EXPLICIT --base-py + --data-json (no registry edit).
    For every record: self-grade (expected vs expected -> must be EQUIVALENT) and an
    auto-perturbed negative control (relation flipped -> should be NOT-EQUIVALENT).
    Prints a per-record table + an overall PASS/FAIL line a worker can grep for.
    """
    records = load_records(args.dataset)
    base_full = build_base_explicit(Path(args.base_py), Path(args.data_json))
    tmo = args.timeout
    print(f"selfcheck dataset={Path(args.dataset).name}  base={Path(args.base_py).name}  "
          f"data={Path(args.data_json).name}  timeout={tmo}ms")
    print(f"{'rec':>3}  {'target':<14} {'self(ms)':>9} {'self':>6}  {'ctrl(ms)':>9} {'ctrl':>6}")
    all_ok = True; worst = 0.0
    for i, r in enumerate(records):
        names = constraint_names(r["expected_pyomo"])
        exp = r["expected_pyomo"]
        t0 = time.perf_counter()
        v_self = grade_on_base(base_full, exp, exp, tmo)
        t_self = (time.perf_counter() - t0) * 1000
        is_whole = len(names) > 1
        pert = None if is_whole else _perturb(exp)
        t_ctrl = float("nan"); v_ctrl = {"equivalent": None, "reason": "skip_whole_or_no_relop"}
        if pert:
            t1 = time.perf_counter()
            v_ctrl = grade_on_base(base_full, pert, exp, tmo)
            t_ctrl = (time.perf_counter() - t1) * 1000
        worst = max(worst, t_self, 0 if pert is None else t_ctrl)
        sd = {True: "OK", False: "FAIL", None: "?"}
        # PASS criteria: self must be EQUIVALENT; control (if any) must be NOT-equivalent
        if v_self["equivalent"] is not True:
            all_ok = False
        if pert and v_ctrl["equivalent"] is not False:
            all_ok = False
        tgt = (names[0] if len(names) == 1 else f"WHOLE({len(names)})")
        print(f"{i:>3}  {tgt:<14} {t_self:>9.0f} {sd[v_self['equivalent']]:>6}  "
              f"{t_ctrl:>9.0f} {sd[v_ctrl['equivalent']]:>6}")
        if v_self["equivalent"] is not True:
            print(f"       !! self-grade reason: {v_self['reason']}")
    print(f"\nworst single-grade: {worst:.0f} ms  (Z3 budget {tmo} ms)")
    print(f"SELFCHECK: {'PASS' if all_ok else 'FAIL'}  "
          f"({'all records self-grade EQUIVALENT and controls are caught' if all_ok else 'see !! lines above'})")

def _print_verdict(i, r, verdict, generated=None, show_gen=False):
    eq = verdict["equivalent"]
    tag = {True: "✅ EQUIVALENT", False: "❌ NOT EQUIVALENT", None: "⚠️  UNGRADED"}[eq]
    print(f"\n[{i:2}] {r['problem_id']} target={verdict.get('target_names')} -> {tag}")
    print(f"     reason: {verdict['reason']}")
    if show_gen and generated:
        print("     --- generated ---")
        for ln in generated.splitlines():
            print(f"     | {ln}")
    if eq is False and verdict.get("counterexample"):
        ce = verdict["counterexample"]
        ce = ce if len(ce) < 400 else ce[:400] + " ...(truncated)"
        print(f"     counterexample: {ce}")

def main():
    ap = argparse.ArgumentParser(description="Constraint-generation Z3 grading harness")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_list = sub.add_parser("list", help="list dataset records + target constraint names")
    ap_list.add_argument("--dataset", default=None, help="dataset JSONL (default: agreste)")
    ap_list.set_defaults(func=cmd_list)

    ap_grade = sub.add_parser("grade", help="grade a pre-supplied generated constraint (no API)")
    ap_grade.add_argument("--record", type=int, required=True, help="record index (see `list`)")
    ap_grade.add_argument("--generated", required=True, help="path to generated Pyomo, or - for stdin")
    ap_grade.add_argument("--dataset", default=None, help="dataset JSONL (default: agreste)")
    ap_grade.set_defaults(func=cmd_grade)

    ap_api = sub.add_parser("api", help="generate via OpenAI API then grade")
    ap_api.add_argument("--model", required=True, help="OpenAI model id, e.g. gpt-5.5")
    ap_api.add_argument("--dataset", default=None, help="dataset JSONL (default: agreste)")
    ap_api.add_argument("--record", type=int, default=0, help="record index (ignored with --all)")
    ap_api.add_argument("--all", action="store_true", help="run every record")
    ap_api.add_argument("--out", help="write results JSONL to this path")
    ap_api.add_argument("--api-key", dest="api_key", default=None, help="override OPENAI_API_KEY")
    ap_api.add_argument("--show-generated", dest="show_generated", action="store_true")
    ap_api.set_defaults(func=cmd_api)

    ap_cal = sub.add_parser("calibrate", help="measure Z3 grading time + whether the instance discriminates")
    ap_cal.add_argument("--dataset", default=None, help="dataset JSONL (default: agreste)")
    ap_cal.set_defaults(func=cmd_calibrate)

    ap_sc = sub.add_parser("selfcheck",
                           help="parallel-safe: validate a dataset against explicit --base-py + --data-json")
    ap_sc.add_argument("--dataset", required=True, help="dataset JSONL (bare name resolves under datasets/)")
    ap_sc.add_argument("--base-py", dest="base_py", required=True, help="path to the model's build_model .py")
    ap_sc.add_argument("--data-json", dest="data_json", required=True, help="path to the data JSON (full or reduced)")
    ap_sc.add_argument("--timeout", type=int, default=5000, help="Z3 timeout per grade (ms)")
    ap_sc.set_defaults(func=cmd_selfcheck)

    ap_val = sub.add_parser("validate-instance",
                            help="confirm the reduced instance grades identically to the full one")
    ap_val.add_argument("--dataset", default=None, help="dataset JSONL whose problem uses the reduced instance")
    ap_val.add_argument("--full-data", required=True, help="path to the FULL-size data JSON to compare against")
    ap_val.add_argument("--timeout-large", type=int, default=120000, help="Z3 timeout (ms) for the full instance")
    ap_val.set_defaults(func=cmd_validate_instance)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
