#!/usr/bin/env python
"""Builder for the tsp4_assign_mip (assignment-relaxation TSP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tsp4_assign_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": ["i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "i9", "i10", "i11", "i12"],
         "doc": "the cities to be visited; an arc runs from an origin city to a destination city, both drawn from this same set"},
    ],
    "params": [
        {"name": "c", "index": "I,I", "kind": "cost",
         "doc": "the travel cost of going directly from the first city to the second city, in cost units per arc"},
    ],
    "vars": [
        {"name": "x", "index": "I,I", "domain": "Binary",
         "doc": "takes the value 1 when the direct arc from the first city to the second city is used, and 0 otherwise"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We plan a tour over a set of cities, choosing for each ordered pair of cities whether the "
    "direct arc from one to the other is used. Every used arc carries a known travel cost. The "
    "objective is to choose the arcs so that the total travel cost of all chosen arcs is as small "
    "as possible."
)

ROWSUM = (
    "def rowsum_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.I) == 1\n"
    "model.rowsum = Constraint(model.I, rule=rowsum_rule)"
)
COLSUM = (
    "def colsum_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.I) == 1\n"
    "model.colsum = Constraint(model.I, rule=colsum_rule)"
)
NO_SELF = (
    "def no_self_rule(model, i):\n"
    "    return model.x[i, i] <= 0\n"
    "model.no_self = Constraint(model.I, rule=no_self_rule)"
)
WHOLESET = "\n".join([ROWSUM, COLSUM, NO_SELF])

records = [
    {"description": (
        "Each city is left exactly once. For every city, considering all the arcs that start at "
        "that city and go to any city, exactly one of those arcs is used."),
     "expected_pyomo": ROWSUM},
    {"description": (
        "Each city is reached exactly once. For every city, considering all the arcs that come "
        "into that city from any city, exactly one of those arcs is used."),
     "expected_pyomo": COLSUM},
    {"description": (
        "No city connects directly to itself. For every city, the arc that starts and ends at "
        "that same city is never used."),
     "expected_pyomo": NO_SELF},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "tsp4_assign_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
