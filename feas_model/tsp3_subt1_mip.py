# converted from models/tsp3_subt1_mip.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

from itertools import combinations

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# city set
model.I = Set(initialize=data['i'], doc='cities')

model.c = Param(model.I, model.I, initialize=data['c'], mutable=True, doc='travel cost')

# decision variables
model.x = Var(model.I, model.I, domain=Binary, doc='leg of trip (i->j)')
model.z = Var(domain=NonNegativeReals, doc='objective')

# base assignment (relaxation)
def rowsum_rule(m, i):
    return sum(m.x[i, j] for j in m.I) == 1
model.rowsum = Constraint(model.I, rule=rowsum_rule)

def colsum_rule(m, j):
    return sum(m.x[i, j] for i in m.I) == 1
model.colsum = Constraint(model.I, rule=colsum_rule)

# exclude diagonal (fix to zero)
for i in data['i']:
    model.x[i, i].fix(0)

# objective definition
def objective_rule(m):
    return m.z == sum(m.c[i, j] * m.x[i, j] for i in m.I for j in m.I)
model.objdef = Constraint(rule=objective_rule)
model.obj = Objective(expr=model.z, sense=minimize)

# ---------- subtour generation (all non-empty, non-full subsets) ----------
# produce all subsets of cities of size 1..(n-1) and give them names n1..nK
cities = list(data['i'])
n_subsets = []
for r in range(1, len(cities)):
    for comb in combinations(cities, r):
        # skip singleton/full if you want — GAMS also excludes empty/full; keep all 1..n-1
        n_subsets.append(set(comb))

# create mapping name -> subset
subset_list = n_subsets
# name them
names = [f"n{idx+1}" for idx in range(len(subset_list))]
subset_map = dict(zip(names, subset_list))

# register subset names as an index set for constraints
model.N = Set(initialize=names, doc='subtour indices')

# se1: sum(i in S) sum(j in S) x(i,j) <= |S| - 1
def se1_rule(m, nname):
    S = subset_map[nname]
    if len(S) <= 1:
        # covers singletons: left side <= 0 so it will be satisfied automatically
        return sum(m.x[i, j] for i in S for j in S) <= max(0, len(S) - 1)
    return sum(m.x[i, j] for i in S for j in S) <= len(S) - 1
model.se1 = Constraint(model.N, rule=se1_rule)
