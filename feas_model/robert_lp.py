# converted from models/robert_lp.py
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
model.tt = Set(initialize=range(1,5), doc='long horizon')
model.t = Set(initialize=range(1,4) , doc='short horizon')
model.misc_rows = Set(initialize=data['misc_rows'], doc='misc row')

# PARAM_BLOCK

model.a = Param(model.r, model.p, initialize=data['a'], mutable=True, doc='input coefficients')
model.c = Param(model.p, model.t, initialize=data['c'], mutable=True, doc='expected profits')
model.misc = Param(model.misc_rows, model.r, initialize=data['misc'], mutable=True, doc='other data')
model.m = Param(initialize=data['m'], mutable=True, doc='maximum production')

# VAR_BLOCK
model.x = Var(model.p, model.tt, domain=NonNegativeReals, doc='production and sales')
model.s = Var(model.r, model.tt, domain=NonNegativeReals, doc='operning stocks')
model.profit = Var(doc='profit')

# CONS_BLOCK

def cc_rule(model, t):
    return sum(model.x[p,t] for p in model.p) <= model.m

def sb_rule(model, r, tt):
    if tt + 1 not in list(model.tt):
        return Constraint.Skip

    rh = model.s[r,tt] - sum(model.a[r,p]*model.x[p,tt] for p in model.p)
    return model.s[r,tt+1] == rh

def pd_rule(model):
    sum1 = sum(sum(model.c[p,t]*model.x[p,t] for p in model.p) - sum(model.misc["storage-c",r]*model.s[r,t] for r in model.r) for t in model.t)
    sum2 = sum(model.misc["res-value",r]*model.s[r,4] for r in model.r)
    return model.profit == sum1 + sum2

model.cc = Constraint(model.t, rule=cc_rule, doc="capacity constraint")
model.sb = Constraint(model.r, model.tt, rule=sb_rule, doc="stock balance")
model.pd = Constraint(rule=pd_rule, doc="profit definition")

def init_stock_cap_rule(model, r):
    return model.s[r, 1] <= model.misc["max-stock", r]
model.init_stock_cap = Constraint(model.r, rule=init_stock_cap_rule,
                                   doc="initial stock cap from max-stock")

# OBJ_BLOCK

model.min_obj = Objective(expr=model.profit, sense=maximize)
