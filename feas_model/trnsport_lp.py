# converted from gamslib trnsport (TRNSPORT, SEQ=1)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "seattle|new-york": value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="A Transportation Problem - least cost shipping schedule")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Canning plants")
model.j = pyo.Set(initialize=data["j"], doc="Markets")

# Parameters
model.a = pyo.Param(
    model.i,
    initialize=data["a"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Capacity of plant i in cases",
)

model.b = pyo.Param(
    model.j,
    initialize=data["b"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Demand at market j in cases",
)

model.d = pyo.Param(
    model.i, model.j,
    initialize=data["d"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Distance in thousands of miles",
)

model.f = pyo.Param(
    initialize=data["f"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Freight in dollars per case per thousand miles",
)

# Variables
model.x = pyo.Var(
    model.i, model.j,
    domain=pyo.NonNegativeReals,
    doc="Shipment quantities in cases",
)

model.z = pyo.Var(
    domain=pyo.Reals,
    doc="Total transportation costs in thousands of dollars",
)

# Constraints
def cost_rule(model):
    # c(i,j) = f*d(i,j)/1000  (transport cost in thousands of dollars per case)
    return model.z == sum(
        (model.f * model.d[i, j] / 1000.0) * model.x[i, j]
        for i in model.i for j in model.j
    )

model.cost = pyo.Constraint(rule=cost_rule, doc="Define objective function")

def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= model.a[i]

model.supply = pyo.Constraint(model.i, rule=supply_rule, doc="Observe supply limit at plant i")

def demand_rule(model, j):
    return sum(model.x[i, j] for i in model.i) >= model.b[j]

model.demand = pyo.Constraint(model.j, rule=demand_rule, doc="Satisfy demand at market j")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.minimize,
    doc="Minimize total transportation costs",
)
