#!/usr/bin/env python
"""Builder for the mesc_lp (multi-echelon supply chain) constraint-generation dataset.

The corpus model builds its constraints as Pyomo ConstraintLists with imperative
.add() loops and lead-time-shifted indices. Every constraint family is LINEAR in
the decision variables (the profit family multiplies variables only by the
constant param coefficients up/uc/dc/hc and the constant discount factor dis**n,
which is a parameter raised to a fixed integer power -> a constant, not a
variable product). So all 9 families are Z3-gradable and kept.

Native constraint names (must be reused so the harness can strip them):
  inv_bal, sales1, sales3, sales5, reorder6, reorder8, pip_bal, unfulfilled, profit

Index conventions (from the corpus .py):
  N  = periods 0..num_periods-1            (30 periods: 0..29)
  N1 = periods 0..num_periods              (0..30; the +1 horizon endpoint)
  M  = stages 0..num_stages-1              (0,1,2,3)
  M0 = stages 0..num_stages-2              (0,1,2; the inventory-carrying stages)
  lt[m] = lead time between stage m and the next (M0-indexed)
  i[0,m], t[0,m] are FIXED initial conditions (init inventory / zero pipeline).
  reorder8 applies ONLY at stage 0 (a precedence quirk in the source reduces its
  stage guard to m==0); we reproduce that scope.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "mesc_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "N", "members": list(range(30)),
         "doc": "the planning periods, numbered from zero; these are the periods in which decisions are made"},
        {"name": "N1", "members": list(range(31)),
         "doc": "the planning periods plus one extra endpoint period, used to index inventory levels that are carried into the period after each decision period"},
        {"name": "M", "members": [0, 1, 2, 3],
         "doc": "all stages of the supply chain, ordered from the most upstream stage zero to the most downstream final stage"},
        {"name": "M0", "members": [0, 1, 2],
         "doc": "the stages that carry inventory, which is every stage except the final downstream stage"},
    ],
    "params": [
        {"name": "up", "index": "M", "kind": "price",
         "doc": "the sales price earned per unit at each stage, in dollars per unit"},
        {"name": "uc", "index": "M", "kind": "cost",
         "doc": "the replenishment cost paid per unit reordered at each stage, in dollars per unit"},
        {"name": "dc", "index": "M", "kind": "cost",
         "doc": "the penalty cost charged per unit of unfulfilled demand carried as backlog at each stage, in dollars per unit"},
        {"name": "hc", "index": "M", "kind": "cost",
         "doc": "the inventory holding cost charged per unit held at each stage, in dollars per unit"},
        {"name": "sc", "index": "M0", "kind": "capacity",
         "doc": "the production or supply capacity at each inventory-carrying stage, the most that may be reordered there in a period"},
        {"name": "lt", "index": "M0", "kind": "lead_time",
         "doc": "the lead time at each inventory-carrying stage, the whole number of periods a reorder placed at that stage takes to arrive"},
        {"name": "dis", "index": "", "kind": "discount",
         "doc": "the per-period discount factor applied to profit, a number between zero and one; a profit earned in period n is discounted by this factor raised to the power n"},
        {"name": "dmd", "index": "N", "kind": "demand",
         "doc": "the customer demand seen at the most downstream stage in each period, in units"},
    ],
    "vars": [
        {"name": "i", "index": "N1, M0", "domain": "NonNegativeReals",
         "doc": "on-hand inventory held at each inventory-carrying stage entering each period; the entries for the opening period are fixed initial inventory and are not decisions"},
        {"name": "t", "index": "N1, M0", "domain": "NonNegativeReals",
         "doc": "pipeline inventory in transit toward each inventory-carrying stage entering each period; the entries for the opening period are fixed at zero and are not decisions"},
        {"name": "r", "index": "N, M0", "domain": "NonNegativeReals",
         "doc": "the reorder quantity placed at each inventory-carrying stage in each period"},
        {"name": "s", "index": "N, M", "domain": "NonNegativeReals",
         "doc": "the units sold or shipped out of each stage in each period"},
        {"name": "b", "index": "N, M", "domain": "NonNegativeReals",
         "doc": "the backlog of unfulfilled demand carried at each stage in each period"},
        {"name": "p", "index": "N", "domain": "Reals",
         "doc": "the discounted profit realized in each period"},
    ],
    "objective": {"sense": "maximize", "expr_var": "p"},
}

NARRATIVE = (
    "We run a multi-echelon supply chain over a sequence of planning periods. The chain has "
    "several stages running from an upstream source down to the final customer-facing stage. "
    "In every period and at every stage we decide how much to reorder from the stage upstream, "
    "how much inventory to hold, how much to ship downstream, and how much demand to leave "
    "unmet as backlog. Reorders take a known number of periods to arrive, sales earn a "
    "stage-specific price, holding inventory and carrying backlog both incur costs, and "
    "reordering costs money. The objective is to maximize total discounted profit summed "
    "across all periods, where profit earned later is worth less by a fixed per-period "
    "discount factor."
)

# ----------------------------------------------------------------------------
# Ground-truth Pyomo. Each rule reproduces the native ConstraintList logic,
# including the lead-time shift and the conditional first-period / scope guards.
# Built with Constraint(... rule=...) under the NATIVE name so the harness strips
# and re-adds it; logical equivalence (not construction style) is what Z3 checks.
# Helper note: model.lt is mutable Param; pyo.value(...) extracts the integer.
# ----------------------------------------------------------------------------

INV_BAL = (
    "def inv_bal_rule(model, n, m):\n"
    "    lt = int(value(model.lt[m]))\n"
    "    arrived = model.r[n - lt, m] if n - lt > -1 else 0\n"
    "    return model.i[n+1, m] == model.i[n, m] + arrived - model.s[n, m]\n"
    "model.inv_bal = Constraint(model.N, model.M0, rule=inv_bal_rule)"
)

SALES1 = (
    "def sales1_rule(model, n):\n"
    "    lt = int(value(model.lt[0]))\n"
    "    arrived = model.r[n - lt, 0] if n - lt > -1 else 0\n"
    "    return model.s[n, 0] <= model.i[n, 0] + arrived\n"
    "model.sales1 = Constraint(model.N, rule=sales1_rule)"
)

SALES3 = (
    "def sales3_rule(model, n):\n"
    "    prev_backlog = model.b[n-1, 0] if n > 0 else 0\n"
    "    return model.s[n, 0] <= model.dmd[n] + prev_backlog\n"
    "model.sales3 = Constraint(model.N, rule=sales3_rule)"
)

SALES5 = (
    "def sales5_rule(model, n, m):\n"
    "    if m < 1:\n"
    "        return Constraint.Skip\n"
    "    return model.s[n, m] == model.r[n, m-1]\n"
    "model.sales5 = Constraint(model.N, model.M, rule=sales5_rule)"
)

REORDER6 = (
    "def reorder6_rule(model, n, m):\n"
    "    return model.r[n, m] <= model.sc[m]\n"
    "model.reorder6 = Constraint(model.N, model.M0, rule=reorder6_rule)"
)

REORDER8 = (
    "def reorder8_rule(model, n):\n"
    "    return model.r[n, 0] <= model.i[n, 1]\n"
    "model.reorder8 = Constraint(model.N, rule=reorder8_rule)"
)

PIP_BAL = (
    "def pip_bal_rule(model, n, m):\n"
    "    lt = int(value(model.lt[m]))\n"
    "    arrived = model.r[n - lt, m] if n - lt > -1 else 0\n"
    "    return model.t[n+1, m] == model.t[n, m] - arrived + model.r[n, m]\n"
    "model.pip_bal = Constraint(model.N, model.M0, rule=pip_bal_rule)"
)

UNFULFILLED = (
    "def unfulfilled_rule(model, n, m):\n"
    "    inflow = model.dmd[n] if m < 1 else model.r[n, m-1]\n"
    "    prev_backlog = model.b[n-1, m] if n > 0 else 0\n"
    "    return model.b[n, m] == inflow + prev_backlog - model.s[n, m]\n"
    "model.unfulfilled = Constraint(model.N, model.M, rule=unfulfilled_rule)"
)

PROFIT = (
    "def profit_rule(model, n):\n"
    "    last = model.M.at(len(model.M))\n"
    "    revenue = sum(model.up[m] * model.s[n, m] for m in model.M)\n"
    "    reorder_cost = sum(model.uc[m] * model.r[n, m] for m in model.M0) + model.uc[last] * model.s[n, last]\n"
    "    backlog_cost = sum(model.dc[m] * model.b[n, m] for m in model.M)\n"
    "    holding_cost = sum(model.hc[m] * model.i[n+1, m] for m in model.M0)\n"
    "    return model.p[n] == model.dis**n * (revenue - reorder_cost - backlog_cost - holding_cost)\n"
    "model.profit = Constraint(model.N, rule=profit_rule)"
)

WHOLESET = "\n".join([INV_BAL, SALES1, SALES3, SALES5, REORDER6, REORDER8,
                      PIP_BAL, UNFULFILLED, PROFIT])

records = [
    {"description": (
        "Track on-hand inventory at each inventory-carrying stage from one period to the next. "
        "For each such stage and period, the inventory carried into the following period equals "
        "the inventory carried into the current period, plus any reorder that was placed earlier "
        "and has now arrived after its lead time has elapsed, minus what is shipped out of the "
        "stage this period. When not enough periods have passed for a reorder to have arrived "
        "yet, no arriving quantity is added."),
     "expected_pyomo": INV_BAL},

    {"description": (
        "Sales out of the most upstream stage in each period cannot exceed what is physically "
        "available there. For each period, the units sold from the upstream stage must not exceed "
        "the inventory on hand at that stage plus any reorder that was placed earlier and has now "
        "arrived after its lead time. Before any reorder has had time to arrive, only the on-hand "
        "inventory is available."),
     "expected_pyomo": SALES1},

    {"description": (
        "Sales out of the most upstream stage in each period are also limited by the demand it "
        "faces together with any demand left unmet earlier. For each period, the units sold from "
        "the upstream stage must not exceed that period's demand plus the backlog carried over "
        "from the previous period. In the very first period there is no earlier backlog, so the "
        "limit is just that period's demand."),
     "expected_pyomo": SALES3},

    {"description": (
        "Link sales out of each downstream stage to the reorders placed by the stage just below "
        "it. For every stage other than the most upstream one, and in each period, the units sold "
        "out of that stage equal the units reordered in the same period by the next stage down the "
        "chain. The most upstream stage is not governed by this rule."),
     "expected_pyomo": SALES5},

    {"description": (
        "Reorders are limited by available capacity. For each inventory-carrying stage and each "
        "period, the quantity reordered must not exceed that stage's supply capacity."),
     "expected_pyomo": REORDER6},

    {"description": (
        "A reorder placed at the most upstream stage cannot draw more than the supplying stage "
        "holds. For each period, the quantity reordered at the most upstream stage must not exceed "
        "the on-hand inventory available at the next stage up the chain."),
     "expected_pyomo": REORDER8},

    {"description": (
        "Track pipeline inventory in transit toward each inventory-carrying stage from one period "
        "to the next. For each such stage and period, the in-transit quantity carried into the "
        "following period equals the in-transit quantity carried into the current period, minus "
        "any reorder that has now arrived after its lead time, plus the new reorder placed this "
        "period. Before any reorder has had time to arrive, nothing is subtracted for arrivals."),
     "expected_pyomo": PIP_BAL},

    {"description": (
        "Track the backlog of unfulfilled demand at each stage from one period to the next. For "
        "each stage and period, the backlog at the end of the period equals the new requirement "
        "arriving at that stage plus any backlog carried over from the previous period, minus what "
        "is sold to satisfy it this period. At the most upstream stage the arriving requirement is "
        "the customer demand, while at every other stage it is the reorder placed by the next "
        "stage down. In the very first period there is no earlier backlog to carry over."),
     "expected_pyomo": UNFULFILLED},

    {"description": (
        "Define the discounted profit realized in each period. For each period, take the sales "
        "revenue earned across all stages, then subtract the cost of all reorders placed plus the "
        "purchase cost of the final stage's sales, subtract the penalty for all backlogged demand, "
        "and subtract the holding cost on the inventory carried into the next period. Discount the "
        "whole amount by the per-period discount factor raised to the power of how many periods "
        "have elapsed, and set the period's profit equal to that discounted net amount."),
     "expected_pyomo": PROFIT},

    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "mesc_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
