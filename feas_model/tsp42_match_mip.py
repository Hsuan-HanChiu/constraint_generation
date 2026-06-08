# converted from models/tsp42_match_mip.py
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

# Undirected edges = where distances are given in data['d']
# data['d'] keys are tuples (i,j) coming from pipe-delimited JSON keys
model.E = pyo.Set(dimen=2, initialize=list(data["d"].keys()), doc="edges")

# Distance d(i,j) only on edges
def d_init(model, i, j):
    return data["d"].get((i, j), 0.0)

model.d = pyo.Param(model.E, mutable=True, initialize=d_init, doc="distance")

# Binary edge variables
model.x = pyo.Var(model.E, domain=pyo.Binary, doc="1 if edge {i,j} is in the tour")

# Objective: sum d(i,j) x(i,j)
model.obj = pyo.Objective(
    expr=sum(model.d[i, j] * model.x[i, j] for (i, j) in model.E),
    sense=pyo.minimize,
)

# Two-matching constraints: degree 2 at each city
def twomatch_rule(model, k):
    return sum(model.x[i, j] for (i, j) in model.E if i == k or j == k) == 2

model.twomatch = pyo.Constraint(model.I, rule=twomatch_rule)
