#!/usr/bin/env python
"""Builder for the tsp3_subt2_mip (TSP with cutset subtour elimination) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tsp3_subt2_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": ["i1", "i2", "i3", "i4", "i5", "i6"],
         "doc": "the cities that must all be visited on a single closed tour"},
        {"name": "N", "members": ["n1", "...", "n62"],
         "doc": "an index over every group of cities that forms a nonempty strict subset of all the cities, that is every group that contains at least one city but not all of them; each member of this set names one such group, and the group of cities it stands for can be recovered by enumerating all such subsets in a fixed order"},
    ],
    "params": [
        {"name": "c", "index": "I,I", "kind": "cost",
         "doc": "the travel cost of going directly from the first city to the second city, for each ordered pair of cities; the cost from a city to itself is zero and is never used"},
    ],
    "vars": [
        {"name": "x", "index": "I,I", "domain": "Binary",
         "doc": "one if the tour goes directly from the first city to the second city, zero otherwise; the entry from a city to itself is fixed to zero so no city links to itself"},
        {"name": "z", "index": "", "domain": "NonNegativeReals",
         "doc": "the total travel cost of the chosen tour"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We plan a single round trip that visits every city exactly once and returns to the "
    "start. For each ordered pair of cities we decide whether the trip travels directly "
    "from the first to the second, and travelling a leg incurs a known cost that depends on "
    "the pair. The goal is to choose the legs so that the total travel cost of the trip is "
    "as small as possible."
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
SE2 = (
    "from itertools import combinations\n"
    "def se2_rule(model, nname):\n"
    "    cities = list(model.I)\n"
    "    subset_list = []\n"
    "    for r in range(1, len(cities)):\n"
    "        for comb in combinations(cities, r):\n"
    "            subset_list.append(set(comb))\n"
    "    names = [f'n{idx+1}' for idx in range(len(subset_list))]\n"
    "    subset_map = dict(zip(names, subset_list))\n"
    "    S = subset_map[nname]\n"
    "    Sc = set(cities) - S\n"
    "    return sum(model.x[i, j] for i in S for j in Sc) >= 1\n"
    "model.se2 = Constraint(model.N, rule=se2_rule)"
)
WHOLESET = "\n".join([ROWSUM, COLSUM, OBJDEF, SE2])

records = [
    {"description": (
        "Every city is left exactly once on the trip. For each city, exactly one direct leg "
        "departs from it to some other city."),
     "expected_pyomo": ROWSUM},
    {"description": (
        "Every city is entered exactly once on the trip. For each city, exactly one direct leg "
        "arrives at it from some other city."),
     "expected_pyomo": COLSUM},
    {"description": (
        "The total travel cost accumulates the cost of every leg that is actually used. Set the "
        "total cost equal to the sum, over all ordered pairs of cities, of the cost of going from "
        "the first city to the second multiplied by whether that leg is travelled."),
     "expected_pyomo": OBJDEF},
    {"description": (
        "The trip must form one connected round trip rather than splitting into several separate "
        "smaller loops. To rule this out, take any group of cities that is not empty and does not "
        "include all the cities. At least one used leg must go from a city inside that group to a "
        "city outside it, so the trip always crosses out of every such group. This must hold for "
        "every possible group of this kind."),
     "expected_pyomo": SE2},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "tsp3_subt2_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
