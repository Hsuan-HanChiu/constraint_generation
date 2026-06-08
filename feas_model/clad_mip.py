# converted from gamslib clad (CLAD, SEQ=397)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "1|Age": value → (1, Age): value).
#
# Censored Least Absolute Deviations (Powell, 1984) estimator computed via the
# MIP formulation of Bilias, Florios & Skouras for Fair's extramarital-affairs
# data (601 households). The survey design matrix has already been mean/variance
# normalized (normalize_X = normalize_y = 1), so Xnms, ynms, omega and the
# disjunctive RHS are carried directly as data.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Censored Least Absolute Deviations estimator (MIP)")

# Sets
model.T = pyo.Set(initialize=data["T"], doc="Sample households (sample size)")
model.p = pyo.Set(initialize=data["p"], doc="Explanatory variables (regressors)")

# Parameters
model.Xnms = pyo.Param(
    model.T, model.p,
    initialize=data["Xnms"],
    mutable=True,
    within=pyo.Reals,
    doc="Normalized design matrix X (unit-variance columns)",
)

model.ynms = pyo.Param(
    model.T,
    initialize=data["ynms"],
    mutable=True,
    within=pyo.Reals,
    doc="Normalized left-censored dependent variable y",
)

model.omega = pyo.Param(
    model.T,
    initialize=data["omega"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Tight valid big-M coefficient for the disjunctive constraints",
)

model.RHS = pyo.Param(
    initialize=data["RHS"],
    mutable=True,
    within=pyo.Reals,
    doc="Normalized censoring threshold (RHS of disjunctive constraints)",
)

model.delta = pyo.Param(
    initialize=data["delta"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Box domain half-width for each estimated parameter",
)

# Variables
model.beta = pyo.Var(
    model.p,
    domain=pyo.Reals,
    doc="Beta coefficients to be estimated",
)

model.phi = pyo.Var(
    model.T,
    domain=pyo.Reals,
    doc="Substitutes max(X(T,p)*beta(p), 0)",
)

model.gamma = pyo.Var(
    model.T,
    domain=pyo.Binary,
    doc="Auxiliary binary for the max() disjunction (phi computation)",
)

model.sm = pyo.Var(
    model.T,
    domain=pyo.NonNegativeReals,
    doc="Slack auxiliary variable for |.| in the objective",
)

model.sp = pyo.Var(
    model.T,
    domain=pyo.NonNegativeReals,
    doc="Surplus auxiliary variable for |.| in the objective",
)

# Constraints
def con_phi_a_rule(model, t):
    return model.phi[t] >= sum(model.beta[pp] * model.Xnms[t, pp] for pp in model.p)

model.con_phi_a = pyo.Constraint(model.T, rule=con_phi_a_rule, doc="phi >= X*beta")

def con_phi_b_rule(model, t):
    return model.phi[t] >= model.RHS

model.con_phi_b = pyo.Constraint(model.T, rule=con_phi_b_rule, doc="phi >= RHS")

def con_phi_c_rule(model, t):
    return model.phi[t] <= sum(model.beta[pp] * model.Xnms[t, pp] for pp in model.p) \
        + model.omega[t] * (1 - model.gamma[t])

model.con_phi_c = pyo.Constraint(model.T, rule=con_phi_c_rule, doc="phi <= X*beta + omega(1-gamma)")

def con_phi_d_rule(model, t):
    return model.phi[t] <= model.RHS + model.omega[t] * model.gamma[t]

model.con_phi_d = pyo.Constraint(model.T, rule=con_phi_d_rule, doc="phi <= RHS + omega*gamma")

def con_s_rule(model, t):
    return model.ynms[t] - model.phi[t] + model.sm[t] - model.sp[t] == 0

model.con_s = pyo.Constraint(model.T, rule=con_s_rule, doc="Residual split into slack/surplus")

# Objective
model.obj = pyo.Objective(
    expr=sum(model.sm[t] + model.sp[t] for t in model.T),
    sense=pyo.minimize,
    doc="Minimize sum of absolute (censored) deviations",
)
