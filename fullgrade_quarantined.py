"""Full-instance grading of the index-mismatch quarantined what-if/why-not records.
Hsuan-Han 2026-06-10: full testing; skip any that take longer than we can afford.
Per-record selfcheck against FULL data with a timeout; passers appended to the model's dataset.
Self-contained (inlines extract helpers — does NOT import the build script, which runs on import)."""
import json, os, re, subprocess, tempfile
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
TL = HERE / ".." / "optichat_org" / "OptiChat" / "testing_library" / "feas_test"
PER_RECORD_TIMEOUT = 90  # seconds

# SCAFF + control-flow check mirror build_optichat_queries.py (incl. Hsuan-Han's 2026-06-13
# change: only TOP-LEVEL control flow is messy; indented loops inside a def-rule are fine).
SCAFF = re.compile(r"^\s*(model\s*=\s*load_model|description\s*=|new_version\s*=|models_dictionary\s*=\s*solve_model|status\s*=|if status|else\s*:|print\(|obj_val\s*=|heur_obj\s*=|#)")
def parse_file(p):
    raw = open(p).read()
    if "=" * 80 not in raw: return None
    return eval(raw.split("=" * 80, 1)[1].strip(), {"None": None, "slice": slice, "True": True, "False": False, "nan": float("nan")})
def extract_constraint(code):
    body = [l for l in code.split("\n") if l.strip() and not SCAFF.match(l)]
    text = "\n".join(body)
    if re.search(r"^(for |if |while |with )", text, re.M): return None
    for l in body:
        if l[:1] in (" ", "\t"): continue
        if l.strip().startswith("def ") or l.strip().startswith("model."): continue
        return None
    if ".fix(" in text: return None
    return text if "Constraint(" in text else None
def is_simple_bound(pyomo):
    if "def " in pyomo or "sum(" in pyomo: return False
    return len(re.findall(r"model\.", pyomo.split("expr=", 1)[-1].rstrip(")"))) == 1

# quarantine models from the 2026-06-12 clean rebuild partition
models = ['alum_mip','ccoil_mip','coex_mip','cvrp_mip','fertd_mip','maxcut_mip',
          'openpit_mip','pp_mip','rcpsp_mip','relief_mip','swath_mip']
rescued_total = 0; skipped = []; tried = 0
for m in models:
    data = parse_file(TL / f"{m}.txt")
    fcg = HERE / "datasets" / f"{m}_constraint_gen.jsonl"
    fq = HERE / "datasets" / f"{m}_optichat_query.jsonl"
    if not isinstance(data, list) or not fcg.exists(): continue
    cg = [json.loads(l) for l in open(fcg)]
    narr, comp = cg[0]["model_narrative"], cg[0]["components"]
    have = {json.loads(l)["expected_pyomo"] for l in open(fq)} if fq.exists() else set()
    full = HERE / "feas_model" / f"{m}_data.json"
    base = HERE / "feas_model" / f"{m}.py"
    for q in data:
        if q.get("subtype") not in ("new_constraint", "constraint_rule"): continue
        pyomo = extract_constraint(q.get("expected_code", ""))
        if not pyomo or is_simple_bound(pyomo): continue
        if pyomo in have: continue          # already in dataset (passed on reduced) -> not quarantined
        tried += 1
        rec = {"problem_id": m, "model_narrative": narr, "components": comp, "query": q["Q"], "expected_pyomo": pyomo}
        tf = Path(tempfile.mktemp(suffix=".jsonl"))
        tf.write_text(json.dumps(rec, ensure_ascii=False) + "\n")
        try:
            out = subprocess.run(["conda","run","--no-capture-output","-n","opti","python","grade_harness.py",
                                  "selfcheck","--dataset",str(tf),"--base-py",str(base),"--data-json",str(full)],
                                 cwd=str(HERE), capture_output=True, text=True, timeout=PER_RECORD_TIMEOUT).stdout
            if "SELFCHECK: PASS" in out:
                with open(fq, "a") as fh: fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                have.add(pyomo); rescued_total += 1
            else:
                skipped.append((m, q["Q"][:35], "grade_fail"))
        except subprocess.TimeoutExpired:
            skipped.append((m, q["Q"][:35], "TIMEOUT"))
        finally:
            tf.unlink(missing_ok=True)
print(f"quarantine candidates tried on FULL data: {tried}")
print(f"RESCUED (passed full grading, appended): {rescued_total}")
print(f"SKIPPED (timeout/fail, stay quarantined): {len(skipped)}")
for s in skipped: print("  ", s)
