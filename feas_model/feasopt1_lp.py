# converted from gamslib feasopt1 (FEASOPT1, SEQ=314)
# Elastic / feasibility-relaxation form of Dantzig's infeasible transportation
# problem. The original transport LP is infeasible because (after a 20% demand
# bump) total demand 1080 exceeds total supply 950 by 130. CPLEX/Gurobi FeasOpt
# finds the minimum relaxation of the demand bounds that restores feasibility.
# This model encodes that elastic problem explicitly: non-negative relaxation
# (slack) variables r(j) are added to the demand constraints, and the objective
# minimizes the total relaxation. The optimum total relaxation equals 130, the
# supply/demand shortfall (matching the FeasOpt sum-of-infeasibilities result).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "seattle|new-york": value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(
    doc="FeasOpt elastic transportation problem - minimum demand relaxation"
)

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Canning plants (supply nodes)")
model.j = pyo.Set(initialize=data["j"], doc="Markets (demand nodes)")

# Parameters
model.a = pyo.Param(
    model.i,
    initialize=data["a"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Capacity of plant i in cases",
)

model.b = pyo.Param(
    model.j,
    initialize=data["b"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Demand at market j in cases (already inflated 20%)",
)

model.c = pyo.Param(
    model.i, model.j,
    initialize=data["c"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Transport cost in thousands of dollars per case",
)

# Variables
model.x = pyo.Var(
    model.i, model.j,
    domain=pyo.NonNegativeReals,
    doc="Shipment quantities in cases",
)

model.r = pyo.Var(
    model.j,
    domain=pyo.NonNegativeReals,
    doc="Demand relaxation (slack) added to each market's requirement",
)

# Constraints
def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= model.a[i]

model.supply = pyo.Constraint(model.i, rule=supply_rule, doc="Observe supply limit at plant i")

def demand_rule(model, j):
    # Relaxed demand: shipments plus relaxation must meet (inflated) demand.
    return sum(model.x[i, j] for i in model.i) + model.r[j] >= model.b[j]

model.demand = pyo.Constraint(model.j, rule=demand_rule, doc="Satisfy demand at market j (elastic)")

# Objective: minimize total relaxation needed to restore feasibility.
model.obj = pyo.Objective(
    expr=sum(model.r[j] for j in model.j),
    sense=pyo.minimize,
    doc="Minimize total demand relaxation (FeasOpt sum-of-infeasibilities)",
)
