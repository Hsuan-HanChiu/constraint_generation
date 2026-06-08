# converted from models/vietman_viettag_mip.py
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

model.i = Set(initialize=range(0, 6), doc='sources of ammonia and fertilizer')
model.id = Set(initialize=range(1, 6), doc='domestic sources - plants')
model.k = Set(initialize=range(1, 13), doc='demand centers')
model.product = Set(initialize=data['product'], doc='ammonia, fertilizer')
# Alias
model.j = Set(initialize=model.i)
model.jd = Set(initialize=model.id)

# PARAM_BLOCK

model.fc = Param(model.i, model.product, initialize=data['fc'], mutable=True, doc='fixed cost of plant erection')
model.c = Param(model.i, model.jd, initialize=data['c'], mutable=True, doc='productiin and shipping cost for ammonia')
model.d = Param(model.j, model.k, initialize=data['d'], mutable=True, doc='production and shipping cost for fertilizer')
model.r = Param(model.k, initialize={int(k):v for k,v in data['r'].items()}, mutable=True, doc='fertilizer demand')
model.bigm = Param(initialize=sum(model.r[k] for k in model.k))

# VAR_BLOCK
model.x = Var(model.i, model.jd, domain=NonNegativeReals, doc='ammonia shipment')
model.y = Var(model.j, model.k, domain=NonNegativeReals, doc='fertilizer shipments')
model.u = Var(model.i, model.jd, model.k, domain=NonNegativeReals, doc='tagged product shipment')
model.z = Var(model.jd, domain=Binary, doc='fertilizer decision')
model.w = Var(model.id, domain=Binary, doc='ammonia decision')
model.tc = Var(doc='total cost')

# CONS_BLOCK

def ta1_rule(model):
    sum1 = (sum(model.fc[id,'ammonia'] * model.w[id] for id in model.id)
            + sum(model.fc[jd,'fertilizer'] * model.z[jd] for jd in model.jd))
    sum2 = sum((model.c[i,j] + model.d[j,k]) * model.u[i,j,k]
            for i in model.i for j in model.jd for k in model.k)
    return model.tc == sum1 + sum2

def fd1_rule(model, k):
    return sum(model.u[i, j, k] for i in model.i for j in model.jd) >= model.r[k]

def ia1_rule(model, id, k):
    return model.r[k]*model.w[id] >= sum(model.u[id,jd,k] for jd in model.jd)

def ift_rule(model, jd, k):
    return model.r[k]*model.z[jd] >= sum(model.u[i,jd,k] for i in model.i)    

model.fd1 = Constraint(model.k, rule=fd1_rule, doc='final demand balance (tagged)')
model.ia1 = Constraint(model.id, model.k, rule=ia1_rule, doc='integer constraint ammonia (tagged)')
model.ift = Constraint(model.jd, model.k, rule=ift_rule, doc='integer constraint fertilizer (tagged)')
model.ta1 = Constraint(rule=ta1_rule, doc='total cost balance (tagged)')

# OBJ_BLOCK

model.obj = Objective(expr=model.tc, sense=minimize)
