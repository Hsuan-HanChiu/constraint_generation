# converted from models/bchoil_mip.py
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
    doc="Oil Pipeline Design Problem"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.n = Set(
    initialize=data["n"],
    doc="Nodes in the oil pipeline network"
)

model.k = Set(
    initialize=data["k"],
    doc="Type of oil pipe"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------
# Pre-compute parameters from data
cap_dict = {}
for key, val in data["cap"].items():
    if isinstance(key, tuple) and len(key) == 1:
        cap_dict[key[0]] = val
    else:
        cap_dict[key] = val

pipecost_dict = {}
for key, val in data["pipecost"].items():
    if isinstance(key, tuple) and len(key) == 1:
        pipecost_dict[key[0]] = val
    else:
        pipecost_dict[key] = val

p_dict = {}
for key, val in data["p"].items():
    if isinstance(key, tuple) and len(key) == 1:
        p_dict[key[0]] = val
    else:
        p_dict[key] = val

# edgedist comes as "i|j" strings from JSON, convert to tuples
edgedist_raw = data.get("edgedist", {})
edgedist_dict = {}
for key, val in edgedist_raw.items():
    if isinstance(key, tuple):
        edgedist_dict[key] = val
    else:
        # Key is a string, already handled by run.py
        edgedist_dict[key] = val

# Convert integer keys to string keys to match data["n"]
edgedist_dict_str = {}
for key, val in edgedist_dict.items():
    if isinstance(key, tuple):
        str_key = tuple(str(k) for k in key)
        edgedist_dict_str[str_key] = val
    else:
        edgedist_dict_str[key] = val
edgedist_dict = edgedist_dict_str

model.cap = Param(
    model.k,
    initialize=cap_dict,
    mutable=True,
    default=0,
    doc="Capacity of type k oil pipe"
)

model.pipecost = Param(
    model.k,
    initialize=pipecost_dict,
    mutable=True,
    default=0,
    doc="Monetary units for type k capacity"
)

model.p = Param(
    model.n,
    initialize=p_dict,
    mutable=True,
    default=0,
    doc="Production at each node"
)

# Build derived parameters and sets
# dist(m,n) = edgedist(m,n) + edgedist(n,m)
# Don't create edgedist Param, just use the dict directly
dist_dict = {}
for m in data["n"]:
    for n in data["n"]:
        val = edgedist_dict.get((m, n), 0) + edgedist_dict.get((n, m), 0)
        if val > 0:
            dist_dict[(m, n)] = val

# arc(m,n) if dist(m,n) > 0
arc_set = set()
for (m, n), val in dist_dict.items():
    if val > 0:
        arc_set.add((m, n))

# Last node is the port (node 33)
port_node = data["n"][-1]

# Remove arcs from port
arc_set = {(m, n) for (m, n) in arc_set if m != port_node}

model.arc = Set(
    initialize=arc_set,
    within=model.n * model.n,
    doc="Arcs in the network"
)

# regnode: all nodes except port
regnode_set = {n for n in data["n"] if n != port_node}

model.regnode = Set(
    initialize=list(regnode_set),
    doc="Non-port nodes"
)

# kk: reduced set of pipe line types (exclude '1' and '2')
kk_set = {k for k in data["k"] if k not in ['1', '2']}

model.kk = Set(
    initialize=list(kk_set),
    doc="Reduced set of pipe line types"
)

# cap1 and pipecost1 (values for type '2')
cap1 = cap_dict.get('2', 0)
pipecost1 = pipecost_dict.get('2', 0)

# Adjust cap and pipecost for kk
cap_adjusted = {}
pipecost_adjusted = {}
for k in kk_set:
    cap_adjusted[k] = cap_dict.get(k, 0) - cap1
    pipecost_adjusted[k] = pipecost_dict.get(k, 0) - pipecost1

model.cap_adj = Param(
    model.kk,
    initialize=cap_adjusted,
    mutable=True,
    doc="Adjusted capacity for kk"
)

model.pipecost_adj = Param(
    model.kk,
    initialize=pipecost_adjusted,
    mutable=True,
    doc="Adjusted pipe cost for kk"
)

model.cap1 = Param(
    initialize=cap1,
    mutable=True,
    doc="Capacity of type 1 (2) oil pipe"
)

model.pipecost1 = Param(
    initialize=pipecost1,
    mutable=True,
    doc="Monetary units for pipe of type 1 (2)"
)

# nw subset (all nodes in this problem)
model.nw = Set(
    initialize=data["n"],
    doc="Subset of nodes"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
# Define variables only for arcs that exist
model.bk = Var(
    model.arc, model.k,
    domain=Binary,
    doc="Build variable for type k pipe on the arc"
)

model.b = Var(
    model.arc,
    domain=Binary,
    doc="Build variable for some pipe on the arc"
)

model.f = Var(
    model.arc,
    domain=NonNegativeReals,
    doc="Flow variable on the arc"
)

model.cost = Var(
    doc="The cost for installing pipes in the network"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.cost

model.obj = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Minimize oil pipeline network construction cost"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# obj.. sum(arc(nw,n), dist(arc)*(pipecost1*b(arc) + sum(kk, pipecost(kk)*bk(arc,kk)))) =e= cost
def obj_constraint_rule(model):
    return sum(
        dist_dict.get(arc, 0) * (
            pipecost1 * model.b[arc] +
            sum(pipecost_adjusted.get(k, 0) * model.bk[arc, k] for k in kk_set)
        )
        for arc in model.arc
    ) == model.cost

model.obj_constraint = Constraint(
    rule=obj_constraint_rule,
    doc="Define cost"
)

# oneout(m)$(not p(m)).. sum((arc(m,n)), b(m,n)) =l= 1
def oneout_rule(model, m):
    if p_dict.get(m, 0) > 0:
        return Constraint.Skip
    # Check if there are any outgoing arcs from m
    outgoing_arcs = [(mm, n) for (mm, n) in model.arc if mm == m]
    if len(outgoing_arcs) == 0:
        return Constraint.Skip
    return sum(model.b[arc] for arc in outgoing_arcs) <= 1

model.oneout = Constraint(
    model.n,
    rule=oneout_rule,
    doc="At most one out-flow each node"
)

# oneoutp(m)$p(m).. sum((arc(m,n)), b(m,n)) =e= 1
def oneoutp_rule(model, m):
    if p_dict.get(m, 0) == 0:
        return Constraint.Skip
    # Check if there are any outgoing arcs from m
    outgoing_arcs = [(mm, n) for (mm, n) in model.arc if mm == m]
    if len(outgoing_arcs) == 0:
        return Constraint.Skip
    return sum(model.b[arc] for arc in outgoing_arcs) == 1

model.oneoutp = Constraint(
    model.n,
    rule=oneoutp_rule,
    doc="One out-flow for each production node"
)

# bal(regnode(nw)).. p(nw) =e= sum(arc(nw,m), f(nw,m)) - sum(arc(m,nw), f(m,nw))
def bal_rule(model, nw):
    if nw not in regnode_set:
        return Constraint.Skip

    # Check if node has any arcs (in or out)
    outgoing_arcs = [(nn, m) for (nn, m) in model.arc if nn == nw]
    incoming_arcs = [(m, nn) for (m, nn) in model.arc if nn == nw]

    # Skip if node has no arcs at all
    if len(outgoing_arcs) == 0 and len(incoming_arcs) == 0:
        return Constraint.Skip

    outflow = sum(model.f[arc] for arc in outgoing_arcs)
    inflow = sum(model.f[arc] for arc in incoming_arcs)
    return p_dict.get(nw, 0) == outflow - inflow

model.bal = Constraint(
    model.n,
    rule=bal_rule,
    doc="Flow conservation constraints"
)

# bigM(arc(nw,n)).. cap1*b(arc) + sum(kk, cap(kk)*bk(arc,kk)) =g= f(arc)
def bigM_rule(model, nw, n):
    return cap1 * model.b[nw, n] + sum(
        cap_adjusted.get(k, 0) * model.bk[nw, n, k] for k in kk_set
    ) >= model.f[nw, n]

model.bigM = Constraint(
    model.arc,
    rule=bigM_rule,
    doc="The flow capacity constraints"
)

# defb(arc(nw,n)).. sum(kk, bk(arc,kk)) =l= b(arc)
def defb_rule(model, nw, n):
    return sum(model.bk[nw, n, k] for k in kk_set) <= model.b[nw, n]

model.defb = Constraint(
    model.arc,
    rule=defb_rule,
    doc="Additional pipe constraint"
)
