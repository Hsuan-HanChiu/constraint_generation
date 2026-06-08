# converted from models/prodsp_lp.py
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
    doc="Stochastic Programming - Production planning with uncertain labor requirements"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.i = Set(
    initialize=data["i"],
    doc="Product classes"
)

model.j = Set(
    initialize=data["j"],
    doc="Workstations"
)

model.s = Set(
    initialize=data["s"],
    doc="Scenarios (nodes)"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK (all mutable = True)
# ----------------------------------------------------------------------
model.c = Param(
    model.i,
    initialize=data["c"],
    mutable=True,
    doc="Profit per product"
)

model.q = Param(
    model.j,
    initialize=data["q"],
    mutable=True,
    doc="Cost of purchasing labor"
)

# Pre-compute random data with fixed seed for reproducibility
seed = data.get("random_seed", 3571)
random.seed(seed)

# Generate t(j,i,s) = uniform(trand(j,'min',i), trand(j,'max',i))
t_dict = {}
for j in data["j"]:
    for i in data["i"]:
        min_val = data["trand"][(j, "min", i)]
        max_val = data["trand"][(j, "max", i)]
        for s in data["s"]:
            t_dict[(j, i, s)] = random.uniform(min_val, max_val)

model.t = Param(
    model.j, model.i, model.s,
    initialize=t_dict,
    mutable=True,
    doc="Labor required per product per scenario"
)

# Generate h(j,s) using normal distribution
# h('work-1',s) = normal(6000, 100)
# h('work-2',s) = normal(4000, 50)
h_dict = {}
for s in data["s"]:
    h_dict[("work-1", s)] = random.gauss(data["h_work1_mean"], data["h_work1_std"])
    h_dict[("work-2", s)] = random.gauss(data["h_work2_mean"], data["h_work2_std"])

model.h = Param(
    model.j, model.s,
    initialize=h_dict,
    mutable=True,
    doc="Available labor per workstation per scenario"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.EProfit = Var(
    domain=Reals,
    doc="Expected profit"
)

model.x = Var(
    model.i,
    domain=NonNegativeReals,
    doc="Products sold"
)

model.v = Var(
    model.j, model.s,
    domain=NonNegativeReals,
    doc="Labor purchased per workstation per scenario"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.EProfit

model.obj = Objective(
    rule=obj_rule,
    sense=maximize,
    doc="Maximize expected profit"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# obj: EProfit = sum(i, c(i)*x(i)) - 1/card(s)*sum((j,s), q(j)*v(j,s))
def obj_def_rule(model):
    card_s = len(data["s"])
    return (model.EProfit ==
            sum(model.c[i] * model.x[i] for i in model.i) -
            (1.0 / card_s) * sum(model.q[j] * model.v[j, s]
                                  for j in model.j for s in model.s))

model.obj_def = Constraint(
    rule=obj_def_rule,
    doc="Expected profit definition"
)

# foo(i): x(i) >= 0 (dummy stage 0 constraint for OSLSE)
# This is already handled by domain=NonNegativeReals for x
def foo_rule(model, i):
    return model.x[i] >= 0

model.foo = Constraint(
    model.i,
    rule=foo_rule,
    doc="Dummy stage 0 constraint"
)

# lbal(j,s): sum(i, t(j,i,s)*x(i)) <= h(j,s) + v(j,s)
def lbal_rule(model, j, s):
    return (sum(t_dict[(j, i, s)] * model.x[i] for i in model.i) <=
            h_dict[(j, s)] + model.v[j, s])

model.lbal = Constraint(
    model.j, model.s,
    rule=lbal_rule,
    doc="Labor balance"
)
