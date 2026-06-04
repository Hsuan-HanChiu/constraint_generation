#!/usr/bin/env python
"""Builder for the asyncloop_lp (transportation with demand slack) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "asyncloop_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"], "doc": "the canning plants that ship the product"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"], "doc": "the markets that receive the product"},
        {"name": "s", "members": ["scen1", "scen2", "scen3", "scen4", "scen5", "scen6", "scen7", "scen8", "scen9", "scen10"],
         "doc": "the demand scenarios; not used by any constraint in this version"},
    ],
    "params": [
        {"name": "f", "index": "", "kind": "rate", "doc": "freight rate in dollars per case per thousand miles"},
        {"name": "pen", "index": "", "kind": "penalty",
         "doc": "penalty charged per case of unfilled demand, in thousands of dollars per case"},
        {"name": "a", "index": "i", "kind": "capacity", "doc": "shipping capacity of each plant, in cases"},
        {"name": "b", "index": "j", "kind": "demand", "doc": "demand of each market, in cases"},
        {"name": "d", "index": "i,j", "kind": "distance", "doc": "distance from a plant to a market, in thousands of miles"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "shipping cost per case on a plant-to-market route, in thousands of dollars; it is the freight rate times the distance divided by one thousand"},
        {"name": "bmult", "index": "s", "kind": "multiplier",
         "doc": "random demand multiplier for each scenario; not used by any constraint in this version"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the number of cases shipped from a plant to a market"},
        {"name": "slack", "index": "j", "domain": "NonNegativeReals",
         "doc": "the number of cases of demand left unfilled at a market"},
        {"name": "z", "index": "", "domain": "Reals", "doc": "total transportation cost in thousands of dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We ship a product from several canning plants to several markets. Each plant-to-market "
    "route has a known shipping cost per case that grows with distance. We decide how many "
    "cases to ship on each route, and we allow some of a market's demand to go unfilled at a "
    "penalty. The objective is to make the total cost as small as possible, counting both the "
    "shipping cost and the penalty for unfilled demand."
)

COST = (
    "def cost_constraint_rule(model):\n"
    "    return model.z == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j) "
    "+ model.pen * sum(model.slack[j] for j in model.j)\n"
    "model.cost_constraint = Constraint(rule=cost_constraint_rule)"
)
SUPPLY = (
    "def supply_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.j) <= model.a[i]\n"
    "model.supply = Constraint(model.i, rule=supply_rule)"
)
DEMAND = (
    "def demand_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.i) + model.slack[j] >= model.b[j]\n"
    "model.demand = Constraint(model.j, rule=demand_rule)"
)
WHOLESET = "\n".join([COST, SUPPLY, DEMAND])

records = [
    {"description": (
        "The total cost has two pieces. The first is the per-case shipping cost on each route "
        "multiplied by the cases shipped on it, summed over every plant and market. The second "
        "charges the unfilled-demand penalty per case for every case left unfilled, summed over "
        "all markets. Set the total cost variable equal to the sum of those two pieces."),
     "expected_pyomo": COST},
    {"description": (
        "No plant can ship out more than its capacity. For each plant, the total cases sent from "
        "it to all markets must not exceed that plant's capacity."),
     "expected_pyomo": SUPPLY},
    {"description": (
        "Each market's demand must be covered by what arrives plus whatever is left unfilled. For "
        "each market, the total cases shipped into it from all plants together with the unfilled "
        "amount at that market must be at least the market's demand."),
     "expected_pyomo": DEMAND},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "asyncloop_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
