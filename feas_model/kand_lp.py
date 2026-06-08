# converted from gamslib kand (KAND, SEQ=187)
# Stochastic programming refinery blending problem (Kall & Wallace).
# Core single deterministic model = GAMS model `kand` / all / (obj, bal, dembal).
# The scenario / SPOSL re-solve (kandsp with eps back-link, eps=0) is dropped:
# it is numerically identical to the core model and is only a reformulation hook.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# JSON uses {sets, scalar_params, indexed_params} format with pipe-key notation
# for multi-dimensional params (e.g. "p-1|raw-1": value → (p-1, raw-1): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="KAND - stochastic refinery blending, total cost minimization")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Raw materials")
model.j = pyo.Set(initialize=data["j"], doc="Products")
model.t = pyo.Set(initialize=data["t"], doc="Time periods")
model.n = pyo.Set(initialize=data["n"], doc="Scenario-tree nodes")

# time-node mapping tn(t,n): list of [t, n] valid pairs
model.tn = pyo.Set(
    dimen=2,
    initialize=[tuple(p) for p in data["tn"]],
    doc="Valid (time, node) pairs",
)

# Parameters
model.c = pyo.Param(
    model.i, initialize=data["c"], mutable=True, within=pyo.NonNegativeReals,
    doc="Present cost of raw materials",
)
model.a = pyo.Param(
    model.j, model.i, initialize=data["a"], mutable=True, within=pyo.NonNegativeReals,
    doc="Yields (product per unit raw material)",
)
model.f = pyo.Param(
    model.j, model.t, initialize=data["f"], mutable=True, within=pyo.NonNegativeReals,
    doc="Cost of outsourcing",
)
model.b = pyo.Param(
    initialize=data["b"], mutable=True, within=pyo.NonNegativeReals,
    doc="Inventory capacity",
)
model.prob = pyo.Param(
    model.n, initialize=data["prob"], mutable=True, within=pyo.NonNegativeReals,
    doc="Node probability",
)
model.dem = pyo.Param(
    model.n, model.j, initialize=data["dem"], mutable=True, within=pyo.NonNegativeReals,
    doc="Stochastic demand",
)

# Variables
model.x = pyo.Var(
    model.i, model.t, domain=pyo.NonNegativeReals,
    doc="Raw material purchased for use in time t",
)
model.y = pyo.Var(
    model.j, model.tn, domain=pyo.NonNegativeReals,
    doc="Outsourced products at (product, time, node)",
)
model.cost = pyo.Var(domain=pyo.Reals, doc="Total cost")

# Constraints
def obj_rule(model):
    purchase = sum(model.c[i] * model.x[i, t] for i in model.i for t in model.t)
    outsource = sum(
        model.prob[n] * model.f[j, t] * model.y[j, t, n]
        for j in model.j for (t, n) in model.tn
    )
    return model.cost == purchase + outsource

model.objdef = pyo.Constraint(rule=obj_rule, doc="Total cost definition")

def bal_rule(model):
    return sum(model.x[i, t] for i in model.i for t in model.t) <= model.b

model.bal = pyo.Constraint(rule=bal_rule, doc="Purchase / inventory limit")

def dembal_rule(model, j, t, n):
    return sum(model.a[j, i] * model.x[i, t] for i in model.i) + model.y[j, t, n] >= model.dem[n, j]

model.dembal = pyo.Constraint(
    model.j, model.tn, rule=dembal_rule, doc="Demand balance",
)

# Objective
model.obj = pyo.Objective(expr=model.cost, sense=pyo.minimize, doc="Minimize total cost")
