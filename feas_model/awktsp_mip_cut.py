# converted from models/awktsp_mip_cut.py
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
model = pyo.ConcreteModel(name="TSP_with_Cuts")

# Sets
model.i = pyo.Set(initialize=data['i'])
model.j = pyo.Set(initialize=data['j'])

# Parameters
model.c = pyo.Param(model.i, model.j, initialize=data['c'])

# Variables
model.x = pyo.Var(model.i, model.j, domain=pyo.Binary)

# Objective
def objective_rule(model):
    return sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)
model.obj = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

# Assignment constraints
def rowsum_rule(model, i):
    return sum(model.x[i, j] for j in model.j) == 1
model.rowsum = pyo.Constraint(model.i, rule=rowsum_rule)

def colsum_rule(model, j):
    return sum(model.x[i, j] for i in model.i) == 1
model.colsum = pyo.Constraint(model.j, rule=colsum_rule)

# Fix diagonal
for i in model.i:
    model.x[i, i].fix(0)

# Subtour elimination cuts (if provided in data)
if 'cuts' in data and len(data['cuts']) > 0:
    model.cut_set = pyo.Set(initialize=range(len(data['cuts'])))

    def cut_rule(model, c):
        cut_data = data['cuts'][c]
        arcs = cut_data['arcs']
        rhs = cut_data['rhs']
        return sum(model.x[i, j] for i, j in arcs) <= rhs
    model.cut = pyo.Constraint(model.cut_set, rule=cut_rule)
