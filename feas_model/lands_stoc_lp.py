# converted from models/lands_stoc_lp.py
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
model.i = Set(initialize=data['i'], doc='power plant type')
model.j = Set(initialize=data['j'], doc='operating mode')
model.s = Set(initialize=data['s'], doc='scenarios')

# PARAM_BLOCK
model.c = Param(model.i, initialize=data['c'], mutable=True, doc='investment cost')
# data['d'] has variations on the GAMs code for 3,  5 or 7. Here we assume it is fixed to 3.
model.d = Param(model.j, initialize=data['d'], mutable=True, doc='energy demand')
model.f = Param(model.i, model.j, initialize=data['f'], mutable=True, doc='operating cost')
model.m = Param(initialize=data['m'], doc='min installed capacity')
model.b = Param(initialize=data['b'], doc='budget limit')
model.dvar = Param(model.s, initialize=data['dvar'], mutable=True, doc='demand variation for mode-1')
def ds_init(m, j, s):
    if j == "mode-1":
        return m.dvar[s]   # uses s
    return m.d[j]
model.ds = Param(model.j, model.s, initialize=ds_init, mutable=True)

# VAR_BLOCK
model.x = Var(model.i, domain=NonNegativeReals, doc='capacity installed')
model.ys = Var(model.i, model.j, model.s, domain=NonNegativeReals, doc='operating level (scenario)')
model.cost = Var(domain=NonNegativeReals, doc='total cost')
model.prob = Param(model.s, initialize=data['prob'], mutable=True, doc='scenario probabilities')

# OBJ_BLOCK
model.obj = Objective(expr=model.cost, sense=minimize)

# CONS_BLOCK
def mincap_rule(m):
    return sum(m.x[i] for i in m.i) >= m.m
model.mincap = Constraint(rule=mincap_rule)

def bbal_rule(m):
    return sum(m.c[i] * m.x[i] for i in m.i) <= m.b
model.bbal = Constraint(rule=bbal_rule)

# cost: cost = sum(i, c(i)*x(i)) + sum(i,j,s, prob(s)*f(i,j)*ys(i,j,s))
def defcosts_rule(m):
    return m.cost == \
        sum(m.c[i] * m.x[i] for i in m.i) + \
        sum(m.prob[s] * m.f[i, j] * m.ys[i, j, s]
            for i in m.i for j in m.j for s in m.s)
model.defcosts = Constraint(rule=defcosts_rule)

# powbals(i,s): sum(j, ys(i,j,s)) <= x(i)
def powbals_rule(m, i, s):
    return sum(m.ys[i, j, s] for j in m.j) <= m.x[i]
model.powbals = Constraint(model.i, model.s, rule=powbals_rule)

# dembals(j,s): sum(i, ys(i,j,s)) >= ds(j,s)
def dembals_rule(m, j, s):
    return sum(m.ys[i, j, s] for i in m.i) >= m.ds[j, s]
model.dembals = Constraint(model.j, model.s, rule=dembals_rule)
