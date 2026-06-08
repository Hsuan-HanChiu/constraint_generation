# converted from gamslib msm (MSM, SEQ=66)
# Morocco Fertilizer Distribution - Transport Mode Selection.
#
# The GAMS model "msm" is solved five times with different rate parameters and
# different dynamic source/destination sets (three transport matrices). This
# conversion captures the UNDERLYING single optimization model corresponding to
# the LAST solve: bagging-centers (ord > 12) -> market centers, bagged-product
# rates. GAMS objective for this solve = 3957.98.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# Pipe-keyed multi-index params (e.g. "n|np|m") are normalized into tuple keys
# (n, np, m) before the model code runs.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

darcs = data["darcs"]   # (n, np, m) -> directed distance (km)
nm = data["nm"]         # (n, m) -> 1.0 if mode m is available at node n
srate = data["srate"]   # (m, mp) -> mode switching cost

# Precompute adjacency for efficient constraint construction.
nm_set = set(nm.keys())                       # available (node, mode) pairs
modes_at = {}                                 # node -> list of available modes
for (n, mm) in nm_set:
    modes_at.setdefault(n, []).append(mm)
inbound = {}    # (n, m) -> list of np with darcs(np, n, m) != 0
outbound = {}   # (n, m) -> list of np with darcs(n, np, m) != 0
for (a, b, mm), dist in darcs.items():
    if dist != 0:
        outbound.setdefault((a, mm), []).append(b)
        inbound.setdefault((b, mm), []).append(a)

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Morocco transport mode selection (bagging centers -> markets)")

# Sets
model.n = pyo.Set(initialize=data["n"], doc="Nodes of the rail/road network")
model.m = pyo.Set(initialize=data["m"], doc="Transport modes (rail, road)")
model.s = pyo.Set(initialize=data["s"], doc="Source nodes (bagging centers)")
model.d = pyo.Set(initialize=data["d"], doc="Destination nodes (market centers)")

# Parameters
model.darcs = pyo.Param(
    model.n, model.n, model.m,
    initialize=darcs, default=0.0, mutable=True, within=pyo.NonNegativeReals,
    doc="Directed arc length (km), symmetric max of rail/road distances",
)
model.mrate = pyo.Param(
    model.m, initialize=data["mrate"], mutable=True, within=pyo.NonNegativeReals,
    doc="Mode travel rate ($ per km per ton)",
)
model.lrate = pyo.Param(
    model.m, initialize=data["lrate"], mutable=True, within=pyo.NonNegativeReals,
    doc="Loading rate ($ per ton)",
)
model.urate = pyo.Param(
    model.m, initialize=data["urate"], mutable=True, within=pyo.NonNegativeReals,
    doc="Unloading rate ($ per ton)",
)
model.srate = pyo.Param(
    model.m, model.m, initialize=srate, mutable=True, within=pyo.NonNegativeReals,
    doc="Mode switching cost ($ per ton)",
)

# Variables (flows are indexed by their source node s)
model.x = pyo.Var(model.s, model.n, model.n, model.m,
                  domain=pyo.NonNegativeReals, doc="Flow on arc (n->np) in mode m, for source s")
model.y = pyo.Var(model.s, model.m,
                  domain=pyo.NonNegativeReals, doc="Loading at source s in mode m")
model.z = pyo.Var(model.s, model.n, model.m,
                  domain=pyo.NonNegativeReals, doc="Unloading at destination node in mode m, for source s")
model.w = pyo.Var(model.s, model.n, model.m, model.m,
                  domain=pyo.NonNegativeReals, doc="Mode switching (m->mp) at node n, for source s")

model.phi = pyo.Var(domain=pyo.Reals, doc="Total cost ($ per ton)")
model.phil = pyo.Var(domain=pyo.Reals, doc="Loading cost ($ per ton)")
model.phiu = pyo.Var(domain=pyo.Reals, doc="Unloading cost ($ per ton)")
model.phis = pyo.Var(domain=pyo.Reals, doc="Switching cost ($ per ton)")
model.phim = pyo.Var(domain=pyo.Reals, doc="Mode travel cost ($ per ton)")

d_set = set(data["d"])

# Node balance: generated for each source s and (node n, mode m) with nm(n,m).
def nb_rule(model, s, n, mm):
    if (n, mm) not in nm_set:
        return pyo.Constraint.Skip
    # inflow
    inflow = sum(model.x[s, np, n, mm] for np in inbound.get((n, mm), []))
    inflow += sum(model.w[s, n, mm, mp] for mp in modes_at.get(n, []))
    if n == s:  # orig(s,n) holds only on the diagonal
        inflow += model.y[s, mm]
    # outflow
    outflow = sum(model.x[s, n, np, mm] for np in outbound.get((n, mm), []))
    if n in d_set:
        outflow += model.z[s, n, mm]
    outflow += sum(model.w[s, n, mp, mm] for mp in modes_at.get(n, []))
    return inflow >= outflow

model.nb = pyo.Constraint(model.s, model.n, model.m, rule=nb_rule, doc="Node balance")

# Destination balance: each destination must receive at least 1 unit from each source.
def db_rule(model, s, dd):
    return sum(model.z[s, dd, mm] for mm in modes_at.get(dd, [])) >= 1
model.db = pyo.Constraint(model.s, model.d, rule=db_rule, doc="Destination balance (deliver 1 unit)")

# Accounting equations
def al_rule(model):
    return model.phil == sum(model.lrate[mm] * model.y[s, mm]
                             for s in model.s for mm in modes_at.get(s, []))
model.al = pyo.Constraint(rule=al_rule, doc="Loading cost")

def au_rule(model):
    return model.phiu == sum(model.urate[mm] * model.z[s, dd, mm]
                             for s in model.s for dd in model.d for mm in modes_at.get(dd, []))
model.au = pyo.Constraint(rule=au_rule, doc="Unloading cost")

def as_rule(model):
    return model.phis == sum(
        model.srate[mm, mp] * model.w[s, n, mm, mp]
        for s in model.s for n in model.n
        for mm in modes_at.get(n, []) for mp in modes_at.get(n, [])
    )
model.as_ = pyo.Constraint(rule=as_rule, doc="Switching cost")

def am_rule(model):
    return model.phim == sum(
        model.mrate[mm] * model.darcs[n, np, mm] * model.x[s, n, np, mm]
        for s in model.s for (n, np, mm) in darcs if darcs[(n, np, mm)] != 0
    )
model.am = pyo.Constraint(rule=am_rule, doc="Mode travel cost")

def cd_rule(model):
    return model.phi == model.phil + model.phiu + model.phis + model.phim
model.cd = pyo.Constraint(rule=cd_rule, doc="Total cost accounting")

# Objective
model.obj = pyo.Objective(expr=model.phi, sense=pyo.minimize, doc="Minimize total transport cost")
