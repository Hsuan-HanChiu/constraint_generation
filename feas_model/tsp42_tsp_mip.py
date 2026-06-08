# converted from models/tsp42_tsp_mip.py
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

cities = list(data["i"])
n = len(cities)
start = cities[0]

# Symmetric distance c(i,j) from triangular data['d']
def c_init(model, i, j):
    if i == j:
        return 0.0
    # data['d'] has some orientation (triangular); use symmetric value
    return data["d"].get((i, j), data["d"].get((j, i), 0.0))

model.c = pyo.Param(
    model.I, model.I,
    mutable=True,
    initialize=c_init,
    doc="symmetric travel cost",
)

# Binary arc variables (directed)
model.x = pyo.Var(
    model.I, model.I,
    domain=pyo.Binary,
    doc="1 if arc i->j is used",
)

# MTZ order variables
def u_bounds(model, i):
    return (1.0, float(n))

model.u = pyo.Var(
    model.I,
    domain=pyo.Reals,
    bounds=u_bounds,
    doc="MTZ order index",
)

# Objective: sum of travel costs
model.obj = pyo.Objective(
    expr=sum(model.c[i, j] * model.x[i, j] for i in model.I for j in model.I),
    sense=pyo.minimize,
)

# Outgoing degree = 1
def outdeg_rule(model, i):
    return sum(model.x[i, j] for j in model.I if j != i) == 1

model.outdeg = pyo.Constraint(model.I, rule=outdeg_rule)

# Incoming degree = 1
def indeg_rule(model, j):
    return sum(model.x[i, j] for i in model.I if i != j) == 1

model.indeg = pyo.Constraint(model.I, rule=indeg_rule)

# No self loops
def no_self_rule(model, i):
    return model.x[i, i] == 0

model.no_self = pyo.Constraint(model.I, rule=no_self_rule)

# Fix order of start city
model.u[start].fix(1.0)

# MTZ subtour elimination
def mtz_rule(model, i, j):
    if i == j:
        return pyo.Constraint.Skip
    if i == start or j == start:
        return pyo.Constraint.Skip
    return model.u[i] - model.u[j] + n * model.x[i, j] <= n - 1

model.mtz = pyo.Constraint(model.I, model.I, rule=mtz_rule)
