# converted from models/lands_det_lp.py
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

# PARAM_BLOCK
model.c = Param(model.i, initialize=data['c'], mutable=True, doc='investment cost')
# data['d'] has variations on the GAMs code for 3,  5 or 7. Here we assume it is fixed to 3.
model.d = Param(model.j, initialize=data['d'], mutable=True, doc='energy demand')
model.f = Param(model.i, model.j, initialize=data['f'], mutable=True, doc='operating cost')
model.m = Param(initialize=data['m'], doc='min installed capacity')
model.b = Param(initialize=data['b'], doc='budget limit')

# VAR_BLOCK
model.x = Var(model.i, domain=NonNegativeReals, doc='capacity installed')
model.y = Var(model.i, model.j, domain=NonNegativeReals, doc='operating level')
model.cost = Var(domain=NonNegativeReals, doc='total cost')

# OBJ_BLOCK
model.obj = Objective(expr=model.cost, sense=minimize)

# CONS_BLOCK
def defcost_rule(m):
    # sum(i, c(i)*x(i)) + sum((i,j), f(i,j)*y(i,j))
    return m.cost == sum(m.c[i] * m.x[i] for i in m.i) + sum(m.f[i, j] * m.y[i, j] for i in m.i for j in m.j)
model.defcost = Constraint(rule=defcost_rule)

def mincap_rule(m):
    return sum(m.x[i] for i in m.i) >= m.m
model.mincap = Constraint(rule=mincap_rule)

def bbal_rule(m):
    return sum(m.c[i] * m.x[i] for i in m.i) <= m.b
model.bbal = Constraint(rule=bbal_rule)

def powbal_rule(m, i):
    return sum(m.y[i, j] for j in m.j) <= m.x[i]
model.powbal = Constraint(model.i, rule=powbal_rule)

def dembal_rule(m, j):
    return sum(m.y[i, j] for i in m.i) >= m.d[j]
model.dembal = Constraint(model.j, rule=dembal_rule)
