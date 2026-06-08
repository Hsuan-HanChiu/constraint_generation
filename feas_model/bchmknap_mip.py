# converted from gamslib bchmknap (BCHMKNAP, SEQ=289)
# Underlying multi-knapsack MIP (the BCH branch-and-cut-and-heuristic facility
# in the GAMS source is only a solve enhancement; the model itself is a plain
# multi-knapsack and is converted/solved directly here).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "r1|c1": value → (r1, c1): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Multi Knapsack Problem (BCHMKNAP) - select columns to maximize value subject to row capacities")

# Sets
model.j = pyo.Set(initialize=data["j"], doc="Columns (items/projects)")
model.i = pyo.Set(initialize=data["i"], doc="Rows (knapsack capacity constraints)")

# Parameters
model.obj_coef = pyo.Param(
    model.j,
    initialize=data["obj"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Objective value of selecting each column",
)

model.rhs = pyo.Param(
    model.i,
    initialize=data["rhs"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Capacity (right-hand side) of each row",
)

# 'a' is sparse in GAMS (blank cells are zero); default missing entries to 0.
model.a = pyo.Param(
    model.i, model.j,
    initialize=data["a"],
    default=0.0,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Resource usage of each column in each row",
)

# Variables
model.x = pyo.Var(
    model.j,
    domain=pyo.Binary,
    doc="Select column j (1) or not (0)",
)

model.slack = pyo.Var(
    model.i,
    domain=pyo.NonNegativeReals,
    doc="Unused capacity (slack) in each row",
)

model.z = pyo.Var(
    domain=pyo.Reals,
    doc="Total objective value",
)

# Constraints
def mk_rule(model, i):
    return sum(model.a[i, j] * model.x[j] for j in model.j) + model.slack[i] == model.rhs[i]

model.mk = pyo.Constraint(model.i, rule=mk_rule, doc="Row capacity (knapsack) balance with slack")

def defobj_rule(model):
    return model.z == sum(model.obj_coef[j] * model.x[j] for j in model.j)

model.defobj = pyo.Constraint(rule=defobj_rule, doc="Accounting: total objective value")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.maximize,
    doc="Maximize total value of selected columns",
)
