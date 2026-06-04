#!/usr/bin/env python
"""Builder for the gussex1_lp (transportation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "gussex1_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"], "doc": "the plants that ship the product"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"], "doc": "the markets that receive the product"},
    ],
    "params": [
        {"name": "f", "index": "", "kind": "rate", "doc": "freight rate in dollars per case per thousand miles"},
        {"name": "a", "index": "i", "kind": "capacity", "doc": "shipping capacity of each plant, in cases"},
        {"name": "b", "index": "j", "kind": "demand", "doc": "demand of each market, in cases"},
        {"name": "d", "index": "i,j", "kind": "distance", "doc": "distance from a plant to a market, in thousands of miles"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "shipping cost per case on a plant-to-market route, in thousands of dollars; it is the freight rate times the distance"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the number of cases shipped from a plant to a market"},
        {"name": "z", "index": "", "domain": "Reals", "doc": "total transportation cost in thousands of dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We ship a product from several plants to several markets. Each plant-to-market "
    "route has a known shipping cost per case that grows with distance. We decide how "
    "many cases to ship on each route. The objective is to make the total shipping "
    "cost as small as possible."
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
        "The total transportation cost is the per-case shipping cost on each route "
        "multiplied by the number of cases shipped on it, summed over every "
        "plant and market. Set the cost variable equal to that total."),
     "expected_pyomo": COST},
    {"description": (
        "No plant can ship out more than its capacity. For each plant, the total "
        "cases sent from it to all markets must not exceed that plant's capacity."),
     "expected_pyomo": SUPPLY},
    {"description": (
        "Every market's demand must be met. For each market, the total cases shipped "
        "into it from all plants must be at least that market's demand."),
     "expected_pyomo": DEMAND},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "gussex1_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
