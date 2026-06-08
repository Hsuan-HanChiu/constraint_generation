#!/usr/bin/env python
"""Builder for the gussgrid_lp (GUSS grid transportation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "gussgrid_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"],
         "doc": "the canning plants that ship product out"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"],
         "doc": "the markets that receive product"},
    ],
    "params": [
        {"name": "a", "index": "i", "kind": "capacity",
         "doc": "the production capacity of each plant, in cases; a plant cannot ship out more than this"},
        {"name": "b", "index": "j", "kind": "demand",
         "doc": "the demand at each market, in cases; each market must receive at least this much"},
        {"name": "d", "index": "i,j", "kind": "distance",
         "doc": "the distance from each plant to each market, in thousands of miles"},
        {"name": "f", "index": "", "kind": "freight",
         "doc": "the freight rate, in dollars per case per thousand miles"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the transport cost per case shipped from a plant to a market, in thousands of dollars per case; derived from the freight rate and the distance"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the quantity shipped from each plant to each market, in cases"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total transportation cost over all shipments, in thousands of dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We run a network of canning plants that ship product to a set of markets. We decide how "
    "many cases to ship from each plant to each market. Every plant-to-market lane carries a "
    "transport cost per case that depends on how far apart the plant and market are. Our goal "
    "is to make the total transportation cost over all shipments as small as possible."
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

records = [
    {"description": (
        "The total transportation cost gathers the cost of every shipment across the whole network. "
        "Value each plant-to-market shipment at its per-case transport cost, add these up over all "
        "plant and market combinations, and set the total transportation cost equal to that sum."),
     "expected_pyomo": COST},
    {"description": (
        "Each plant can only ship out as much as it can produce. For each plant, the total quantity "
        "shipped from that plant to all markets must not exceed that plant's capacity."),
     "expected_pyomo": SUPPLY},
    {"description": (
        "Every market must have its demand met. For each market, the total quantity shipped into that "
        "market from all plants must be at least that market's demand."),
     "expected_pyomo": DEMAND},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, account for "
        "the total transportation cost as the combined cost of every shipment across the whole network. "
        "Second, keep each plant from shipping out more than it can produce. Finally, make sure every "
        "market receives at least as much as it demands."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "gussgrid_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
