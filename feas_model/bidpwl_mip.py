# converted from gamslib bidpwl (BIDPWL, SEQ=385)
# Bid evaluation with piecewise-linear cost functions.
# Each vendor's cost is a piecewise-linear function of the units purchased,
# represented by segments. Each segment s of vendor v is defined by a start
# point (px, py), a length pl, and a slope pg. A binary picks the active
# segment per vendor; a positive variable measures how far into the segment
# we go. Segment 0 is the "no deal" segment (length 0 -> x = y = 0).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional members (e.g. "b|2": value → (b, 2): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# Active vendor-segment pairs come in as pipe-strings ("b|2"); split into (v, s)
# tuples with an integer segment index to match the normalized param keys.
def _split_seg(key):
    v, s = key.split("|")
    return (v, int(s))

seg_pairs = [_split_seg(k) for k in data["seg"]]

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Bid evaluation with piecewise-linear cost functions")

# Sets
model.v = pyo.Set(initialize=data["v"], doc="Vendors")
model.seg = pyo.Set(within=model.v * pyo.Integers, initialize=seg_pairs,
                    doc="Active (vendor, segment) pairs")

# Scalar parameters
model.req = pyo.Param(initialize=data["req"], mutable=True,
                      within=pyo.NonNegativeReals,
                      doc="Total units required")

# Segment parameters (indexed by active (vendor, segment) pairs)
model.px = pyo.Param(model.seg, initialize=data["px"], mutable=True,
                     within=pyo.Reals, doc="Segment start x coordinate (q-min)")
model.py = pyo.Param(model.seg, initialize=data["py"], mutable=True,
                     within=pyo.Reals, doc="Segment start y coordinate (base cost)")
model.pl = pyo.Param(model.seg, initialize=data["pl"], mutable=True,
                     within=pyo.NonNegativeReals, doc="Segment length (q-max - q-min)")
model.pg = pyo.Param(model.seg, initialize=data["pg"], mutable=True,
                     within=pyo.NonNegativeReals, doc="Segment slope (unit price)")

# Variables
model.cost = pyo.Var(domain=pyo.Reals, doc="Total cost")
model.x = pyo.Var(model.v, domain=pyo.Reals, doc="Units purchased from each vendor")
model.y = pyo.Var(model.v, domain=pyo.Reals, doc="Cost of units from each vendor")
model.segx = pyo.Var(model.seg, domain=pyo.NonNegativeReals,
                     doc="Distance travelled into a segment from its start point")
model.segb = pyo.Var(model.seg, domain=pyo.Binary,
                     doc="1 if the segment is the active one for its vendor")

# Constraints
def segcap_rule(model, v, s):
    # segment travel cannot exceed the segment length, and only if active
    return model.segx[v, s] <= model.pl[v, s] * model.segb[v, s]
model.segcap = pyo.Constraint(model.seg, rule=segcap_rule,
                              doc="Segment travel bounded by length when active")

def oneseg_rule(model, v):
    return sum(model.segb[v, s] for (vv, s) in model.seg if vv == v) == 1
model.oneseg = pyo.Constraint(model.v, rule=oneseg_rule,
                              doc="Exactly one segment active per vendor")

def defx_rule(model, v):
    # x(v) = sum over segments of [ start-x * active + travel ]  (sign(l) >= 0)
    return model.x[v] == sum(
        model.segb[v, s] * model.px[v, s] + model.segx[v, s]
        for (vv, s) in model.seg if vv == v
    )
model.defx = pyo.Constraint(model.v, rule=defx_rule,
                            doc="Define units purchased from a vendor")

def defy_rule(model, v):
    # y(v) = sum over segments of [ start-y * active + slope * travel ]
    return model.y[v] == sum(
        model.segb[v, s] * model.py[v, s] + model.segx[v, s] * model.pg[v, s]
        for (vv, s) in model.seg if vv == v
    )
model.defy = pyo.Constraint(model.v, rule=defy_rule,
                            doc="Define cost of units from a vendor")

def demand_rule(model):
    return model.req == sum(model.x[v] for v in model.v)
model.demand = pyo.Constraint(rule=demand_rule, doc="Meet total requirement")

def costdef_rule(model):
    return model.cost == sum(model.y[v] for v in model.v)
model.costdef = pyo.Constraint(rule=costdef_rule, doc="Total cost definition")

# Objective
model.obj = pyo.Objective(expr=model.cost, sense=pyo.minimize,
                          doc="Minimize total cost")
