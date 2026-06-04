#!/usr/bin/env python
"""Verify the generic builder: for each model, freeze the original .py base into
(components, data, extras), rebuild a scaffold generically, and confirm the
generic base gives IDENTICAL grading verdicts to the original base on the whole
dataset battery (correct + perturbations). PASS = the generic builder is a
drop-in replacement for that model's .py."""
import sys
import grade_harness as gh
import generic_builder as gb

MODELS = {
    "agreste_lp293": "agreste_lp293_constraint_gen.jsonl",
    "binpacking_mip": "binpacking_mip_constraint_gen.jsonl",
    "tsp1_mip": "tsp1_mip_constraint_gen.jsonl",
    "gussex1_lp": "gussex1_lp_constraint_gen.jsonl",
    "blend_lp57": "blend_lp57_constraint_gen.jsonl",
    "decomp_lp97": "decomp_lp97_constraint_gen.jsonl",
    "csp_mip": "csp_mip_constraint_gen.jsonl",
    "flowshop_mip": "flowshop_mip_constraint_gen.jsonl",
    "fawley_lp": "fawley_lp_constraint_gen.jsonl",
    "orani_lp": "orani_lp_constraint_gen.jsonl",
    "nurses_mip": "nurses_mip_constraint_gen.jsonl",
    "poutil_mip": "poutil_mip_constraint_gen.jsonl",
}

def battery(exp):
    cases = [("correct", exp)]
    flip = gh._perturb(exp)
    if flip and flip != exp:
        cases.append(("flip", flip))
    if "sum(" in exp:
        cases.append(("2x", exp.replace("sum(", "2 * sum(", 1)))
    return cases

for pid, ds in MODELS.items():
    reg = gh.MODEL_REGISTRY[pid]
    orig = gh.build_base_explicit(reg["base_py"], reg["data_json"])
    data = gh._load_data(reg["data_json"])
    try:
        comps, fdata, extras = gb.freeze_scaffold(orig)
        gen = gb.generic_build_model(comps, fdata, extras)
    except Exception as e:
        print(f"{pid:16} FREEZE/BUILD ERROR: {type(e).__name__}: {e}")
        continue
    recs = gh.load_records(ds)
    n = agree = disagree = err = 0
    for r in recs:
        exp = r["expected_pyomo"]
        for _, cand in battery(exp):
            try:
                vo = gh.grade_on_base(orig, cand, exp, gh.Z3CC.Z3_TIMEOUT_MS)["equivalent"]
                vg = gh.grade_on_base(gen, cand, exp, gh.Z3CC.Z3_TIMEOUT_MS)["equivalent"]
            except Exception as e:
                err += 1; continue
            n += 1
            if vo == vg: agree += 1
            else:
                disagree += 1
                print(f"   DISAGREE {pid} {gh.constraint_names(exp)} orig={vo} gen={vg}")
    tag = "PASS" if (disagree == 0 and err == 0 and agree == n and n > 0) else "FAIL"
    print(f"{pid:16} cases={n:3} agree={agree:3} disagree={disagree} err={err}  -> {tag}")
