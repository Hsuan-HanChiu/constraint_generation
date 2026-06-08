# converted from models/ampl_lp2.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="AMPL Sample Problem: maximum revenue production planning"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.p = Set(
    initialize=data["p"],
    doc="products"
)
model.r = Set(
    initialize=data["r"],
    doc="raw materials"
)
model.tl = Set(
    initialize=data["tl"],
    doc="extended time periods"
)
model.t = Set(
    initialize=data["t"],
    doc="active production periods (subset of tl)"
)

# For GAMS-style tl.first / tl.last:
first_tl = min(data["tl"])
last_tl = max(data["tl"])

# ----------------------------------------------------------------------
# PARAM_BLOCK  (all mutable = True)
# ----------------------------------------------------------------------
# b(r): initial stock
model.b = Param(
    model.r,
    initialize=data["b"],
    mutable=True,
    doc="initial stock of raw material r"
)

# d(r): storage cost
model.d = Param(
    model.r,
    initialize=data["d"],
    mutable=True,
    doc="storage cost per unit of raw material r per period"
)

# f(r): residual value
model.f = Param(
    model.r,
    initialize=data["f"],
    mutable=True,
    doc="residual value per unit of raw material r at the end"
)

# a(r,p): raw material inputs to produce a unit of product
model.a = Param(
    model.r,
    model.p,
    initialize=data["a"],
    mutable=True,
    doc="raw material amount of r required per unit of product p"
)

# c(p,t): profit per unit
model.c = Param(
    model.p,
    model.t,
    initialize=data["c"],
    mutable=True,
    doc="profit from selling one unit of product p in period t"
)

# m: maximum production per period
model.m = Param(
    initialize=data["m"],
    mutable=True,
    doc="maximum total production per period"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
# x(p,tl): production level
model.x = Var(
    model.p,
    model.tl,
    domain=NonNegativeReals,
    doc="production level of product p in extended period tl"
)

# s(r,tl): storage at beginning of period
model.s = Var(
    model.r,
    model.tl,
    domain=NonNegativeReals,
    doc="inventory of raw material r at beginning of extended period tl"
)

# profit: income minus storage cost plus residual value
model.profit = Var(
    doc="total profit (income minus storage costs plus residual value)"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
model.obj = Objective(
    expr=model.profit,
    sense=maximize,
    doc="maximize total profit"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------
# limit(t).. sum(p, x(p,t)) =l= m;
def limit_rule(model, t):
    return sum(model.x[p, t] for p in model.p) <= model.m

model.limit = Constraint(
    model.t,
    rule=limit_rule,
    doc="capacity constraint: total production per active period t"
)

def balance_rule(model, r, tl):
    if tl == last_tl:
        return Constraint.Skip
    return model.s[r, tl + 1] == model.s[r, tl] - sum(
        model.a[r, p] * model.x[p, tl] for p in model.p
    )

model.balance = Constraint(
    model.r,
    model.tl,
    rule=balance_rule,
    doc="raw material balance between consecutive extended periods"
)

def profit_def_rule(model):
    # Revenue term
    revenue = sum(
        model.c[p, t] * model.x[p, t]
        for p in model.p
        for t in model.t
    )

    # Inventory-related term
    inv_term = sum(
        (
            (-model.d[r] if tl in model.t else 0.0)
            + (model.f[r] if tl == last_tl else 0.0)
        )
        * model.s[r, tl]
        for r in model.r
        for tl in model.tl
    )

    return model.profit == revenue + inv_term

model.profit_def = Constraint(
    rule=profit_def_rule,
    doc="definition of total profit as revenue plus inventory terms"
)

# ----------------------------------------------------------------------
# BOUND_BLOCK
# ----------------------------------------------------------------------
for r in model.r:
    model.s[r, first_tl].setub(model.b[r])
