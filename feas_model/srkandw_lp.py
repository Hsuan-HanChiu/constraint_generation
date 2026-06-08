# converted from gamslib srkandw (SRKANDW, SEQ=248)
# Stochastic-programming refinery blending model (Kall & Wallace).
# The GAMS file wraps the core LP in a ScenRed scenario-reduction loop that
# re-solves the model many times. This conversion keeps the single underlying
# optimization model evaluated over the FULL (unreduced) scenario tree, i.e.
# the GAMS "$label NoScenReduction" path where sn(n)=yes and sprob(n)=prob(n).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

model = pyo.ConcreteModel(doc="Refinery blending under demand uncertainty (full scenario tree)")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Raw materials")
model.j = pyo.Set(initialize=data["j"], doc="Products")
model.t = pyo.Set(initialize=data["t"], doc="Time periods")
model.n = pyo.Set(initialize=data["n"], doc="Scenario-tree nodes")
model.tn = pyo.Set(dimen=2, initialize=data["tn"], doc="Valid (time, node) pairs")

# Parameters
model.c = pyo.Param(
    model.i, initialize=data["c"], mutable=True, within=pyo.NonNegativeReals,
    doc="Present cost of raw materials",
)
model.a = pyo.Param(
    model.j, model.i, initialize=data["a"], mutable=True, within=pyo.NonNegativeReals,
    doc="Yield of product j per unit of raw material i",
)
model.f = pyo.Param(
    model.j, model.t, initialize=data["f"], mutable=True, within=pyo.NonNegativeReals,
    doc="Cost of outsourcing product j in period t",
)
model.b = pyo.Param(
    initialize=data["b"], mutable=True, within=pyo.NonNegativeReals,
    doc="Total raw-material inventory capacity",
)
model.sprob = pyo.Param(
    model.n, initialize=data["sprob"], mutable=True, within=pyo.NonNegativeReals,
    doc="Node probability in the (full) scenario tree",
)
model.dem = pyo.Param(
    model.j, model.n, initialize=data["dem"], mutable=True, within=pyo.NonNegativeReals,
    doc="Stochastic product demand at each node",
)

# Variables
model.x = pyo.Var(
    model.i, model.t, domain=pyo.NonNegativeReals,
    doc="Raw material purchased for use in period t",
)
model.y = pyo.Var(
    model.j, model.tn, domain=pyo.NonNegativeReals,
    doc="Outsourced product j at (time, node)",
)
model.cost = pyo.Var(domain=pyo.Reals, doc="Total expected cost")

# Constraints
def bal_rule(model):
    return sum(model.x[i, t] for i in model.i for t in model.t) <= model.b
model.bal = pyo.Constraint(rule=bal_rule, doc="Total purchase limited by inventory capacity")

def dembal_rule(model, jj, t, nd):
    return sum(model.a[jj, i] * model.x[i, t] for i in model.i) + model.y[jj, t, nd] >= model.dem[jj, nd]
model.dembal = pyo.Constraint(model.j, model.tn, rule=dembal_rule, doc="Demand balance at each node")

def cost_rule(model):
    purchase = sum(model.c[i] * model.x[i, t] for i in model.i for t in model.t)
    outsource = sum(model.sprob[nd] * model.f[jj, t] * model.y[jj, t, nd]
                    for jj in model.j for (t, nd) in model.tn)
    return model.cost == purchase + outsource
model.obj_def = pyo.Constraint(rule=cost_rule, doc="Total expected cost definition")

# Objective
model.obj = pyo.Objective(expr=model.cost, sense=pyo.minimize, doc="Minimize total expected cost")
