#!/usr/bin/env python
"""Builder for the bid_mip (bid evaluation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "bid_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "v", "members": ["a", "b", "c", "d", "e"],
         "doc": "the vendors that can supply the commodity"},
        {"name": "s", "members": [1, 2, 3, 4],
         "doc": "the price segments a vendor may offer, given as ascending tier numbers; a higher segment number is a higher-volume tier"},
        {"name": "vs", "members": [["a", 1], ["b", 1], ["b", 2], ["b", 3], ["b", 4], ["c", 1], ["d", 1], ["e", 1], ["e", 2]],
         "doc": "the set of valid vendor-segment deals that are actually offered; a vendor may offer several segments and only the pairs listed here are available to choose"},
    ],
    "params": [
        {"name": "req", "index": "", "kind": "demand",
         "doc": "the total quantity of the commodity that must be procured, in units"},
        {"name": "setup", "index": "vs", "kind": "cost",
         "doc": "the fixed setup cost charged in dollars for selecting a given vendor-segment deal, incurred once if that deal is chosen"},
        {"name": "price", "index": "vs", "kind": "price",
         "doc": "the unit purchase price in dollars per unit for a given vendor-segment deal"},
        {"name": "qmin", "index": "vs", "kind": "bound",
         "doc": "the minimum quantity in units that must be purchased on a vendor-segment deal if that deal is selected"},
        {"name": "qmax", "index": "vs", "kind": "bound",
         "doc": "the maximum quantity in units that may be purchased on a vendor-segment deal"},
    ],
    "vars": [
        {"name": "c", "index": "", "domain": "NonNegativeReals",
         "doc": "the total procurement cost over all chosen deals, in dollars"},
        {"name": "pl", "index": "vs", "domain": "NonNegativeReals",
         "doc": "the quantity in units purchased on each vendor-segment deal"},
        {"name": "plb", "index": "vs", "domain": "Binary",
         "doc": "the binary decision for each vendor-segment deal, equal to one if that deal is selected and zero otherwise"},
    ],
    "objective": {"sense": "minimize", "expr_var": "c"},
}

NARRATIVE = (
    "We must procure a fixed total quantity of a commodity from a set of vendors. Each vendor "
    "offers one or more deals, where a deal is a price segment with its own fixed setup cost, "
    "unit price, and quantity limits. For each available vendor-segment deal we decide whether "
    "to select it and how much to purchase on it. Choosing a deal incurs its setup cost, and "
    "every purchased unit is charged at that deal's unit price. The objective is to minimize the "
    "total procurement cost, which combines the setup costs of the selected deals and the unit "
    "purchase costs of the quantities bought."
)

DEMAND = (
    "def demand_rule(model):\n"
    "    return model.req == sum(model.pl[vs] for vs in model.vs)\n"
    "model.demand = Constraint(rule=demand_rule)"
)
COSTDEF = (
    "def costdef_rule(model):\n"
    "    return model.c == sum(model.price[vs] * model.pl[vs] + model.setup[vs] * model.plb[vs] for vs in model.vs)\n"
    "model.costdef = Constraint(rule=costdef_rule)"
)
MINPL = (
    "def minpl_rule(model, v, s):\n"
    "    return model.pl[v, s] >= model.qmin[v, s] * model.plb[v, s]\n"
    "model.minpl = Constraint(model.vs, rule=minpl_rule)"
)
MAXPL = (
    "def maxpl_rule(model, v, s):\n"
    "    return model.pl[v, s] <= model.qmax[v, s] * model.plb[v, s]\n"
    "model.maxpl = Constraint(model.vs, rule=maxpl_rule)"
)
ONEONLY = (
    "def oneonly_rule(model, v):\n"
    "    terms = [model.plb[v, s] for s in model.s if (v, s) in model.vs]\n"
    "    if not terms:\n"
    "        return Constraint.Skip\n"
    "    return sum(terms) <= 1\n"
    "model.oneonly = Constraint(model.v, rule=oneonly_rule)"
)
WHOLESET = "\n".join([DEMAND, COSTDEF, MINPL, MAXPL, ONEONLY])

records = [
    {"description": (
        "The total quantity purchased across all available vendor-segment deals must exactly meet "
        "the required procurement amount. Add up the quantity bought on every deal and set that sum "
        "equal to the total requirement."),
     "expected_pyomo": DEMAND},
    {"description": (
        "The total procurement cost accounts for both the per-unit purchase charges and the fixed "
        "setup charges. For each available deal, charge its unit price on every unit purchased and "
        "charge its setup cost once if that deal is selected. Set the total cost equal to the sum of "
        "these amounts over all deals."),
     "expected_pyomo": COSTDEF},
    {"description": (
        "Each deal carries a minimum purchase quantity that applies only when the deal is selected. "
        "For every available vendor-segment deal, the quantity purchased on it must be at least its "
        "minimum quantity when the deal is chosen, and may be nothing when it is not chosen."),
     "expected_pyomo": MINPL},
    {"description": (
        "Each deal carries a maximum purchase quantity that applies only when the deal is selected. "
        "For every available vendor-segment deal, the quantity purchased on it must not exceed its "
        "maximum quantity when the deal is chosen, and must be nothing when it is not chosen."),
     "expected_pyomo": MAXPL},
    {"description": (
        "A vendor's segments are alternatives, so at most one deal may be accepted from any single "
        "vendor. For each vendor, the number of selected deals among that vendor's available segments "
        "must be no more than one."),
     "expected_pyomo": ONEONLY},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "bid_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
