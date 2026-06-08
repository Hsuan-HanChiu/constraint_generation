# converted from models/blend_lp54.py
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
model.compdat = Param(model.elem.union({'price'}), model.alloy, mutable = True, initialize=data['compdat'], doc="composition data (pct and price)")
model.rb = Param(model.elem, initialize=data['rb'], mutable = True, doc="required blend")

# VAR_BLOCK
model.v = Var(model.alloy, domain=NonNegativeReals, doc="purchase of alloy (pounds)")
model.phi = Var(domain=NonNegativeReals, doc="total cost")

# OBJ_BLOCK
model.obj = Objective(expr=model.phi, sense=minimize)

# CONS_BLOCK
def pc_rule(model, e):
    return sum(model.compdat[e, a] * model.v[a] for a in model.alloy) == model.rb[e]
model.pc = Constraint(model.elem, rule=pc_rule, doc="purchase constraint")

model.ac = Constraint(expr=model.phi == sum(model.compdat["price", a] * model.v[a] for a in model.alloy), doc="accounting: total cost")
