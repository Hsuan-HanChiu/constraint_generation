#!/usr/bin/env python
"""Builder for the feasopt1_lp (FeasOpt elastic transportation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "feasopt1_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"],
         "doc": "the canning plants, which act as the supply nodes that ship product out"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"],
         "doc": "the markets, which act as the demand nodes that need product delivered"},
    ],
    "params": [
        {"name": "a", "index": "i", "kind": "capacity",
         "doc": "the production capacity available at each plant, in cases"},
        {"name": "b", "index": "j", "kind": "demand",
         "doc": "the requirement that must be met at each market, in cases, already inflated by twenty percent above the nominal level"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the per-case transport cost from a plant to a market, in thousands of dollars per case"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the quantity shipped from a plant to a market, in cases"},
        {"name": "r", "index": "j", "domain": "NonNegativeReals",
         "doc": "the amount by which a market's requirement is allowed to fall short, that is the relaxation or slack granted to that market's demand, in cases"},
    ],
    "objective": {"sense": "minimize", "expr_var": "total demand relaxation summed over all markets"},
}

NARRATIVE = (
    "We run a transportation operation that ships a product from a set of plants to a set of "
    "markets. Each plant has a limited amount it can produce, and each market has a requirement "
    "it would like met. Total demand exceeds total supply, so the markets cannot all be fully "
    "served. For each market we decide how much to ship in from each plant, and we also allow "
    "each market's requirement to be relaxed by some amount so that a feasible plan exists. "
    "The objective is to make the total amount of relaxation granted across all markets as small "
    "as possible, finding the least shortfall that restores feasibility."
)

SUPPLY = (
    "def supply_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.j) <= model.a[i]\n"
    "model.supply = Constraint(model.i, rule=supply_rule)"
)
DEMAND = (
    "def demand_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.i) + model.r[j] >= model.b[j]\n"
    "model.demand = Constraint(model.j, rule=demand_rule)"
)
WHOLESET = "\n".join([SUPPLY, DEMAND])

records = [
    {"description": (
        "Each plant can only ship out as much as it is able to produce. For each plant, the total "
        "quantity shipped from that plant to all of the markets must not exceed that plant's "
        "available capacity."),
     "expected_pyomo": SUPPLY},
    {"description": (
        "Each market's requirement has to be covered, but we permit it to be met short by granting "
        "that market some relaxation. For each market, the total quantity shipped into it from all "
        "of the plants, together with the relaxation granted to that market, must be at least that "
        "market's requirement."),
     "expected_pyomo": DEMAND},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, for each "
        "plant, the total quantity shipped from that plant to all markets must not exceed that "
        "plant's available capacity. Finally, for each market, the total quantity shipped into it "
        "from all plants, together with the relaxation granted to that market, must be at least that "
        "market's requirement."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "feasopt1_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
