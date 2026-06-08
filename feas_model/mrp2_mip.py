# converted from gamslib mrp2 (MRP2, SEQ=207)
# Materials Requirement Planning, MIP formulation (mrp2l: capacity + lot-sizing).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "LQ8811|AJ8172": value → tuple key).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Materials Requirement Planning (MRP2) - MIP lot-sizing with capacity")

# Sets
model.PP = pyo.Set(initialize=data["PP"], ordered=True, doc="SKU numbers")
model.TT = pyo.Set(initialize=data["TT"], ordered=True, doc="Time buckets")
model.KK = pyo.Set(initialize=data["KK"], ordered=True, doc="Resources")

# Parameters
model.R = pyo.Param(
    model.PP, model.PP,
    initialize=data["R"],
    default=0.0,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Number of component i needed to make one parent j (bill of materials)",
)

model.demand = pyo.Param(
    model.PP, model.TT,
    initialize=data["demand"],
    default=0.0,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="External demand for an item in a period",
)

model.LT = pyo.Param(
    model.PP,
    initialize=data["LT"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Lead time",
)

model.LS = pyo.Param(
    model.PP,
    initialize=data["LS"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Lot size",
)

model.I = pyo.Param(
    model.PP,
    initialize=data["I"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Beginning inventory",
)

model.U = pyo.Param(
    model.PP, model.KK,
    initialize=data["U"],
    default=0.0,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Fraction of resource k needed by one unit of i",
)

model.M = pyo.Param(
    model.PP,
    initialize=data["M"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Big-M for production-indicator linking constraint",
)

# Variables
model.d = pyo.Var(
    model.PP, model.TT,
    domain=pyo.Binary,
    doc="Production indicator (1 if SKU produced in period)",
)

model.x = pyo.Var(
    model.PP, model.TT,
    domain=pyo.NonNegativeReals,
    doc="Number of SKUs to produce in period",
)

model.objvar = pyo.Var(domain=pyo.Reals, doc="Objective value")

# Helper: ordinal positions (1-based) for time buckets
_TT = list(model.TT)
_card = len(_TT)
_ord = {t: i + 1 for i, t in enumerate(_TT)}

# Constraints
def defobj_rule(model):
    return model.objvar == sum(
        (_card - _ord[t] + 1) * model.x[p, t] for p in model.PP for t in model.TT
    )
model.defobj = pyo.Constraint(rule=defobj_rule, doc="Objective accounting (weighted production)")

def defreq_rule(model, p, t):
    # production-on-hand (respecting lead time) + beginning inventory
    # must cover cumulative external + dependent demand up to period t
    lhs = sum(
        model.x[p, tp] for tp in model.TT if _ord[tp] <= _ord[t] - pyo.value(model.LT[p])
    ) + model.I[p]
    rhs = sum(
        model.demand[p, tp] + sum(model.R[p, pp] * model.x[pp, tp] for pp in model.PP)
        for tp in model.TT if _ord[tp] <= _ord[t]
    )
    return lhs >= rhs
model.defreq = pyo.Constraint(model.PP, model.TT, rule=defreq_rule, doc="Material requirement")

def deflot_rule(model, p, t):
    return model.x[p, t] >= model.d[p, t] * model.LS[p]
model.deflot = pyo.Constraint(model.PP, model.TT, rule=deflot_rule, doc="Lot size lower bound")

def defprod_rule(model, p, t):
    return model.x[p, t] <= model.d[p, t] * model.M[p]
model.defprod = pyo.Constraint(model.PP, model.TT, rule=defprod_rule, doc="Production indicator big-M")

def defcap_rule(model, t, k):
    return sum(model.U[p, k] * model.x[p, t] for p in model.PP) <= 1
model.defcap = pyo.Constraint(model.TT, model.KK, rule=defcap_rule, doc="Resource capacity")

# Objective
model.obj = pyo.Objective(
    expr=model.objvar,
    sense=pyo.minimize,
    doc="Minimize weighted (earliness-penalized) production",
)
