# converted from models/tsp5_MTZ_mip.py
import json
from pyomo.environ import *
import pyomo.environ as pe

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pe.ConcreteModel()

# Sets
model.I = pe.Set(initialize=sorted(list(data["ii"])), doc="Cities")

# Parameters
model.c = pe.Param(
    model.I,
    model.I,
    initialize=data["c"],
    default=0.0,
    mutable=True,
    doc="Travel cost"
)

cities = list(model.I)
n = len(cities)
depot = cities[0]

model.n = pe.Param(initialize=n, mutable=True, doc="Number of cities")
model.depot = depot

# Variables
model.x = pe.Var(
    model.I,
    model.I,
    domain=pe.Binary,
    doc="Arc selection"
)
model.p = pe.Var(
    model.I,
    domain=pe.NonNegativeReals,
    doc="Position in tour"
)

for i in model.I:
    model.x[i, i].fix(0)

for i in model.I:
    if i == model.depot:
        model.p[i].fix(0)
    else:
        model.p[i].setlb(0)
        model.p[i].setub(n - 1)

# Constraints
def rowsum_rule(model, i):
    return sum(model.x[i, j] for j in model.I) == 1

model.rowsum = pe.Constraint(model.I, rule=rowsum_rule, doc="Leave each city once")

def colsum_rule(model, j):
    return sum(model.x[i, j] for i in model.I) == 1

model.colsum = pe.Constraint(model.I, rule=colsum_rule, doc="Arrive at each city once")

def mtz_rule(model, i, j):
    if i == j:
        return pe.Constraint.Skip
    if i == model.depot or j == model.depot:
        return pe.Constraint.Skip
    return (
        model.p[i] - model.p[j] + model.n * model.x[i, j]
        <= model.n - 1
    )

model.defMTZ = pe.Constraint(
    model.I,
    model.I,
    rule=mtz_rule,
    doc="MTZ subtour elimination"
)

# Objective
def obj_rule(model):
    return sum(model.c[i, j] * model.x[i, j] for i in model.I for j in model.I)

model.obj = pe.Objective(rule=obj_rule, sense=pe.minimize, doc="Total tour cost")
