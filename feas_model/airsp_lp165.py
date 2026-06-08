# converted from models/airsp_lp165.py
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
model.i = Set(initialize=data['i'])
model.j = Set(initialize=data['j'])
model.h = Set(initialize=data['h'])
model.ss = Set(initialize=data['ss'])
model.ij = Set(dimen=2, initialize=data['ij'])
model.jh = Set(dimen=2, initialize=data['jh'])

# PARAM_BLOCK
model.dd = Param(model.j, model.h, initialize=data['dd'], mutable = True, doc='demand distribution on route j')
model.lambda_ = Param(model.j, model.h, initialize=data['lambda'], mutable = True, doc='probability of demand state h on route j')
model.c = Param(model.i, model.j, initialize=data['c'], mutable = True, doc='costs per aircraft (1000s)')
model.p = Param(model.i, model.j, initialize=data['p'], mutable = True, doc='passenger capacity of aircraft i on route j')
model.aa = Param(model.i, initialize=data['aa'], mutable = True, doc='aircraft availability')
model.k = Param(model.j, initialize=data['k'], mutable = True, doc='revenue lost (1000 per 100 bumped)')

# VAR_BLOCK
model.x = Var(model.i, model.j, within=NonNegativeReals, doc='number of aircraft type i assigned to route j')
model.z = Var(model.j, within=NonNegativeReals, doc='allocated capacity')
model.bh = Var(model.j, model.h, within=NonNegativeReals, doc='passengers bumped')
model.phi = Var(within=NonNegativeReals, doc='total expected costs')
model.oc = Var(within=NonNegativeReals, doc='operating cost')

# OBJ_BLOCK
def obj_rule(model):
    return model.phi
model.obj = Objective(rule=obj_rule, sense=minimize)

# CONS_BLOCK
def ab_rule(model, i):
    return sum(model.x[i, j] for j in model.j if (i, j) in model.ij) <= model.aa[i]
model.ab = Constraint(model.i, rule=ab_rule, doc='aircraft balance')

def cb_rule(model, j):
    return model.z[j] == sum(model.p[i, j] * model.x[i, j] for i in model.i if (i, j) in model.ij)
model.cb = Constraint(model.j, rule=cb_rule, doc='capacity balance')

def dbh_rule(model, j, h):
    return model.dd[j, h] - model.bh[j, h] <= model.z[j]
model.dbh = Constraint(model.j, model.h, rule=dbh_rule, doc='demand balance')

def ocd_rule(model):
    return model.oc == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j if (i, j) in model.ij)
model.ocd = Constraint(rule=ocd_rule, doc='operating cost definition')

def objh_rule(model):
    return model.phi == model.oc + sum(model.k[j] * sum(model.lambda_[j, h] * model.bh[j, h] for h in model.h) for j in model.j)
model.objh = Constraint(rule=objh_rule, doc='objective function')
