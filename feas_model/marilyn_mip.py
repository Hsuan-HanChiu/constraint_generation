# converted from gamslib marilyn (MARILYN, SEQ=193)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional sets/params (e.g. "c1|c2": → (c1, c2)).

data = globals().get("data", {})


def _as_tuple(k):
    return tuple(k.split("|")) if isinstance(k, str) else tuple(k)


# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Marilyn eight-digit numerical puzzle (place 1..8 in circles, no serial neighbors)")

# Sets
model.c = pyo.Set(initialize=data["c"], doc="Circles")
model.cc = pyo.SetOf(model.c)

# net(c,cc): symmetric adjacency between circles (both directions)
model.net = pyo.Set(
    dimen=2,
    within=model.c * model.cc,
    initialize=[_as_tuple(k) for k in data["net"]],
    doc="Adjacent circles (symmetric)",
)

# Parameters
model.bign = pyo.Param(
    initialize=data["bign"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Big-M constant for the serial-difference indicator",
)

model.gap = pyo.Param(
    initialize=data["gap"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Minimum required difference between adjacent digits",
)

model.lo = pyo.Param(
    initialize=data["lo"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Smallest digit value",
)

model.up = pyo.Param(
    initialize=data["up"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Largest digit value",
)

# Variables
model.x = pyo.Var(
    model.c,
    domain=pyo.Integers,
    bounds=(pyo.value(model.lo), pyo.value(model.up)),
    doc="Digit to be placed in each circle",
)

model.ll = pyo.Var(
    model.c, model.cc,
    domain=pyo.Binary,
    doc="Less-or-greater indicator for adjacent circles",
)

model.y = pyo.Var(
    model.c, model.cc,
    domain=pyo.Binary,
    doc="Digit assignment indicator (circle c gets digit cc)",
)

model.dummy = pyo.Var(
    domain=pyo.Reals,
    doc="Objective accounting variable (sum of digits)",
)


# Constraints
def less_rule(model, c, cc):
    return model.x[cc] <= model.x[c] - model.gap + model.bign * model.ll[c, cc]


model.less = pyo.Constraint(model.net, rule=less_rule, doc="Links having smaller neighbors")


def more_rule(model, c, cc):
    return model.x[cc] >= model.x[c] + model.gap - model.bign * model.ll[cc, c]


model.more = pyo.Constraint(model.net, rule=more_rule, doc="Links having larger neighbors")


def cross_rule(model, c, cc):
    return model.ll[c, cc] + model.ll[cc, c] == 1


model.cross = pyo.Constraint(model.net, rule=cross_rule, doc="Links are one way or the other")


def digit_rule(model, c):
    return model.x[c] == sum((i + 1) * model.y[c, cc] for i, cc in enumerate(model.cc))


model.digit = pyo.Constraint(model.c, rule=digit_rule, doc="Assignment of digits to circles")


def rowsum_rule(model, c):
    return sum(model.y[c, cc] for cc in model.cc) == 1


model.rowsum = pyo.Constraint(model.c, rule=rowsum_rule, doc="Each circle gets exactly one digit")


def colsum_rule(model, c):
    return sum(model.y[cc, c] for cc in model.cc) == 1


model.colsum = pyo.Constraint(model.c, rule=colsum_rule, doc="Each digit is used exactly once")


def obj_rule(model):
    return model.dummy == sum(model.x[c] for c in model.c)


model.ap = pyo.Constraint(rule=obj_rule, doc="Accounting: sum of placed digits")

# Objective
model.obj = pyo.Objective(
    expr=model.dummy,
    sense=pyo.minimize,
    doc="Minimize the accounting variable (sum of digits = 36)",
)
