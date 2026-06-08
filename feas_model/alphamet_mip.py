# converted from gamslib alphamet (ALPHAMET, SEQ=170)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "k|i": value → (k, i): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Alphametics - a mathematical puzzle (GEORGIA+OREGON+VERMONT=VIRGINIA)")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Letters")
model.j = pyo.Set(initialize=data["i"], doc="Letters (alias of i)")
model.k = pyo.Set(initialize=data["k"], ordered=True, doc="Slices (addition columns)")
model.lead = pyo.Set(initialize=data["lead"], within=model.i, doc="Lead letters (cannot be zero)")

# Parameters
model.lhs = pyo.Param(
    model.k, model.i,
    initialize=data["lhs"],
    default=0,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Input count for each letter in slice",
)

model.rhs = pyo.Param(
    model.i, model.k,
    initialize=data["rhs"],
    default=0,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Result count for each letter in slice",
)

# Variables
model.x = pyo.Var(
    model.i, model.j,
    domain=pyo.Binary,
    doc="Assignment of digits (values) to letters",
)

model.y = pyo.Var(
    model.i,
    domain=pyo.Reals,
    doc="Assigned value of each letter",
)

model.c = pyo.Var(
    model.k,
    domain=pyo.NonNegativeIntegers,
    doc="Carry of each slice",
)

model.z = pyo.Var(
    domain=pyo.Reals,
    doc="Sum of carries (objective)",
)

# ── helpers for GAMS lag index c(k-1) ────────────────────────────────────────
_klist = list(data["k"])


def _carry_lag(model, k):
    # GAMS c(k-1); for the first slice k-1 is out of domain -> 0
    pos = _klist.index(k)
    if pos == 0:
        return 0
    return model.c[_klist[pos - 1]]


# Constraints
def obj_rule(model):
    # z =e= sum(k, c(k-1)); first lag term is 0
    return model.z == sum(_carry_lag(model, k) for k in model.k)

model.objdef = pyo.Constraint(rule=obj_rule, doc="Defines objective: sum of carries")


def eq_rule(model, k):
    # c(k-1) + sum(i, lhs(k,i)*y(i)) =e= sum(i, rhs(i,k)*y(i)) + 10*c(k)$(ord(k) <> card(k))
    lhs_expr = _carry_lag(model, k) + sum(model.lhs[k, i] * model.y[i] for i in model.i)
    rhs_expr = sum(model.rhs[i, k] * model.y[i] for i in model.i)
    if k != _klist[-1]:  # 10*c(k) dropped for the last slice
        rhs_expr = rhs_expr + 10 * model.c[k]
    return lhs_expr == rhs_expr

model.eq = pyo.Constraint(model.k, rule=eq_rule, doc="Defines addition for each slice")


def ydef_rule(model, i):
    # y(i) =e= sum(j, (ord(j) - 1)*x(i,j))
    return model.y[i] == sum(pos * model.x[i, j] for pos, j in enumerate(model.j))

model.ydef = pyo.Constraint(model.i, rule=ydef_rule, doc="Assigned value from digit assignment")


def x1_rule(model, i):
    # each letter gets exactly one digit
    return sum(model.x[i, j] for j in model.j) == 1

model.x1 = pyo.Constraint(model.i, rule=x1_rule, doc="Assignment constraint one")


def x2_rule(model, j):
    # each digit assigned to exactly one letter
    return sum(model.x[i, j] for i in model.i) == 1

model.x2 = pyo.Constraint(model.j, rule=x2_rule, doc="Assignment constraint two")


def ld_rule(model, lead):
    # y(lead) =g= 1 ; lead letters cannot be zero
    return model.y[lead] >= 1

model.ld = pyo.Constraint(model.lead, rule=ld_rule, doc="Bound on lead letters")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.minimize,
    doc="Minimize sum of carries",
)
