# converted from models/tsp4_tspcut_mip.py
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

# Set of cities
model.I = pyo.Set(initialize=data["i"], doc="cities")

# Cost parameter c(i,j)
def c_init(m, i, j):
    return data["c"].get((i, j), 0.0)

model.c = pyo.Param(
    model.I, model.I,
    mutable=True,
    initialize=c_init,
    doc="travel cost"
)

# Basic info for MTZ
cities = list(data["i"])
n = len(cities)
start_city = cities[0]

# Binary tour variables
model.x = pyo.Var(
    model.I, model.I,
    domain=pyo.Binary,
    doc="1 if arc i->j is used"
)

# MTZ order variables
def u_bounds(m, i):
    return (1.0, float(n))

model.u = pyo.Var(
    model.I,
    domain=pyo.Reals,
    bounds=u_bounds,
    doc="MTZ order"
)

# Objective: minimize total cost
model.obj = pyo.Objective(
    expr=sum(model.c[i, j] * model.x[i, j] for i in model.I for j in model.I),
    sense=pyo.minimize,
    doc="total tour cost"
)

# One outgoing arc per city
def outdeg_rule(m, i):
    return sum(m.x[i, j] for j in m.I) == 1

model.outdeg = pyo.Constraint(model.I, rule=outdeg_rule, doc="outgoing degree")

# One incoming arc per city
def indeg_rule(m, j):
    return sum(m.x[i, j] for i in m.I) == 1

model.indeg = pyo.Constraint(model.I, rule=indeg_rule, doc="incoming degree")

# No self loops
def no_self_rule(m, i):
    return m.x[i, i] == 0

model.no_self = pyo.Constraint(model.I, rule=no_self_rule, doc="no self loops")

# Fix order of start city
model.u[start_city].fix(1.0)

# MTZ subtour elimination
def mtz_rule(m, i, j):
    if i == j:
        return pyo.Constraint.Skip
    if i == start_city or j == start_city:
        return pyo.Constraint.Skip
    return m.u[i] - m.u[j] + n * m.x[i, j] <= n - 1

model.mtz = pyo.Constraint(model.I, model.I, rule=mtz_rule, doc="MTZ cuts")
