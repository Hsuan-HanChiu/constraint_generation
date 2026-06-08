# converted from gamslib dicex (DICEX, SEQ=272)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "dice1|face1": value → (dice1, face1): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Non-transitive Dice Design - maximize number of wins")

# Sets
model.f = pyo.Set(initialize=data["f"], doc="Faces on a dice")
model.d = pyo.Set(initialize=data["d"], doc="Number of dice")

# Ordered lists for positional (lead/lag) indexing
_d = list(data["d"])
_f = list(data["f"])

# Parameters
model.wn = pyo.Param(
    initialize=data["wn"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Min wins needed",
)

model.big = pyo.Param(
    initialize=data["big"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Big-M (card(d)*card(f))",
)

model.fnum = pyo.Param(
    model.d, model.f,
    initialize=data["fnum"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Assigned face values",
)

# Variables
model.wnx = pyo.Var(
    domain=pyo.Reals,
    doc="Number of wins",
)

model.fval = pyo.Var(
    model.d, model.f,
    domain=pyo.Integers,
    bounds=(1, len(_d) * len(_f)),
    doc="Value of dice face (integer)",
)

# fval(dice1,face1) fixed to 1
model.fval[_d[0], _f[0]].fix(1)

model.comp = pyo.Var(
    model.d, model.f, model.f,
    domain=pyo.Binary,
    doc="One if face f of dice d beats face fp of next dice",
)

model.fmap = pyo.Var(
    model.d, model.f, model.d, model.f,
    domain=pyo.Binary,
    doc="Assigns values to dice faces",
)

# Constraints
def eq1_rule(model, d):
    # count the wins: sum over (f,fp) of comp = wnx
    return sum(model.comp[d, f, fp] for f in model.f for fp in model.f) == model.wnx

model.eq1 = pyo.Constraint(model.d, rule=eq1_rule, doc="Count the wins")


def eq2_rule(model, d, f, fp):
    # non-transitive relation: fval(d,f) + big*(1-comp) >= fval(d++1, fp) + 1
    # d++1 is circular lead over dice
    d_next = _d[(_d.index(d) + 1) % len(_d)]
    return (
        model.fval[d, f] + model.big * (1 - model.comp[d, f, fp])
        >= model.fval[d_next, fp] + 1
    )

model.eq2 = pyo.Constraint(model.d, model.f, model.f, rule=eq2_rule, doc="Definition of non-transitive relation")


def eq3_rule(model, d, f):
    # different face values within a single dice (consecutive faces strictly increasing)
    # GAMS eq3(d,f-1): fval(d,f-1)+1 <= fval(d,f) → for each ordered pair of adjacent faces
    fi = _f.index(f)
    if fi == 0:
        return pyo.Constraint.Skip
    return model.fval[d, _f[fi - 1]] + 1 <= model.fval[d, f]

model.eq3 = pyo.Constraint(model.d, model.f, rule=eq3_rule, doc="Different face values for a single dice")


def eq4_rule(model, d, f):
    # assign values to faces: sum((dp,fp), fnum(dp,fp)*fmap(d,f,dp,fp)) = fval(d,f)
    return (
        sum(model.fnum[dp, fp] * model.fmap[d, f, dp, fp] for dp in model.d for fp in model.f)
        == model.fval[d, f]
    )

model.eq4 = pyo.Constraint(model.d, model.f, rule=eq4_rule, doc="Assign values to faces")


def eq5_rule(model, dp, fp):
    # make face assignment unique: sum((d,f), fmap(d,f,dp,fp)) = 1
    return sum(model.fmap[d, f, dp, fp] for d in model.d for f in model.f) == 1

model.eq5 = pyo.Constraint(model.d, model.f, rule=eq5_rule, doc="Make face assignment unique")

# Objective
model.obj = pyo.Objective(
    expr=model.wnx,
    sense=pyo.maximize,
    doc="Maximize number of wins",
)
