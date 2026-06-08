# converted from models/danwolfe_lp.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

import random
import math

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="Multi-Commodity Network Flow Problem"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.i = Set(
    initialize=data["i"],
    doc="Nodes"
)

model.j = Set(
    initialize=data["i"],
    doc="Nodes (alias)"
)

model.k = Set(
    initialize=data["k"],
    doc="Commodities"
)

# ----------------------------------------------------------------------
# Generate random instance
# ----------------------------------------------------------------------
seed = data.get("random_seed", 12345)
random.seed(seed)

edgedensity = data.get("edgedensity", 0.3)

# Generate edges e(i,j) — use a list (deterministic order) plus a set (fast membership).
e_list = []
e_set = set()
for i in data["i"]:
    for j in data["i"]:
        if i != j and random.random() < edgedensity:
            e_list.append((i, j))
            e_set.add((i, j))

model.e = Set(
    initialize=e_list,
    dimen=2,
    doc="Edges"
)

# Generate cost(e)
cost_dict = {}
for e in e_list:
    cost_dict[e] = random.uniform(1, 10)

model.cost = Param(
    model.e,
    initialize=cost_dict,
    mutable=True,
    doc="Cost for edge use"
)

# Generate cap(e)
cap_dict = {}
num_comm = len(data["k"])
for e in e_list:
    cap_dict[e] = random.uniform(50, 100) * math.log(num_comm)

model.cap = Param(
    model.e,
    initialize=cap_dict,
    mutable=True,
    doc="Bundle capacity"
)

# Generate bal(k,i) and kdem(k)
# GAMS logic:
# loop(k,
#    kdem(k) = uniform(50,150);
#    inum    = uniformInt(1,card(i)); bal(k,i)$(ord(i) = inum) = kdem(k);
#    inum    = uniformInt(1,card(i)); bal(k,i)$(ord(i) = inum) = bal(k,i) - kdem(k);
#    kdem(k) = sum(i$(bal(k,i) > 0), bal(k,i));
# );

bal_dict = {}
kdem_dict = {}

i_list = list(data["i"])
num_nodes = len(i_list)

for k in data["k"]:
    # Generate demand
    kdem_initial = random.uniform(50, 150)

    # Pick first node (source) - uniformInt(1, card(i)) returns 1-based index
    inum1 = random.randint(1, num_nodes)
    source = i_list[inum1 - 1]  # Convert to 0-based
    bal_dict[(k, source)] = kdem_initial

    # Pick second node (can be same or different) - add to existing balance
    inum2 = random.randint(1, num_nodes)
    sink = i_list[inum2 - 1]  # Convert to 0-based
    bal_dict[(k, sink)] = bal_dict.get((k, sink), 0) - kdem_initial

    # Recompute kdem as sum of positive balances
    kdem_actual = sum(bal_dict.get((k, i), 0) for i in i_list if bal_dict.get((k, i), 0) > 0)
    kdem_dict[k] = kdem_actual

model.bal = Param(
    model.k, model.i,
    initialize=bal_dict,
    mutable=True,
    default=0,
    doc="Balance"
)

model.kdem = Param(
    model.k,
    initialize=kdem_dict,
    mutable=True,
    doc="Demand"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.x = Var(
    model.k, model.i, model.j,
    domain=NonNegativeReals,
    doc="Multi-commodity flow"
)

model.z = Var(
    domain=Reals,
    doc="Objective"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.z

model.obj = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Minimize total cost"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# defobj.. z =e= sum((k,e), cost(e)*x(k,e))
def defobj_rule(model):
    return model.z == sum(
        model.cost[i, j] * model.x[k, i, j]
        for k in data["k"]
        for (i, j) in e_list
    )

model.defobj = Constraint(
    rule=defobj_rule,
    doc="Define objective"
)

# defbal(k,i).. sum(e(i,j), x(k,e)) - sum(e(j,i), x(k,e)) =e= bal(k,i)
def defbal_rule(model, k, i):
    outflow = sum(model.x[k, i, j] for (ip, j) in e_list if ip == i)
    inflow = sum(model.x[k, j, i] for (j, ip) in e_list if ip == i)
    return outflow - inflow == model.bal[k, i]

model.defbal = Constraint(
    model.k, model.i,
    rule=defbal_rule,
    doc="Balancing constraint"
)

# defcap(e).. sum(k, x(k,e)) =l= cap(e)
def defcap_rule(model, i, j):
    if (i, j) not in e_set:
        return Constraint.Skip
    return sum(model.x[k, i, j] for k in data["k"]) <= model.cap[i, j]

model.defcap = Constraint(
    model.e,
    rule=defcap_rule,
    doc="Bundling capacity"
)
