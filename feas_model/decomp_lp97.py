# converted from models/decomp_lp97.py
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
model.i = Set(initialize=data['i'])  # plants
model.j = Set(initialize=data['j'])  # terminals

# PARAM_BLOCK
model.c = Param(model.i, model.j, initialize=data['c'], mutable = True, doc="cost matrix")
model.t = Param(model.i, model.j, initialize=data['t'], mutable = True, doc="tankers required")
model.a = Param(model.i, initialize=data['a'], mutable = True, doc="availability")
model.b = Param(model.j, initialize=data['b'], mutable = True, doc="requirements")
model.ctank = Param(initialize=data['ctank'], mutable = True, doc="tanker cost")
model.cship = Param(initialize=data['cship'], mutable = True, doc="shipping cost")

# VAR_BLOCK
model.x = Var(model.i, model.j, domain=NonNegativeReals, doc="shipments")
model.cost = Var(domain=NonNegativeReals, doc="total cost")
model.tank = Var(domain=NonNegativeReals, doc="total tankers used")
model.ship = Var(domain=NonNegativeReals, doc="shipping cost")

# OBJ_BLOCK
model.obj = Objective(expr=model.cost, sense=minimize)

# CONS_BLOCK
model.defcost = Constraint(expr=model.cost == model.cship * model.ship + model.ctank * model.tank)
model.defship = Constraint(expr=model.ship == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j))
model.deftank = Constraint(expr=model.tank == sum(model.t[i, j] * model.x[i, j] for i in model.i for j in model.j))
model.supply = Constraint(model.i, rule=lambda model, i: sum(model.x[i, j] for j in model.j) <= model.a[i])
model.demand = Constraint(model.j, rule=lambda model, j: sum(model.x[i, j] for i in model.i) >= model.b[j])
