# converted from gamslib dicegrid (DICEGRID, SEQ=330)
# MIP Decomposition and Parallel Grid Submission - DICE Example.
# dicegrid.gms is a grid-computing wrapper: it pulls in the original `dice`
# model (`$call gamslib -q dice` / `$include dice.gms`) and wraps a parallel
# Cplex grid submit/collect/incumbent scaffolding (mutex, trigger files, GDX
# containers) around the SAME design MIP. The underlying optimization model is
# the non-transitive dice design `xdice`.
#
# Non-transitive Dice Design.
# Design a set of dice with integer face values such that, cyclically,
# dice1 beats dice2 (on average), dice2 beats dice3, and dice3 beats dice1.
# Primary model = `xdice`: a MIP that MAXIMIZES the (common) number of
# pairwise face wins `wnx` each die scores against the next die in the cycle.
# (The grid submit/collect loop, mutex, incumbent files, and the dice model's
#  second solve `facecomp`/`min z` reporting re-solve are all dropped here per
#  the OptiChat single-deterministic-model convention.)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

model = pyo.ConcreteModel(doc="Non-transitive Dice Design - maximize cyclic pairwise wins")

# Sets
model.f = pyo.Set(initialize=data["f"], doc="Faces on a dice", ordered=True)
model.dice = pyo.Set(initialize=data["dice"], doc="The dice", ordered=True)

# Scalar parameters
model.flo = pyo.Param(initialize=data["flo"], mutable=True, doc="Lowest face value")
model.fup = pyo.Param(initialize=data["fup"], mutable=True, doc="Highest face value")

# Helper: next dice in the cyclic order (dice++1 in GAMS)
_dice_list = list(data["dice"])
def _next_dice(d):
    return _dice_list[(_dice_list.index(d) + 1) % len(_dice_list)]

_face_list = list(data["f"])

# Variables
model.wnx = pyo.Var(domain=pyo.NonNegativeReals, doc="Number of wins (common per die)")
model.fval = pyo.Var(
    model.dice, model.f,
    domain=pyo.NonNegativeReals,
    bounds=lambda m, d, f: (pyo.value(m.flo), pyo.value(m.fup)),
    doc="Face value on each die (may be fractional in the design model)",
)
model.comp = pyo.Var(
    model.dice, model.f, model.f,
    domain=pyo.Binary,
    doc="comp[d,f,fp]=1 implies face f of die d beats face fp of the next die",
)

# Fix the first face of the first die to the lowest value (symmetry breaking, GAMS fval.fx)
model.fval[_dice_list[0], _face_list[0]].fix(pyo.value(model.flo))

# Constraints
def eq1_rule(m, d):
    # count the wins: each die wins exactly wnx face-vs-face comparisons
    return sum(m.comp[d, f, fp] for f in m.f for fp in m.f) == m.wnx
model.eq1 = pyo.Constraint(model.dice, rule=eq1_rule, doc="Count the wins per die")

def eq3_rule(m, d, f, fp):
    # non-transitive relation (big-M): if comp[d,f,fp]=1 then fval[d,f] >= fval[next(d),fp]+1
    return m.fval[d, f] + (m.fup - m.flo + 1) * (1 - m.comp[d, f, fp]) >= m.fval[_next_dice(d), fp] + 1
model.eq3 = pyo.Constraint(model.dice, model.f, model.f, rule=eq3_rule,
                           doc="Definition of the non-transitive (cyclic) winning relation")

def eq4_rule(m, d, f):
    # strictly increasing face values within a die (eq4(dice,f-1) in GAMS)
    i = _face_list.index(f)
    if i == 0:
        return pyo.Constraint.Skip
    return m.fval[d, _face_list[i - 1]] + 1 <= m.fval[d, f]
model.eq4 = pyo.Constraint(model.dice, model.f, rule=eq4_rule,
                           doc="Distinct, strictly increasing face values per die")

# Objective
model.obj = pyo.Objective(expr=model.wnx, sense=pyo.maximize,
                          doc="Maximize the common number of pairwise wins")
