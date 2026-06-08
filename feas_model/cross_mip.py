# converted from models/cross_mip.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="Alcuin's River Crossing Problem"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.i = Set(
    initialize=data["i"],
    doc="Items (goose, wolf, corn)"
)

model.t = Set(
    initialize=data["t"],
    doc="Time periods"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------
# dir(t) = power(-1, ord(t) - 1)
# This alternates: +1, -1, +1, -1, ... (near to far is +1, far to near is -1)
t_list = list(data["t"])
dir_dict = {}
for idx, t in enumerate(t_list):
    ord_t = idx + 1  # 1-based indexing
    dir_dict[t] = (-1) ** (ord_t - 1)

model.dir = Param(
    model.t,
    initialize=dir_dict,
    mutable=True,
    doc="Crossing direction: +1 near to far, -1 far to near"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.y = Var(
    model.i, model.t,
    domain=Binary,
    doc="1 iff the item is on the far side at time t"
)

model.cross = Var(
    model.i, model.t,
    domain=NonNegativeReals,
    bounds=(0, 1),
    doc="Crossing the river"
)

model.done = Var(
    model.t,
    domain=NonNegativeReals,
    bounds=(0, 1),
    doc="All items on far side"
)

model.nocross = Var(
    domain=Reals,
    doc="Number of non-crossing periods"
)

# ----------------------------------------------------------------------
# Fix initial conditions: all items start on near side at t1
# ----------------------------------------------------------------------
for i in data["i"]:
    model.y[i, "t1"].fix(0)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.nocross

model.obj = Objective(
    rule=obj_rule,
    sense=maximize,
    doc="Maximize number of non-crossing periods"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# DefCross(i,t+1).. y(i,t+1) =e= y(i,t) + dir(t)*cross(i,t)
# This defines the state transition: position at t+1 depends on position at t
# and whether the item crossed (in direction dir(t))
def defcross_rule(model, i, t):
    t_idx = t_list.index(t)
    if t_idx + 1 >= len(t_list):
        return Constraint.Skip
    t_next = t_list[t_idx + 1]
    return model.y[i, t_next] == model.y[i, t] + dir_dict[t] * model.cross[i, t]

model.DefCross = Constraint(
    model.i, model.t,
    rule=defcross_rule,
    doc="State transition for crossing"
)

# DefDone(i,t).. done(t) =l= y(i,t)
# done(t) = 1 only if all items are on far side
def defdone_rule(model, i, t):
    return model.done[t] <= model.y[i, t]

model.DefDone = Constraint(
    model.i, model.t,
    rule=defdone_rule,
    doc="Everything on far side"
)

# limCross(t+1).. sum(i, cross(i,t)) =l= 1
# At most one item can cross at a time
def limcross_rule(model, t):
    t_idx = t_list.index(t)
    if t_idx + 1 >= len(t_list):
        return Constraint.Skip
    return sum(model.cross[i, t] for i in data["i"]) <= 1

model.limCross = Constraint(
    model.t,
    rule=limcross_rule,
    doc="At most one item crosses at a time"
)

# EatNone1(t).. dir(t)*(y('goose',t) + y('wolf',t) - 1) =l= done(t)
# Goose and wolf cannot be together on near side (when farmer is on far side)
# If dir(t) = +1 (going to far): wolf and goose together on near side is bad
# If dir(t) = -1 (returning): wolf and goose together on far side is bad
# done(t) forces this constraint to be satisfied only when not everything is on far side
def eatnone1_rule(model, t):
    return dir_dict[t] * (model.y['goose', t] + model.y['wolf', t] - 1) <= model.done[t]

model.EatNone1 = Constraint(
    model.t,
    rule=eatnone1_rule,
    doc="Goose and wolf cannot be left alone"
)

# EatNone2(t).. dir(t)*(y('goose',t) + y('corn',t) - 1) =l= done(t)
# Goose and corn cannot be together on near side (when farmer is on far side)
def eatnone2_rule(model, t):
    return dir_dict[t] * (model.y['goose', t] + model.y['corn', t] - 1) <= model.done[t]

model.EatNone2 = Constraint(
    model.t,
    rule=eatnone2_rule,
    doc="Goose and corn cannot be left alone"
)

# Obj.. nocross =e= sum(t, done(t))
def obj_def_rule(model):
    return model.nocross == sum(model.done[t] for t in t_list)

model.Obj = Constraint(
    rule=obj_def_rule,
    doc="Define objective as sum of done periods"
)
