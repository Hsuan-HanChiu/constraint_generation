# converted from gamslib phosdis (PHOSDIS, SEQ=78)
# Sea Distances for a World Phosphate Model — shortest sea-route LP.
#
# The original GAMS file solves the underlying `route` model seven times in a
# `for` loop, picking four source nodes at a time (a "piecemeal" device used only
# to fit the model under small-machine / community-license size limits) and
# remapping the resulting marginals into producer/market distance tables.
# Those iteration/reporting re-solves are scenario plumbing, not the model.
#
# This file converts the UNDERLYING single optimization model: the `route`
# multi-source shortest-path LP for the final batch of sources
# (s = {veracruz, yucatan-ch}), which is the last solve in the loop and the one
# whose objective the task references (~959033).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "odessa|istanbul": value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# darc(n,np): directed arc distances (symmetric — every link stored both ways).
darc_data = data["darc"]

# Arc list and per-node adjacency (which arcs leave / enter each node).
arcs = list(darc_data.keys())
out_arcs = {}   # node -> list of np with arc (node, np)
in_arcs = {}    # node -> list of n  with arc (n, node)
for (a, b) in arcs:
    out_arcs.setdefault(a, []).append(b)
    in_arcs.setdefault(b, []).append(a)

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="World Phosphate Model - shortest sea-route LP")

# Sets
model.nodes = pyo.Set(initialize=data["nodes"], doc="Ports / nodes")
model.src = pyo.Set(initialize=data["src"], doc="Source nodes (origins to route from)")
model.dest = pyo.Set(initialize=data["dest"], doc="Destination nodes to reach")
model.arcs = pyo.Set(initialize=arcs, dimen=2, doc="Directed arcs with a distance")

# Parameters
model.darc = pyo.Param(
    model.arcs,
    initialize=darc_data,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Directed arc distance (nautical miles)",
)

# Variables
model.x = pyo.Var(
    model.src, model.arcs,
    domain=pyo.NonNegativeReals,
    doc="Flow from source s on arc (n, np)",
)

model.cost = pyo.Var(
    domain=pyo.Reals,
    doc="Total cost / length (nautical miles)",
)

# Constraints
# Node balance: for each source s and every node n != s, inflow to n must be at
# least one unit more than outflow from n. Requiring +1 of net inflow at every
# non-source node forces a unit of flow to reach each node, so the minimum-cost
# solution is the shortest-route (spanning) tree from s; the constraint duals
# recover the shortest sea distances.
def nb_rule(model, s, n):
    if n == s:
        return pyo.Constraint.Skip
    inflow = sum(model.x[s, a, n] for a in in_arcs.get(n, []))
    outflow = sum(model.x[s, n, b] for b in out_arcs.get(n, []))
    return inflow >= outflow + 1

model.nb = pyo.Constraint(model.src, model.nodes, rule=nb_rule, doc="Node balance")

def cd_rule(model):
    return model.cost == sum(
        model.darc[a, b] * model.x[s, a, b]
        for s in model.src
        for (a, b) in model.arcs
    )

model.cd = pyo.Constraint(rule=cd_rule, doc="Cost definition")

# Objective
model.obj = pyo.Objective(
    expr=model.cost,
    sense=pyo.minimize,
    doc="Minimize total route length",
)
