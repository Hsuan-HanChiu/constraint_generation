# converted from models/ampl_lp.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# SET_BLOCK
model.p = Set(initialize=data['p'], doc='products')
model.r = Set(initialize=data['r'], doc='raw materials')
model.tl = Set(initialize=data['tl'], doc='extended t')
model.t = Set(within=model.tl, initialize=data['t'], doc='periods')

# PARAM_BLOCK
model.b = Param(model.r, initialize=data['b'], mutable = True, doc='initial stock')
model.d = Param(model.r, initialize=data['d'], mutable = True, doc='storage cost')
model.f = Param(model.r, initialize=data['f'], mutable = True, doc='residual value')
model.m = Param(initialize=data['m'], mutable = True, doc='maximum production')

model.a = Param(model.r, model.p, initialize=data['a'], mutable = True, doc='raw material inputs to produce a unit of product')
model.c = Param(model.p, model.t, initialize=data['c'], mutable = True, doc='profit')

# VAR_BLOCK
model.x = Var(model.p, model.tl, domain=PositiveReals, doc='production level')
model.s = Var(model.r, model.tl, domain=PositiveReals, doc='storage at beginning of period')
model.profit = Var(domain=PositiveReals, doc='income minus cost')

# OBJ_BLOCK
model.obj = Objective(
    expr=model.profit,
    sense=maximize,
    doc='Profit maximization'
)

# CONS_BLOCK
def limit_rule(model, t):
    return sum(model.x[p, t] for p in model.p) <= model.m
model.limit = Constraint(model.t, rule=limit_rule, doc='capacity constraint')

def balance_rule(model, r, tl):
    if tl == 1:
        return model.s[r, tl] == model.b[r]
    if tl > 1:
        return model.s[r, tl] == model.s[r, tl - 1] - sum(model.a[r, p] * model.x[p, tl - 1] for p in model.p)
model.balance = Constraint(model.r, model.tl, rule=balance_rule, doc='raw material balance')

def obj_rule(model):
    return model.profit == sum(model.c[p, t] * model.x[p, t] for p in model.p for t in model.t) + \
           sum((-model.d[r] if t in model.t else model.f[r]) * model.s[r, t] for r in model.r for t in model.tl)
model.obj_constraint = Constraint(rule=obj_rule, doc='profit definition')
