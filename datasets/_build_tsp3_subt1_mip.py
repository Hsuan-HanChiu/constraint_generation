#!/usr/bin/env python
"""Builder for the tsp3_subt1_mip (TSP with subset subtour elimination) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tsp3_subt1_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": ["i1", "i2", "i3", "i4", "i5", "i6"],
         "doc": "the cities that must all be visited on the tour"},
        {"name": "N", "members": ["n1", "n2", "...", "n62"],
         "doc": "an index over every nonempty proper subset of the cities; each member names one such subset (sizes one through the number of cities minus one). The subsets are enumerated by taking, for every size from one up to one less than the total number of cities, all combinations of cities of that size in the natural order of the city list, and naming them n1, n2, and so on in that enumeration order. A constraint is written once per subset"},
    ],
    "params": [
        {"name": "c", "index": "I,I", "kind": "cost",
         "doc": "the travel cost of going directly from the first city to the second city of the pair; the diagonal (a city to itself) is zero"},
    ],
    "vars": [
        {"name": "x", "index": "I,I", "domain": "Binary",
         "doc": "one when the tour goes directly from the first city to the second city of the pair, zero otherwise; the diagonal entries (a city to itself) are fixed to zero so no city links to itself"},
        {"name": "z", "index": "", "domain": "NonNegativeReals",
         "doc": "the total travel cost of the chosen tour"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We plan a single round trip that visits a set of cities. For every ordered pair of cities we "
    "decide whether the trip travels directly from the first to the second. Each direct leg has a "
    "known travel cost. The objective is to make the total travel cost of the chosen route as small "
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
OBJDEF = (
    "def objdef_rule(model):\n"
    "    return model.z == sum(model.c[i, j] * model.x[i, j] for i in model.I for j in model.I)\n"
    "model.objdef = Constraint(rule=objdef_rule)"
)
SE1 = (
    "from itertools import combinations\n"
    "def _subset_map(model):\n"
    "    cities = list(model.I)\n"
    "    subsets = []\n"
    "    for r in range(1, len(cities)):\n"
    "        for comb in combinations(cities, r):\n"
    "            subsets.append(set(comb))\n"
    "    names = [f'n{idx+1}' for idx in range(len(subsets))]\n"
    "    return dict(zip(names, subsets))\n"
    "def se1_rule(model, nname):\n"
    "    S = _subset_map(model)[nname]\n"
    "    return sum(model.x[i, j] for i in S for j in S) <= max(0, len(S) - 1)\n"
    "model.se1 = Constraint(model.N, rule=se1_rule)"
)
WHOLESET = "\n".join([ROWSUM, COLSUM, OBJDEF, SE1])

records = [
    {"description": (
        "Every city must have exactly one outgoing direct leg. For each city, the legs that leave it "
        "to go directly to some city must together add up to exactly one."),
     "expected_pyomo": ROWSUM},
    {"description": (
        "Every city must have exactly one incoming direct leg. For each city, the legs that arrive at "
        "it coming directly from some city must together add up to exactly one."),
     "expected_pyomo": COLSUM},
    {"description": (
        "The total travel cost is the sum over every ordered pair of cities of that pair's travel cost "
        "counted only when the trip uses the direct leg between them. Set the total cost equal to this sum."),
     "expected_pyomo": OBJDEF},
    {"description": (
        "No proper group of cities may form its own closed loop separate from the rest of the route. "
        "For each such group of cities, the number of chosen direct legs that both start and end inside "
        "the group must be no more than one fewer than the number of cities in the group."),
     "expected_pyomo": SE1},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "tsp3_subt1_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
