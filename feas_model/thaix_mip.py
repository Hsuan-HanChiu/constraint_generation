# converted from gamslib thaix (THAIX, SEQ=105)
# Thai Navy Problem Extended: allocate ships to transport personnel from ports
# to a training center. The GAMS source re-solves the model three times with
# different objective weights (w1/w2/w3). We build the single underlying core
# optimization model corresponding to the third solve (w1=0, w2=0, w3=1),
# i.e. minimizing man-miles, whose optimum is 1640980.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params and list-of-lists for tuple sets.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(
    doc="Thai Navy Problem Extended - ship routing / personnel assignment (min man-miles)"
)

# Sets
model.p = pyo.Set(initialize=data["p"], doc="Ports")
model.v = pyo.Set(initialize=data["v"], doc="Voyages")
model.k = pyo.Set(initialize=data["k"], doc="Ship classes")

# Multidimensional capability maps
model.vk = pyo.Set(
    dimen=2, initialize=data["vk"], doc="Voyage capability: (voyage, ship class)"
)
model.vkp = pyo.Set(
    dimen=3,
    initialize=data["vkp"],
    doc="Trips: (voyage, ship class, port)",
)

# Parameters
model.d = pyo.Param(
    model.p,
    initialize=data["d"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Number of men at port p needing transport",
)
model.shipcap = pyo.Param(
    model.k,
    initialize=data["shipcap"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Ship capacity in men",
)
model.n = pyo.Param(
    model.k,
    initialize=data["n"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Number of ships of class k available",
)
model.dist = pyo.Param(
    model.v,
    initialize=data["dist"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Voyage distance",
)

# Variables
# z(v,k): number of times voyage vk is used (integer), defined over vk only,
#         with z.up = n(k) from the GAMS source.
model.z = pyo.Var(
    model.vk,
    domain=pyo.NonNegativeIntegers,
    doc="Number of times voyage vk is used",
)
for (vv, kk) in model.vk:
    model.z[vv, kk].setub(value(model.n[kk]))

# y(v,k,p): number of men transported from port p via voyage vk (continuous >= 0)
model.y = pyo.Var(
    model.vkp,
    domain=pyo.NonNegativeReals,
    doc="Number of men transported from port p via voyage vk",
)

# Constraints
def demand_rule(model, pp):
    return (
        sum(model.y[vv, kk, qq] for (vv, kk, qq) in model.vkp if qq == pp)
        >= model.d[pp]
    )

model.demand = pyo.Constraint(model.p, rule=demand_rule, doc="Pick up all the men at port p")


def voycap_rule(model, vv, kk):
    return (
        sum(model.y[v2, k2, qq] for (v2, k2, qq) in model.vkp if v2 == vv and k2 == kk)
        <= model.shipcap[kk] * model.z[vv, kk]
    )

model.voycap = pyo.Constraint(model.vk, rule=voycap_rule, doc="Observe variable capacity of voyage vk")


def shiplim_rule(model, kk):
    return sum(model.z[vv, k2] for (vv, k2) in model.vk if k2 == kk) <= model.n[kk]

model.shiplim = pyo.Constraint(model.k, rule=shiplim_rule, doc="Observe limit of class k")

# Objective: minimize man-miles (third GAMS solve, w1=0, w2=0, w3=1)
model.obj = pyo.Objective(
    expr=sum(model.dist[vv] * model.y[vv, kk, qq] for (vv, kk, qq) in model.vkp),
    sense=pyo.minimize,
    doc="Minimize man-miles = sum(dist(v) * y(v,k,p))",
)
