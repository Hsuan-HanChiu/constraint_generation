# converted from gamslib maxcut (MAXCUT, SEQ=338)
# Max-Cut MIP. Original GAMS model seeds a Goemans/Williamson SDP rounding
# solution into a MIP; only the MIP core is converted here (binary node-side
# variables + edge-cut linearization). Instance: tg20_7777 (400 nodes, 800 edges).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format. Edge set
# members are (i, j) node-name tuples; the weight param 'w' uses pipe keys
# "i|j" that may normalize to either string- or int-valued tuples, so we
# re-key it against the edge set members below to stay robust.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# Edge set members (list of (i, j) tuples, node names as strings, i < j).
_edges = [tuple(str(t) for t in e) for e in data["e"]]

# Re-key edge weights against the canonical string-tuple edge members so the
# Param index matches the edge set regardless of how the JSON keys normalized.
_w_raw = data["w"]
_w = {}
for e in _edges:
    if e in _w_raw:
        _w[e] = float(_w_raw[e])
    else:
        # fall back to int-tuple key produced by pipe-key normalization
        _w[e] = float(_w_raw[tuple(int(t) for t in e)])

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Max-Cut MIP: partition nodes to maximize cut edge weight")

# Sets
model.n = pyo.Set(initialize=[str(x) for x in data["n"]], doc="Graph nodes (vertices)")
model.e = pyo.Set(dimen=2, initialize=_edges, doc="Graph edges (i, j) with i < j")

# Parameters
model.w = pyo.Param(
    model.e,
    initialize=_w,
    mutable=True,
    within=pyo.Reals,
    doc="Edge weight w(i, j)",
)

# Variables
model.x = pyo.Var(
    model.n,
    domain=pyo.Binary,
    doc="Side of the cut each node is assigned to (0 or 1)",
)

model.cut = pyo.Var(
    model.e,
    bounds=(0, 1),
    domain=pyo.NonNegativeReals,
    doc="1 if edge (i, j) crosses the cut, else 0 (relaxed to [0,1])",
)

model.z = pyo.Var(domain=pyo.Reals, doc="Total weight of edges crossing the cut")

# Constraints
def obj_def_rule(model):
    return model.z == sum(model.w[i, j] * model.cut[i, j] for (i, j) in model.e)

model.obj_def = pyo.Constraint(rule=obj_def_rule, doc="Accounting: total cut weight")

def xor1_rule(model, i, j):
    return model.cut[i, j] <= model.x[i] + model.x[j]

model.xor1 = pyo.Constraint(model.e, rule=xor1_rule, doc="cut <= x_i + x_j")

def xor2_rule(model, i, j):
    return model.cut[i, j] <= 2 - model.x[i] - model.x[j]

model.xor2 = pyo.Constraint(model.e, rule=xor2_rule, doc="cut <= 2 - x_i - x_j")

def xor3_rule(model, i, j):
    return model.cut[i, j] >= model.x[i] - model.x[j]

model.xor3 = pyo.Constraint(model.e, rule=xor3_rule, doc="cut >= x_i - x_j")

def xor4_rule(model, i, j):
    return model.cut[i, j] >= model.x[j] - model.x[i]

model.xor4 = pyo.Constraint(model.e, rule=xor4_rule, doc="cut >= x_j - x_i")

# Objective
model.obj = pyo.Objective(
    expr=model.z,
    sense=pyo.maximize,
    doc="Maximize total weight of edges crossing the cut",
)
