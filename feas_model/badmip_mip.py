# converted from models/badmip_mip.py
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

model.i = Set(initialize=range(1, 21), doc='')
model.ii = Set(initialize=range(2, 20), doc='subset of i')

# PARAM_BLOCK

model.s = Param(initialize=data['s'], mutable=True, doc='')

# VAR_BLOCK

model.obj = Var(domain=Reals)
model.x = Var(model.i, domain=Integers)

# CONS_BLOCK

def eq1_rule(model):
      return (model.s+1)*model.x[1] >= model.s - 1

def eq2_rule(model, i):
  if i not in model.ii:
    return Constraint.Skip
  return -model.s*model.x[i-1] + (model.s+1)*model.x[i] - model.x[i+1] >= (-1)**i*(model.s+1)

def eq3_rule(model):
  return -model.s*model.x[18] - (3*model.s-1)*model.x[19] + 3*model.x[20] >= -(5*model.s-7)


def defobj_rule(model):
  return model.obj == -model.x[20]

model.eq1 = Constraint(rule=eq1_rule)
model.eq2 = Constraint(model.ii, rule=eq2_rule)
model.eq3 = Constraint(rule=eq3_rule)
model.defobj = Constraint(rule=defobj_rule)

for i in model.i:
  if i <= 13:
      model.x[i].setub(10)
  else:
      model.x[i].setub(1e6)

# OBJ_BLOCK

model.min_obj = Objective(expr=model.obj, sense=minimize)
