#!/usr/bin/env python
"""Builder for the knapsack_mip (binary knapsack) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "knapsack_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "i9", "i10"],
         "doc": "the set of candidate items available to place into the knapsack, indexed by label"},
    ],
    "params": [
        {"name": "p", "index": "i", "kind": "profit",
         "doc": "the profit gained from including each item in the selection, in value units per item"},
        {"name": "w", "index": "i", "kind": "weight",
         "doc": "the weight each item contributes if it is included, in weight units per item"},
        {"name": "c", "index": "", "kind": "capacity",
         "doc": "the total weight capacity of the knapsack, in weight units; a single scalar"},
    ],
    "vars": [
        {"name": "x", "index": "i", "domain": "Binary",
         "doc": "selection indicator for each item; equals 1 if the item is placed in the knapsack and 0 otherwise"},
        {"name": "z", "index": "", "domain": "NonNegativeReals",
         "doc": "the total profit accumulated from the selected items, in value units; a single scalar"},
    ],
    "objective": {"sense": "maximize", "expr_var": "z"},
}

NARRATIVE = (
    "We are choosing which items to pack into a single knapsack. For each item we decide "
    "whether or not to include it. Every item carries a known profit if we take it and a "
    "known weight that it adds to the load. We also track the total profit collected from "
    "the items we choose. The objective is to maximize the total profit of the selected items."
)

CAP_RESTR = (
    "def cap_restr_rule(model):\n"
    "    return sum(model.w[i] * model.x[i] for i in model.i) <= model.c\n"
    "model.cap_restr = Constraint(expr=cap_restr_rule(model))"
)
UTILITY = (
    "def utility_rule(model):\n"
    "    return model.z == sum(model.p[i] * model.x[i] for i in model.i)\n"
    "model.utility = Constraint(expr=utility_rule(model))"
)
WHOLESET = "\n".join([CAP_RESTR, UTILITY])

CAP_INTENT = (
    "the combined weight of all the items chosen for the knapsack stays within its weight capacity"
)
UTIL_INTENT = (
    "the tracked total profit equals the profit summed over every item that is selected"
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, " + CAP_INTENT + ". "
    "Finally, " + UTIL_INTENT + "."
)

records = [
    {"description": (
        "The items packed into the knapsack cannot weigh more than it can carry. Adding up the "
        "weight contributed by every item that is selected, the total must not exceed the "
        "knapsack's weight capacity."),
     "expected_pyomo": CAP_RESTR},
    {"description": (
        "The total profit being tracked has to reflect exactly the items that were chosen. Summing "
        "the profit of every selected item, set the tracked total profit equal to that sum."),
     "expected_pyomo": UTILITY},
    {"description": WHOLESET_DESC,
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "knapsack_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
