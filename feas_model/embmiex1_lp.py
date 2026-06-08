# converted from gamslib embmiex1 (EMBMIEX1, SEQ=417)
# The GAMS source wraps the classic transportation LP (trnsport) in an embedded-code
# GAMSModelInstance scenario loop. The embedded-code / ModelInstance scaffolding and the
# scenario updaters (newsupply/newdemand over set s) are a tooling demonstration; the
# underlying optimization model is a single transport LP, converted here with its base
# instance (a = newsupply['base'], b = newdemand['base']).
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
model = pyo.ConcreteModel(doc="Transportation problem - minimize shipping cost from plants to markets")

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

model.c = pyo.Param(
    model.i, model.j,
    initialize=data["c"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Transport cost in thousands of dollars per case",
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
def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= model.a[i]

model.supply = pyo.Constraint(model.i, rule=supply_rule, doc="Observe supply limit at plant i")

def demand_rule(model, j):
    return sum(model.x[i, j] for i in model.i) >= model.b[j]

model.demand = pyo.Constraint(model.j, rule=demand_rule, doc="Satisfy demand at market j")

def cost_rule(model):
    return model.z == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)

model.cost = pyo.Constraint(rule=cost_rule, doc="Accounting: total transportation cost")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.minimize,
    doc="Minimize total transportation cost",
)
