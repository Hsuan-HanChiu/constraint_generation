#!/usr/bin/env python
"""Builder for the prodmix_lp (production mix) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "prodmix_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "desk", "members": ["d1", "d2", "d3", "d4"],
         "doc": "the types of desks the factory can produce"},
        {"name": "shop", "members": ["carpentry", "finishing"],
         "doc": "the workshops, each a production stage every desk must pass through"},
    ],
    "params": [
        {"name": "labor", "index": "shop, desk", "kind": "requirement",
         "doc": "the labor requirement in man-hours to make one unit of a given desk type in a given shop"},
        {"name": "caplim", "index": "shop", "kind": "capacity",
         "doc": "the labor capacity in man-hours available in each shop over the planning horizon"},
        {"name": "price", "index": "desk", "kind": "price",
         "doc": "the selling price in dollars earned per unit of each desk type"},
    ],
    "vars": [
        {"name": "mix", "index": "desk", "domain": "NonNegativeReals",
         "doc": "the number of units produced of each desk type"},
        {"name": "profit", "index": "", "domain": "Reals",
         "doc": "the total profit in dollars"},
    ],
    "objective": {"sense": "maximize", "expr_var": "profit"},
}

NARRATIVE = (
    "We run a furniture factory that produces several types of desks. Every desk must pass "
    "through each of our workshops, and each desk type consumes a known amount of labor in "
    "every workshop. We decide how many units of each desk type to make. Each desk type sells "
    "at a known price, and our goal is to choose the production amounts that make the total "
    "profit as large as possible."
)

CAP = (
    "def cap_rule(model, s):\n"
    "    return sum(model.labor[s, d] * model.mix[d] for d in model.desk) <= model.caplim[s]\n"
    "model.cap = Constraint(model.shop, rule=cap_rule)"
)
AP = (
    "def ap_rule(model):\n"
    "    return model.profit == sum(model.price[d] * model.mix[d] for d in model.desk)\n"
    "model.ap = Constraint(rule=ap_rule)"
)
WHOLESET = "\n".join([CAP, AP])

CAP_DESC = (
    "Each workshop has a limited amount of labor available. For each workshop, the total labor "
    "used across all desk types, where each desk type draws on that workshop's labor in "
    "proportion to how many units of it are produced, must not exceed the labor capacity of "
    "that workshop."
)
AP_DESC = (
    "The total profit is earned by selling the desks produced. Set the total profit equal to "
    "the sum across all desk types of the selling price of a desk type times the number of "
    "units of it produced."
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for each workshop, the total labor used across all desk types, where each desk type "
    "draws on that workshop's labor in proportion to how many units of it are produced, must not "
    "exceed the labor capacity of that workshop. "
    "Finally, set the total profit equal to the sum across all desk types of the selling price of "
    "a desk type times the number of units of it produced."
)

records = [
    {"description": CAP_DESC, "expected_pyomo": CAP},
    {"description": AP_DESC, "expected_pyomo": AP},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "prodmix_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
