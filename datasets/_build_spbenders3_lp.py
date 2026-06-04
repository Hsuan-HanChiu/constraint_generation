#!/usr/bin/env python
"""Builder for the spbenders3_lp (stochastic transport, extensive form) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "spbenders3_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": ["f1", "f2", "f3"],
         "doc": "the factories that produce and ship product"},
        {"name": "J", "members": ["d1", "d2", "d3", "d4", "d5"],
         "doc": "the distribution centers, also called markets, that receive product and serve demand"},
        {"name": "S", "members": ["lo", "mid", "hi"],
         "doc": "the demand scenarios, each a possible realization of market demand with its own probability"},
    ],
    "params": [
        {"name": "capacity", "index": "I", "kind": "capacity",
         "doc": "the maximum quantity each factory can produce, in units"},
        {"name": "prodcost", "index": "", "kind": "cost",
         "doc": "the production cost per unit produced at any factory, in dollars per unit"},
        {"name": "price", "index": "", "kind": "price",
         "doc": "the sales price earned per unit sold at any market, in dollars per unit"},
        {"name": "wastecost", "index": "", "kind": "cost",
         "doc": "the cost per unit of product that is received at a market but not sold, in dollars per unit"},
        {"name": "transcost", "index": "I,J", "kind": "cost",
         "doc": "the transportation cost per unit shipped from a factory to a distribution center, in dollars per unit"},
        {"name": "scen_prob", "index": "S", "kind": "probability",
         "doc": "the probability of each demand scenario; the probabilities across scenarios sum to one"},
        {"name": "scen_demand", "index": "S,J", "kind": "demand",
         "doc": "the demand at each distribution center under each scenario, in units"},
    ],
    "vars": [
        {"name": "ship", "index": "I,J", "domain": "NonNegativeReals",
         "doc": "the quantity shipped from each factory to each distribution center"},
        {"name": "product", "index": "I", "domain": "NonNegativeReals",
         "doc": "the quantity produced at each factory"},
        {"name": "received", "index": "J", "domain": "NonNegativeReals",
         "doc": "the quantity that arrives at each distribution center; this is decided before the demand scenario is known and is the same across all scenarios"},
        {"name": "sales", "index": "S,J", "domain": "NonNegativeReals",
         "doc": "the quantity sold at each distribution center under each scenario"},
        {"name": "waste", "index": "S,J", "domain": "NonNegativeReals",
         "doc": "the quantity received at each distribution center that goes unsold under each scenario, treated as overstock"},
    ],
    "objective": {"sense": "maximize", "expr_var": "obj"},
}

NARRATIVE = (
    "We run a production and distribution network where several factories make a product and ship it "
    "to distribution centers that serve uncertain market demand. Demand is captured by a set of scenarios, "
    "each with its own probability. Before demand is known we decide how much each factory produces and how "
    "much it ships to each distribution center, which fixes how much arrives at each center. Once a scenario's "
    "demand is revealed, we decide how much of the arriving product is sold and how much goes unsold as waste. "
    "The objective is to maximize the expected profit, where profit credits sales revenue, charges for unsold "
    "waste, and subtracts the transportation and production costs, with the sales-and-waste part averaged over "
    "the scenarios by their probabilities."
)

PRODUCTION = (
    "def production_rule(model, i):\n"
    "    return model.product[i] == sum(model.ship[i, j] for j in model.J)\n"
    "model.production = Constraint(model.I, rule=production_rule)"
)
CAPACITY_CON = (
    "def capacity_con_rule(model, i):\n"
    "    return model.product[i] <= model.capacity[i]\n"
    "model.capacity_con = Constraint(model.I, rule=capacity_con_rule)"
)
RECEIVE = (
    "def receive_rule(model, j):\n"
    "    return model.received[j] == sum(model.ship[i, j] for i in model.I)\n"
    "model.receive = Constraint(model.J, rule=receive_rule)"
)
SELLING = (
    "def selling_rule(model, s, j):\n"
    "    return model.sales[s, j] + model.waste[s, j] == model.received[j]\n"
    "model.selling = Constraint(model.S, model.J, rule=selling_rule)"
)
MARKET = (
    "def market_rule(model, s, j):\n"
    "    return model.sales[s, j] <= model.scen_demand[s, j]\n"
    "model.market = Constraint(model.S, model.J, rule=market_rule)"
)
WHOLESET = "\n".join([PRODUCTION, CAPACITY_CON, RECEIVE, SELLING, MARKET])

records = [
    {"description": (
        "Each factory's output must match everything it ships out. For each factory, the quantity it produces "
        "equals the total quantity it ships across all the distribution centers."),
     "expected_pyomo": PRODUCTION},
    {"description": (
        "No factory can produce more than its production limit. For each factory, the quantity produced must "
        "not exceed that factory's capacity."),
     "expected_pyomo": CAPACITY_CON},
    {"description": (
        "Each distribution center receives whatever the factories send it. For each distribution center, the "
        "quantity that arrives there equals the total quantity shipped to it from all the factories."),
     "expected_pyomo": RECEIVE},
    {"description": (
        "Whatever arrives at a distribution center is either sold or left unsold, in every scenario. For each "
        "distribution center under each scenario, the quantity sold plus the quantity wasted equals the quantity "
        "that arrived at that center."),
     "expected_pyomo": SELLING},
    {"description": (
        "Sales at a distribution center cannot exceed the demand there. For each distribution center under each "
        "scenario, the quantity sold must not exceed that scenario's demand at that center."),
     "expected_pyomo": MARKET},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "spbenders3_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
