# converted from gamslib coex (COEX, SEQ=219)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional members (e.g. "1|2|3|4" → (1, 2, 3, 4)).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Peacefully Coexisting Armies of Queens")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Size of chess board (board positions)")

# M(i,j,ii,jj): shared/conflicting positions where a black queen at (i,j) and a
# white queen at (ii,jj) would attack each other (same row, column, or diagonal).
model.M = pyo.Set(
    dimen=4,
    initialize=data["M"],
    doc="Shared positions on the board (attacking pairs)",
)

# Variables
model.b = pyo.Var(
    model.i, model.i,
    domain=pyo.Binary,
    doc="Square occupied by a black queen",
)

model.w = pyo.Var(
    model.i, model.i,
    domain=pyo.Binary,
    doc="Square occupied by a white queen",
)

model.tot = pyo.Var(
    domain=pyo.Reals,
    doc="Total queens in each army",
)

# Constraints
def eq1_rule(model, i, j, ii, jj):
    return model.b[i, j] + model.w[ii, jj] <= 1

model.eq1 = pyo.Constraint(model.M, rule=eq1_rule, doc="Keeps armies at peace")

def eq2_rule(model):
    return model.tot == sum(model.b[i, j] for i in model.i for j in model.i)

model.eq2 = pyo.Constraint(rule=eq2_rule, doc="Add up all the black queens")

def eq3_rule(model):
    return model.tot == sum(model.w[i, j] for i in model.i for j in model.i)

model.eq3 = pyo.Constraint(rule=eq3_rule, doc="Add up all the white queens")

# Objective
model.obj = pyo.Objective(
    expr=model.tot,
    sense=pyo.maximize,
    doc="Maximize total queens in each army",
)
