# converted from gamslib stablem (STABLEM, SEQ=389)
# Stable Marriage Problem (Gale-Shapley). Single feasible base MIP:
# minimize total woman preference rank subject to a perfect, stable matching.
# The GAMS source then loops adding MIP cuts to enumerate alternative stable
# matchings; the final cut-augmented solve becomes integer infeasible (no more
# distinct solutions). Those re-solves are dropped here — only the base
# feasible model is built. Dataset: premer (4 men, 4 women).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "Alice|Alan": value → (Alice, Alan)).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Stable Marriage Problem - minimize total woman preference rank over a stable perfect matching")

# Sets
model.m = pyo.Set(initialize=data["m"], doc="Men")
model.w = pyo.Set(initialize=data["w"], doc="Women")

# Parameters
model.wp = pyo.Param(
    model.w, model.m,
    initialize=data["wp"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Woman preferences: rank woman w assigns to man m (1 = most preferred)",
)

model.mp = pyo.Param(
    model.m, model.w,
    initialize=data["mp"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Man preferences: rank man m assigns to woman w (1 = most preferred)",
)

# Variables
model.match = pyo.Var(
    model.w, model.m,
    domain=pyo.Binary,
    doc="1 if woman w is matched with man m",
)

model.rank = pyo.Var(
    domain=pyo.Reals,
    doc="Total woman preference rank of the matching",
)

# Constraints
def onem_rule(model, w):
    return sum(model.match[w, m] for m in model.m) == 1

model.onem = pyo.Constraint(model.w, rule=onem_rule, doc="Each woman matched to exactly one man")

def onew_rule(model, m):
    return sum(model.match[w, m] for w in model.w) == 1

model.onew = pyo.Constraint(model.m, rule=onew_rule, doc="Each man matched to exactly one woman")

def stable_rule(model, w, m):
    # No blocking pair: if w prefers some man mm over m, and m prefers some woman
    # ww over w, then at most one of those better matches can be active.
    terms = [model.match[w, mm] for mm in model.m if pyo.value(model.wp[w, mm]) > pyo.value(model.wp[w, m])]
    terms += [model.match[ww, m] for ww in model.w if pyo.value(model.mp[m, ww]) > pyo.value(model.mp[m, w])]
    if not terms:
        # m is w's top man AND w is m's top woman → no better match exists; trivially satisfied.
        return pyo.Constraint.Skip
    return sum(terms) <= 1

model.stable = pyo.Constraint(model.w, model.m, rule=stable_rule, doc="Stability: no blocking pair")

def defrank_rule(model):
    return model.rank == sum(model.wp[w, m] * model.match[w, m] for w in model.w for m in model.m)

model.defrank = pyo.Constraint(rule=defrank_rule, doc="Accounting: total woman preference rank")

# Objective
model.obj = pyo.Objective(
    expr=model.rank,
    sense=pyo.minimize,
    doc="Minimize total woman preference rank (woman-pessimal / man-optimal not enforced; any min-rank stable matching)",
)
