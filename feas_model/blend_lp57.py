# converted from models/blend_lp57.py
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
model.alloy = Set(initialize=data['alloy'])
model.elem = Set(initialize=data['elem'])

# PARAM_BLOCK
model.compdat = Param(model.elem | Set(initialize=['price']), model.alloy, mutable = True, initialize=data['compdat'], doc='composition data (pct and price)')
model.rb = Param(model.elem, initialize=data['rb'], mutable = True, doc='required blend')

# VAR_BLOCK
model.v = Var(model.alloy, domain=NonNegativeReals, doc='purchase of alloy (pounds)')
model.phi = Var(domain=NonNegativeReals, doc='total cost')

# OBJ_BLOCK
model.obj = Objective(expr=model.phi, sense=minimize)

# CONS_BLOCK
def pc_rule(model, elem):
    return sum(model.compdat[elem, alloy] * model.v[alloy] for alloy in model.alloy) == model.rb[elem]
model.pc = Constraint(model.elem, rule=pc_rule, doc='purchase constraint')

model.mb = Constraint(expr=sum(model.v[alloy] for alloy in model.alloy) == 1, doc='material balance')

model.ac = Constraint(expr=model.phi == sum(model.compdat['price', alloy] * model.v[alloy] for alloy in model.alloy), doc='accounting: total cost')
