# converted from gamslib trnsgrid (TRNSGRID, SEQ=315)
# NOTE: the GAMS original wraps this transportation LP in a GAMS Grid Facility
# loop that re-solves it over 5 random demand scenarios. That scenario/grid
# machinery is a solve-technique demonstration, not part of the optimization
# model, so it is dropped here; this is the underlying base model on the
# original (deterministic) demands.
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
model = pyo.ConcreteModel(doc="Grid Transportation Problem - base transportation model")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Canning plants")
model.j = pyo.Set(initialize=data["j"], doc="Markets")

# Parameters
model.a = pyo.Param(
    model.i, initialize=data["a"], mutable=True, within=pyo.NonNegativeReals,
    doc="Capacity of plant i in cases",
)
model.b = pyo.Param(
    model.j, initialize=data["b"], mutable=True, within=pyo.NonNegativeReals,
    doc="Demand at market j in cases",
)
model.d = pyo.Param(
    model.i, model.j, initialize=data["d"], mutable=True, within=pyo.NonNegativeReals,
    doc="Distance in thousands of miles",
)
model.f = pyo.Param(
    initialize=float(data["f"]), mutable=True, within=pyo.NonNegativeReals,
    doc="Freight in dollars per case per thousand miles",
)

def c_init(model, i, j):
    return model.f * model.d[i, j] / 1000.0

model.c = pyo.Param(
    model.i, model.j, initialize=c_init, mutable=True, within=pyo.NonNegativeReals,
    doc="Transport cost in thousands of dollars per case",
)

# Variables
model.x = pyo.Var(model.i, model.j, domain=pyo.NonNegativeReals, doc="Shipment quantities in cases")
model.z = pyo.Var(domain=pyo.Reals, doc="Total transportation cost in thousands of dollars")

# Constraints
def cost_rule(model):
    return model.z == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)
model.cost = pyo.Constraint(rule=cost_rule, doc="Define objective function")

def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= model.a[i]
model.supply = pyo.Constraint(model.i, rule=supply_rule, doc="Observe supply limit at plant i")

def demand_rule(model, j):
    return sum(model.x[i, j] for i in model.i) >= model.b[j]
model.demand = pyo.Constraint(model.j, rule=demand_rule, doc="Satisfy demand at market j")

# Objective
model.obj = pyo.Objective(expr=model.z, sense=pyo.minimize, doc="Minimize total transportation cost")
