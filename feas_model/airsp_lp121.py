# converted from models/airsp_lp121.py
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
model.i = Set(initialize=data['i'])  # aircraft types and unassigned passengers
model.j = Set(initialize=data['j'])  # assigned and unassigned routes
model.h = Set(initialize=data['h'])  # demand states
model.ss = Set(initialize=data['ss'])  # nodes
model.ij = Set(within=model.i * model.j, initialize=data['ij'])  # possible assignments
model.jh = Set(within=model.j * model.h, initialize=data['jh'])  # possible demand states

# PARAM_BLOCK
model.dd = Param(model.j, model.h, initialize=data['dd'] , mutable = True, doc='demand distribution on route j')
model.lambda_ = Param(model.j, model.h, initialize=data['lambda'], mutable = True, doc='probability of demand state h on route j')
model.c = Param(model.i, model.j, initialize=data['c'], mutable = True, doc='costs per aircraft (1000s)')
model.p = Param(model.i, model.j, initialize=data['p'], mutable = True, doc='passenger capacity of aircraft i on route j')
model.aa = Param(model.i, initialize=data['aa'], mutable = True, doc='aircraft availability')
model.k = Param(model.j, initialize=data['k'], mutable = True, doc='revenue lost (1000 per 100  bumped)')

# VAR_BLOCK
model.x = Var(model.i, model.j, domain=NonNegativeReals, doc='number of aircraft type i assigned to route j')
model.z = Var(model.j, domain=NonNegativeReals, doc='allocated capacity')
model.bh = Var(model.j, model.h, domain=NonNegativeReals, doc='passengers bumped')
model.phi = Var(domain=NonNegativeReals, doc='total expected costs')
model.oc = Var(domain=NonNegativeReals, doc='operating cost')

# OBJ_BLOCK
model.obj = Objective(
    expr=model.oc + sum(model.k[j] * sum(model.lambda_[j, h] * model.bh[j, h] for h in model.h) for j in model.j),
    sense=minimize
)

# CONS_BLOCK
def aircraft_balance_rule(model, i):
    return sum(model.x[i, j] for j in model.j if (i, j) in model.ij) <= model.aa[i]
model.ab = Constraint(model.i, rule=aircraft_balance_rule, doc='aircraft balance')

def capacity_balance_rule(model, j):
    return model.z[j] == sum(model.p[i, j] * model.x[i, j] for i in model.i if (i, j) in model.ij)
model.cb = Constraint(model.j, rule=capacity_balance_rule, doc='capacity balance')

def demand_balance_rule(model, j, h):
    return model.dd[j, h] - model.bh[j, h] <= model.z[j]
model.dbh = Constraint(model.j, model.h, rule=demand_balance_rule, doc='demand balance')

def operating_cost_definition_rule(model):
    return model.oc == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j if (i, j) in model.ij)
model.ocd = Constraint(rule=operating_cost_definition_rule, doc='operating cost definition')
