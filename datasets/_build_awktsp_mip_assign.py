#!/usr/bin/env python
"""Builder for the awktsp_mip_assign constraint-generation dataset.

Assignment-relaxation MIP for a TSP: a binary x[i,j] chooses which city
follows which. The model carries only the two assignment (degree) constraints;
the no-self-loop diagonal is fixed in the scaffold, not authored as a constraint.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "awktsp_mip_assign_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["i1", "i2", "i3", "i4", "i5", "i6", "i7"],
         "doc": "the cities, treated as origins; each city is a place the tour passes through"},
        {"name": "j", "members": ["i1", "i2", "i3", "i4", "i5", "i6", "i7"],
         "doc": "the cities, treated as destinations; this is the same collection of cities as the origin set, used to name where an arc lands"},
    ],
    "params": [
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the cost of travelling directly from the origin city to the destination city, in distance units; the cost from a city to itself is zero"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "Binary",
         "doc": "a binary indicator that is one when the route goes directly from the origin city to the destination city and zero otherwise; the entries from a city to itself are held at zero so no city links to itself"},
    ],
    "objective": {"sense": "minimize", "expr_var": "c*x"},
}

NARRATIVE = (
    "We are planning a closed route that visits a collection of cities. For every ordered "
    "pair of cities we decide whether the route travels directly from the first to the "
    "second. Each direct leg between two cities has a known travel cost, and the goal is to "
    "choose the legs so that the total travel cost of the route is as small as possible."
)

ROWSUM = (
    "def rowsum_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.j) == 1\n"
    "model.rowsum = Constraint(model.i, rule=rowsum_rule)"
)
COLSUM = (
    "def colsum_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.i) == 1\n"
    "model.colsum = Constraint(model.j, rule=colsum_rule)"
)
WHOLESET = "\n".join([ROWSUM, COLSUM])

records = [
    {"description": (
        "The route must depart from every city exactly once. For each origin city, exactly "
        "one direct leg leaving that city to some destination city is chosen."),
     "expected_pyomo": ROWSUM},
    {"description": (
        "The route must arrive at every city exactly once. For each destination city, exactly "
        "one direct leg coming into that city from some origin city is chosen."),
     "expected_pyomo": COLSUM},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "awktsp_mip_assign",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
