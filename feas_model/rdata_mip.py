# converted from models/rdata_mip.py
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
model.plant = Set(initialize=data['plant'], doc='plants')
model.commodity = Set(initialize=data['commodity'], doc='commodities')
model.process = Set(initialize=data['process'], doc='processes')
model.unit = Set(initialize=data['unit'], doc='units')
model.union = Set(initialize=data['union'], doc='unions')
model.rawmat = Set(initialize=data['rawmat'], doc='raw materials')

# PARAM_BLOCK
model.demand = Param(model.commodity, initialize=data['demand'], mutable=True, default=0,
                     doc='demand in millions of units')
model.a = Param(model.commodity, model.process, initialize=data['a'], mutable=True, default=0,
                doc='input-output matrix')
model.b = Param(model.unit, model.process, initialize=data['b'], mutable=True, default=0,
                doc='capacity utilization matrix')
model.k80 = Param(model.unit, model.plant, initialize=data['k80'], mutable=True, default=0,
                  doc='capacity in 1980 (millions of units)')
model.emp = Param(model.plant, model.union, initialize=data['emp'], mutable=True, default=0,
                  doc='employment (thousands)')

# Computed parameter: ur(process,plant,union) - union relationship to plant processes
ur = {}
for proc in data['process']:
    for plant in data['plant']:
        for union in data['union']:
            val = 0
            for unit in data['unit']:
                k80_val = data['k80'].get((unit, plant), 0)
                b_val = data['b'].get((unit, proc), 0)
                emp_val = data['emp'].get((plant, union), 0)
                if k80_val > 0:
                    val += emp_val * b_val
            if val != 0:
                ur[(proc, plant, union)] = val

# Computed parameter: mu(union) - maximum
mu = {}
for union in data['union']:
    mu[union] = sum(ur.get((proc, plant, union), 0) for proc in data['process'] for plant in data['plant'])

model.ur = Param(model.process, model.plant, model.union, initialize=ur, mutable=True, default=0,
                 doc='union relationship to plant processes')
model.mu = Param(model.union, initialize=mu, mutable=True, default=0, doc='maximum')

# VAR_BLOCK
model.nunion = Var(domain=NonNegativeReals, doc='number of unions')
model.z = Var(model.process, model.plant, domain=NonNegativeReals, doc='process level (million units)')
model.up = Var(model.union, domain=Binary, doc='union participation')
model.u = Var(model.commodity, domain=NonNegativeReals, doc='purchase of raw materials (million units)')

# OBJ_BLOCK
model.obj = Objective(expr=model.nunion, sense=minimize, doc='minimize number of unions')

# CONS_BLOCK
def mb_rule(model, commodity):
    """Material balance constraint (million units)"""
    return sum(model.a[commodity, proc] * model.z[proc, plant] 
               for proc in model.process for plant in model.plant) + \
           (model.u[commodity] if commodity in data['rawmat'] else 0) == \
           model.demand[commodity]
model.mb = Constraint(model.commodity, rule=mb_rule, doc='material balance (million units)')

def cc_rule(model, unit, plant):
    """Capacity constraint (million units)"""
    return sum(model.b[unit, proc] * model.z[proc, plant] for proc in model.process) <= model.k80[unit, plant]
model.cc = Constraint(model.unit, model.plant, rule=cc_rule, doc='capacity constraint (million units)')

def ub_rule(model, union):
    """Union balance constraint"""
    if value(model.mu[union]) > 0:
        return sum(model.ur[proc, plant, union] * model.z[proc, plant] 
                   for proc in model.process for plant in model.plant) <= model.mu[union] * model.up[union]
    return Constraint.Skip
model.ub = Constraint(model.union, rule=ub_rule, doc='union balance')

def ud_rule(model):
    """Union definition constraint"""
    return model.nunion == sum(model.up[union] for union in model.union)
model.ud = Constraint(rule=ud_rule, doc='union definition')
