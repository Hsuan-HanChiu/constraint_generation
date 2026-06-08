#!/usr/bin/env python
"""Builder for the embmiex1_lp (transportation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "embmiex1_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"],
         "doc": "the canning plants where product is produced and shipped from"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"],
         "doc": "the markets where product is demanded and shipped to"},
    ],
    "params": [
        {"name": "a", "index": "i", "kind": "capacity",
         "doc": "the production capacity available at each plant, in cases"},
        {"name": "b", "index": "j", "kind": "demand",
         "doc": "the quantity required at each market, in cases"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the transport cost of shipping from a plant to a market, in thousands of dollars per case"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the amount shipped from each plant to each market, in cases"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total transportation cost over all plant-market shipments, in thousands of dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We run a distribution operation that ships a product from a set of plants to a set of "
    "markets. For every plant and market we decide how much to ship along that route. Each "
    "plant can only supply so much, each market needs a certain amount delivered, and every "
    "route carries a known per-case shipping cost. The objective is to make the total "
    "transportation cost across all routes as small as possible."
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
COST = (
    "def cost_rule(model):\n"
    "    return model.z == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)\n"
    "model.cost = Constraint(rule=cost_rule)"
)
WHOLESET = "\n".join([SUPPLY, DEMAND, COST])

SUPPLY_DESC = (
    "For each plant, the total amount shipped out of that plant to all markets cannot "
    "exceed the production capacity available at that plant."
)
DEMAND_DESC = (
    "For each market, the total amount shipped into that market from all plants must be "
    "at least the quantity required at that market."
)
COST_DESC = (
    "The total transportation cost is the sum over every plant and market route of the "
    "amount shipped along that route valued at its per-case shipping cost. Set the total "
    "cost equal to this sum."
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for each plant the total shipped out to all markets stays within that plant's "
    "production capacity. "
    "Second, for each market the total shipped in from all plants meets that market's "
    "required quantity. "
    "Finally, define the total transportation cost as the sum across every route of the "
    "amount shipped valued at its per-case shipping cost."
)

records = [
    {"description": SUPPLY_DESC, "expected_pyomo": SUPPLY},
    {"description": DEMAND_DESC, "expected_pyomo": DEMAND},
    {"description": COST_DESC, "expected_pyomo": COST},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "embmiex1_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
