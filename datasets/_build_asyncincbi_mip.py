#!/usr/bin/env python
"""Builder for the asyncincbi_mip (pk1 MIPLIB underlying MIP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "asyncincbi_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "rows", "members": ["r1", "r2", "r3"],
         "doc": "the set of coupling rows; each row pairs two continuous quantities with a weighted combination of the on/off decisions"},
        {"name": "bins", "members": ["b33", "b34", "b35"],
         "doc": "the set of on/off items, each of which is either selected or not"},
    ],
    "params": [
        {"name": "rhs", "index": "", "kind": "requirement",
         "doc": "a single fixed target value that every coupling row must meet exactly; a scalar"},
        {"name": "coef", "index": "rows,bins", "kind": "weight",
         "doc": "the contribution that selecting an item adds to a given row, given for every row and item combination"},
    ],
    "vars": [
        {"name": "xmax", "index": "", "domain": "NonNegativeReals",
         "doc": "a single nonnegative quantity that serves as a common ceiling over all the per-row continuous quantities; this is the value the model drives down"},
        {"name": "xlo", "index": "rows", "domain": "NonNegativeReals",
         "doc": "the first nonnegative continuous quantity associated with each row"},
        {"name": "xhi", "index": "rows", "domain": "NonNegativeReals",
         "doc": "the second nonnegative continuous quantity associated with each row"},
        {"name": "b", "index": "bins", "domain": "Binary",
         "doc": "the selection decision for each item; equals 1 if the item is selected and 0 otherwise"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We choose which of a set of items to select and we set two nonnegative continuous "
    "quantities for each of several rows. There is also one overall nonnegative ceiling "
    "quantity that sits above every per-row continuous quantity. The objective is to make "
    "that overall ceiling quantity as small as possible."
)

BOUND_LO = (
    "def bound_lo_rule(model, r):\n"
    "    return model.xmax >= model.xlo[r]\n"
    "model.bound_lo = Constraint(model.rows, rule=bound_lo_rule)"
)
BOUND_HI = (
    "def bound_hi_rule(model, r):\n"
    "    return model.xmax >= model.xhi[r]\n"
    "model.bound_hi = Constraint(model.rows, rule=bound_hi_rule)"
)
COUPLING = (
    "def coupling_rule(model, r):\n"
    "    return model.xlo[r] - model.xhi[r] + sum(model.coef[r, j] * model.b[j] for j in model.bins) == model.rhs\n"
    "model.coupling = Constraint(model.rows, rule=coupling_rule)"
)
WHOLESET = "\n".join([BOUND_LO, BOUND_HI, COUPLING])

records = [
    {"description": (
        "The overall ceiling quantity must sit at or above the first continuous quantity of "
        "every row. For each row, the ceiling quantity must be at least as large as that row's "
        "first continuous quantity."),
     "expected_pyomo": BOUND_LO},
    {"description": (
        "The overall ceiling quantity must also sit at or above the second continuous quantity "
        "of every row. For each row, the ceiling quantity must be at least as large as that "
        "row's second continuous quantity."),
     "expected_pyomo": BOUND_HI},
    {"description": (
        "Each row must exactly meet its fixed target. For every row, take the row's first "
        "continuous quantity, subtract its second continuous quantity, and add up the "
        "contributions of all the items that are selected, where each selected item adds its "
        "contribution for that row. This combined amount must equal the fixed target."),
     "expected_pyomo": COUPLING},
    {"description": (
        "To build the complete model, enforce the following relationships in order. "
        "First, the overall ceiling quantity must be at least the first continuous quantity of "
        "every row. Second, the overall ceiling quantity must also be at least the second "
        "continuous quantity of every row. Finally, each row must exactly meet its fixed target, "
        "where the row's first continuous quantity minus its second continuous quantity plus the "
        "summed contributions of the selected items equals that target."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "asyncincbi_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
