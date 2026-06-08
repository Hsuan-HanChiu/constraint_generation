# converted from models/tsp4_assign_mip.py
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
model = pyo.ConcreteModel()

# Cities
model.I = pyo.Set(initialize=data["i"], doc="cities")

# Cost c(i,j)
def c_init(model, i, j):
    return data["c"].get((i, j), 0.0)

model.c = pyo.Param(
    model.I, model.I,
    mutable=True,
    initialize=c_init,
    doc="travel cost",
)

# Decision variables x(i,j)
model.x = pyo.Var(
    model.I, model.I,
    domain=pyo.Binary,
    doc="1 if arc i->j is used",
)

# Objective: assignment cost
model.obj = pyo.Objective(
    expr=sum(model.c[i, j] * model.x[i, j] for i in model.I for j in model.I),
    sense=pyo.minimize,
)

# Row sum: leave each city once
def rowsum_rule(model, i):
    return sum(model.x[i, j] for j in model.I) == 1

model.rowsum = pyo.Constraint(model.I, rule=rowsum_rule)

# Column sum: arrive at each city once
def colsum_rule(model, j):
    return sum(model.x[i, j] for i in model.I) == 1

model.colsum = pyo.Constraint(model.I, rule=colsum_rule)

# No self arcs
def no_self_rule(model, i):
    return model.x[i, i] == 0

model.no_self = pyo.Constraint(model.I, rule=no_self_rule)
