# converted from gamslib bchtsp (BCHTSP, SEQ=348)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "i1|i2": value → (i1, i2): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
# Traveling Salesman Problem (asymmetric) on a 7-city subset of the p43 ATSP
# instance. The GAMS source solved this as an assignment problem and eliminated
# subtours via BCH lazy cuts supplied during branch-and-cut. Here the underlying
# MIP is made standalone by adding Miller-Tucker-Zemlin (MTZ) subtour-elimination
# constraints, which yield the same optimal tour length (78).

model = pyo.ConcreteModel(doc="Traveling Salesman Problem (p43 7-city subset, MTZ subtour elimination)")

# Sets
model.city = pyo.Set(initialize=data["city"], doc="Cities to visit")

# Parameters
model.c = pyo.Param(
    model.city, model.city,
    initialize=data["c"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Travel cost on the leg from one city to another",
)

# Variables
model.x = pyo.Var(
    model.city, model.city,
    domain=pyo.Binary,
    doc="1 if the tour travels directly from city i to city j",
)

n = len(model.city)
model.u = pyo.Var(
    model.city,
    domain=pyo.NonNegativeReals,
    bounds=(0, n - 1),
    doc="MTZ ordering position of each city in the tour",
)

# Exclude self-loops on the diagonal
for i in model.city:
    model.x[i, i].fix(0)

# Constraints
def rowsum_rule(model, i):
    return sum(model.x[i, j] for j in model.city if j != i) == 1

model.rowsum = pyo.Constraint(model.city, rule=rowsum_rule, doc="Leave each city exactly once")

def colsum_rule(model, j):
    return sum(model.x[i, j] for i in model.city if i != j) == 1

model.colsum = pyo.Constraint(model.city, rule=colsum_rule, doc="Arrive at each city exactly once")

first = list(model.city)[0]

def mtz_rule(model, i, j):
    if i == j or i == first or j == first:
        return pyo.Constraint.Skip
    return model.u[i] - model.u[j] + n * model.x[i, j] <= n - 1

model.mtz = pyo.Constraint(model.city, model.city, rule=mtz_rule, doc="MTZ subtour-elimination constraints")

# Objective
model.obj = pyo.Objective(
    expr=sum(model.c[i, j] * model.x[i, j] for i in model.city for j in model.city),
    sense=pyo.minimize,
    doc="Minimize total tour length",
)
