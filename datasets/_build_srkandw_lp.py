#!/usr/bin/env python
"""Builder for the srkandw_lp (stochastic refinery blending) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "srkandw_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["raw-1", "raw-2"],
         "doc": "the raw materials available for purchase"},
        {"name": "j", "members": ["p-1", "p-2"],
         "doc": "the finished products that must be supplied to meet demand"},
        {"name": "t", "members": ["time-1", "time-2"],
         "doc": "the time periods in the planning horizon"},
        {"name": "n", "members": ["n-1", "n-2", "n-3", "n-4", "n-5", "n-6",
                                   "n-7", "n-8", "n-9", "n-10", "n-11", "n-12"],
         "doc": "the nodes of the scenario tree, each a possible realization of uncertain demand"},
        {"name": "tn", "members": [["time-1", "n-1"], ["time-1", "n-2"], ["time-1", "n-3"],
                                   ["time-2", "n-4"], ["time-2", "n-5"], ["time-2", "n-6"],
                                   ["time-2", "n-7"], ["time-2", "n-8"], ["time-2", "n-9"],
                                   ["time-2", "n-10"], ["time-2", "n-11"], ["time-2", "n-12"]],
         "doc": "the valid pairs of time period and scenario-tree node; a node belongs to exactly one period, so this set says which period each node sits in"},
    ],
    "params": [
        {"name": "c", "index": "i", "kind": "cost",
         "doc": "the present purchase cost per unit of each raw material, in dollars per unit"},
        {"name": "a", "index": "j,i", "kind": "yield",
         "doc": "the amount of product obtained per unit of raw material, giving for each product and raw material the yield of that product from one unit of that material"},
        {"name": "f", "index": "j,t", "kind": "cost",
         "doc": "the cost per unit of meeting product demand by outsourcing in a given period, in dollars per unit"},
        {"name": "b", "index": "", "kind": "capacity",
         "doc": "the total raw-material inventory capacity, an upper bound on the combined quantity of all raw materials purchased across the whole horizon, in units"},
        {"name": "sprob", "index": "n", "kind": "probability",
         "doc": "the probability of each scenario-tree node, used to weight outsourcing costs into an expected value"},
        {"name": "dem", "index": "j,n", "kind": "demand",
         "doc": "the demand for each product at each scenario-tree node, in units; this is the stochastic quantity that varies across nodes"},
    ],
    "vars": [
        {"name": "x", "index": "i,t", "domain": "NonNegativeReals",
         "doc": "the quantity of each raw material purchased for use in each time period"},
        {"name": "y", "index": "j,tn", "domain": "NonNegativeReals",
         "doc": "the quantity of each product obtained by outsourcing, for each valid period-node pair"},
        {"name": "cost", "index": "", "domain": "Reals",
         "doc": "the total expected cost over the horizon, in dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We run a refinery that turns raw materials into finished products to meet demand "
    "that is uncertain and described by a scenario tree. In each time period we decide how "
    "much of each raw material to purchase, and for each product at each scenario node we "
    "decide how much to obtain by outsourcing when in-house production falls short. "
    "Purchasing raw materials incurs a per-unit cost, and outsourcing incurs a per-unit "
    "cost that we weight by the probability of each scenario. The objective is to minimize "
    "the total expected cost over the whole horizon."
)

BAL = (
    "def bal_rule(model):\n"
    "    return sum(model.x[i, t] for i in model.i for t in model.t) <= model.b\n"
    "model.bal = Constraint(rule=bal_rule)"
)
DEMBAL = (
    "def dembal_rule(model, jj, t, nd):\n"
    "    return sum(model.a[jj, i] * model.x[i, t] for i in model.i) + model.y[jj, t, nd] >= model.dem[jj, nd]\n"
    "model.dembal = Constraint(model.j, model.tn, rule=dembal_rule)"
)
OBJ_DEF = (
    "def obj_def_rule(model):\n"
    "    purchase = sum(model.c[i] * model.x[i, t] for i in model.i for t in model.t)\n"
    "    outsource = sum(model.sprob[nd] * model.f[jj, t] * model.y[jj, t, nd] for jj in model.j for (t, nd) in model.tn)\n"
    "    return model.cost == purchase + outsource\n"
    "model.obj_def = Constraint(rule=obj_def_rule)"
)
WHOLESET = "\n".join([BAL, DEMBAL, OBJ_DEF])

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, keep the combined quantity of all raw materials purchased across every "
    "period and material within the available inventory capacity. "
    "Second, for each product in each period and scenario node, make sure that the "
    "product yielded in house from the raw materials used that period together with "
    "whatever is outsourced is enough to satisfy that product's demand at that node. "
    "Finally, set the total expected cost equal to the cost of purchasing all raw "
    "materials plus the probability-weighted cost of all outsourcing."
)

records = [
    {"description": (
        "The combined quantity of all raw materials purchased, added up over every raw "
        "material and every time period, must not exceed the available raw-material "
        "inventory capacity."),
     "expected_pyomo": BAL},
    {"description": (
        "For each product in each time period and scenario node, the product made in house "
        "from the raw materials used in that period together with the amount obtained by "
        "outsourcing must be at least the demand for that product at that node. The in-house "
        "amount is the total across all raw materials of how much of the product is yielded "
        "from the quantity of that material used in that period."),
     "expected_pyomo": DEMBAL},
    {"description": (
        "The total expected cost is the cost of all raw-material purchases plus the expected "
        "cost of all outsourcing. The purchasing part values every quantity of raw material "
        "bought in every period at that material's unit cost. The outsourcing part values "
        "every outsourced quantity at its product-and-period unit cost and weights it by the "
        "probability of its scenario node. Set the total cost equal to the sum of these two "
        "parts."),
     "expected_pyomo": OBJ_DEF},
    {"description": WHOLESET_DESC,
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "srkandw_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
