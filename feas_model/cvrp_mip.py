# converted from gamslib cvrp (CVRP, SEQ=435)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "n1|n2": value → (n1, n2): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Capacitated Vehicle Routing Problem (a-n32-k05, 16 nodes, 3 vehicles, MTZ subtour elimination)")

# Sets
model.node = pyo.Set(initialize=data["node"], doc="Customer/depot nodes")
model.vehicle = pyo.Set(initialize=data["vehicle"], doc="Vehicles in the fleet")
model.depot = pyo.Set(initialize=data["depot"], within=model.node, doc="Depot node(s)")

# Allowed arcs: every ordered pair of distinct nodes, for every vehicle
model.arc = pyo.Set(
    dimen=3,
    initialize=[(i, j, k) for i in data["node"] for j in data["node"] for k in data["vehicle"] if i != j],
    doc="Allowed arcs (i, j, k): vehicle k may travel from node i to node j (i != j)",
)

# Parameters
model.demand = pyo.Param(
    model.node,
    initialize=data["demand"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Demand of the customer at each node",
)

model.capacity = pyo.Param(
    model.vehicle,
    initialize=data["capacity"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Capacity of each vehicle",
)

model.distance = pyo.Param(
    model.node, model.node,
    initialize=data["distance"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Euclidean distance between each pair of nodes",
)

model.card = pyo.Param(
    initialize=data["card"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Number of nodes (cardinality of the node set), used in MTZ bound",
)

# Variables
model.X = pyo.Var(
    model.arc,
    domain=pyo.Binary,
    doc="1 if vehicle k travels directly from node i to node j",
)

model.P = pyo.Var(
    model.node,
    domain=pyo.NonNegativeReals,
    bounds=(0, pyo.value(model.card) - 1),
    doc="MTZ ordering / cumulative-load variable for each node",
)

model.totdist = pyo.Var(
    domain=pyo.Reals,
    doc="Total distance travelled by the fleet",
)

# Fix the MTZ variable to 0 at the depot
for d in model.depot:
    model.P[d].fix(0)

# Constraints
def node_balance_rule(model, j, k):
    return (
        sum(model.X[i, j, k] for i in model.node if i != j)
        == sum(model.X[j, i, k] for i in model.node if i != j)
    )
model.eq_node_balance = pyo.Constraint(
    model.node, model.vehicle, rule=node_balance_rule,
    doc="Every vehicle that enters a node must also leave it",
)

def enter_once_rule(model, j):
    if j in model.depot:
        return pyo.Constraint.Skip
    return sum(model.X[i, j, k] for i in model.node for k in model.vehicle if i != j) == 1
model.eq_enter_once = pyo.Constraint(
    model.node, rule=enter_once_rule,
    doc="Each customer node is visited exactly once",
)

def leave_depot_rule(model, k, d):
    return sum(model.X[d, j, k] for j in model.node if j not in model.depot) == 1
model.eq_leave_depot = pyo.Constraint(
    model.vehicle, model.depot, rule=leave_depot_rule,
    doc="Each vehicle leaves the depot exactly once",
)

def capacity_rule(model, k):
    return (
        sum(
            model.demand[j] * model.X[i, j, k]
            for i in model.node for j in model.node
            if i != j and j not in model.depot
        )
        <= model.capacity[k]
    )
model.eq_capacity = pyo.Constraint(
    model.vehicle, rule=capacity_rule,
    doc="Total demand served by each vehicle must not exceed its capacity",
)

def mtz_rule(model, i, j):
    if i == j:
        return pyo.Constraint.Skip
    extra = model.card if j in model.depot else 0
    return (
        model.P[i] - model.P[j]
        <= model.card - model.card * sum(model.X[i, j, k] for k in model.vehicle) - 1 + extra
    )
model.eq_mtz = pyo.Constraint(
    model.node, model.node, rule=mtz_rule,
    doc="Miller-Tucker-Zemlin subtour elimination",
)

def totdist_rule(model):
    return model.totdist == sum(
        model.distance[i, j] * model.X[i, j, k] for (i, j, k) in model.arc
    )
model.eq_tot_dist = pyo.Constraint(rule=totdist_rule, doc="Accounting: total distance")

# Objective
model.obj = pyo.Objective(
    expr=model.totdist,
    sense=pyo.minimize,
    doc="Minimize total distance travelled",
)
