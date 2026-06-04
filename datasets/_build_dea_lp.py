#!/usr/bin/env python
"""Builder for the dea_lp (data envelopment analysis, dual LP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "dea_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": ["Depot1", "Depot2", "...", "Depot20"],
         "doc": "the decision-making units being compared, here the depots; every unit contributes one weight in the peer combination"},
        {"name": "J", "members": ["stock", "wages", "issues", "receipts", "reqs"],
         "doc": "all measured attributes of a unit, partitioned into inputs and outputs"},
        {"name": "Ji", "members": ["stock", "wages"],
         "doc": "the input attributes, the resources a unit consumes; a subset of J"},
        {"name": "Jo", "members": ["issues", "receipts", "reqs"],
         "doc": "the output attributes, the products a unit delivers; a subset of J"},
    ],
    "params": [
        {"name": "data", "index": "I,J", "kind": "measurement",
         "doc": "the observed level of attribute J for unit I, in the natural unit of that attribute; for inputs it is the amount consumed and for outputs the amount produced"},
        {"name": "isel", "index": "", "kind": "selector",
         "doc": "the single unit currently under evaluation; the analysis benchmarks this one unit against the whole peer group, and this unit's own attribute levels appear on the right-hand side of the balance relations"},
        {"name": "norm", "index": "", "kind": "scale",
         "doc": "a fixed scaling constant applied to the radial efficiency term, here 100"},
        {"name": "vlo", "index": "", "kind": "weight",
         "doc": "a small fixed coefficient that prices the input slacks in the efficiency expression"},
        {"name": "ulo", "index": "", "kind": "weight",
         "doc": "a small fixed coefficient that prices the output slacks in the efficiency expression"},
    ],
    "vars": [
        {"name": "lam", "index": "I", "domain": "NonNegativeReals",
         "doc": "the weight placed on each peer unit when building the composite benchmark unit"},
        {"name": "vs", "index": "Ji", "domain": "NonNegativeReals",
         "doc": "the input slack for each input attribute, the shortfall of the composite unit's input below the radially scaled target"},
        {"name": "us", "index": "Jo", "domain": "NonNegativeReals",
         "doc": "the output slack for each output attribute, the surplus of the composite unit's output above the evaluated unit's level"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the radial efficiency multiplier applied to the evaluated unit's inputs"},
        {"name": "eff", "index": "", "domain": "Reals",
         "doc": "the overall efficiency score that the model reports for the evaluated unit"},
    ],
    "objective": {"sense": "minimize", "expr_var": "eff"},
}

NARRATIVE = (
    "We benchmark one selected operating unit against a group of comparable peer units, "
    "each described by a set of input attributes it consumes and output attributes it produces. "
    "The model chooses how much weight to place on each peer unit when forming a composite "
    "reference unit, a radial scaling factor on the selected unit's inputs, and slack terms on "
    "the inputs and outputs. The objective is to minimize the reported efficiency score, which "
    "combines the scaled radial term with small penalties on the input and output slacks."
)

DII = (
    "def dii_rule(model, jj):\n"
    "    i0 = model.isel.value\n"
    "    return sum(model.lam[i] * model.data[i, jj] for i in model.I) + model.vs[jj] == model.z * model.data[i0, jj]\n"
    "model.dii = Constraint(model.Ji, rule=dii_rule)"
)
DIO = (
    "def dio_rule(model, jj):\n"
    "    i0 = model.isel.value\n"
    "    return sum(model.lam[i] * model.data[i, jj] for i in model.I) - model.us[jj] == model.data[i0, jj]\n"
    "model.dio = Constraint(model.Jo, rule=dio_rule)"
)
DOBJ = (
    "def dobj_rule(model):\n"
    "    return model.eff == model.norm * model.z "
    "- model.vlo * sum(model.vs[j] for j in model.Ji) "
    "- model.ulo * sum(model.us[j] for j in model.Jo)\n"
    "model.dobj = Constraint(rule=dobj_rule)"
)
WHOLESET = "\n".join([DII, DIO, DOBJ])

records = [
    {"description": (
        "For each input attribute, the composite reference unit built from the weighted peers, "
        "after adding its input slack, must match the evaluated unit's level of that input scaled "
        "by the radial efficiency multiplier. In other words the weighted total of that input "
        "across all peer units plus the slack on that input equals the radial multiplier times the "
        "evaluated unit's own value of that input."),
     "expected_pyomo": DII},
    {"description": (
        "For each output attribute, the composite reference unit built from the weighted peers, "
        "after removing its output slack, must match the evaluated unit's level of that output. "
        "In other words the weighted total of that output across all peer units minus the slack on "
        "that output equals the evaluated unit's own value of that output."),
     "expected_pyomo": DIO},
    {"description": (
        "The reported efficiency score is defined from the radial term and the slack penalties. "
        "Set the efficiency score equal to the scaling constant times the radial multiplier, then "
        "subtract a small penalty on the total input slack and a small penalty on the total output "
        "slack, each penalty using its own fixed coefficient."),
     "expected_pyomo": DOBJ},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "dea_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
