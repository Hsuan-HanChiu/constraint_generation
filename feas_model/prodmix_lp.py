# converted from gamslib prodmix (PRODMIX, SEQ=3)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "shop|desk": value → (shop, desk): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Production Mix Problem - furniture desk profit maximization")

# Sets
model.desk = pyo.Set(initialize=data["desk"], doc="Types of desks produced")
model.shop = pyo.Set(initialize=data["shop"], doc="Workshops (production stages)")

# Parameters
model.labor = pyo.Param(
    model.shop, model.desk,
    initialize=data["labor"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Labor requirement (man-hours) of each desk in each shop",
)

model.caplim = pyo.Param(
    model.shop,
    initialize=data["caplim"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Labor capacity (man-hours) available in each shop",
)

model.price = pyo.Param(
    model.desk,
    initialize=data["price"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Selling price in dollars per desk",
)

# Variables
model.mix = pyo.Var(
    model.desk,
    domain=pyo.NonNegativeReals,
    doc="Number of each desk produced",
)

model.profit = pyo.Var(
    domain=pyo.Reals,
    doc="Total profit in dollars",
)

# Constraints
def cap_rule(model, s):
    return sum(model.labor[s, d] * model.mix[d] for d in model.desk) <= model.caplim[s]

model.cap = pyo.Constraint(model.shop, rule=cap_rule, doc="Shop labor capacity (man-hours)")

def profit_rule(model):
    return model.profit == sum(model.price[d] * model.mix[d] for d in model.desk)

model.ap = pyo.Constraint(rule=profit_rule, doc="Accounting: total profit")

# Objective
model.obj = pyo.Objective(
    expr=model.profit,
    sense=pyo.maximize,
    doc="Maximize total profit",
)
