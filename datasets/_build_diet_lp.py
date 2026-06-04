#!/usr/bin/env python
"""Builder for the diet_lp (Stigler diet) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "diet_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "n", "members": ["calorie", "protein", "calcium", "iron", "vitamin-a",
                                   "vitamin-b1", "vitamin-b2", "niacin", "vitamin-c"],
         "doc": "the nutrients that the daily diet must supply"},
        {"name": "f", "members": ["wheat", "cornmeal", "cannedmilk", "margarine", "cheese",
                                  "peanut-b", "lard", "liver", "porkroast", "salmon",
                                  "greenbeans", "cabbage", "onions", "potatoes", "spinach",
                                  "sweet-pot", "peaches", "prunes", "limabeans", "navybeans"],
         "doc": "the foods that can be purchased for the diet"},
    ],
    "params": [
        {"name": "b", "index": "n", "kind": "requirement",
         "doc": "the required daily allowance of each nutrient, in that nutrient's own units"},
        {"name": "a", "index": "f,n", "kind": "nutrition",
         "doc": "the amount of a nutrient obtained per dollar spent on a food, in that nutrient's own units per dollar"},
    ],
    "vars": [
        {"name": "x", "index": "f", "domain": "NonNegativeReals",
         "doc": "the number of dollars spent daily on each food"},
        {"name": "cost", "index": "", "domain": "NonNegativeReals",
         "doc": "the total daily food bill, in dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We plan a daily diet by choosing how many dollars to spend on each available food. "
    "Each food delivers known amounts of various nutrients per dollar spent. We decide the "
    "dollar amount to spend on each food. The objective is to make the total daily food bill "
    "as small as possible."
)

NB = (
    "def nutrient_balance_rule(model, n):\n"
    "    return sum(model.a[f, n] * model.x[f] for f in model.f) >= model.b[n]\n"
    "model.nb = Constraint(model.n, rule=nutrient_balance_rule)"
)
CB = (
    "def cost_balance_rule(model):\n"
    "    return model.cost == sum(model.x[f] for f in model.f)\n"
    "model.cb = Constraint(rule=cost_balance_rule)"
)
WHOLESET = "\n".join([NB, CB])

records = [
    {"description": (
        "Every nutrient must be supplied in at least its required daily allowance. For each "
        "nutrient, add up the amount of that nutrient delivered by every food given how many "
        "dollars are spent on it, and require that total to be at least the required allowance "
        "for that nutrient."),
     "expected_pyomo": NB},
    {"description": (
        "The total daily food bill is the sum of the dollars spent on all the foods. Set the "
        "cost variable equal to that total."),
     "expected_pyomo": CB},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "diet_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
