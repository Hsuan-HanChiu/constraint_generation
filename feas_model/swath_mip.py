# converted from gamslib swath (SWATH, SEQ=325)
# Mission Planning for Synthetic Aperture Radar Surveillance.
# TSP-type MIP: route an aircraft through swaths (each scanned via one of its
# valid node-combinations) minimizing total flight distance. Core MIP only:
# degree + flow-balance + swath-tour linking; iterative subtour-elimination
# cuts (dynamic in the original GAMS loop) are dropped.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params; "s0|n1|s1|n2" → ('s0','n1','s1','n2').
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# Arc set a(s,n,s,n): the keys of l are exactly the valid (from-combo → to-combo)
# arcs (between distinct swaths' valid node-combinations, no self/within-swath).
arcs = list(data["l"].keys())

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="SWATH - SAR surveillance mission planning (TSP-type MIP)")

# Sets
model.s = pyo.Set(initialize=data["s"], doc="Swaths (regions to scan)")
model.n = pyo.Set(initialize=data["n"], doc="Nodes (entry/exit points of a swath)")
model.a = pyo.Set(dimen=4, initialize=arcs, doc="Arcs between valid swath-node combinations")

# valid swath-node combinations appearing as a from-endpoint of some arc
sx = sorted({(i, ni) for (i, ni, j, nj) in arcs})
model.sx = pyo.Set(dimen=2, initialize=sx, doc="Valid swath-node combinations")

# Parameters
model.l = pyo.Param(
    model.a,
    initialize=data["l"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Arc length (flight distance) between swath-node combinations",
)

# Variables
model.x = pyo.Var(model.a, domain=pyo.Binary, doc="1 if arc is used in the tour")
model.y = pyo.Var(model.s, model.s, domain=pyo.Binary, doc="1 if swath j follows swath i")
model.z = pyo.Var(domain=pyo.Reals, doc="Total tour length (objective)")

# Constraints
def defone_rule(model, sw):
    # exactly one arc enters each swath (across all its valid node-combos)
    return sum(model.x[i, ni, j, nj] for (i, ni, j, nj) in model.a if j == sw) == 1

model.defone = pyo.Constraint(model.s, rule=defone_rule, doc="One entering arc per swath")

def defbal_rule(model, sw, nd):
    if (sw, nd) not in model.sx:
        return pyo.Constraint.Skip
    inflow = sum(model.x[i, ni, j, nj] for (i, ni, j, nj) in model.a if (j, nj) == (sw, nd))
    outflow = sum(model.x[i, ni, j, nj] for (i, ni, j, nj) in model.a if (i, ni) == (sw, nd))
    return inflow - outflow == 0

model.defbal = pyo.Constraint(model.s, model.n, rule=defbal_rule, doc="Flow balance at each swath-node combination")

def defy_rule(model, i, j):
    if i == j:
        return pyo.Constraint.Skip
    return model.y[i, j] == sum(
        model.x[ii, ni, jj, nj] for (ii, ni, jj, nj) in model.a if ii == i and jj == j
    )

model.defy = pyo.Constraint(model.s, model.s, rule=defy_rule, doc="Swath tour determined by node tour")

def defobj_rule(model):
    return model.z == sum(model.l[a] * model.x[a] for a in model.a)

model.defobj = pyo.Constraint(rule=defobj_rule, doc="Accounting: total tour length")

# Objective
model.obj = pyo.Objective(expr=model.z, sense=pyo.minimize, doc="Minimize total flight distance")
