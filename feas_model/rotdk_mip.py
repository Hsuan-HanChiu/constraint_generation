# converted from gamslib rotdk (ROTDK, SEQ=185)
# Robust Optimization: capacity expansion of one telecom location with demand
# uncertainty (Laguna 1998). Time-dependent knapsack / robust MIP.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "t1|1": value → (t1, 1): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Robust capacity expansion under demand uncertainty")

# Sets
model.j = pyo.Set(initialize=data["j"], doc="Components (capacity sizes)")
model.t = pyo.Set(initialize=data["t"], ordered=True, doc="Time periods")
model.s = pyo.Set(initialize=data["s"], doc="Scenarios")

# Parameters
model.c = pyo.Param(
    model.j, initialize=data["c"], mutable=True, within=pyo.NonNegativeReals,
    doc="Capacity size of each component",
)
model.p = pyo.Param(
    model.j, initialize=data["p"], mutable=True, within=pyo.NonNegativeReals,
    doc="Capacity cost of each component",
)
model.dis = pyo.Param(
    model.t, initialize=data["dis"], mutable=True, within=pyo.NonNegativeReals,
    doc="Discount factor by time period",
)
model.D = pyo.Param(
    model.t, model.s, initialize=data["D"], mutable=True, within=pyo.NonNegativeReals,
    doc="Demand in each period under each scenario",
)
model.w = pyo.Param(
    initialize=data["w"], mutable=True, within=pyo.NonNegativeReals,
    doc="Shortage penalty",
)

# Variables
model.x = pyo.Var(
    model.j, model.t, domain=pyo.NonNegativeIntegers,
    doc="Number of each component expanded in each period",
)
model.z = pyo.Var(
    model.s, domain=pyo.NonNegativeReals,
    doc="Max capacity shortage in each scenario",
)
model.cap = pyo.Var(
    model.t, domain=pyo.Reals,
    doc="Installed capacity in each period",
)
model.obj_var = pyo.Var(domain=pyo.Reals, doc="Total discounted cost plus penalty")

# Constraints
def capbal_rule(model, t):
    # cap(t) = cap(t-1) + sum(j, c(j)*x(j,t)); cap(t-1)=0 at the first period
    prev = model.t.prev(t) if t != model.t.first() else None
    cap_prev = model.cap[prev] if prev is not None else 0
    return model.cap[t] == cap_prev + sum(model.c[j] * model.x[j, t] for j in model.j)

model.capbal = pyo.Constraint(model.t, rule=capbal_rule, doc="Capacity balance over time")

def dembal_rule(model, t, s):
    return model.cap[t] + model.z[s] >= model.D[t, s]

model.dembal = pyo.Constraint(model.t, model.s, rule=dembal_rule, doc="Demand balance per scenario")

def objdef_rule(model):
    card_s = len(model.s)
    return model.obj_var == (
        sum(model.dis[t] * model.p[j] * model.x[j, t] for j in model.j for t in model.t)
        + (model.w / card_s) * sum(model.z[s] for s in model.s)
    )

model.objdef = pyo.Constraint(rule=objdef_rule, doc="Objective accounting")

# Objective
model.obj = pyo.Objective(expr=model.obj_var, sense=pyo.minimize, doc="Minimize discounted expansion cost plus expected shortage penalty")
