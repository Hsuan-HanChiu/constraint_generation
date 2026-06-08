# converted from models/awktsp_mip_assign.py
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(name="TSP_Assignment")

# Sets
model.i = pyo.Set(initialize=data['i'])
model.j = pyo.Set(initialize=data['j'])

# Parameters
model.c = pyo.Param(model.i, model.j, initialize=data['c'])

# Variables
model.x = pyo.Var(model.i, model.j, domain=pyo.Binary)

# Objective: minimize total cost
def objective_rule(model):
    return sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)
model.obj = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

# Constraints: leave each city only once
def rowsum_rule(model, i):
    return sum(model.x[i, j] for j in model.j) == 1
model.rowsum = pyo.Constraint(model.i, rule=rowsum_rule)

# Constraints: arrive at each city only once
def colsum_rule(model, j):
    return sum(model.x[i, j] for i in model.i) == 1
model.colsum = pyo.Constraint(model.j, rule=colsum_rule)

# Fix diagonal to zero (no self-loops)
for i in model.i:
    model.x[i, i].fix(0)
