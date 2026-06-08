# converted from gamslib epscmmip (EPSCMMIP, SEQ=384)
# Multi-objective multi-dimensional 0/1 knapsack, solved by the eps-constraint method.
#
# The original GAMS model is the AUGMECON2 *driver*: it solves the same MIP hundreds
# of times, sweeping an epsilon bound on the second objective to trace the whole
# Pareto front. We keep ONE representative deterministic MIP:
#   maximize the primary objective k1 = sum_j c1[j]*X[j]
#   subject to the knapsack constraints   sum_j a[i,j]*X[j] <= b[i]
#   and the eps-constraint on the secondary objective:  sum_j c2[j]*X[j] >= eps
# The eps loop is dropped. eps is a single mutable Param fixed at a representative
# mid-range value (see NOTE / _data.json).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(
    doc="eps-constraint multi-objective 0/1 multi-dimensional knapsack (single representative MIP)"
)

# Sets
model.J = pyo.Set(initialize=data["J"], doc="Items / decision variables")
model.I = pyo.Set(initialize=data["I"], doc="Knapsack (resource) constraints")

# Parameters
model.c1 = pyo.Param(
    model.J,
    initialize=data["c1"],
    mutable=True,
    within=pyo.Reals,
    doc="Primary objective (k1) coefficients per item",
)

model.c2 = pyo.Param(
    model.J,
    initialize=data["c2"],
    mutable=True,
    within=pyo.Reals,
    doc="Secondary objective (k2) coefficients per item",
)

model.a = pyo.Param(
    model.I, model.J,
    initialize=data["a"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Technological (resource-use) coefficients",
)

model.b = pyo.Param(
    model.I,
    initialize=data["b"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Right-hand side (capacity) of each knapsack constraint",
)

model.eps = pyo.Param(
    initialize=data["eps"],
    mutable=True,
    within=pyo.Reals,
    doc="Epsilon lower bound on the secondary objective k2 (representative value)",
)

# Variables
model.X = pyo.Var(
    model.J,
    domain=pyo.Binary,
    doc="Whether each item is selected",
)

# Constraints
def con_rule(model, i):
    return sum(model.a[i, j] * model.X[j] for j in model.J) <= model.b[i]

model.con = pyo.Constraint(model.I, rule=con_rule, doc="Knapsack resource limits")

def epscon_rule(model):
    return sum(model.c2[j] * model.X[j] for j in model.J) >= model.eps

model.epscon = pyo.Constraint(rule=epscon_rule, doc="eps-constraint on secondary objective k2")

# Objective
model.obj = pyo.Objective(
    expr=sum(model.c1[j] * model.X[j] for j in model.J),
    sense=pyo.maximize,
    doc="Maximize primary objective k1",
)
