# converted from gamslib food (FOOD, SEQ=352)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "m1|v1": value → (m1, v1): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Food Manufacturing - blending of oils over six months")

# Sets
model.m = pyo.Set(initialize=data["m"], ordered=True, doc="Planning periods (months)")
model.p = pyo.Set(initialize=data["p"], doc="Raw oils")
model.pv = pyo.Set(initialize=data["pv"], within=model.p, doc="Vegetable oils")
model.pnv = pyo.Set(initialize=data["pnv"], within=model.p, doc="Non-vegetable oils")

# Scalar parameters
model.maxstore = pyo.Param(initialize=data["maxstore"], mutable=True, doc="Maximum storage of each raw oil")
model.maxusepv = pyo.Param(initialize=data["maxusepv"], mutable=True, doc="Maximum use of vegetable oils")
model.maxusepnv = pyo.Param(initialize=data["maxusepnv"], mutable=True, doc="Maximum use of non-vegetable oils")
model.minusep = pyo.Param(initialize=data["minusep"], mutable=True, doc="Minimum use of a raw oil when blended")
model.maxnusep = pyo.Param(initialize=data["maxnusep"], mutable=True, doc="Maximum number of raw oils in a blend")
model.sp = pyo.Param(initialize=data["sp"], mutable=True, doc="Sales price of refined and blended oil")
model.sc = pyo.Param(initialize=data["sc"], mutable=True, doc="Storage cost of raw oils")
model.hmin = pyo.Param(initialize=data["hmin"], mutable=True, doc="Minimum hardness of refined oil")
model.hmax = pyo.Param(initialize=data["hmax"], mutable=True, doc="Maximum hardness of refined oil")

# Indexed parameters
model.stock = pyo.Param(model.p, initialize=data["stock"], mutable=True, doc="Stock at beginning and end")
model.h = pyo.Param(model.p, initialize=data["h"], mutable=True, doc="Hardness of raw oils")
model.cost = pyo.Param(model.m, model.p, initialize=data["cost"], mutable=True, doc="Raw oil cost per period")

# Variables
model.produce = pyo.Var(model.m, domain=pyo.NonNegativeReals, doc="Production of blended/refined oil per month")
model.use = pyo.Var(model.m, model.p, domain=pyo.NonNegativeReals, doc="Usage of raw oil per month")
model.induse = pyo.Var(model.m, model.p, domain=pyo.Binary, doc="Indicator for usage of raw oil per month")
model.buy = pyo.Var(model.m, model.p, domain=pyo.NonNegativeReals, doc="Purchase of raw oil per month")
model.store = pyo.Var(model.m, model.p, domain=pyo.NonNegativeReals, doc="Storage of raw oil at end of month")
model.profit = pyo.Var(domain=pyo.Reals, doc="Objective variable")

# Bounds on storage: up to maxstore per month; final month fixed to stock level
_mlist = list(model.m)
_last = _mlist[-1]
for mm in model.m:
    for pp in model.p:
        model.store[mm, pp].setub(pyo.value(model.maxstore))
for pp in model.p:
    model.store[_last, pp].fix(pyo.value(model.stock[pp]))

# Objective accounting equation
def defobj_rule(model):
    return model.profit == (
        sum(model.sp * model.produce[mm] for mm in model.m)
        - sum(model.cost[mm, pp] * model.buy[mm, pp] for mm in model.m for pp in model.p)
        - sum(model.sc * model.store[mm, pp] for mm in model.m for pp in model.p)
    )
model.defobj = pyo.Constraint(rule=defobj_rule, doc="Objective definition")

# Constraints
def defusepv_rule(model, mm):
    return sum(model.use[mm, pp] for pp in model.pv) <= model.maxusepv
model.defusepv = pyo.Constraint(model.m, rule=defusepv_rule, doc="Maximum use of vegetable oils")

def defusepnv_rule(model, mm):
    return sum(model.use[mm, pp] for pp in model.pnv) <= model.maxusepnv
model.defusepnv = pyo.Constraint(model.m, rule=defusepnv_rule, doc="Maximum use of non-vegetable oils")

def defproduce_rule(model, mm):
    return model.produce[mm] == sum(model.use[mm, pp] for pp in model.p)
model.defproduce = pyo.Constraint(model.m, rule=defproduce_rule, doc="Production of refined oil")

def defhmin_rule(model, mm):
    return sum(model.h[pp] * model.use[mm, pp] for pp in model.p) >= model.hmin * model.produce[mm]
model.defhmin = pyo.Constraint(model.m, rule=defhmin_rule, doc="Minimum hardness requirement")

def defhmax_rule(model, mm):
    return sum(model.h[pp] * model.use[mm, pp] for pp in model.p) <= model.hmax * model.produce[mm]
model.defhmax = pyo.Constraint(model.m, rule=defhmax_rule, doc="Maximum hardness requirement")

# steady-state stock: previous month's storage uses circular lag (m1's prev is the last month)
def stockbal_rule(model, mm, pp):
    idx = _mlist.index(mm)
    prev = _mlist[idx - 1]  # circular: for m1 (idx 0) this is _mlist[-1] = last month
    return model.store[prev, pp] + model.buy[mm, pp] == model.use[mm, pp] + model.store[mm, pp]
model.stockbal = pyo.Constraint(model.m, model.p, rule=stockbal_rule, doc="Stock balance constraint")

# logical constraints
def minuse_rule(model, mm, pp):
    return model.use[mm, pp] >= model.minusep * model.induse[mm, pp]
model.minuse = pyo.Constraint(model.m, model.p, rule=minuse_rule, doc="Minimum usage of raw oil when blended")

def maxuse_rule(model, mm, pp):
    cap = (model.maxusepv if pp in model.pv else model.maxusepnv)
    return model.use[mm, pp] <= cap * model.induse[mm, pp]
model.maxuse = pyo.Constraint(model.m, model.p, rule=maxuse_rule, doc="Usage is 0 if induse is 0")

def maxnuse_rule(model, mm):
    return sum(model.induse[mm, pp] for pp in model.p) <= model.maxnusep
model.maxnuse = pyo.Constraint(model.m, rule=maxnuse_rule, doc="Maximum number of raw oils used in a blend")

def deflogic1_rule(model, mm):
    return sum(model.induse[mm, pp] for pp in model.pv) <= model.induse[mm, "o3"] * len(model.pv)
model.deflogic1 = pyo.Constraint(model.m, rule=deflogic1_rule, doc="If a vegetable oil is used, o3 must be used")

# Objective
model.obj = pyo.Objective(expr=model.profit, sense=pyo.maximize, doc="Maximize total profit")
