# converted from gamslib absmip (ABSMIP, SEQ=208)
#
# The original GAMS file is a teaching example that loops over several
# discontinuous-function MIP formulations (abs, max, min, sign) and re-solves
# each one in both max and min sense over five bound configurations.
# There is no single canonical objective in the source.
#
# This file extracts the single underlying optimization model: the MIP
# formulation of  y = min(x, 0)  (the GAMS sub-model "zminM" solved in the
# minimize sense), using the first bound configuration  x in [-5, 5].
# The loops, reporting parameters, and scenario re-solves are dropped.
#
#   e1:      x = xp - xn        (split x into positive / negative parts)
#   e2:      xp <= |x.up| * b   (xp active only when b = 1)
#   e3:      xn <= |x.lo| * (1-b)   (xn active only when b = 0)
#   defzmin: y = -xn
#   minimize y   ->   y = min(x, 0) = -5  at x = -5
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

model = pyo.ConcreteModel(doc="ABSMIP: MIP formulation of y = min(x, 0)")

# Parameters (bounds on the argument x; |x.up| and |x.lo| act as big-M values)
model.xlo = pyo.Param(initialize=data["xlo"], mutable=True, within=pyo.Reals,
                      doc="Lower bound on argument x")
model.xup = pyo.Param(initialize=data["xup"], mutable=True, within=pyo.Reals,
                      doc="Upper bound on argument x")

# Variables
model.x = pyo.Var(domain=pyo.Reals, bounds=(pyo.value(model.xlo), pyo.value(model.xup)),
                  doc="Argument to the function")
model.xp = pyo.Var(domain=pyo.NonNegativeReals, doc="Positive part of x")
model.xn = pyo.Var(domain=pyo.NonNegativeReals, doc="Negative part of x")
model.b = pyo.Var(domain=pyo.Binary, doc="1 if x is in its positive part")
model.y = pyo.Var(domain=pyo.Reals, doc="Result of function evaluation y = min(x, 0)")

# Constraints
def e1_rule(model):
    return model.x == model.xp - model.xn
model.e1 = pyo.Constraint(rule=e1_rule, doc="Split x into positive and negative part")

def e2_rule(model):
    return model.xp <= abs(pyo.value(model.xup)) * model.b
model.e2 = pyo.Constraint(rule=e2_rule, doc="Restrict positive part of x")

def e3_rule(model):
    return model.xn <= abs(pyo.value(model.xlo)) * (1 - model.b)
model.e3 = pyo.Constraint(rule=e3_rule, doc="Restrict negative part of x")

def defzmin_rule(model):
    return model.y == -model.xn
model.defzmin = pyo.Constraint(rule=defzmin_rule, doc="Definition of y = min(x, 0)")

# Objective: minimize y  ->  y = min(x, 0)
model.obj = pyo.Objective(expr=model.y, sense=pyo.minimize,
                          doc="Minimize y to evaluate min(x, 0)")
