# converted from models/ajax_lp.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# SET_BLOCK
model.m = Set(initialize=data['m'])
model.g = Set(initialize=data['g'])

# PARAM_BLOCK
model.prate = Param(model.g, model.m, initialize=data['prate'], mutable = True, doc='Production rate (tons per hour)')
model.pcost = Param(model.g, model.m, initialize=data['pcost'], mutable = True, doc='Production cost ($ per ton)')
model.dempr_demand = Param(model.g, initialize= {g: data['dempr'][g, 'demand'] for g in model.g}, mutable = True, doc='Demand (tons per month)')
model.dempr_price = Param(model.g, initialize={g: data['dempr'][g, 'price'] for g in model.g}, mutable = True, doc='Price ($ per ton)')
model.avail = Param(model.m, initialize=data['avail'], mutable = True, doc='Available machine time (hours per month)')

# VAR_BLOCK
model.outp = Var(model.g, model.m, within=NonNegativeReals, doc='Production (tons per month)')
model.profit = Var(within=NonNegativeReals, doc='Profit ($ per month)')

# OBJ_BLOCK
model.obj = Objective(expr=model.profit, sense=maximize)

# CONS_BLOCK
def capacity_rule(model, m):
    return sum(model.outp[g, m] / model.prate[g, m] for g in model.g) <= model.avail[m]
model.cap = Constraint(model.m, rule=capacity_rule, doc='Machine capacity (hours per month)')

def demand_rule(model, g):
    return sum(model.outp[g, m] for m in model.m) == model.dempr_demand[g]
model.dem = Constraint(model.g, rule=demand_rule, doc='Demand (tons per month)')

def profit_def_rule(model):
    return model.profit == sum(model.dempr_demand[g] * model.dempr_price[g] for g in model.g) \
           - sum(model.pcost[g, m] * model.outp[g, m] for g in model.g for m in model.m)
model.pdef = Constraint(rule=profit_def_rule, doc='Profit definition ($ per month)')
