#!/usr/bin/env python
"""Builder for the decomp_lp97 (transportation with shipping + tanker cost)
constraint-generation dataset. Run with plain python to (re)generate the JSONL."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "decomp_lp97_constraint_gen.jsonl"

# ---- shared model vocabulary (same components block in every record) ----
COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["plant-1", "plant-2"],
         "doc": "the plants that ship the product out"},
        {"name": "j", "members": ["term-1", "term-2", "term-3", "term-4"],
         "doc": "the terminals that receive the product"},
    ],
    "params": [
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "shipping cost per unit on a plant-to-terminal route, in dollars per unit"},
        {"name": "t", "index": "i,j", "kind": "rate",
         "doc": "number of tankers needed per unit shipped on a plant-to-terminal route; most routes need none"},
        {"name": "a", "index": "i", "kind": "availability",
         "doc": "amount of product available at each plant, in units"},
        {"name": "b", "index": "j", "kind": "requirement",
         "doc": "amount of product required at each terminal, in units"},
        {"name": "ctank", "index": "", "kind": "cost",
         "doc": "cost charged per tanker used, in dollars per tanker"},
        {"name": "cship", "index": "", "kind": "cost",
         "doc": "weight applied to the shipping cost component when forming total cost, a unitless multiplier"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the number of units shipped from a plant to a terminal"},
        {"name": "cost", "index": "", "domain": "NonNegativeReals",
         "doc": "total cost of the plan, in dollars"},
        {"name": "tank", "index": "", "domain": "NonNegativeReals",
         "doc": "total number of tankers used across all routes"},
        {"name": "ship", "index": "", "domain": "NonNegativeReals",
         "doc": "total shipping cost across all routes, in dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We move a product from several plants to several terminals. Each plant-to-terminal "
    "route has a known shipping cost per unit, and some routes also need a number of "
    "tankers per unit shipped. We decide how many units to send on each route. We also "
    "track the total shipping cost, the total number of tankers used, and the overall "
    "cost of the plan. The objective is to make the overall cost as small as possible."
)

# ---- ground-truth Pyomo for each constraint (self-contained over model.* only) ----
DEFCOST = (
    "model.defcost = Constraint(expr=model.cost == model.cship * model.ship "
    "+ model.ctank * model.tank)"
)

DEFSHIP = (
    "model.defship = Constraint(expr=model.ship == "
    "sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j))"
)

DEFTANK = (
    "model.deftank = Constraint(expr=model.tank == "
    "sum(model.t[i, j] * model.x[i, j] for i in model.i for j in model.j))"
)

SUPPLY = (
    "def supply_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.j) <= model.a[i]\n"
    "model.supply = Constraint(model.i, rule=supply_rule)"
)

DEMAND = (
    "def demand_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.i) >= model.b[j]\n"
    "model.demand = Constraint(model.j, rule=demand_rule)"
)

WHOLESET = "\n".join([DEFCOST, DEFSHIP, DEFTANK, SUPPLY, DEMAND])

records = [
    {
        "description": (
            "The overall cost of the plan combines the total shipping cost and the "
            "total tanker usage. Take the total shipping cost weighted by its multiplier "
            "and add the total tankers used priced at the per-tanker charge, and set the "
            "overall cost equal to that sum."
        ),
        "expected_pyomo": DEFCOST,
    },
    {
        "description": (
            "The total shipping cost adds up the per-unit shipping cost on each route "
            "multiplied by the units sent on that route, summed over every plant and "
            "terminal. Set the total shipping cost equal to that amount."
        ),
        "expected_pyomo": DEFSHIP,
    },
    {
        "description": (
            "The total number of tankers used adds up the tankers needed per unit on "
            "each route multiplied by the units sent on that route, summed over every "
            "plant and terminal. Set the total tankers used equal to that amount."
        ),
        "expected_pyomo": DEFTANK,
    },
    {
        "description": (
            "No plant can send out more than what it has available. For each plant, the "
            "total units shipped from it to all terminals must not exceed the amount "
            "available at that plant."
        ),
        "expected_pyomo": SUPPLY,
    },
    {
        "description": (
            "Every terminal's requirement must be met. For each terminal, the total "
            "units shipped into it from all plants must be at least the amount required "
            "at that terminal."
        ),
        "expected_pyomo": DEMAND,
    },
    {
        "description": "Generate the complete constraint set for this model.",
        "expected_pyomo": WHOLESET,
    },
]

with open(OUT, "w") as f:
    for r in records:
        rec = {
            "problem_id": "decomp_lp97",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {OUT} ({len(records)} records)")
