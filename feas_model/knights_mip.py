# converted from gamslib knights (KNIGHTS, SEQ=158)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "h|m1": value → ("h", "m1"): value).
#
# This is the "tight" knightx formulation of the Maximum Knights Problem:
# place as many knights as possible on an 8x8 board so that no two attack each
# other. The original GAMS file then loops to enumerate ALL max-knight
# arrangements; that enumeration loop ends Integer-Infeasible once solutions are
# exhausted. We keep only the single deterministic max-placement MIP, whose
# optimum is 32 knights.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Maximum Knights Problem - max non-attacking knights on a board")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="board coordinates (rows / columns)")
model.n = pyo.Set(initialize=data["n"], doc="possible knight moves")
model.axis = pyo.Set(initialize=data["axis"], doc="move axis: horizontal (h) / vertical (v)")

# Parameters
model.move = pyo.Param(
    model.axis, model.n,
    initialize=data["move"],
    mutable=True,
    within=pyo.Integers,
    doc="relative position (lag) of each allowed knight move along each axis",
)

# Variables
model.x = pyo.Var(
    model.i, model.i,
    domain=pyo.Binary,
    doc="1 if a knight is placed on cell (i, j)",
)

model.total = pyo.Var(
    domain=pyo.Reals,
    doc="total number of knights placed on the board",
)

# Helper: board coordinates are integers 1..card(i)
_coords = [int(c) for c in data["i"]]


def _on_board(c):
    return c in _coords


# Constraints
def deftotal_rule(model):
    return model.total == sum(model.x[i, j] for i in model.i for j in model.i)


model.deftotal = pyo.Constraint(rule=deftotal_rule, doc="total knights on board")


def defmovex_rule(model, n, i, j):
    ti = int(i) + int(pyo.value(model.move["h", n]))
    tj = int(j) + int(pyo.value(model.move["v", n]))
    if not (_on_board(ti) and _on_board(tj)):
        return pyo.Constraint.Skip
    return model.x[str(ti), str(tj)] + model.x[i, j] <= 1


model.defmovex = pyo.Constraint(
    model.n, model.i, model.i,
    rule=defmovex_rule,
    doc="non-attacking restriction: a knight and any cell it attacks cannot both hold knights",
)

# Objective
model.obj = pyo.Objective(
    expr=model.total,
    sense=pyo.maximize,
    doc="Maximize the number of knights placed",
)
