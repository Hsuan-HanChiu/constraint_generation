# converted from models/fawley_lp.py
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
model.cr = Set(initialize=data['cr'], doc='crude oils')
model.ci = Set(initialize=data['ci'], doc='components imported')
model.cf = Set(initialize=data['cf'], doc='final products')
model.cfq = Set(initialize=data['cfq'], doc='final products quality blended')
model.cfr = Set(initialize=data['cfr'], doc='final products recipe blended')
model.k = Set(initialize=data['k'], doc='productive units')
model.p = Set(initialize=data['p'], doc='processes')
model.kuse = Set(initialize=data['kuse'], doc='unit-process pairs for capacity use')
model.bposs = Set(initialize=data['bposs'], doc='blending possibilities for quality blends')
model.s = Set(initialize=data['s'], doc='product specifications')
model.m = Set(initialize=data['m'], doc='product measures')
model.ms = Set(initialize=data['ms'], doc='measure-specification pairs')
model.cfm = Set(initialize=data['cfm'], doc='required measure pairs')
model.l = Set(initialize=data['l'], doc='quality limits')
model.r = Set(initialize=data['r'], doc='recipes')
model.tr = Set(initialize=data['tr'], doc='transfer options')

# PARAM_BLOCK
model.m3tob = Param(initialize=data['m3tob'], mutable=True, doc='barrels per m3')
model.pbmg = Param(initialize=data['pbmg'], mutable=True, doc='lead content in motor gas (grams per liter)')
model.ppb = Param(initialize=data['ppb'], mutable=True, doc='lead price ($ per kg)')
model.ocpb = Param(initialize=data['ocpb'], mutable=True, doc='lead cost ($ per m3 of gasoline)')

model.crdat = Param(model.cr, Any, initialize=data['crdat'], mutable=True, default=0, doc='crude oil information')
model.ddat = Param(model.cf, Any, initialize=data['ddat'], mutable=True, default=0, doc='demand data')
model.kdat = Param(model.k, Any, initialize=data['kdat'], mutable=True, default=0, doc='capacity data')
model.ap = Param(model.c, model.p, initialize=data['ap'], mutable=True, default=0, doc='process yields')
model.recipes = Param(model.cf, model.c, model.r, initialize=data['recipes'], mutable=True, default=0, doc='blending recipes')
model.at = Param(model.c, model.tr, initialize=data['at'], mutable=True, default=0, doc='transfer processes')
model.specs = Param(model.cf, model.l, model.s, initialize=data['specs'], mutable=True, default=0, doc='product specifications')
model.prop = Param(model.c, Any, initialize=data['prop'], mutable=True, default=0, doc='properties')
model.char = Param(model.c, model.m, initialize=data['char'], mutable=True, default=0, doc='conversion for product balance')
model.bp = Param(model.k, model.p, initialize=data['bp'], mutable=True, default=0, doc='capacity utilization (m3 per ton)')
model.kp = Param(model.k, initialize=data['kp'], mutable=True, doc='capacity (1000 m3)')
model.oc = Param(model.k, initialize=data['oc'], mutable=True, doc='operating costs ($ per m3)')
model.pcr = Param(model.cr, initialize=data['pcr'], mutable=True, doc='plantgate crude price ($ per ton)')
model.pimp = Param(model.c, initialize=data['pimp'], mutable=True, default=0, doc='price of imported components ($ per ton)')
model.invent = Param(model.c, initialize=data['invent'], mutable=True, default=0, doc='inventory change (1000 tons)')
model.dir = Param(model.l, initialize=data['dir'], mutable=True, doc='sign of over-under specs')

# VAR_BLOCK
model.u = Var(model.c, domain=NonNegativeReals, doc='crude purchase (1000 tons)')
model.z = Var(model.p, domain=NonNegativeReals, doc='production levels (1000 tons)')
model.cap = Var(model.k, domain=NonNegativeReals, doc='capacity use (1000 m3)')
model.trans = Var(model.tr, domain=NonNegativeReals, doc='transfer activities (1000 tons)')
model.import_var = Var(model.c, domain=NonNegativeReals, doc='import of components (1000 tons)')
model.bq = Var(model.c, model.cf, domain=NonNegativeReals, doc='quality blending activity (1000 tons)')
model.rb = Var(model.cf, model.r, domain=NonNegativeReals, doc='recipe blending activity (1000 tons)')
model.q = Var(model.cf, model.m, domain=NonNegativeReals, doc='final product measure (1000 tons or m3)')
model.ov = Var(model.cf, model.l, model.s, domain=NonNegativeReals, doc='over or under blending (1000 units)')
model.sales = Var(model.cf, domain=NonNegativeReals, doc='final product sales (1000 tons)')
model.revenue = Var(domain=Reals, doc='final product revenue (1000 $)')
model.recurrent = Var(domain=Reals, doc='operating cost (1000 $)')
model.purchase = Var(domain=Reals, doc='external product purchase (1000 $)')
model.transport = Var(domain=Reals, doc='transport cost (1000 $)')
model.profit = Var(domain=Reals, doc='operating profit (1000 $)')

# CONS_BLOCK
def material_balance_rule(model, c):
    """Component balance (1000 tons)"""
    return (
        (model.u[c] if c in model.cr else 0)
        + sum(model.ap[c, p] * model.z[p] for p in model.p)
        + sum(model.at[c, t] * model.trans[t] for t in model.tr)
        + (model.import_var[c] if c in model.ci else 0)
        == sum(model.bq[c, cfq] for cfq in model.cfq if (cfq, c) in model.bposs)
        + model.invent[c]
        + sum(model.recipes[cfr, c, rr] * model.rb[cfr, rr] for cfr in model.cfr for rr in model.r)
    )
model.mbal = Constraint(model.c, rule=material_balance_rule, doc='component balance (1000 tons)')

def capacity_balance_rule(model, k):
    """Capacity constraints (1000 m3)"""
    return model.cap[k] == sum(model.bp[k, p] * model.z[p] for p in model.p)
model.kbal = Constraint(model.k, rule=capacity_balance_rule, doc='capacity constraints (1000 m3)')

def demand_balance_rule(model, cf):
    """Demand balance (1000 tons)"""
    if cf in model.cfq:
        return model.sales[cf] == model.q[cf, 'weight']
    else:
        return model.sales[cf] == sum(model.recipes[cf, c, rr] * model.rb[cf, rr] for c in model.c for rr in model.r)
model.dbal = Constraint(model.cf, rule=demand_balance_rule, doc='demand balance (1000 tons)')

def quality_spec_rule(model, cfq, l, s_spec):
    """Quality constraint (1000 units)"""
    if value(model.specs[cfq, l, s_spec]) == 0:
        return Constraint.Skip
    lhs = sum(
        model.prop[c, s_spec] * sum(model.char[c, mm] * model.bq[c, cfq] for mm in model.m if (mm, s_spec) in model.ms)
        for c in model.c if (cfq, c) in model.bposs
    )
    rhs = sum(model.specs[cfq, l, s_spec] * model.q[cfq, mm] for mm in model.m if (mm, s_spec) in model.ms)
    return lhs + model.dir[l] * model.ov[cfq, l, s_spec] == rhs
model.qsb = Constraint(model.cfq, model.l, model.s, rule=quality_spec_rule, doc='quality constraint (1000 units)')

def product_balance_rule(model, cfq, mm):
    """Product balance (1000 units)"""
    if (cfq, mm) not in model.cfm:
        return Constraint.Skip
    return model.q[cfq, mm] == sum(model.char[c, mm] * model.bq[c, cfq] for c in model.c if (cfq, c) in model.bposs)
model.pbal = Constraint(model.cfq, model.m, rule=product_balance_rule, doc='product balance (1000 units)')

def revenue_def_rule(model):
    """Revenue definition (1000 $)"""
    return model.revenue == sum(model.ddat[cf, 'price'] * model.sales[cf] for cf in model.cf)
model.drev = Constraint(rule=revenue_def_rule, doc='revenue definition (1000 $)')

def operating_cost_rule(model):
    """Recurrent cost definition (1000 $)"""
    return model.recurrent == sum(model.oc[k] * model.cap[k] for k in model.k) + model.ocpb * model.q['motor-gas', 'volume']
model.doper = Constraint(rule=operating_cost_rule, doc='recurrent cost definition (1000 $)')

def purchase_cost_rule(model):
    """Purchase cost definition (1000 $)"""
    return model.purchase == sum(model.pcr[cr] * model.u[cr] for cr in model.cr) + sum(model.pimp[ci] * model.import_var[ci] for ci in model.ci)
model.dpur = Constraint(rule=purchase_cost_rule, doc='purchase cost definition (1000 $)')

def transport_cost_rule(model):
    """Transport cost definition (1000 $)"""
    return model.transport == sum(model.crdat[cr, 'transport'] * model.u[cr] for cr in model.cr)
model.dtran = Constraint(rule=transport_cost_rule, doc='transport cost definition (1000 $)')

def profit_def_rule(model):
    """Profit definition (1000 $)"""
    return model.profit == model.revenue - model.recurrent - model.purchase - model.transport
model.dprof = Constraint(rule=profit_def_rule, doc='profit definition (1000 $)')

# Bounds
for cr in model.cr:
    model.u[cr].setub(data['crdat'].get((cr, 'supply'), 0))
for cf in model.cf:
    model.sales[cf].fix(data['ddat'].get((cf, 'demand'), 0))
for k in model.k:
    model.cap[k].setub(data['kp'].get(k, 0))

# OBJ_BLOCK
model.obj = Objective(expr=model.profit, sense=maximize)
