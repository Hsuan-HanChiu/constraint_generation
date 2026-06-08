# converted from models/asyncloop_lp.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

import random

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="Transportation Problem with Async Loop (Sequential Version)"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.i = Set(
    initialize=data["i"],
    doc="Canning plants"
)

model.j = Set(
    initialize=data["j"],
    doc="Markets"
)

model.s = Set(
    initialize=data["s"],
    doc="Scenarios"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------
# Pre-compute parameters from data
a_dict = {}
for key, val in data["a"].items():
    if isinstance(key, tuple) and len(key) == 1:
        a_dict[key[0]] = val
    else:
        a_dict[key] = val

b_dict = {}
for key, val in data["b"].items():
    if isinstance(key, tuple) and len(key) == 1:
        b_dict[key[0]] = val
    else:
        b_dict[key] = val

d_dict = {}
for key, val in data["d"].items():
    if isinstance(key, tuple):
        d_dict[key] = val
    else:
        d_dict[key] = val

# Convert integer tuple keys to string tuple keys if needed
d_dict_str = {}
for key, val in d_dict.items():
    if isinstance(key, tuple):
        str_key = tuple(str(k) for k in key)
        d_dict_str[str_key] = val
    else:
        d_dict_str[key] = val
d_dict = d_dict_str

model.a = Param(
    model.i,
    initialize=a_dict,
    mutable=True,
    doc="Capacity of plant i in cases"
)

model.b = Param(
    model.j,
    initialize=b_dict,
    mutable=True,
    doc="Demand at market j in cases"
)

model.d = Param(
    model.i, model.j,
    initialize=d_dict,
    mutable=True,
    default=0,
    doc="Distance in thousands of miles"
)

model.f = Param(
    initialize=data.get("f", 90),
    mutable=True,
    doc="Freight in dollars per case per thousand miles"
)

model.pen = Param(
    initialize=data.get("pen", 1000),
    mutable=True,
    doc="Penalty for unfilled demand"
)

# Compute transport cost c(i,j) = f * d(i,j) / 1000
c_dict = {}
f_val = data.get("f", 90)
for i in data["i"]:
    for j in data["j"]:
        c_dict[(i, j)] = f_val * d_dict.get((i, j), 0) / 1000.0

model.c = Param(
    model.i, model.j,
    initialize=c_dict,
    mutable=True,
    doc="Transport cost in thousands of dollars per case"
)

# Generate random bmult values for scenarios
seed = data.get("random_seed", 12345)
random.seed(seed)
bmult_dict = {}
for s in data["s"]:
    bmult_dict[s] = random.uniform(0.9, 1.1)

model.bmult = Param(
    model.s,
    initialize=bmult_dict,
    mutable=True,
    doc="Random multiplier for demand in each scenario"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.x = Var(
    model.i, model.j,
    domain=NonNegativeReals,
    doc="Shipment quantities in cases"
)

model.slack = Var(
    model.j,
    domain=NonNegativeReals,
    doc="Slack for unfilled demand"
)

model.z = Var(
    doc="Total transportation costs in thousands of dollars"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
# For compatibility with run.py, create obj as an alias to z
def obj_rule(model):
    return model.z

model.obj = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Minimize total transportation costs"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# cost.. z =e= sum((i,j), c(i,j)*x(i,j)) + pen*sum(j, slack(j))
def cost_constraint_rule(model):
    return model.z == sum(
        model.c[i, j] * model.x[i, j] for i in model.i for j in model.j
    ) + model.pen * sum(model.slack[j] for j in model.j)

model.cost_constraint = Constraint(
    rule=cost_constraint_rule,
    doc="Define objective function"
)

# supply(i).. sum(j, x(i,j)) =l= a(i)
def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= model.a[i]

model.supply = Constraint(
    model.i,
    rule=supply_rule,
    doc="Observe supply limit at plant i"
)

# demand(j).. sum(i, x(i,j)) =g= b(j) + slack(j)
# This means: shipment + slack >= demand
# Which is equivalent to: shipment >= demand - slack
# Slack represents unfilled demand
def demand_rule(model, j):
    return sum(model.x[i, j] for i in model.i) + model.slack[j] >= model.b[j]

model.demand = Constraint(
    model.j,
    rule=demand_rule,
    doc="Satisfy demand at market j"
)
