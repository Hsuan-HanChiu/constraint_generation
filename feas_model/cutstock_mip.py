# converted from gamslib cutstock (CUTSTOCK, SEQ=294)
# Gilmore-Gomory cutting stock. The original GAMS model solves this by
# column generation (an iterative loop of master RMIP + knapsack pricing).
# Here the column-generation loop is DROPPED: we use the final pattern set
# the GAMS run terminates with (6 patterns) and solve the standalone integer
# pattern-selection master, which reaches the known optimum of 453 rolls.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "w1|p1": value → (w1, p1): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Cutting Stock - integer pattern-selection master (minimize rolls)")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Finished widths to be produced")
model.p = pyo.Set(initialize=data["p"], doc="Available cutting patterns")

# Parameters
model.r = pyo.Param(
    initialize=data["r"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Raw roll width",
)

model.w = pyo.Param(
    model.i,
    initialize=data["w"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Width of each finished product i",
)

model.d = pyo.Param(
    model.i,
    initialize=data["d"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Demand (number of rolls required) for each width i",
)

model.aip = pyo.Param(
    model.i, model.p,
    initialize=data["aip"],
    default=0,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Number of width i produced by one application of pattern p",
)

# Variables
# Upper bound on any single pattern = total demand (mirrors xp.up in GAMS).
xp_ub = sum(value(model.d[i]) for i in model.i)

model.xp = pyo.Var(
    model.p,
    domain=pyo.NonNegativeIntegers,
    bounds=(0, xp_ub),
    doc="Number of raw rolls cut using pattern p",
)

# Constraints
def demand_rule(model, i):
    return sum(model.aip[i, p] * model.xp[p] for p in model.p) >= model.d[i]

model.demand = pyo.Constraint(model.i, rule=demand_rule, doc="Meet demand for each width")

# Objective
model.obj = pyo.Objective(
    expr=sum(model.xp[p] for p in model.p),
    sense=pyo.minimize,
    doc="Minimize total number of raw rolls used",
)
