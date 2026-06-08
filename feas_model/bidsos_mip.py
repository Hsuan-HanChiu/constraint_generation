# converted from gamslib bidsos (BIDSOS, SEQ=163)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "a|1": value → (a, 1): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Bid Evaluation with SOS2 Sets - minimize total purchase cost")

# Sets
model.v = pyo.Set(initialize=data["v"], doc="Vendors")
model.s = pyo.Set(initialize=data["s"], ordered=True, doc="Bid segments (ordered for SOS2)")
model.vs = pyo.Set(
    within=model.v * model.s,
    initialize=data["vs"],
    doc="Active (vendor, segment) bid possibilities",
)

# Parameters
model.req = pyo.Param(
    initialize=data["req"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Required number of units to purchase",
)

model.qmax = pyo.Param(
    model.vs,
    initialize=data["qmax"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Upper quantity bound of each (vendor, segment) bid",
)

model.cost = pyo.Param(
    model.vs,
    initialize=data["cost"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Total segment cost of each (vendor, segment) bid",
)

# Variables
model.pl = pyo.Var(
    model.vs,
    domain=pyo.NonNegativeReals,
    doc="Purchase level (SOS2 interpolation weight) per (vendor, segment)",
)

model.c = pyo.Var(
    domain=pyo.Reals,
    doc="Total cost",
)

# Constraints
def demand_rule(model):
    return model.req == sum(model.qmax[v, s] * model.pl[v, s] for (v, s) in model.vs)

model.demand = pyo.Constraint(rule=demand_rule, doc="Demand: weighted quantities meet requirement")

def costdef_rule(model):
    return model.c == sum(model.cost[v, s] * model.pl[v, s] for (v, s) in model.vs)

model.costdef = pyo.Constraint(rule=costdef_rule, doc="Cost definition: weighted segment costs")

def convex_rule(model, vv):
    return sum(model.pl[v, s] for (v, s) in model.vs if v == vv) == 1

model.convex = pyo.Constraint(model.v, rule=convex_rule, doc="Convexity: weights per vendor sum to 1")

# SOS2 sets (one per vendor): purchase-level weights over that vendor's
# segments form a special ordered set of type 2 (at most two adjacent nonzero).
def sos_rule(model, vv):
    return [model.pl[v, s] for (v, s) in model.vs if v == vv]

model.sos = pyo.SOSConstraint(model.v, rule=sos_rule, sos=2)

# Objective
model.obj = pyo.Objective(
    expr=model.c,
    sense=pyo.minimize,
    doc="Minimize total purchase cost",
)
