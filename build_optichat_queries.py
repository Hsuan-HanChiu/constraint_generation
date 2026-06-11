"""Build what-if/why-not constraint-gen records from OptiChat testing_library/feas_test.

Per Hsuan-Han (2026-06-10):
 - subset = WHAT-IF/new_constraint + WHY-NOT/constraint_rule + (.fix) heuristic converted to == constraints
 - route SIMPLE VARIABLE BOUNDS -> checklist (deferred); NON-bound (complex) -> dataset
 - same 5-field schema, description -> query (verbatim OptiChat Q); reuse model narrative+components
 - record source + info explicitly so queries are trackable
Tangled multi-statement heuristics (loops / conditional fixes) -> manual-review section (not auto-built).
"""
import os, re, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))
TL = os.path.join(HERE, "..", "optichat_org", "OptiChat", "testing_library", "feas_test")
DSDIR = os.path.join(HERE, "datasets")

def parse_file(p):
    raw = open(p).read()
    if "=" * 80 not in raw:
        return None
    body = raw.split("=" * 80, 1)[1].strip()
    return eval(body, {"None": None, "slice": slice, "True": True, "False": False, "nan": float("nan")})

SCAFFOLD = re.compile(
    r"^\s*(model\s*=\s*load_model|description\s*=|new_version\s*=|models_dictionary\s*=\s*solve_model"
    r"|status\s*=|if status|else\s*:|print\(|obj_val\s*=|heur_obj\s*=|#)"
)

def extract_constraint(code):
    """Return (kind, pyomo) where kind in {clean, fix_simple, messy}.
    clean      -> Constraint(expr=...) and/or def-rule+Constraint(rule=...) block (multi-line aware)
    fix_simple -> only literal var.fix(<number>) statements, converted to '== number' Constraints
    messy      -> loops / computed values / mixed fix+constraint / unexpected statements -> manual review
    """
    body = [l for l in code.split("\n") if l.strip() and not SCAFFOLD.match(l)]
    text = "\n".join(body)
    # control flow -> messy
    if re.search(r"^\s*(for |if |while |with )", text, re.M):
        return ("messy", code.strip())
    # any unexpected top-level (non-indented) statement that isn't def / model.* -> messy (e.g. `xn_val = ...`)
    for l in body:
        if l[:1] in (" ", "\t"):
            continue
        s = l.strip()
        if s.startswith("def ") or s.startswith("model."):
            continue
        return ("messy", code.strip())
    has_fix = ".fix(" in text
    has_cons = "Constraint(" in text
    if has_fix:
        lit = re.findall(r"model\.(\w+(?:\[[^\]]*\])?)\.fix\(\s*(-?[\d.]+)\s*\)", text)
        allf = re.findall(r"model\.[\w\[\]'\". ]+?\.fix\([^)]*\)", text)
        if len(lit) != len(allf) or has_cons:      # non-literal fix, or fix mixed with Constraint
            return ("messy", code.strip())
        parts = []
        for v, val in lit:
            nm = re.sub(r"\W", "", v)
            parts.append(f"model.fix_{nm} = Constraint(expr=model.{v} == {val})")
        return ("fix_simple", "\n".join(parts))
    if has_cons:
        return ("clean", text)
    return ("messy", code.strip())

def is_simple_bound(pyomo):
    if "def " in pyomo:            # indexed rule -> complex
        return False
    if "sum(" in pyomo:
        return False
    # one model.<var> term vs a constant, single line
    body = pyomo.split("expr=", 1)[-1].rstrip(")")
    return len(re.findall(r"model\.", body)) == 1

# --- load narrative+components+constraint-intents from existing per-constraint datasets ---
def load_model_meta(model):
    f = os.path.join(DSDIR, f"{model}_constraint_gen.jsonl")
    if not os.path.exists(f):
        return None
    recs = [json.loads(l) for l in open(f)]
    per = [r for r in recs if not r["description"].strip().lower().startswith("to build the complete")]
    comp = dict(recs[0]["components"])
    comp["constraints"] = [{"name": (r["expected_pyomo"].split("model.")[1].split(" ")[0].split("=")[0].strip()
                                     if "model." in r["expected_pyomo"] else "c"),
                            "intent": r["description"]} for r in per]
    return recs[0]["model_narrative"], comp

dataset = {}        # model -> list of records
checklist = []      # simple bounds
manual = []         # messy heuristics
deferred = []       # complex but model has no existing dataset

for path in sorted(glob.glob(os.path.join(TL, "*.txt"))):
    model = os.path.basename(path)[:-4]
    data = parse_file(path)
    if not isinstance(data, list):
        continue
    meta = load_model_meta(model)
    src = f"testing_library/feas_test/{model}.txt"
    for d in data:
        st = d.get("subtype")
        if st not in ("new_constraint", "constraint_rule", "heuristic"):
            continue
        typ = str(d.get("type", "")).replace("_", "-").upper()
        kind, pyomo = extract_constraint(d.get("expected_code", ""))
        info = {"source": src, "model": model, "type": typ, "subtype": st,
                "query": d.get("Q", ""), "constraint": pyomo,
                "expected_obj": d.get("expected_obj")}
        if kind == "messy":
            manual.append(info); continue
        if is_simple_bound(pyomo):
            checklist.append(info); continue
        # complex clean -> dataset (needs model meta)
        if meta is None:
            deferred.append(info); continue
        narr, comp = meta
        dataset.setdefault(model, []).append({
            "problem_id": model, "model_narrative": narr, "components": comp,
            "query": d.get("Q", ""), "expected_pyomo": pyomo,
        })  # clean 5-field schema (Hsuan-Han 2026-06-10: no _source/_type/_expected_obj). Source traceability is via this builder + the checklist.

# write per-model dataset files
nrec = 0
for model, recs in dataset.items():
    with open(os.path.join(DSDIR, f"{model}_optichat_query.jsonl"), "w") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        nrec += len(recs)

json.dump({"checklist": checklist, "manual": manual, "deferred": deferred},
          open(os.path.join(HERE, "_optichat_build_aux.json"), "w"), ensure_ascii=False)

print(f"DATASET records: {nrec} across {len(dataset)} models")
print(f"CHECKLIST (simple bounds): {len(checklist)}")
print(f"MANUAL-REVIEW (messy heuristics): {len(manual)}")
print(f"DEFERRED (complex but no existing dataset): {len(deferred)} | models: {sorted(set(d['model'] for d in deferred))}")
