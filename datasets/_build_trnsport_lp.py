#!/usr/bin/env python
"""Builder for the trnsport_lp (canonical GAMS transport) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "trnsport_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"],
         "doc": "the canning plants that act as supply sources"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"],
         "doc": "the markets that act as demand destinations"},
    ],
    "params": [
        {"name": "a", "index": "i", "kind": "capacity",
         "doc": "the production capacity available at each plant, in cases"},
        {"name": "b", "index": "j", "kind": "demand",
         "doc": "the demand that must be met at each market, in cases"},
        {"name": "d", "index": "i,j", "kind": "distance",
         "doc": "the distance from each plant to each market, in thousands of miles"},
        {"name": "f", "index": "", "kind": "rate",
         "doc": "the freight rate, in dollars per case per thousand miles"},
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
    "We run a set of canning plants that ship a product to a set of markets. For every "
    "plant-to-market pair we decide how many cases to ship. Shipping a case over a route "
    "costs a freight rate that scales with the distance of that route, so longer routes "
    "are more expensive per case. The objective is to choose the shipment quantities that "
    "make the total transportation cost as small as possible."
)

COST = (
    "def cost_rule(model):\n"
    "    return model.z == sum(model.f * model.d[i, j] / 1000.0 * model.x[i, j] for i in model.i for j in model.j)\n"
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
    "The total transportation cost accumulates the cost of every shipment across all "
    "plant-to-market routes. For each route, the cost of moving a case is the freight rate "
    "applied over that route's distance, and the route's total cost is that per-case cost "
    "times the number of cases shipped on it. Set the total cost equal to the sum of these "
    "route costs over every plant and market."
)
SUPPLY_DESC = (
    "Each plant can only ship as much as it is able to produce. For each plant, the total "
    "amount shipped from it to all the markets must not exceed that plant's available capacity."
)
DEMAND_DESC = (
    "Every market's requirement must be covered. For each market, the total amount shipped "
    "into it from all the plants must be at least that market's demand."
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, the total transportation cost accumulates the cost of every shipment across all "
    "plant-to-market routes, where each route's cost is the freight rate applied over that "
    "route's distance times the cases shipped on it, and the total cost equals the sum of "
    "these route costs over every plant and market. "
    "Second, for each plant the total amount shipped from it to all the markets must not "
    "exceed that plant's available capacity. "
    "Finally, for each market the total amount shipped into it from all the plants must be "
    "at least that market's demand."
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
            "problem_id": "trnsport_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
