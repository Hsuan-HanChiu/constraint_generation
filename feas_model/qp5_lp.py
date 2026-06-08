# converted from gamslib qp5 (QP5, SEQ=175)
# Linear approximation of qp4 (portfolio mean-absolute-deviation model).
# Despite the "qp" name, the GAMS model solves "using lp": the objective and all
# constraints are linear, so this is an LP.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "GAB|960102": value → (GAB, 960102)).
# mean(s), dev(s,d) and totmean are the GAMS-derived parameters of the selected
# subset (50 stocks, 29 days).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="QP5 - linear approximation of mean-absolute-deviation portfolio model")

# Sets
model.s = pyo.Set(initialize=data["s"], doc="Selected stocks")
model.d = pyo.Set(initialize=data["d"], doc="Selected days")

# Parameters
model.mean = pyo.Param(
    model.s,
    initialize=data["mean"],
    mutable=True,
    within=pyo.Reals,
    doc="Mean of daily return for each stock",
)

model.dev = pyo.Param(
    model.s, model.d,
    initialize=data["dev"],
    mutable=True,
    within=pyo.Reals,
    doc="Deviation of daily return from its mean",
)

model.totmean = pyo.Param(
    initialize=data["totmean"],
    mutable=True,
    within=pyo.Reals,
    doc="Total (average) mean return across selected stocks",
)

# Variables
model.x = pyo.Var(
    model.s,
    domain=pyo.NonNegativeReals,
    doc="Investments (portfolio weights)",
)

model.wplus = pyo.Var(
    model.d,
    domain=pyo.NonNegativeReals,
    doc="Intermediate variable: positive part of deviation",
)

model.wmin = pyo.Var(
    model.d,
    domain=pyo.NonNegativeReals,
    doc="Intermediate variable: negative part of deviation",
)

model.z = pyo.Var(
    domain=pyo.Reals,
    doc="Objective variable: total absolute deviation",
)

# Constraints
def wdef_rule(model, dd):
    return model.wplus[dd] - model.wmin[dd] == sum(model.x[ss] * model.dev[ss, dd] for ss in model.s)

model.wdef = pyo.Constraint(model.d, rule=wdef_rule, doc="Definition of positive/negative deviation parts")

def budget_rule(model):
    return sum(model.x[ss] for ss in model.s) == 1.0

model.budget = pyo.Constraint(rule=budget_rule, doc="Budget: portfolio weights sum to 1")

def retcon_rule(model):
    return sum(model.mean[ss] * model.x[ss] for ss in model.s) >= model.totmean * 1.25

model.retcon = pyo.Constraint(rule=retcon_rule, doc="Return constraint: portfolio mean return at least 1.25 x totmean")

def zdef_rule(model):
    return model.z == sum(model.wplus[dd] + model.wmin[dd] for dd in model.d)

model.zdef = pyo.Constraint(rule=zdef_rule, doc="Accounting: objective variable equals total absolute deviation")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.minimize,
    doc="Minimize total absolute deviation",
)
