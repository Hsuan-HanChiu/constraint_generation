# converted from models/tforss_lp.py
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

model.c = Set(initialize=data['c'], doc='commodities')
model.cf = Set(initialize=data['cf'], doc='final products')
model.cl = Set(initialize=data['cl'], doc='log types')
model.s = Set(initialize=data['s'], doc='species')
model.k = Set(initialize=data['k'], doc='site classes')
model.at = Set(initialize=data['at'], doc='tree age')
model.p = Set(initialize=data['p'], doc='processes')
model.m = Set(initialize=data['m'], doc='productive units')

# PARAM_BLOCK

model.scd = Param(model.k, initialize=data['scd'], mutable=True, doc='site class distribution')
model.land = Param(model.s, initialize=data['land'], mutable=True, doc='land available (1000ha)')
model.ymf = Param(model.at, model.k, model.s, model.cl, initialize=data['ymf'], doc='yield of managed forest (m3/ha)')
model.a = Param(model.c, model.p, initialize=data['a'], doc='input output matrix')
model.b = Param(model.m, model.p, initialize=data['b'], doc='capacity utilization')
model.pc = Param(model.p, initialize=data['pc'], doc='process cost (us$ per m3 input)')
model.pd = Param(model.cf, initialize=data['pd'], doc='sales price (us$ per unit)')
model.nu = Param(model.m, initialize=data['nu'], doc='investment costs (us$ per m3 input)')

at_positions = {at: i+1 for i, at in enumerate(model.at)}  # GAMS ord() starts at 1
model.age = Param(model.at, initialize=lambda m, at: 10 * at_positions[at], doc='Age of trees (years)')

model.mup = Param(initialize=data['mup'], doc='planting cost (us$ per ha)')
model.muc = Param(initialize=data['muc'], doc='cutting cost (us$ per m3)')
model.life = Param(initialize=data['life'], doc='plant life (years)')
model.rho = Param(initialize=data['rho'], doc='discount rate')


# VAR_BLOCK

# Multi-indexed variables
model.v = Var(model.s, model.k, model.at, domain=NonNegativeReals, doc='Management of new forest (1000 ha per year)')
model.r = Var(model.c, domain=NonNegativeReals, doc='Supply of logs to industry (1000 m3 per year)')
model.z = Var(model.p, domain=NonNegativeReals, doc='Process level (1000 m3 input per year)')
model.h = Var(model.m, domain=NonNegativeReals, doc='Capacity (1000 m3 input per year)')
model.x = Var(model.c, domain=NonNegativeReals, doc='Final shipments (1000 units per year)')

# Scalar variables
model.phik = Var(domain=NonNegativeReals, doc='Investment cost (1000 US$ per year)')
model.phir = Var(domain=NonNegativeReals, doc='Process cost (1000 US$ per year)')
model.phix = Var(domain=NonNegativeReals, doc='Sales revenue (1000 US$ per year)')
model.phil = Var(domain=NonNegativeReals, doc='Cutting cost (1000 US$ per year)')
model.phip = Var(domain=NonNegativeReals, doc='Planting cost (1000 US$ per year)')
model.phi = Var(domain=NonNegativeReals, doc='Total benefits (discounted cost)')

# OBJ_BLOCK

model.obj = Objective(expr=model.phi, sense=maximize)

# CONS_BLOCK

def lbal_rule(model, cl):
      return model.r[cl] == sum(model.ymf[at, k, s, cl] * model.v[s, k, at] for s in model.s for k in model.k for at in model.at)

model.lbal = Constraint(model.cl, rule=lbal_rule)

def bal_rule(model, c):
      lh = sum(model.a[c, p] * model.z[p] for p in model.p)
      if c in data['cl']:
            lh += model.r[c]
      rhs = model.x[c] if c in data['cf'] else 0
      return lh >= rhs

model.bal = Constraint(model.c, rule=bal_rule)

def cap_rule(model, m):
      return sum(model.b[m, p] * model.z[p] for p in model.p) == model.h[m]

model.cap = Constraint(model.m, rule=cap_rule)

def landc_rule(model, s, k):
      lhs = sum(model.v[s, k, at] * model.age[at] for at in model.at)
      rhs = model.land[s] * model.scd[k]
      return lhs <= rhs

model.landc = Constraint(model.s, model.k, rule=landc_rule)

def ainvc_rule(model):
      rhs = model.rho / (1 - (1 + model.rho)**(-model.life))*sum(model.nu[m]*model.h[m] for m in model.m)
      return model.phik == rhs

model.ainvc = Constraint(rule=ainvc_rule)

def aproc_rule(model):
      rhs = sum(model.pc[p] * model.z[p] for p in model.p)
      return model.phir == rhs

model.aproc = Constraint(rule=aproc_rule)

def asales_rule(model):
      rhs = sum(model.pd[cf] * model.x[cf] for cf in model.cf)
      return model.phix == rhs

model.asales = Constraint(rule=asales_rule)

def acutc_rule(model):
      rhs = model.muc * sum(model.r[cl] for cl in model.cl)
      return model.phil == rhs

model.acutc = Constraint(rule=acutc_rule)

def aplnt_rule(model):
      rhs = model.mup * sum(model.v[s,k,at] * (1+model.rho)**model.age[at] for s in model.s for k in model.k for at in model.at)
      return model.phip == rhs

model.aplnt = Constraint(rule=aplnt_rule)

def benefit_rule(model):
      rhs = model.phix - model.phik - model.phir - model.phil - model.phip
      return model.phi == rhs

model.benefit = Constraint(rule=benefit_rule)
