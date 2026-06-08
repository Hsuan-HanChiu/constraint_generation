#!/usr/bin/env python
"""Builder for the trnsgrid_lp (grid transportation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "trnsgrid_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"],
         "doc": "the supply locations, the canning plants that ship product out"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"],
         "doc": "the demand locations, the markets that receive product"},
    ],
    "params": [
        {"name": "a", "index": "i", "kind": "capacity",
         "doc": "the production capacity available at each plant, in cases"},
        {"name": "b", "index": "j", "kind": "demand",
         "doc": "the demand that must be met at each market, in cases"},
        {"name": "d", "index": "i,j", "kind": "distance",
         "doc": "the distance from a plant to a market, in thousands of miles"},
        {"name": "f", "index": "", "kind": "freight",
         "doc": "the freight rate in dollars per case per thousand miles"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the transport cost per case shipped from a plant to a market, in thousands of dollars per case; derived from the freight rate and distance"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the quantity shipped from a plant to a market, in cases"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total transportation cost over all shipments, in thousands of dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We run a distribution network of canning plants that ship product to a set of markets. "
    "The decision is how many cases to ship along each plant-to-market route, and we also track "
    "the total transportation cost that results. Shipping a case along a route costs an amount "
    "that grows with the distance and the freight rate. The objective is to make the total "
    "transportation cost as small as possible."
)

COST = (
    "def cost_rule(model):\n"
    "    return model.z == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)\n"
    "model.cost = Constraint(rule=cost_rule)"
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
WHOLESET = "\n".join([COST, SUPPLY, DEMAND])

COST_DESC = (
    "Set the total transportation cost equal to the cost of all shipments, where each route's "
    "shipment is valued at its per-case transport cost and these are added up over every "
    "plant-to-market route."
)
SUPPLY_DESC = (
    "For each plant, the total quantity shipped out of that plant to all markets must not exceed "
    "the production capacity available at that plant."
)
DEMAND_DESC = (
    "For each market, the total quantity shipped into that market from all plants must be at least "
    "the demand at that market."
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, " + COST_DESC[0].lower() + COST_DESC[1:] + " "
    "Second, " + SUPPLY_DESC[0].lower() + SUPPLY_DESC[1:] + " "
    "Finally, " + DEMAND_DESC[0].lower() + DEMAND_DESC[1:]
)

records = [
    {"description": COST_DESC, "expected_pyomo": COST},
    {"description": SUPPLY_DESC, "expected_pyomo": SUPPLY},
    {"description": DEMAND_DESC, "expected_pyomo": DEMAND},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "trnsgrid_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
