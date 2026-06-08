# converted from gamslib bchstock (BCHSTOCK, SEQ=349)
#
# Cutting-stock master problem (Gilmore-Gomory column generation).
# The original GAMS model solves the LP relaxation, then uses a BCH pricing
# callback to generate cutting patterns, and finally re-solves the master as a
# MIP over the full pattern set (objective = 453 rolls). The BCH callbacks are
# a solve-time mechanism only: here we build the single core MIP directly over
# the final pattern set (initial single-width patterns p1-p4 plus the two
# generated columns p5,p6; p7-p10 are unused empty slots).
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
model = pyo.ConcreteModel(doc="Cutting Stock - minimize number of raw paper rolls used")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Widths (paper products to cut)")
model.p = pyo.Set(initialize=data["p"], doc="Cutting patterns")

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
    doc="Width of each product",
)

model.d = pyo.Param(
    model.i,
    initialize=data["d"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Demand for each width",
)

model.aip = pyo.Param(
    model.i, model.p,
    initialize=data["aip"],
    default=0,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Number of width i produced by pattern p",
)

# Variables
model.xp = pyo.Var(
    model.p,
    domain=pyo.NonNegativeIntegers,
    bounds=(0, sum(data["d"].values())),
    doc="Number of times each pattern is used",
)

model.z = pyo.Var(
    domain=pyo.NonNegativeReals,
    doc="Total number of patterns (raw rolls) used",
)

# Constraints
def numpat_rule(model):
    return sum(model.xp[p] for p in model.p) == model.z

model.numpat = pyo.Constraint(rule=numpat_rule, doc="Number of patterns (rolls) used")

def demand_rule(model, i):
    return sum(model.aip[i, p] * model.xp[p] for p in model.p) >= model.d[i]

model.demand = pyo.Constraint(model.i, rule=demand_rule, doc="Meet demand for each width")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.minimize,
    doc="Minimize the number of raw rolls used",
)
