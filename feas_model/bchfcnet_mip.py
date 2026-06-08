# converted from gamslib bchfcnet (BCHFCNET, SEQ=287)
# Single-commodity, uncapacitated, fixed-charge network flow problem (Berlin, 52 nodes).
# The original GAMS model drives a Branch-and-Cut-and-Heuristic (BCH) callback facility;
# those callbacks are solve-time cut generators and carry no model structure, so they are
# dropped here. With the model switches usetree/usett1/usett2 = 0 (their values in
# berlin2.inc), the active master problem is a pure fixed-charge network flow MIP:
#   minimize  sum_arc (vcost*x + fcost*y)   s.t.  flow conservation  and  x <= xupp*y.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "n1|n2|a1": value → (n1, n2, a1)).
# The sparse arc index set is stored as a list of pipe strings and split here.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

arc_tuples = [tuple(a.split("|")) if isinstance(a, str) else tuple(a) for a in data["arc"]]

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Fixed-charge network flow problem (Berlin, 52 nodes)")

# Sets
model.n = pyo.Set(initialize=data["n"], doc="Network nodes")
model.s = pyo.Set(initialize=data["s"], doc="Sub-arc index (parallel arcs)")
model.arc = pyo.Set(
    dimen=3,
    initialize=arc_tuples,
    doc="Existing arcs (m, n, s) over which flow may be routed",
)

# Parameters
model.vcost = pyo.Param(
    initialize=data["vcost"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Variable cost per unit of flow on an arc",
)

model.fcost = pyo.Param(
    model.arc,
    initialize=data["fcost"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Fixed cost charged when an arc is opened",
)

model.xupp = pyo.Param(
    model.arc,
    initialize=data["xupp"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Upper bound on flow over an arc (= total source supply)",
)

model.demand = pyo.Param(
    model.n,
    initialize=data["demand"],
    default=0.0,
    mutable=True,
    within=pyo.Reals,
    doc="Node net demand (negative at the single source node)",
)

# Variables
model.x = pyo.Var(
    model.arc,
    domain=pyo.NonNegativeReals,
    doc="Flow routed over each arc",
)

model.y = pyo.Var(
    model.arc,
    domain=pyo.Binary,
    doc="Fixed-charge build/usage decision for each arc",
)

# Constraints
def bal_rule(model, j):
    inflow = sum(model.x[m, n, sa] for (m, n, sa) in model.arc if n == j)
    outflow = sum(model.x[m, n, sa] for (m, n, sa) in model.arc if m == j)
    return inflow - outflow == model.demand[j]

model.bal = pyo.Constraint(model.n, rule=bal_rule, doc="Flow conservation at each node")

def bf_rule(model, m, n, sa):
    return model.x[m, n, sa] <= model.xupp[m, n, sa] * model.y[m, n, sa]

model.bf = pyo.Constraint(model.arc, rule=bf_rule, doc="Binary forcing: no flow on a closed arc")

# Objective
model.obj = pyo.Objective(
    expr=sum(
        model.vcost * model.x[m, n, sa] + model.fcost[m, n, sa] * model.y[m, n, sa]
        for (m, n, sa) in model.arc
    ),
    sense=pyo.minimize,
    doc="Minimize total variable plus fixed network cost",
)
