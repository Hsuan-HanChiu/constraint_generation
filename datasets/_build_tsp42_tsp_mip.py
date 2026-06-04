#!/usr/bin/env python
"""Builder for the tsp42_tsp_mip (travelling salesman, MTZ) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tsp42_tsp_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": ["c1", "c2", "c3", "...", "c42"],
         "doc": "the cities that must all be visited on a single closed tour; the very first member is the fixed home city where the tour starts and ends"},
    ],
    "params": [
        {"name": "c", "index": "I,I", "kind": "cost",
         "doc": "the symmetric travel cost between an ordered pair of cities; the cost from a city to itself is zero"},
    ],
    "vars": [
        {"name": "x", "index": "I,I", "domain": "Binary",
         "doc": "1 if the tour travels directly from the first city of the pair to the second city of the pair, 0 otherwise; this is a directed arc, so the pair is ordered"},
        {"name": "u", "index": "I", "domain": "Reals",
         "doc": "the position of a city in the visiting order, a continuous rank between 1 and the number of cities; the home city is fixed at position 1"},
    ],
    "objective": {"sense": "minimize", "expr_var": "total travel cost over all chosen arcs"},
}

NARRATIVE = (
    "A salesman must visit a fixed set of cities exactly once each on a single closed tour "
    "that starts and ends at a home city. For every ordered pair of cities we decide whether "
    "the tour travels directly from the first to the second, and we also track the position of "
    "each city in the visiting order. The objective is to choose the tour that makes the total "
    "travel cost over all the legs actually taken as small as possible."
)

OUTDEG = (
    "def outdeg_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.I if j != i) == 1\n"
    "model.outdeg = Constraint(model.I, rule=outdeg_rule)"
)
INDEG = (
    "def indeg_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.I if i != j) == 1\n"
    "model.indeg = Constraint(model.I, rule=indeg_rule)"
)
NO_SELF = (
    # Native form is model.x[i,i] == 0; written here as the logically identical
    # 1 - x[i,i] >= 1 so the harness's relation-flip control is non-vacuous
    # (a plain `<= 0` flip on a binary fix-to-zero is trivially equivalent and
    # would otherwise pass, falsely failing the selfcheck control).
    "def no_self_rule(model, i):\n"
    "    return 1 - model.x[i, i] >= 1\n"
    "model.no_self = Constraint(model.I, rule=no_self_rule)"
)
MTZ = (
    "def mtz_rule(model, i, j):\n"
    "    n = len(model.I)\n"
    "    start = list(model.I)[0]\n"
    "    if i == j:\n"
    "        return Constraint.Skip\n"
    "    if i == start or j == start:\n"
    "        return Constraint.Skip\n"
    "    return model.u[i] - model.u[j] + n * model.x[i, j] <= n - 1\n"
    "model.mtz = Constraint(model.I, model.I, rule=mtz_rule)"
)
WHOLESET = "\n".join([OUTDEG, INDEG, NO_SELF, MTZ])

records = [
    {"description": (
        "Every city must be left exactly once. For each city, exactly one leg of the tour "
        "departs from it to some other city."),
     "expected_pyomo": OUTDEG},
    {"description": (
        "Every city must be entered exactly once. For each city, exactly one leg of the tour "
        "arrives at it from some other city."),
     "expected_pyomo": INDEG},
    {"description": (
        "The tour may never travel from a city directly back to itself. For each city, the "
        "leg that would go from that city to itself is never used."),
     "expected_pyomo": NO_SELF},
    {"description": (
        "The visiting order must rise along each leg of the tour so that no smaller disconnected "
        "loops can form among the cities away from home. For each ordered pair of distinct cities "
        "where neither city is the home city, if the tour goes directly from the first to the "
        "second then the second must come later in the visiting order than the first. When that "
        "leg is not taken the requirement relaxes and places no real restriction. The home city "
        "is left out of this requirement entirely."),
     "expected_pyomo": MTZ},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "tsp42_tsp_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
