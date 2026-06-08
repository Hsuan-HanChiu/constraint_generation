# converted from gamslib knapsack (KNAPSACK, SEQ=436)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "shop|desk": value → (shop, desk): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Binary Knapsack Problem - maximize utility within weight capacity")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Items")

# Parameters
model.p = pyo.Param(
    model.i,
    initialize=data["p"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Profit of each item",
)

model.w = pyo.Param(
    model.i,
    initialize=data["w"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Weight of each item",
)

model.c = pyo.Param(
    initialize=data["c"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Knapsack weight capacity",
)

# Variables
model.x = pyo.Var(
    model.i,
    domain=pyo.Binary,
    doc="1 if item is selected, 0 otherwise",
)

model.z = pyo.Var(
    domain=pyo.Reals,
    bounds=(0, None),
    doc="Total utility of the selection",
)

# Constraints
def cap_restr_rule(model):
    return sum(model.w[i] * model.x[i] for i in model.i) <= model.c

model.cap_restr = pyo.Constraint(rule=cap_restr_rule, doc="Capacity restriction (total weight)")

def utility_rule(model):
    return model.z == sum(model.p[i] * model.x[i] for i in model.i)

model.utility = pyo.Constraint(rule=utility_rule, doc="Accounting: total utility")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.maximize,
    doc="Maximize total utility",
)
