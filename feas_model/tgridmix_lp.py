# converted from models/tgridmix_lp.py
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
model = pyo.ConcreteModel(doc="Grid/MT transport problem")

# Sets
model.I = pyo.Set(initialize=data["i"], doc="Canning plants")
model.J = pyo.Set(initialize=data["j"], doc="Markets")

# Parameters
model.a = pyo.Param(
    model.I,
    initialize=data["a"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Capacity of plant i in cases"
)

model.b = pyo.Param(
    model.J,
    initialize=data["b"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Demand at market j in cases"
)

model.d = pyo.Param(
    model.I,
    model.J,
    initialize=data["d"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Distance in thousands of miles"
)

model.f = pyo.Param(
    initialize=float(data["f"]),
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Freight per case per thousand miles"
)

def c_init(model, i, j):
    return model.f * model.d[i, j] / 1000.0

model.c = pyo.Param(
    model.I,
    model.J,
    initialize=c_init,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Transport cost in thousands of dollars per case"
)

# Variables
model.x = pyo.Var(
    model.I,
    model.J,
    domain=pyo.NonNegativeReals,
    doc="Shipment quantities in cases"
)

model.z = pyo.Var(
    domain=pyo.Reals,
    doc="Total transportation costs in thousands of dollars"
)

# Constraints
def cost_rule(model):
    return model.z == sum(
        model.c[i, j] * model.x[i, j] for i in model.I for j in model.J
    )

model.cost = pyo.Constraint(rule=cost_rule, doc="Define objective function")

def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.J) <= model.a[i]

model.supply = pyo.Constraint(
    model.I,
    rule=supply_rule,
    doc="Supply limit at plant i"
)

def demand_rule(model, j):
    return sum(model.x[i, j] for i in model.I) >= model.b[j]

model.demand = pyo.Constraint(
    model.J,
    rule=demand_rule,
    doc="Satisfy demand at market j"
)

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.minimize,
    doc="Minimize total transportation cost"
)
