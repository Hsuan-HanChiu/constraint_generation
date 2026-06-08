#!/usr/bin/env python
"""Builder for the epscmmip_mip (eps-constraint multi-objective 0/1 knapsack) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "epscmmip_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "J", "members": ["j1", "j2", "j3", "j4", "j5", "j6", "j7", "j8", "j9", "j10",
                                   "j11", "j12", "j13", "j14", "j15", "j16", "j17", "j18", "j19", "j20",
                                   "j21", "j22", "j23", "j24", "j25", "j26", "j27", "j28", "j29", "j30",
                                   "j31", "j32", "j33", "j34", "j35", "j36", "j37", "j38", "j39", "j40",
                                   "j41", "j42", "j43", "j44", "j45", "j46", "j47", "j48", "j49", "j50"],
         "doc": "the set of candidate items, each of which may be selected or not"},
        {"name": "I", "members": ["i1", "i2"],
         "doc": "the set of resource constraints; each member is one shared resource whose total consumption is capped"},
    ],
    "params": [
        {"name": "c1", "index": "J", "kind": "value",
         "doc": "the primary value contributed by selecting each item; the quantity being maximized"},
        {"name": "c2", "index": "J", "kind": "value",
         "doc": "the secondary value contributed by selecting each item; the quantity that must clear a floor"},
        {"name": "a", "index": "I,J", "kind": "usage",
         "doc": "the amount of each resource consumed by selecting each item; nonnegative"},
        {"name": "b", "index": "I", "kind": "capacity",
         "doc": "the total available amount of each resource; nonnegative"},
        {"name": "eps", "index": "", "kind": "threshold",
         "doc": "the minimum acceptable level of total secondary value; a single scalar floor that the selection must reach"},
    ],
    "vars": [
        {"name": "X", "index": "J", "domain": "Binary",
         "doc": "the selection indicator for each item; equals 1 if the item is selected and 0 otherwise"},
    ],
    "objective": {"sense": "maximize", "expr_var": "obj"},
}

NARRATIVE = (
    "We choose which items to select from a pool of candidates. Each item is either taken or left "
    "out. Every item contributes a primary value and a secondary value when selected, and selecting "
    "items consumes several shared resources, each of which is available only in limited supply. The "
    "objective is to maximize the total primary value of the selected items."
)

CON = (
    "def con_rule(model, i):\n"
    "    return sum(model.a[i, j] * model.X[j] for j in model.J) <= model.b[i]\n"
    "model.con = Constraint(model.I, rule=con_rule)"
)
EPSCON = (
    "def epscon_rule(model):\n"
    "    return sum(model.c2[j] * model.X[j] for j in model.J) >= model.eps\n"
    "model.epscon = Constraint(rule=epscon_rule)"
)
WHOLESET = "\n".join([CON, EPSCON])

records = [
    {"description": (
        "For each resource, the total amount consumed by the items that are selected must not exceed "
        "the amount of that resource available."),
     "expected_pyomo": CON},
    {"description": (
        "The total secondary value of the selected items must reach at least the required minimum "
        "level."),
     "expected_pyomo": EPSCON},
    {"description": (
        "To build the complete model, enforce the following relationships in order. "
        "First, for each resource the total amount consumed by the selected items must not exceed the "
        "amount of that resource available. "
        "Finally, the total secondary value of the selected items must reach at least the required "
        "minimum level."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "epscmmip_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
