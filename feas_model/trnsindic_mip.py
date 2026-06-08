# converted from gamslib trnsindic (TRNSINDIC, SEQ=412)
# Fixed-charge transportation problem with indicator/big-M logic.
# Core model: bigMModel (transport + binary arc-use with min-ship and zero-if-unused logic).
# Scenario/reporting re-solves (indicatorModel, indicatorbigMModel variants) are dropped.
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
model = pyo.ConcreteModel(doc="Fixed-charge transportation with indicator constraints")

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

model.fixcost = pyo.Param(
    model.i, model.j,
    initialize=data["fixcost"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Fixed cost in thousands of dollars if arc used",
)

model.minshipping = pyo.Param(
    initialize=data["minshipping"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Minimum shipping of cases on a used arc",
)

model.bigM = pyo.Param(
    initialize=data["bigM"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Sufficiently large number (max plant capacity)",
)

# Variables
model.x = pyo.Var(
    model.i, model.j,
    domain=pyo.NonNegativeReals,
    doc="Shipment quantities in cases",
)

model.use = pyo.Var(
    model.i, model.j,
    domain=pyo.Binary,
    doc="1 if arc (i,j) is used in solution",
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

def minship_rule(model, i, j):
    return model.x[i, j] >= model.minshipping * model.use[i, j]

model.minship = pyo.Constraint(model.i, model.j, rule=minship_rule, doc="Ensure minimum shipping on a used arc")

def maxship_rule(model, i, j):
    return model.x[i, j] <= model.bigM * model.use[i, j]

model.maxship = pyo.Constraint(model.i, model.j, rule=maxship_rule, doc="Ensure zero shipping if arc not used")

def cost_rule(model):
    return model.z == sum(
        model.c[i, j] * model.x[i, j] + model.fixcost[i, j] * model.use[i, j]
        for i in model.i for j in model.j
    )

model.cost = pyo.Constraint(rule=cost_rule, doc="Define total transportation cost")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.minimize,
    doc="Minimize total transportation cost",
)
