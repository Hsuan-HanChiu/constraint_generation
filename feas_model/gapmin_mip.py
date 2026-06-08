# converted from gamslib gapmin (GAPMIN, SEQ=182)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "r1|i1": value → (r1, i1): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Generalized Assignment Problem - min-cost assignment of items to resources")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Resources")
model.j = pyo.Set(initialize=data["j"], doc="Items")

# Parameters
model.a = pyo.Param(
    model.i, model.j,
    initialize=data["a"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Utilization of resource i by item j",
)

model.f = pyo.Param(
    model.i, model.j,
    initialize=data["f"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Cost of assigning item j to resource i",
)

model.b = pyo.Param(
    model.i,
    initialize=data["b"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Available resources (capacity) of resource i",
)

# Variables
model.x = pyo.Var(
    model.i, model.j,
    domain=pyo.Binary,
    doc="1 if item j is assigned to resource i",
)

model.z = pyo.Var(
    domain=pyo.Reals,
    doc="Total cost of assignment",
)

# Constraints
def capacity_rule(model, i):
    return sum(model.a[i, j] * model.x[i, j] for j in model.j) <= model.b[i]

model.capacity = pyo.Constraint(model.i, rule=capacity_rule, doc="Resource availability (capacity)")

def choice_rule(model, j):
    return sum(model.x[i, j] for i in model.i) == 1

model.choice = pyo.Constraint(model.j, rule=choice_rule, doc="Assignment: one resource per item")

def defz_rule(model):
    return model.z == sum(model.f[i, j] * model.x[i, j] for i in model.i for j in model.j)

model.defz = pyo.Constraint(rule=defz_rule, doc="Accounting: total assignment cost")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.minimize,
    doc="Minimize total assignment cost",
)
