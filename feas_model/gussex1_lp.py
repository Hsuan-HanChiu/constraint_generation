# converted from models/gussex1_lp.py
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
model.i = Set(initialize=data['i'], doc='canning plants')
model.j = Set(initialize=data['j'], doc='markets')

# SCALAR_PARAMS_BLOCK
model.f = Param(initialize=data['f'], mutable=True, 
                doc='freight in dollars per case per thousand miles')

# PARAM_BLOCK
model.a = Param(model.i, initialize=data['a'], mutable=True, 
                doc='capacity of plant i in cases')
model.b = Param(model.j, initialize=data['b'], mutable=True, 
                doc='demand at market j in cases')
model.d = Param(model.i, model.j, initialize=data['d'], mutable=True, default=0,
                doc='distance in thousands of miles')

# Computed parameter: transport cost in thousands of dollars per case
def c_init(model, i, j):
    return model.f * model.d[i, j] / 1000
model.c = Param(model.i, model.j, initialize=c_init, 
                doc='transport cost in thousands of dollars per case')

# VAR_BLOCK
model.x = Var(model.i, model.j, domain=NonNegativeReals, 
              doc='shipment quantities in cases')
model.z = Var(domain=Reals, 
              doc='total transportation costs in thousands of dollars')

# OBJ_BLOCK
model.obj = Objective(expr=model.z, sense=minimize, 
                      doc='minimize transportation cost')

# CONS_BLOCK
def cost_rule(model):
    """Define objective function"""
    return model.z == sum(model.c[i, j] * model.x[i, j] 
                          for i in model.i for j in model.j)
model.cost = Constraint(rule=cost_rule, doc='define objective function')

def supply_rule(model, i):
    """Observe supply limit at plant i"""
    return sum(model.x[i, j] for j in model.j) <= model.a[i]
model.supply = Constraint(model.i, rule=supply_rule, 
                          doc='observe supply limit at plant i')

def demand_rule(model, j):
    """Satisfy demand at market j"""
    return sum(model.x[i, j] for i in model.i) >= model.b[j]
model.demand = Constraint(model.j, rule=demand_rule, 
                          doc='satisfy demand at market j')
