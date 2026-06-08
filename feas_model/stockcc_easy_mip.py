# converted from models/stockcc_easy_mip.py
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

model.nn = Set(initialize=[f"n{x}" for x in range(1, 49)], doc='items')
model.mm = Set(initialize=[f"i{x}" for x in range(1, 10)], doc='reorder intervals')

# PARAM_BLOCK

model.N = Param(initialize=100, mutable=True, doc='max total number of replenishments')
model.Y = Param(model.mm, initialize=data['Y'], mutable=True, doc='possible number of orders')
model.Dv = Param(model.nn, initialize=data['Dv'], mutable=True, doc='demand rate times unit cost of item nn')
model.CostZ = Param(model.nn, model.mm, initialize={
      (n, m): 1.5*model.Dv[n]/model.Y[m] for n in model.nn for m in model.mm}, mutable=True, doc='cost for item nn with order schedule mm')


# VAR_BLOCK
model.x = Var(model.nn, domain=Reals, doc='number of orders per unit time')
model.z = Var(model.nn, model.mm, domain=Binary, doc='discrete orders choices')
model.obj = Var()

# CONS_BLOCK

def defobjmip_rule(model):
   return model.obj == sum(model.CostZ[nn, mm]*model.z[nn,mm] for nn in model.nn for mm in model.mm)

def capacity_rule(model):
   return sum(model.x[nn] for nn in model.nn) <= 3*model.N

def defx_rule(model, nn):
    return sum(model.z[nn, mm]*model.Y[mm] for mm in model.mm) == model.x[nn]

def defsos_rule(model, nn):
    return sum(model.z[nn, mm] for mm in model.mm) == 1

model.defobjmip = Constraint(rule=defobjmip_rule)
model.capacity = Constraint(rule=capacity_rule)
model.defx = Constraint(model.nn, rule=defx_rule)
model.defsos = Constraint(model.nn, rule=defsos_rule)

for n in model.nn:
  model.x[n].setlb(model.Y['i1'])
  model.x[n].setub(model.Y['i9'])

# OBJ_BLOCK

model.min_obj = Objective(expr=model.obj, sense=minimize)
