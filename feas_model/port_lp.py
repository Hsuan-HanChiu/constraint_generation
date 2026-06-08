# converted from gamslib port (PORT, SEQ=50)
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
model = pyo.ConcreteModel(doc="Simple Portfolio Model - bond investment selection")

# Sets
model.b = pyo.Set(initialize=data["b"], doc="Bonds")
model.g = pyo.Set(within=model.b, initialize=data["g"], doc="Bond grouping (subset of bonds)")

# Parameters
model.rating = pyo.Param(
    model.b, initialize=data["rating"], mutable=True, within=pyo.NonNegativeReals,
    doc="Bond rating",
)
model.maturity = pyo.Param(
    model.b, initialize=data["maturity"], mutable=True, within=pyo.NonNegativeReals,
    doc="Bond maturity in years",
)
model.yld = pyo.Param(
    model.b, initialize=data["yield"], mutable=True, within=pyo.NonNegativeReals,
    doc="Bond yield in percent",
)
model.taxrate = pyo.Param(
    model.b, initialize=data["taxrate"], mutable=True, within=pyo.NonNegativeReals, default=0.0,
    doc="Bond tax rate",
)

# Variables
model.investment = pyo.Var(model.b, domain=pyo.NonNegativeReals, doc="Investment in each bond")
model.tinvest = pyo.Var(domain=pyo.NonNegativeReals, bounds=(0, 10), doc="Total investment")
model.ret = pyo.Var(domain=pyo.Reals, doc="Total after-tax return")

# Constraints
def groupmin_rule(model):
    return sum(model.investment[g] for g in model.g) >= 4
model.groupmin = pyo.Constraint(rule=groupmin_rule, doc="Minimum investment in group")

def rdef_rule(model):
    return sum(model.rating[b] * model.investment[b] for b in model.b) <= 1.4 * model.tinvest
model.rdef = pyo.Constraint(rule=rdef_rule, doc="Rating definition")

def mdef_rule(model):
    return sum(model.maturity[b] * model.investment[b] for b in model.b) <= 5.0 * model.tinvest
model.mdef = pyo.Constraint(rule=mdef_rule, doc="Maturity definition")

def tdef_rule(model):
    return model.tinvest == sum(model.investment[b] for b in model.b)
model.tdef = pyo.Constraint(rule=tdef_rule, doc="Total investment definition")

def idef_rule(model):
    return model.ret == sum(model.yld[b] / 100 * (1 - model.taxrate[b]) * model.investment[b] for b in model.b)
model.idef = pyo.Constraint(rule=idef_rule, doc="Total after-tax return definition")

# Objective
model.obj = pyo.Objective(expr=model.ret, sense=pyo.maximize, doc="Maximize total after-tax return")
