# converted from models/latin_mip.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# Sets
model.S = Set(initialize=data['s'], doc='squares')
model.V = Set(initialize=data['v'], doc='values')
model.K = Set(initialize=data['k'], doc='rows')
model.L = Set(initialize=data['l'], doc='cols')

# Binary decision y(s,v,k,l)
model.y = Var(model.S, model.V, model.K, model.L, domain=Binary, doc='square s has value v in cell(k,l)')
# optional deviation variable (kept continuous, as in GAMS but not required)
model.dev = Var(model.V, model.K, model.L, doc='deviation (unused)')
# objective variable
model.w = Var(doc='objective')

# Constraints
def n2_rule(m, s, k, l):
# exactly one value for each cell
  return sum(m.y[s, v, k, l] for v in m.V) == 1
model.n2 = Constraint(model.S, model.K, model.L, rule=n2_rule)

def n3_rule(m, s, v, l):
# columns entries unique
  return sum(m.y[s, v, k, l] for k in m.K) == 1
model.n3 = Constraint(model.S, model.V, model.L, rule=n3_rule)


def n5_rule(m, s, v, k):
# row entries unique
  return sum(m.y[s, v, k, l] for l in m.L) == 1
model.n5 = Constraint(model.S, model.V, model.K, rule=n5_rule)

def n6_rule(m, v, k, l):
# entries in the two squares must differ: at most one square can claim v at (k,l)
  return sum(m.y[s, v, k, l] for s in m.S) <= 1
model.n6 = Constraint(model.V, model.K, model.L, rule=n6_rule)


# objective definition: w = sum y
def nobj_rule(m):
  return m.w == sum(m.y[s, v, k, l] for s in m.S for v in m.V for k in m.K for l in m.L)
model.nobj = Constraint(rule=nobj_rule)

model.obj = Objective(expr=model.w, sense=minimize)

# apply optional fix to position the solution
fix = data.get('new_fix')
if fix:
  s = fix['s']
  v = fix['v']
  k = fix['k']
  l = fix['l']
