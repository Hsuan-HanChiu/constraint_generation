#!/usr/bin/env python
"""Builder for the bidsos_mip (SOS bid evaluation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "bidsos_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "v", "members": ["a", "b", "c", "d", "e"],
         "doc": "the set of vendors who have submitted bids"},
        {"name": "s", "members": ["nodeal", 0, 1, 2, 3, 4, 5],
         "doc": "the ordered set of bid segments; each vendor offers a piecewise-linear price-quantity schedule and the segments are the ordered breakpoints of that schedule, with 'nodeal' representing the option of purchasing nothing from the vendor"},
        {"name": "vs", "members": "list of valid (vendor, segment) pairs",
         "doc": "the set of valid vendor-segment bid possibilities; only some segments are defined for each vendor, so this set lists exactly which (vendor, segment) breakpoints actually exist"},
    ],
    "params": [
        {"name": "req", "index": "", "kind": "demand",
         "doc": "the total number of units that must be purchased across all vendors, a single scalar"},
        {"name": "qmax", "index": "vs", "kind": "quantity",
         "doc": "the quantity associated with each vendor-segment breakpoint, in units; the purchased quantity from a vendor is the interpolation of these breakpoint quantities using the purchase-level weights"},
        {"name": "cost", "index": "vs", "kind": "cost",
         "doc": "the total cost associated with each vendor-segment breakpoint, in dollars; the cost incurred from a vendor is the interpolation of these breakpoint costs using the purchase-level weights"},
    ],
    "vars": [
        {"name": "pl", "index": "vs", "domain": "NonNegativeReals",
         "doc": "the purchase-level interpolation weight placed on each vendor-segment breakpoint; the weights on a vendor's breakpoints select an operating point along that vendor's piecewise-linear schedule"},
        {"name": "c", "index": "", "domain": "Reals",
         "doc": "the total purchase cost across all vendors, in dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "c"},
}

NARRATIVE = (
    "We must purchase a required total number of units from a group of vendors, each of whom has "
    "submitted a bid in the form of a piecewise-linear schedule that relates the quantity bought "
    "to its total cost. For each vendor we decide an operating point along that vendor's schedule "
    "by choosing interpolation weights on the vendor's breakpoints, which determines how much is "
    "bought from that vendor and at what cost. The objective is to minimize the total purchase cost "
    "across all vendors."
)

DEMAND = (
    "def demand_rule(model):\n"
    "    return model.req == sum(model.qmax[v, s] * model.pl[v, s] for (v, s) in model.vs)\n"
    "model.demand = Constraint(rule=demand_rule)"
)
COSTDEF = (
    "def costdef_rule(model):\n"
    "    return model.c == sum(model.cost[v, s] * model.pl[v, s] for (v, s) in model.vs)\n"
    "model.costdef = Constraint(rule=costdef_rule)"
)
CONVEX = (
    "def convex_rule(model, vv):\n"
    "    return sum(model.pl[v, s] for (v, s) in model.vs if v == vv) == 1\n"
    "model.convex = Constraint(model.v, rule=convex_rule)"
)
WHOLESET = "\n".join([DEMAND, COSTDEF, CONVEX])

DESC_DEMAND = (
    "The total quantity purchased across all vendors must exactly meet the required amount. "
    "For every vendor-segment breakpoint, weight its quantity by the purchase level chosen for "
    "that breakpoint, and the sum of these weighted quantities over all breakpoints must equal "
    "the required total number of units."
)
DESC_COSTDEF = (
    "The total purchase cost is the cost obtained by interpolating along each vendor's schedule. "
    "For every vendor-segment breakpoint, weight its cost by the purchase level chosen for that "
    "breakpoint, and set the total cost equal to the sum of these weighted costs over all breakpoints."
)
DESC_CONVEX = (
    "For each vendor, the purchase-level weights placed on that vendor's breakpoints must sum to "
    "one, so that the chosen operating point is a valid interpolation along the vendor's schedule."
)

records = [
    {"description": DESC_DEMAND, "expected_pyomo": DEMAND},
    {"description": DESC_COSTDEF, "expected_pyomo": COSTDEF},
    {"description": DESC_CONVEX, "expected_pyomo": CONVEX},
    {"description": (
        "To build the complete model, enforce the following relationships in order. "
        "First, the weighted quantities across all vendor-segment breakpoints must add up to "
        "exactly the required total number of units to purchase. "
        "Second, the total purchase cost must equal the weighted costs summed over all "
        "vendor-segment breakpoints. "
        "Finally, for each vendor the purchase-level weights on that vendor's breakpoints must "
        "sum to one so that the chosen operating point is a valid interpolation along the "
        "vendor's schedule."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "bidsos_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
