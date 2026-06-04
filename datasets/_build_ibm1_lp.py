#!/usr/bin/env python
"""Builder for the ibm1_lp (metal blending) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "ibm1_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "s", "members": ["bin-1", "bin-2", "bin-3", "bin-4", "bin-5", "aluminum", "silicon"],
         "doc": "the scrap metals and pure materials available for blending"},
        {"name": "sl", "members": ["bin-1", "bin-2", "bin-3", "bin-4", "bin-5"],
         "doc": "the locally available scrap blends, a subset of the blending materials"},
        {"name": "e", "members": ["aluminum", "silicon", "iron", "copper", "manganese", "magnesium"],
         "doc": "the chemical elements tracked in the final blend"},
    ],
    "params": [
        {"name": "prop", "index": "e,s", "kind": "composition",
         "doc": "the fraction of a blending material that consists of a given element, as a proportion between zero and one"},
        {"name": "sup", "index": "s,attr", "kind": "supply",
         "doc": "supply and cost data per material, keyed by attribute: inventory is the pounds available, min-use is the minimum pounds that must be used, and cost is the price in dollars per pound"},
        {"name": "target_weight", "index": "", "kind": "requirement",
         "doc": "the total weight the final blend must reach, in pounds"},
    ],
    "vars": [
        {"name": "x", "index": "s", "domain": "NonNegativeReals",
         "doc": "the pounds of each blending material used in the blend"},
        {"name": "bc", "index": "e", "domain": "NonNegativeReals",
         "doc": "the pounds of each chemical element present in the final blend"},
        {"name": "cost", "index": "", "domain": "NonNegativeReals",
         "doc": "the total material cost of the blend, in dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We produce a metal blend by mixing scrap metals and pure materials. Each "
    "material has a known price per pound and a known chemical makeup. We decide how "
    "many pounds of each material to use, which in turn determines how much of each "
    "chemical element ends up in the blend. The objective is to make the total cost "
    "of the materials as small as possible."
)

YIELD = (
    "def yield_rule(model):\n"
    "    return sum(model.x[s] for s in model.s) == model.target_weight\n"
    "model.yield_con = Constraint(rule=yield_rule)"
)
EBAL = (
    "def ebal_rule(model, e):\n"
    "    return model.bc[e] == sum(model.prop[e, s] * model.x[s] for s in model.s)\n"
    "model.ebal = Constraint(model.e, rule=ebal_rule)"
)
CDEF = (
    "def cdef_rule(model):\n"
    "    return model.cost == sum(model.sup[s, 'cost'] * model.x[s] for s in model.s)\n"
    "model.cdef = Constraint(rule=cdef_rule)"
)
WHOLESET = "\n".join([YIELD, EBAL, CDEF])

records = [
    {"description": (
        "The finished blend has to weigh exactly the required amount. Make the total "
        "pounds of all materials used add up to that required weight."),
     "expected_pyomo": YIELD},
    {"description": (
        "Track how much of each chemical element is in the blend. For every element, "
        "the pounds of that element in the blend equal the sum over all materials of "
        "how much that material contributes, where each material contributes its "
        "fraction of that element times the pounds of the material used."),
     "expected_pyomo": EBAL},
    {"description": (
        "Account for the total material cost. Set the cost equal to the sum over all "
        "materials of the price per pound of the material times the pounds of it used."),
     "expected_pyomo": CDEF},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "ibm1_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
