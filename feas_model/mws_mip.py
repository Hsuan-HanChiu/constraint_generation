# converted from models/mws_mip.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

import math

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="Maximum Weighted Score estimator for work-trip mode choice model"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.p = Set(
    initialize=data["p"],
    doc="Explanatory variables"
)

model.T = Set(
    initialize=data["T"],
    doc="Sample size (households)"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK (all mutable = True)
# ----------------------------------------------------------------------
# Extract X data (only for p columns) and y data (DEPEND column)
X_data_filtered = {}
y_data = {}

for key, val in data["X"].items():
    if isinstance(key, tuple) and len(key) == 2:
        t, col = key
        if col in data["p"]:
            X_data_filtered[key] = val
        elif col == "DEPEND":
            y_data[t] = val

model.X = Param(
    model.T, model.p,
    initialize=X_data_filtered,
    mutable=True,
    doc="Explanatory variables"
)

model.y = Param(
    model.T,
    initialize=y_data,
    mutable=True,
    doc="Binary dependent variable"
)

model.delta = Param(
    initialize=data["delta"],
    mutable=True,
    doc="Domain for every parameter to be estimated"
)

model.normalize_X = Param(
    initialize=data.get("normalize_X", 1),
    mutable=True,
    doc="Whether to normalize X"
)

# Pre-compute mean and stdev for normalization
mean_dict = {}
stdev_dict = {}
p_list = list(model.p)
T_list = list(model.T)
card_T = len(T_list)

for p in p_list:
    # Compute mean
    sum_val = sum(X_data_filtered.get((t, p), 0) for t in T_list)
    mean_val = sum_val / card_T
    mean_dict[p] = mean_val

    # Compute stdev
    sum_sq = sum((X_data_filtered.get((t, p), 0) - mean_val)**2 for t in T_list)
    stdev_val = math.sqrt(sum_sq / (card_T - 1))
    stdev_dict[p] = stdev_val

def init_mean(model):
    return mean_dict

model.mean = Param(
    model.p,
    initialize=init_mean,
    mutable=True,
    doc="Average of X over T"
)

def init_stdev(model):
    return stdev_dict

model.stdev = Param(
    model.p,
    initialize=init_stdev,
    mutable=True,
    doc="Standard deviation of X over T"
)

# Pre-compute normalized X
Xnms_dict = {}
normalize = data.get("normalize_X", 1)

for t in T_list:
    for p in p_list:
        x_val = X_data_filtered.get((t, p), 0)
        if normalize == 1:
            if stdev_dict[p] > 0:
                Xnms_dict[(t, p)] = (x_val - mean_dict[p]) / stdev_dict[p]
            else:
                Xnms_dict[(t, p)] = 1
        else:
            Xnms_dict[(t, p)] = x_val

def init_Xnms(model):
    return Xnms_dict

model.Xnms = Param(
    model.T, model.p,
    initialize=init_Xnms,
    mutable=True,
    doc="Normalized X matrix"
)

# Pre-compute omega (big M coefficients)
omega_dict = {}
delta_val = data["delta"]
p_ord = {p: i+1 for i, p in enumerate(p_list)}

for t in T_list:
    omega_val = 0
    for p in p_list:
        xnms_val = Xnms_dict.get((t, p), 0)
        if p_ord[p] == 1:
            omega_val += abs(xnms_val)
        else:
            omega_val += delta_val * abs(xnms_val)
    omega_dict[t] = omega_val

def init_omega(model):
    return omega_dict

model.omega = Param(
    model.T,
    initialize=init_omega,
    mutable=True,
    doc="Big M coefficient for disjunctive constraints"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.z = Var(
    model.T,
    domain=Binary,
    doc="Indicates if sign coincidence for y and linear combination of X"
)

model.beta = Var(
    model.p,
    domain=Reals,
    bounds=(-delta_val, delta_val),
    doc="Vector components to estimate in max weighted score"
)

model.mws = Var(
    domain=Reals,
    doc="Objective variable"
)

# Fix beta for first parameter (ord(p) = 1)
first_p = p_list[0]
model.beta[first_p].fix(1)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.mws

model.obj = Objective(
    rule=obj_rule,
    sense=maximize,
    doc="Maximize weighted number of sign coincidences"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# objfun: mws = sum of z(T)
def objfun_rule(model):
    return model.mws == sum(model.z[t] for t in model.T)

model.objfun = Constraint(
    rule=objfun_rule,
    doc="Objective function is weighted number of sign coincidences"
)

# cosg(T): sign coincidence constraint between y and X*beta
# (1 - 2*y(T))*sum(p, beta(p)*Xnms(T,p)) <= omega(T)*(1 - z(T))
def cosg_rule(model, t):
    y_val = y_data.get(t, 0)
    return (
        (1 - 2*y_val) * sum(model.beta[p] * Xnms_dict[(t, p)] for p in model.p)
        <= omega_dict[t] * (1 - model.z[t])
    )

model.cosg = Constraint(
    model.T,
    rule=cosg_rule,
    doc="Sign coincidence constraint between y and X*beta"
)
