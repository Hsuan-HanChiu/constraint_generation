# converted from gamslib tsp2 (TSP2, SEQ=178)
# Traveling Salesman Problem with Miller-Tucker-Zemlin (MTZ) subtour elimination.
# The original GAMS model solves the TSP by iteratively adding subtour-elimination
# constraints. Here we ship a single standalone MIP with the full MTZ formulation
# over the 10-city br17 (TSPLIB) subproblem, whose optimal tour cost is 39.
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
model = pyo.ConcreteModel(doc="Traveling Salesman Problem (br17, 10 cities) with MTZ subtour elimination")

# Sets
model.ii = pyo.Set(initialize=list(data["ii"]), doc="Cities")

# Parameters
model.c = pyo.Param(
    model.ii, model.ii,
    initialize=data["c"],
    default=0.0,
    mutable=True,
    doc="Travel cost between cities",
)

cities = list(model.ii)
n = len(cities)
depot = cities[0]

model.n = pyo.Param(initialize=n, mutable=True, doc="Number of cities")
model.depot = depot

# Variables
model.x = pyo.Var(
    model.ii, model.ii,
    domain=pyo.Binary,
    doc="Arc selection: 1 if leg city i -> city j is in the tour",
)
model.u = pyo.Var(
    model.ii,
    domain=pyo.NonNegativeReals,
    doc="MTZ position variable (subtour elimination)",
)

# Exclude the diagonal (no self-loops)
for i in model.ii:
    model.x[i, i].fix(0)

# MTZ position bounds; pin the depot position to 0
for i in model.ii:
    if i == model.depot:
        model.u[i].fix(0)
    else:
        model.u[i].setlb(0)
        model.u[i].setub(n - 1)

# Constraints
def rowsum_rule(model, i):
    return sum(model.x[i, j] for j in model.ii) == 1

model.rowsum = pyo.Constraint(model.ii, rule=rowsum_rule, doc="Leave each city exactly once")

def colsum_rule(model, j):
    return sum(model.x[i, j] for i in model.ii) == 1

model.colsum = pyo.Constraint(model.ii, rule=colsum_rule, doc="Arrive at each city exactly once")

def se_rule(model, i, j):
    if i == j:
        return pyo.Constraint.Skip
    if i == model.depot or j == model.depot:
        return pyo.Constraint.Skip
    return model.u[i] - model.u[j] + model.n * model.x[i, j] <= model.n - 1

model.se = pyo.Constraint(model.ii, model.ii, rule=se_rule, doc="MTZ subtour elimination")

# Objective
def obj_rule(model):
    return sum(model.c[i, j] * model.x[i, j] for i in model.ii for j in model.ii)

model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize, doc="Minimize total tour cost")
