#!/usr/bin/env python
"""Builder for the paperco_lp (paper company supply chain LP) constraint-generation dataset.

Model was FLAGGED as possibly nonlinear. Verified each constraint with
polynomial_degree: ap, aq, pp, pq, plog, cp, cw, pc are all Params (mutable),
so every product is param x var. All 5 constraints are degree 1 = LINEAR.
No constraint excluded.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "paperco_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "L", "members": ["company", "farmer"],
         "doc": "the log suppliers from whom raw logs are obtained"},
        {"name": "W", "members": ["ground", "chips"],
         "doc": "the wood product forms that are produced from logs and fed into pulp making"},
        {"name": "P", "members": ["pulp-1", "pulp-2"],
         "doc": "the pulp types that are produced, sold, or purchased"},
        {"name": "Q", "members": ["kraft", "newsprint", "printing"],
         "doc": "the paper types that are produced and sold as finished product"},
    ],
    "params": [
        {"name": "plog", "index": "", "kind": "cost",
         "doc": "the price paid per unit of log, in dollars per unit, the same for every supplier"},
        {"name": "ap", "index": "W,P", "kind": "technical_coefficient",
         "doc": "the amount of a given wood product required to make one unit of a given pulp type, indexed by wood product then pulp type"},
        {"name": "aq", "index": "P,Q", "kind": "technical_coefficient",
         "doc": "the amount of a given pulp type required to make one unit of a given paper type, indexed by pulp type then paper type"},
        {"name": "cw", "index": "W,P", "kind": "cost",
         "doc": "the shipping cost per unit of wood product sent toward a given pulp type, in dollars per unit, indexed by wood product then pulp type"},
        {"name": "cp", "index": "P,Q", "kind": "cost",
         "doc": "the shipping cost per unit of pulp sent toward a given paper type, in dollars per unit, indexed by pulp type then paper type"},
        {"name": "pq", "index": "Q", "kind": "price",
         "doc": "the selling price per unit of each paper type, in dollars per unit"},
        {"name": "pc", "index": "W", "kind": "cost",
         "doc": "the per-unit purchase cost of each wood product, in dollars per unit"},
        {"name": "pp", "index": "P", "kind": "price",
         "doc": "the per-unit price of each pulp type under the active scenario, used both as the selling price for pulp sold and as the cost for pulp purchased"},
        {"name": "paper_lb", "index": "Q", "kind": "bound",
         "doc": "the minimum output required for each paper type, in units; enforced as a lower bound on the paper output variable"},
        {"name": "paper_ub", "index": "Q", "kind": "bound",
         "doc": "the maximum output allowed for each paper type, in units; enforced as an upper bound on the paper output variable"},
        {"name": "sales_ub", "index": "P", "kind": "bound",
         "doc": "the maximum amount of each pulp type that may be sold under the active scenario, in units; enforced as an upper bound on the pulp sales variable"},
        {"name": "purchase_ub", "index": "P", "kind": "bound",
         "doc": "the maximum amount of each pulp type that may be purchased under the active scenario, in units; enforced as an upper bound on the pulp purchase variable"},
    ],
    "vars": [
        {"name": "logs", "index": "L", "domain": "NonNegativeReals",
         "doc": "the quantity of logs obtained from each supplier"},
        {"name": "xw", "index": "W,P", "domain": "NonNegativeReals",
         "doc": "the quantity of each wood product shipped toward making each pulp type, indexed by wood product then pulp type"},
        {"name": "pulp", "index": "P", "domain": "NonNegativeReals",
         "doc": "the quantity of each pulp type produced"},
        {"name": "xp", "index": "P,Q", "domain": "NonNegativeReals",
         "doc": "the quantity of each pulp type shipped toward making each paper type, indexed by pulp type then paper type"},
        {"name": "paper", "index": "Q", "domain": "NonNegativeReals",
         "doc": "the quantity of each paper type produced; bounded below and above by the paper output bounds"},
        {"name": "sales", "index": "P", "domain": "NonNegativeReals",
         "doc": "the quantity of each pulp type sold on the open market; bounded above by the sales limit"},
        {"name": "purchase", "index": "P", "domain": "NonNegativeReals",
         "doc": "the quantity of each pulp type bought from the open market; bounded above by the purchase limit"},
        {"name": "profit", "index": "", "domain": "Reals",
         "doc": "the net operating income earned across the whole operation, in dollars"},
    ],
    "objective": {"sense": "maximize", "expr_var": "profit"},
}

NARRATIVE = (
    "We run an integrated paper company. We obtain logs from suppliers, turn them into "
    "wood products, convert wood products into pulp, and convert pulp into finished paper "
    "that we sell. We can also buy pulp on the open market or sell our own pulp instead of "
    "converting it. We decide how many logs to obtain from each supplier, how much wood "
    "product to ship into each pulp type, how much pulp to make, how much pulp to ship into "
    "each paper type, how much paper to produce, and how much pulp to buy or sell. The "
    "objective is to maximize net operating income, which is the revenue from selling paper "
    "and pulp minus the cost of logs, the shipping cost of wood products and pulp, the "
    "purchase cost of wood products, and the cost of buying pulp."
)

LOGBAL = (
    "model.logbal = Constraint(expr=\n"
    "    0.97 * sum(model.logs[l] for l in model.L)\n"
    "    == sum(model.xw[w, p] for w in model.W for p in model.P))"
)
WBAL = (
    "def wbal_rule(model, w, p):\n"
    "    return model.xw[w, p] == model.ap[w, p] * model.pulp[p]\n"
    "model.wbal = Constraint(model.W, model.P, rule=wbal_rule)"
)
PBAL = (
    "def pbal_rule(model, p):\n"
    "    return sum(model.xp[p, q] for q in model.Q) == model.purchase[p] - model.sales[p] + model.pulp[p]\n"
    "model.pbal = Constraint(model.P, rule=pbal_rule)"
)
QBAL = (
    "def qbal_rule(model, p, q):\n"
    "    return model.xp[p, q] == model.aq[p, q] * model.paper[q]\n"
    "model.qbal = Constraint(model.P, model.Q, rule=qbal_rule)"
)
OBJ_DEF = (
    "def obj_def_rule(model):\n"
    "    revenue_pulp = sum(model.pp[p] * model.sales[p] for p in model.P)\n"
    "    revenue_paper = sum(model.pq[q] * model.paper[q] for q in model.Q)\n"
    "    cost_logs = sum(model.plog * model.logs[l] for l in model.L)\n"
    "    cost_pulp_tr = sum(model.cp[p, q] * model.xp[p, q] for p in model.P for q in model.Q)\n"
    "    cost_wood = sum((model.cw[w, p] + model.pc[w]) * model.xw[w, p] for w in model.W for p in model.P)\n"
    "    cost_purchase = sum(model.pp[p] * model.purchase[p] for p in model.P)\n"
    "    return model.profit == (revenue_pulp + revenue_paper - cost_logs - cost_pulp_tr - cost_wood - cost_purchase)\n"
    "model.obj_def = Constraint(rule=obj_def_rule)"
)
WHOLESET = "\n".join([LOGBAL, WBAL, PBAL, QBAL, OBJ_DEF])

records = [
    {"description": (
        "Almost all of the logs obtained get turned into wood products, with a small fraction lost "
        "in the process. Across all suppliers, ninety-seven percent of the total logs obtained must "
        "equal the total amount of wood product shipped out across every wood product form and pulp "
        "destination."),
     "expected_pyomo": LOGBAL},
    {"description": (
        "Each pulp type needs wood products in fixed amounts per unit of pulp made. For each "
        "combination of a wood product form and a pulp type, the amount of that wood product shipped "
        "toward that pulp type must equal the amount of pulp of that type produced times the amount "
        "of that wood product needed per unit of that pulp."),
     "expected_pyomo": WBAL},
    {"description": (
        "Each pulp type must balance what is made and traded against what is used downstream. For "
        "each pulp type, the total amount of that pulp shipped toward all paper types must equal the "
        "amount purchased on the market, minus the amount sold on the market, plus the amount produced."),
     "expected_pyomo": PBAL},
    {"description": (
        "Each paper type needs pulp in fixed amounts per unit of paper made. For each combination of "
        "a pulp type and a paper type, the amount of that pulp shipped toward that paper type must "
        "equal the amount of paper of that type produced times the amount of that pulp needed per "
        "unit of that paper."),
     "expected_pyomo": QBAL},
    {"description": (
        "Net operating income is total revenue minus total cost. Revenue comes from selling pulp on "
        "the market at the pulp price and from selling paper at the paper price. Costs are the price "
        "of all logs obtained, the shipping cost of all pulp sent toward paper, the combined shipping "
        "and purchase cost of all wood products, and the cost of buying pulp on the market at the pulp "
        "price. Set net operating income equal to that revenue less those costs."),
     "expected_pyomo": OBJ_DEF},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "paperco_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
