# converted from models/trnspwlx_mip.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

import math

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="Transportation Problem with Piecewise Linear Functions"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.i = Set(
    initialize=data["i"],
    doc="Canning plants"
)

model.j = Set(
    initialize=data["j"],
    doc="Markets"
)

model.s = Set(
    initialize=data["s"],
    doc="Segments for piecewise linear function"
)

model.sl = Set(
    initialize=data["sl"],
    doc="Segment labels (x, y, l, g)"
)

# ij(i,j) set - all (i,j) combinations
ij_list = [(i, j) for i in data["i"] for j in data["j"]]
model.ij = Set(
    initialize=ij_list,
    dimen=2,
    doc="Index set for transportation routes"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------
model.a = Param(
    model.i,
    initialize=data["a"],
    mutable=True,
    doc="Capacity of plant i in cases"
)

model.b = Param(
    model.j,
    initialize=data["b"],
    mutable=True,
    doc="Demand at market j in cases"
)

# d(i,j) - distance in thousands of miles
d_dict = {}
for key, val in data["d"].items():
    if isinstance(key, tuple) and len(key) == 2:
        d_dict[key] = val

model.d = Param(
    model.i, model.j,
    initialize=d_dict,
    mutable=True,
    doc="Distance in thousands of miles"
)

model.f = Param(
    initialize=data["f"],
    mutable=True,
    doc="Freight in dollars per case per thousand miles"
)

# Compute c(i,j) = f * d(i,j) / 1000
c_dict = {}
for (i, j), dist in d_dict.items():
    c_dict[(i, j)] = data["f"] * dist / 1000

model.c = Param(
    model.i, model.j,
    initialize=c_dict,
    mutable=True,
    doc="Transport cost in thousands of dollars per case"
)

# sqrtp(s,sl) - piecewise linear function data
sqrtp_dict = {}
for key, val in data["sqrtp"].items():
    if isinstance(key, tuple) and len(key) == 2:
        sqrtp_dict[key] = val

model.sqrtp = Param(
    model.s, model.sl,
    initialize=sqrtp_dict,
    mutable=True,
    doc="Piecewise linear function for sqrt"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.x = Var(
    model.i, model.j,
    domain=NonNegativeReals,
    doc="Shipment quantities in cases"
)

model.z = Var(
    domain=Reals,
    doc="Total transportation costs in thousands of dollars"
)

# Variables for piecewise linear approximation
# delta(i,j,s) - amount of x in segment s
model.delta = Var(
    model.i, model.j, model.s,
    domain=NonNegativeReals,
    doc="Amount in each segment"
)

# y(i,j,s) - binary indicator for whether segment s is used
model.y_seg = Var(
    model.i, model.j, model.s,
    domain=Binary,
    doc="Binary indicator for segment usage"
)

# sqrtx(i,j) - the approximated sqrt(x(i,j))
model.sqrtx = Var(
    model.i, model.j,
    domain=NonNegativeReals,
    doc="Approximated sqrt of x"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.z

model.obj = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Minimize total transportation cost"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# supply(i).. sum(ij(i,j), x(i,j)) =l= a(i)
def supply_rule(model, i):
    return sum(model.x[i, j] for (ip, j) in ij_list if ip == i) <= data["a"][i]

model.supply = Constraint(
    model.i,
    rule=supply_rule,
    doc="Observe supply limit at plant i"
)

# demand(j).. sum(ij(i,j), x(i,j)) =g= b(j)
def demand_rule(model, j):
    return sum(model.x[i, j] for (i, jp) in ij_list if jp == j) >= data["b"][j]

model.demand = Constraint(
    model.j,
    rule=demand_rule,
    doc="Satisfy demand at market j"
)

# Build the piecewise linear function
# x(i,j) = sum(s, x_start[s] * y_seg[i,j,s] + delta[i,j,s])
# sqrtx(i,j) = sum(s, y_start[s] * y_seg[i,j,s] + slope[s] * delta[i,j,s])

s_list = list(data["s"])

# Extract x, y, l, g for each segment
x_start = {}
y_start = {}
length = {}
slope = {}

for s in s_list:
    x_start[s] = sqrtp_dict.get((s, "x"), 0)
    y_start[s] = sqrtp_dict.get((s, "y"), 0)
    length[s] = sqrtp_dict.get((s, "l"), 0)
    slope[s] = sqrtp_dict.get((s, "g"), 0)

# Define x as sum of segments
def defx_rule(model, i, j):
    if (i, j) not in ij_list:
        return Constraint.Skip
    return model.x[i, j] == sum(
        x_start[s] * model.y_seg[i, j, s] + model.delta[i, j, s]
        for s in s_list
    )

model.defx = Constraint(
    model.ij,
    rule=defx_rule,
    doc="Define x from segments"
)

# Define sqrtx as sum of segment contributions
def defsqrtx_rule(model, i, j):
    if (i, j) not in ij_list:
        return Constraint.Skip
    return model.sqrtx[i, j] == sum(
        y_start[s] * model.y_seg[i, j, s] + slope[s] * model.delta[i, j, s]
        for s in s_list
    )

model.defsqrtx = Constraint(
    model.ij,
    rule=defsqrtx_rule,
    doc="Define sqrtx from segments"
)

# Limit delta to segment length when segment is active
def limit_delta_rule(model, i, j, s):
    if (i, j) not in ij_list:
        return Constraint.Skip
    if length[s] < 0 or length[s] > 1000:  # unbounded segments (s0 and s6)
        return Constraint.Skip
    return model.delta[i, j, s] <= length[s] * model.y_seg[i, j, s]

model.limit_delta = Constraint(
    model.ij, model.s,
    rule=limit_delta_rule,
    doc="Limit delta to segment length"
)

# At most one segment can be active
def one_segment_rule(model, i, j):
    if (i, j) not in ij_list:
        return Constraint.Skip
    return sum(model.y_seg[i, j, s] for s in s_list) <= 1

model.one_segment = Constraint(
    model.ij,
    rule=one_segment_rule,
    doc="At most one segment active"
)

# defobjdisc.. z =e= sum(ij(i,j), c(i,j)*sqrtx(i,j))
def defobjdisc_rule(model):
    return model.z == sum(
        c_dict[(i, j)] * model.sqrtx[i, j]
        for (i, j) in ij_list
    )

model.defobjdisc = Constraint(
    rule=defobjdisc_rule,
    doc="Define objective with piecewise linear sqrt"
)
