# converted from gamslib spbenders5 (SPBENDERS5, SEQ=422)
# Source is a parallel-MPI stochastic-Benders driver of the SAME stochastic
# transport model as spbenders3. The Benders master/subproblem split and the
# MPI/GamsModelInstance machinery are a solve technique, not part of the model.
# This file builds the equivalent monolithic extensive-form LP (mirrors
# spbenders3_lp).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Stochastic transport - extensive form")

# Sets
model.I = pyo.Set(initialize=data["i"], doc="Factories")
model.J = pyo.Set(initialize=data["j"], doc="Distribution centers")
model.S = pyo.Set(initialize=data["s"], doc="Scenarios")

# Parameters
model.capacity = pyo.Param(
    model.I,
    initialize=data["capacity"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Factory capacities"
)

model.prodcost = pyo.Param(
    initialize=float(data["prodcost"]),
    mutable=True,
    within=pyo.Reals,
    doc="Unit production cost"
)

model.price = pyo.Param(
    initialize=float(data["price"]),
    mutable=True,
    within=pyo.Reals,
    doc="Unit sales price"
)

model.wastecost = pyo.Param(
    initialize=float(data["wastecost"]),
    mutable=True,
    within=pyo.Reals,
    doc="Unit waste cost"
)

model.transcost = pyo.Param(
    model.I,
    model.J,
    initialize=data["transcost"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Unit transportation cost"
)

model.scen_prob = pyo.Param(
    model.S,
    initialize=data["scen_prob"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Scenario probabilities"
)

model.scen_demand = pyo.Param(
    model.S,
    model.J,
    initialize=data["scen_demand"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Scenario-specific demand"
)

# Variables
model.ship = pyo.Var(
    model.I,
    model.J,
    domain=pyo.NonNegativeReals,
    doc="Shipments from factories to distribution centers"
)

model.product = pyo.Var(
    model.I,
    domain=pyo.NonNegativeReals,
    doc="Production at factories"
)

model.received = pyo.Var(
    model.J,
    domain=pyo.NonNegativeReals,
    doc="Quantity sent to each market"
)

model.sales = pyo.Var(
    model.S,
    model.J,
    domain=pyo.NonNegativeReals,
    doc="Scenario sales"
)

model.waste = pyo.Var(
    model.S,
    model.J,
    domain=pyo.NonNegativeReals,
    doc="Scenario waste (overstock)"
)

# Constraints

def production_rule(model, i):
    return model.product[i] == sum(model.ship[i, j] for j in model.J)

model.production = pyo.Constraint(
    model.I,
    rule=production_rule,
    doc="Production balance at each factory"
)

def capacity_rule(model, i):
    return model.product[i] <= model.capacity[i]

model.capacity_con = pyo.Constraint(
    model.I,
    rule=capacity_rule,
    doc="Capacity limits at factories"
)

def receive_rule(model, j):
    return model.received[j] == sum(model.ship[i, j] for i in model.I)

model.receive = pyo.Constraint(
    model.J,
    rule=receive_rule,
    doc="Received quantity at markets"
)

def selling_rule(model, s, j):
    return model.sales[s, j] + model.waste[s, j] == model.received[j]

model.selling = pyo.Constraint(
    model.S,
    model.J,
    rule=selling_rule,
    doc="Split received into sales and waste per scenario"
)

def market_rule(model, s, j):
    return model.sales[s, j] <= model.scen_demand[s, j]

model.market = pyo.Constraint(
    model.S,
    model.J,
    rule=market_rule,
    doc="Upper bound on sales per scenario"
)

# Objective

def obj_rule(model):
    expected_recourse = sum(
        model.scen_prob[s]
        * (
            sum(model.price * model.sales[s, j] for j in model.J)
            - sum(model.wastecost * model.waste[s, j] for j in model.J)
        )
        for s in model.S
    )
    shipping_cost = sum(
        model.transcost[i, j] * model.ship[i, j]
        for i in model.I
        for j in model.J
    )
    production_cost = sum(
        model.prodcost * model.product[i] for i in model.I
    )
    return expected_recourse - shipping_cost - production_cost

model.obj = pyo.Objective(
    rule=obj_rule,
    sense=pyo.maximize,
    doc="Expected total profit"
)
