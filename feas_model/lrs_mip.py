# converted from gamslib lrs (LRS, SEQ=312)
# Linear Recursive Sequence Optimization Model.
# Given a 0/1 observation sequence c(t), find the linear recursive sequence
#     k(t) = k(t-n) XOR k(t-(n-r))   (mod 2),  t = n+1, ..., card(t)
# that minimizes the number of disagreements between c(t) and k(t).
# Only k(1..n) are binary decision variables; k(t) for t>n are continuous in
# [0,1] and assume binary values automatically once k(1..n) are fixed.
# The XOR recurrence is linearized with four mixed-integer inequalities.
#
# This converts the single primary optimization model `lrs` (GAMS line 100,
# OBJECTIVE VALUE 111). The iterative `lrssub` decomposition re-solves are
# dropped; the full model reproduces the same optimum on its own.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# Sectioned JSON ({sets, scalar_params, indexed_params}) is normalized upstream.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# Integer time indices (set members arrive as strings; coerce for lag arithmetic).
t_members = sorted(int(x) for x in data["t"])
f_members = sorted(int(x) for x in data["f"])
c_init = {int(k): float(v) for k, v in data["c"].items()}

# Recurrence structure (n = card(f), r given, n_minus_r = n - r).
n = int(round(float(data["n"])))
r = int(round(float(data["r"])))
n_minus_r = int(round(float(data["n_minus_r"])))

f_set = set(f_members)

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Linear Recursive Sequence fitting (XOR recurrence, MIP)")

# Sets
model.t = pyo.Set(initialize=t_members, ordered=True, doc="Time horizon")
model.f = pyo.Set(initialize=f_members, ordered=True, doc="First n steps (binary k)")

# Parameters
model.c = pyo.Param(
    model.t,
    initialize=c_init,
    mutable=True,
    within=pyo.Binary,
    doc="Observed 0/1 sequence to fit",
)
model.n = pyo.Param(initialize=n, mutable=True, within=pyo.NonNegativeReals, doc="Recurrence order = card(f)")
model.r = pyo.Param(initialize=r, mutable=True, within=pyo.NonNegativeReals, doc="Recurrence shift parameter")
model.n_minus_r = pyo.Param(initialize=n_minus_r, mutable=True, within=pyo.NonNegativeReals, doc="n - r")

# Variables
# k(t): binary for t in f (first n), continuous in [0,1] otherwise.
def k_domain(model, tt):
    return pyo.Binary if tt in f_set else pyo.UnitInterval

model.k = pyo.Var(model.t, domain=k_domain, doc="Recursive sequence (binary on f, continuous elsewhere)")

model.z = pyo.Var(domain=pyo.Reals, doc="Objective: number of disagreements")

# Recurrence index set: t for which k(t) = k(t-n) XOR k(t-(n-r)) is defined,
# i.e. t = n+1, ..., last  (302 constraints for n=48, t up to 350).
rec_t = [tt for tt in t_members if tt - n >= t_members[0] and tt - n_minus_r >= t_members[0]]

# Objective constraint: z counts disagreements.
#   c(t)=0 -> penalize k(t)=1  (add k(t))
#   c(t)=1 -> penalize k(t)=0  (add 1 - k(t))
def obj_rule(model):
    return model.z == sum(
        (model.k[tt] if pyo.value(model.c[tt]) == 0 else (1 - model.k[tt]))
        for tt in model.t
    )

model.objdef = pyo.Constraint(rule=obj_rule, doc="Disagreement count accounting")

# XOR linearization: k(t) = k(t-n) XOR k(t-(n-r))
def modup1_rule(model, tt):
    return model.k[tt] <= model.k[tt - n] + model.k[tt - n_minus_r]

def modup2_rule(model, tt):
    return model.k[tt] <= 2 - model.k[tt - n] - model.k[tt - n_minus_r]

def modlo1_rule(model, tt):
    return model.k[tt] >= -model.k[tt - n] + model.k[tt - n_minus_r]

def modlo2_rule(model, tt):
    return model.k[tt] >= model.k[tt - n] - model.k[tt - n_minus_r]

model.modup1 = pyo.Constraint(rec_t, rule=modup1_rule, doc="XOR upper bound (false,false)")
model.modup2 = pyo.Constraint(rec_t, rule=modup2_rule, doc="XOR upper bound (true,true)")
model.modlo1 = pyo.Constraint(rec_t, rule=modlo1_rule, doc="XOR lower bound (false,true)")
model.modlo2 = pyo.Constraint(rec_t, rule=modlo2_rule, doc="XOR lower bound (true,false)")

# Objective
model.obj = pyo.Objective(expr=model.z, sense=pyo.minimize, doc="Minimize disagreements")
