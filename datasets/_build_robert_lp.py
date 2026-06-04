#!/usr/bin/env python
"""Builder for the robert_lp (multi-period production/inventory LP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "robert_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "p", "members": ["low", "medium", "high"], "doc": "the product qualities that can be produced and sold"},
        {"name": "r", "members": ["scrap", "new"], "doc": "the raw materials consumed to make the products"},
        {"name": "tt", "members": [1, 2, 3, 4], "doc": "the long planning horizon of periods, including a final period 4 used only to value leftover stock"},
        {"name": "t", "members": [1, 2, 3], "doc": "the short planning horizon of operating periods in which production and sales actually happen"},
        {"name": "misc_rows", "members": ["max-stock", "storage-c", "res-value"], "doc": "labels for rows of the misc table: a per-material stock ceiling, a per-material storage cost, and a per-material end-of-horizon residual value"},
    ],
    "params": [
        {"name": "a", "index": "r,p", "kind": "coefficient",
         "doc": "amount of a raw material consumed to make one unit of a product"},
        {"name": "c", "index": "p,t", "kind": "profit",
         "doc": "expected profit per unit from producing and selling a product in a short-horizon period, in dollars per unit"},
        {"name": "misc", "index": "misc_rows,r", "kind": "table",
         "doc": "a small table of per-material figures; the max-stock row gives each material's stock ceiling, the storage-c row gives the cost of holding one unit of that material for one period, and the res-value row gives the value of one leftover unit of that material at the end of the horizon"},
        {"name": "m", "index": "", "kind": "capacity",
         "doc": "the maximum total production allowed in any single short-horizon period, in units"},
    ],
    "vars": [
        {"name": "x", "index": "p,tt", "domain": "NonNegativeReals",
         "doc": "the number of units of a product produced and sold in a period"},
        {"name": "s", "index": "r,tt", "domain": "NonNegativeReals",
         "doc": "the opening stock of a raw material at the start of a period"},
        {"name": "profit", "index": "", "domain": "Reals", "doc": "total profit over the horizon, in dollars"},
    ],
    "objective": {"sense": "maximize", "expr_var": "profit"},
}

NARRATIVE = (
    "We run a small plant over several periods that turns raw materials into products of "
    "different qualities. In each operating period we decide how many units of each product "
    "to make and sell, and we carry opening stocks of each raw material from one period to "
    "the next. Making products consumes raw materials and earns a per-unit profit, holding "
    "stock costs money each period, and any material left at the end of the horizon still has "
    "some residual value. The objective is to maximize the total profit over the whole horizon."
)

CC = (
    "def cc_rule(model, t):\n"
    "    return sum(model.x[p, t] for p in model.p) <= model.m\n"
    "model.cc = Constraint(model.t, rule=cc_rule)"
)
SB = (
    "def sb_rule(model, r, tt):\n"
    "    if tt + 1 not in list(model.tt):\n"
    "        return Constraint.Skip\n"
    "    rh = model.s[r, tt] - sum(model.a[r, p] * model.x[p, tt] for p in model.p)\n"
    "    return model.s[r, tt + 1] == rh\n"
    "model.sb = Constraint(model.r, model.tt, rule=sb_rule)"
)
PD = (
    "def pd_rule(model):\n"
    "    sum1 = sum(sum(model.c[p, t] * model.x[p, t] for p in model.p) - sum(model.misc['storage-c', r] * model.s[r, t] for r in model.r) for t in model.t)\n"
    "    sum2 = sum(model.misc['res-value', r] * model.s[r, 4] for r in model.r)\n"
    "    return model.profit == sum1 + sum2\n"
    "model.pd = Constraint(rule=pd_rule)"
)
INIT_STOCK_CAP = (
    "def init_stock_cap_rule(model, r):\n"
    "    return model.s[r, 1] <= model.misc['max-stock', r]\n"
    "model.init_stock_cap = Constraint(model.r, rule=init_stock_cap_rule)"
)
WHOLESET = "\n".join([CC, SB, PD, INIT_STOCK_CAP])

records = [
    {"description": (
        "In any operating period the plant has a limited total output. For each operating "
        "period, the total units produced across all products must not exceed the maximum "
        "allowed production for a single period."),
     "expected_pyomo": CC},
    {"description": (
        "Raw material stock carries over from one period to the next, reduced by what "
        "production consumes. For each raw material and each period that has a following "
        "period, the opening stock at the start of the next period equals the opening stock "
        "of the current period minus the amount of that material used up by the current "
        "period's production across all products."),
     "expected_pyomo": SB},
    {"description": (
        "Total profit adds up the earnings from production and sales, charges for holding "
        "stock, and credits leftover material at the end. For each operating period, take "
        "the per-unit profit earned on every product made and sold and subtract the storage "
        "cost of the opening stock of every raw material. Sum that over all operating "
        "periods, then add the residual value of the opening stock of every raw material at "
        "the final period of the horizon. Set the profit variable equal to that total."),
     "expected_pyomo": PD},
    {"description": (
        "The plant cannot start out holding more of a raw material than it has room for. "
        "For each raw material, the opening stock at the very first period must not exceed "
        "that material's stock ceiling."),
     "expected_pyomo": INIT_STOCK_CAP},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "robert_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
