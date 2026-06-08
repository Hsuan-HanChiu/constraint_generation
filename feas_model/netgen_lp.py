# converted from gamslib netgen (NETGEN, SEQ=323)
# Min-cost-flow LP on the NETGEN-generated instance (first/NETGEN solve only).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "1|26": value → (1, 26): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── instance reshaping ────────────────────────────────────────────────────────
# Nodes come in as string members ("1".."50"); arcs as pipe-strings ("1|26").
# Normalize to integer node ids and (int, int) arc tuples so the flow
# conservation network is keyed consistently across sets, params and vars.
nodes = [int(n) for n in data["node"]]
arcs = [tuple(int(p) for p in a.split("|")) for a in data["arc"]]

# data_normalize already converts 2D pipe params to (int, int) tuples.
cost_raw = data["cost"]
cap_raw = data["capacity"]
cost = {tuple(int(x) for x in k): float(v) for k, v in cost_raw.items()}
capacity = {tuple(int(x) for x in k): float(v) for k, v in cap_raw.items()}
supply = {int(k): float(v) for k, v in data["supply"].items()}
demand = {int(k): float(v) for k, v in data["demand"].items()}
# ─────────────────────────────────────────────────────────────────────────────

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="NETGEN minimum-cost-flow problem")

# Sets
model.node = pyo.Set(initialize=nodes, doc="Network nodes")
model.arc = pyo.Set(within=model.node * model.node, initialize=arcs, doc="Directed arcs")

# Parameters
model.cost = pyo.Param(
    model.arc, initialize=cost, mutable=True, within=pyo.NonNegativeReals,
    doc="Unit shipping cost on each arc",
)
model.capacity = pyo.Param(
    model.arc, initialize=capacity, mutable=True, within=pyo.NonNegativeReals,
    doc="Flow capacity (upper bound) on each arc",
)
model.supply = pyo.Param(
    model.node, initialize=supply, mutable=True, within=pyo.NonNegativeReals,
    doc="Exogenous supply injected at each node",
)
model.demand = pyo.Param(
    model.node, initialize=demand, mutable=True, within=pyo.NonNegativeReals,
    doc="Exogenous demand withdrawn at each node",
)

# Variables
model.x = pyo.Var(
    model.arc, domain=pyo.NonNegativeReals,
    doc="Flow on each arc (bounded above by capacity)",
)

# Arc capacity bounds: x.up(a) = capacity(a)
def cap_bound_rule(model, i, j):
    return model.x[i, j] <= model.capacity[i, j]

model.cap = pyo.Constraint(model.arc, rule=cap_bound_rule, doc="Arc capacity")

# Flow conservation (multiplier == 1):
# supply(nn) + sum(arcs into nn) x  ==  sum(arcs out of nn) x + demand(nn)
def balance_rule(model, nn):
    inflow = sum(model.x[i, j] for (i, j) in model.arc if j == nn)
    outflow = sum(model.x[i, j] for (i, j) in model.arc if i == nn)
    return model.supply[nn] + inflow == outflow + model.demand[nn]

model.net = pyo.Constraint(model.node, rule=balance_rule, doc="Flow conservation")

# Objective
model.obj = pyo.Objective(
    expr=sum(model.cost[i, j] * model.x[i, j] for (i, j) in model.arc),
    sense=pyo.minimize,
    doc="Minimize total shipping cost",
)
