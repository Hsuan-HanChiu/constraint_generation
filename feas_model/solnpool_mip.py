# converted from models/solnpool_mip.py
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
model.i = Set(initialize=data['i'], doc='warehouses')
model.j = Set(initialize=data['j'], doc='regions')

# PARAM_BLOCK
model.f = Param(model.i, initialize=data['f'], mutable=True, doc='fixed costs')
model.c = Param(model.i, initialize=data['c'], mutable=True, doc='capacity')
model.d = Param(model.j, initialize=data['d'], mutable=True, doc='demand')
model.t = Param(model.j, model.i, initialize=data['t'], mutable=True, doc='transport costs')

# VAR_BLOCK
model.totcost = Var(domain=Reals, doc='total cost')
model.fcost = Var(domain=Reals, doc='fixed cost')
model.tcost = Var(domain=Reals, doc='transportation cost')
model.ow = Var(model.i, domain=Binary, doc='indicator for open warehouse')
model.oa = Var(model.i, model.j, domain=Binary, doc='indicator for open shipment arc')

# OBJ_BLOCK
model.obj = Objective(expr=model.totcost, sense=minimize, doc='minimize total cost')

# CONS_BLOCK
def deftotcost_rule(model):
    """Definition of total cost"""
    return model.totcost == model.fcost + model.tcost
model.deftotcost = Constraint(rule=deftotcost_rule, doc='definition total cost')

def deffcost_rule(model):
    """Definition of fixed cost"""
    return model.fcost == sum(model.f[i] * model.ow[i] for i in model.i)
model.deffcost = Constraint(rule=deffcost_rule, doc='definition fixed cost')

def deftcost_rule(model):
    """Definition of transportation cost"""
    return model.tcost == sum(model.t[j, i] * model.oa[i, j] for i in model.i for j in model.j)
model.deftcost = Constraint(rule=deftcost_rule, doc='definition transportation cost')

def defwcap_rule(model, i):
    """Limit utilization of warehouse by its capacity"""
    return sum(model.d[j] * model.oa[i, j] for j in model.j) <= model.c[i]
model.defwcap = Constraint(model.i, rule=defwcap_rule, doc='limit utilization by capacity')

def onew_rule(model, j):
    """Only one warehouse per region"""
    return sum(model.oa[i, j] for i in model.i) == 1
model.onew = Constraint(model.j, rule=onew_rule, doc='only one warehouse per region')

def defow_rule(model, i, j):
    """Warehouse open if shipment from i to j"""
    return model.ow[i] >= model.oa[i, j]
model.defow = Constraint(model.i, model.j, rule=defow_rule, doc='warehouse open if shipment')
