# converted from models/trnspwl_mip.py
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
    doc="Transportation Problem with Piecewise Linear Economies of Scale (Formulation B)"
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
    doc="SOS2 elements / discretization points"
)

model.ss = Set(
    initialize=data["ss"],
    within=model.s,
    doc="Sample points (subset of s)"
)

model.g = Set(
    initialize=data["g"],
    within=model.s,
    doc="Segments"
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

# Discretization parameters
xlow = data["xlow"]
xhigh = data["xhigh"]
xmax = max(data["a"].values())

# Build p(s) and sqrtp(s) for formulation B (bounded discretization)
# p('slope0') = 0, p(ss) = xlow + ..., p('slopeN') = xmax
# sqrtp(s) = sqrt(p(s))

s_list = list(data["s"])
ss_list = list(data["ss"])

p_dict = {}
sqrtp_dict = {}

# slope0 = 0
p_dict['slope0'] = 0
sqrtp_dict['slope0'] = math.sqrt(0)

# Sample points s1...s6
for idx, s in enumerate(ss_list):
    offset = idx  # 0-based offset for s1, s2, ..., s6
    p_val = xlow + (xhigh - xlow) / (len(ss_list) - 1) * offset
    p_dict[s] = p_val
    sqrtp_dict[s] = math.sqrt(p_val)

# slopeN = xmax
p_dict['slopeN'] = xmax
sqrtp_dict['slopeN'] = math.sqrt(xmax)

model.p = Param(
    model.s,
    initialize=p_dict,
    mutable=True,
    doc="x coordinate of sample point"
)

model.sqrtp = Param(
    model.s,
    initialize=sqrtp_dict,
    mutable=True,
    doc="y coordinate of sample point (sqrt of p)"
)

# Build nseg(g) and ninc(g) for formulation B
# nseg(g) = p(g+1) - p(g)
# ninc(g) = sqrtp(g+1) - sqrtp(g)

g_list = list(data["g"])
nseg_dict = {}
ninc_dict = {}

for idx, g in enumerate(g_list):
    # Find the next element in s
    g_idx = s_list.index(g)
    if g_idx + 1 < len(s_list):
        next_s = s_list[g_idx + 1]
        nseg_dict[g] = p_dict[next_s] - p_dict[g]
        ninc_dict[g] = sqrtp_dict[next_s] - sqrtp_dict[g]

model.nseg = Param(
    model.g,
    initialize=nseg_dict,
    mutable=True,
    doc="Relative increase of x in segment"
)

model.ninc = Param(
    model.g,
    initialize=ninc_dict,
    mutable=True,
    doc="Relative increase of sqrtx in segment"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.x = Var(
    model.i, model.j,
    domain=NonNegativeReals,
    doc="Shipment quantities in cases"
)

model.sqrtx = Var(
    model.i, model.j,
    domain=NonNegativeReals,
    doc="Square root of shipment quantities"
)

model.seg = Var(
    model.i, model.j, model.s,
    domain=NonNegativeReals,
    doc="Shipment in segment"
)

model.gs = Var(
    model.i, model.j, model.s,
    domain=Binary,
    doc="Indicator for shipment in segment"
)

model.z = Var(
    domain=Reals,
    doc="Total transportation costs in thousands of dollars"
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

# supply(i).. sum(j, x(i,j)) =l= a(i)
def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= data["a"][i]

model.supply = Constraint(
    model.i,
    rule=supply_rule,
    doc="Observe supply limit at plant i"
)

# demand(j).. sum(i, x(i,j)) =g= b(j)
def demand_rule(model, j):
    return sum(model.x[i, j] for i in model.i) >= data["b"][j]

model.demand = Constraint(
    model.j,
    rule=demand_rule,
    doc="Satisfy demand at market j"
)

# defx(i,j).. x(i,j) =e= sum(g, p(g)*gs(i,j,g) + nseg(g)*seg(i,j,g))
def defx_rule(model, i, j):
    return model.x[i, j] == sum(
        p_dict[g] * model.gs[i, j, g] + nseg_dict[g] * model.seg[i, j, g]
        for g in g_list
    )

model.defx = Constraint(
    model.i, model.j,
    rule=defx_rule,
    doc="Definition of x"
)

# defsqrt(i,j).. sqrtx(i,j) =e= sum(g, sqrtp(g)*gs(i,j,g) + ninc(g)*seg(i,j,g))
def defsqrt_rule(model, i, j):
    return model.sqrtx[i, j] == sum(
        sqrtp_dict[g] * model.gs[i, j, g] + ninc_dict[g] * model.seg[i, j, g]
        for g in g_list
    )

model.defsqrt = Constraint(
    model.i, model.j,
    rule=defsqrt_rule,
    doc="Definition of sqrt"
)

# defseg(i,j,g).. seg(i,j,g) =l= gs(i,j,g)
def defseg_rule(model, i, j, g):
    if g not in g_list:
        return Constraint.Skip
    return model.seg[i, j, g] <= model.gs[i, j, g]

model.defseg = Constraint(
    model.i, model.j, model.g,
    rule=defseg_rule,
    doc="Segment can only have shipment if indicator is on"
)

# defgs(i,j).. sum(g, gs(i,j,g)) =l= 1
def defgs_rule(model, i, j):
    return sum(model.gs[i, j, g] for g in g_list) <= 1

model.defgs = Constraint(
    model.i, model.j,
    rule=defgs_rule,
    doc="Select at most one segment"
)

# defobjdisc.. z =e= sum((i,j), c(i,j)*sqrtx(i,j))
def defobjdisc_rule(model):
    return model.z == sum(
        c_dict[(i, j)] * model.sqrtx[i, j]
        for i in model.i
        for j in model.j
    )

model.defobjdisc = Constraint(
    rule=defobjdisc_rule,
    doc="Define objective with discretized sqrt"
)
