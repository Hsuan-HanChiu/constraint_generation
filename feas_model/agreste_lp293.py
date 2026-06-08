# converted from models/agreste_lp293.py
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
model.c = Set(initialize=data['c'], doc='crops')
model.p = Set(initialize=data['p'], doc='cropping activities')
model.s = Set(initialize=data['s'], doc='land types')
model.tm = Set(initialize=data['tm'], doc='months')
model.sc = Set(within=model.s, initialize=data['sc'], doc='crop lands')
model.r = Set(initialize=data['r'], doc='livestock feeding alternatives')
model.ty = Set(initialize=data['ty'], doc='year')
model.dr = Set(initialize=data['dr'], doc='family consumption bundle alternatives')
model.km = Set(initialize=data['km'], doc='technology characteristics')

# PARAM_BLOCK - Basic parameters first
model.landc = Param(model.s, initialize=data['landc'], mutable = True, doc='land data (ha)')
model.rations = Param(model.r, initialize=data['rations'], mutable = True, doc='livestock rations feeding alternative (cr per head)')
model.xcropl = Param(model.p, model.s, initialize=data.get('xcropl', {}), default=0, mutable = True, doc='limits on cropping activities')
model.ldp = Param(model.s, model.s, initialize=data['ldp'], default=0,mutable = True, doc='land downgrading possibilities')
model.lio = Param(model.s, model.r, initialize=data['lio'], default=0, mutable = True, doc='land requirements for livestock feed alternatives (ha per head)')
model.labor = Param(model.p, model.tm, initialize=data['labor'], default=0, mutable = True, doc='labor requirements for cropping (man-days per ha)')
model.llab = Param(model.tm, model.r, initialize=data['llab'], default=0, mutable = True, doc='labor requirement for livestock feed (man-days per head)')
model.cbndl = Param(model.c, model.dr, initialize=data['cbndl'], default=0, mutable = True, doc='consumption bundles (tons per bundle)')
model.crev = Param(model.c, model.ty, initialize=data['crev'], default=0, mutable = True, doc='crop revenue time series (cr per ha)')
model.price = Param(model.c, initialize=data['price'], mutable = True, doc='crop reference prices (cr per kg)')

# Scalar parameters
model.fwage = Param(initialize=data['fwage'], doc='family reservation wage rate (cr per man-month)')
model.twage = Param(initialize=data['twage'], doc='temporary labor wage rate (cr per man-month)')
model.pwage = Param(initialize=data['pwage'], doc='permanent labor wage rate (cr per man-year)')
model.vsc = Param(initialize=data['vsc'], doc='value of self-consumption (cr per bundle)')
model.wcbar = Param(initialize=data['wcbar'], doc='working capital (cr)')
model.famlab = Param(initialize=data['famlab'], doc='family labor (man equivalent wrks)')
model.lprice = Param(initialize=data['lprice'], doc='livestock price (cr per head)')
model.vetpr = Param(initialize=data['vetpr'], doc='cost of veterinary service (cr per head)')
model.dpm = Param(initialize=data['dpm'], doc='man-days per man month')
model.phi = Param(initialize=data['phi'], doc='risk factor')

# Yield and technology parameters
model.yield_param = Param(model.p, model.c, model.s, initialize=data['yield'], default=0, doc='crop yields (kg per ha)')
model.techc = Param(model.p, model.km, initialize=data['techc'], default=0, doc='cropping technology requirements (cr per ha)')

# Derived parameters (following GAMS calculation order)
# ps(p,s) = yes$sum(c, yield(p,c,s))
def ps_init():
    ps_set = []
    for p in model.p:
        for s in model.s:
            if sum(data['yield'].get((p,c,s), 0) for c in model.c) > 0:
                ps_set.append((p,s))
    return ps_set

model.ps = Set(within=model.p*model.s, initialize=ps_init(), doc='process-land possibilities')

# ravg(c) = sum(ty, crev(c,ty))/card(ty)
def ravg_init(model, c):
    return sum(model.crev[c,ty] for ty in model.ty) / len(model.ty)

model.ravg = Param(model.c, initialize=ravg_init, doc='average crop revenues (cr per ha)')

# prdev(c,ty)$ravg(c) = 1000*price(c)*(crev(c,ty)/ravg(c) - 1)
def prdev_init(model, c, ty):
    ravg_val = value(model.ravg[c])
    if ravg_val > 0:
        return 1000 * model.price[c] * (model.crev[c,ty] / ravg_val - 1)
    else:
        return 0

model.prdev = Param(model.c, model.ty, initialize=prdev_init, doc='price deviations for crops (cr per ton)')

# pcost(p) = sum(km, techc(p,km))
def pcost_init(model, p):
    return sum(model.techc[p,km] for km in model.km)

model.pcost = Param(model.p, initialize=pcost_init, doc='cropping technology costs (cr per ha)')

# a(p) = 1; a(p)$sum(s, yield(p,"cotton-h",s)) = 0;
def a_init(model, p):
    cotton_yield_sum = sum(model.yield_param[p,'cotton-h',s] for s in model.s)
    if cotton_yield_sum > 0:
        return 0
    else:
        return 1

model.a = Param(model.p, initialize=a_init, doc='cropping constants')

# VAR_BLOCK
model.xcrop = Var(model.p, model.s, within=NonNegativeReals, doc='cropping activities (ha)')
model.xliver = Var(model.r, within=NonNegativeReals, doc='livestock activity defined on feed techniques (head)')
model.xlive = Var(within=NonNegativeReals, doc='livestock production (head)')
model.lswitch = Var(model.s, within=NonNegativeReals, doc='land downgrading (ha)')
model.xprod = Var(model.c, within=NonNegativeReals, doc='crop production (ton)')
model.cons = Var(model.dr, within=NonNegativeReals, doc='on-farm consumption (ton)')
model.sales = Var(model.c, within=NonNegativeReals, doc='crop sales (ton)')
model.flab = Var(model.tm, within=NonNegativeReals, doc='family labor (man-days)')
model.tlab = Var(model.tm, within=NonNegativeReals, doc='temporary labor (man-days)')
model.plab = Var(within=NonNegativeReals, doc='permanent labor (workers)')
model.rationr = Var(within=NonNegativeReals, doc='livestock ration requirements (cr)')
model.pdev = Var(model.ty, within=NonNegativeReals, doc='positive price deviations (cr)')
model.ndev = Var(model.ty, within=NonNegativeReals, doc='negative price deviations (cr)')
model.yfarm = Var(doc='farm income (cr)')
model.revenue = Var(within=NonNegativeReals, doc='from crop and livestock sales (cr)')
model.cropcost = Var(within=NonNegativeReals, doc='accounting: cropping activities cost (cr)')
model.labcost = Var(within=NonNegativeReals, doc='accounting: labor costs - including family (cr)')
model.vetcost = Var(within=NonNegativeReals, doc='accounting: veterinary services cost (cr)')

# CONSTRAINT BLOCK
# landb(s).. sum(p$ps(p,s), a(p)*xcrop(p,s))$sc(s) + sum(sp, ldp(s,sp)*lswitch(sp)) + sum(r, lio(s,r)*xliver(r)) =l= landc(s)
def landb_rule(model, s):
    crop_term = 0
    if s in model.sc:  # $sc(s) condition
        crop_term = sum(model.a[p] * model.xcrop[p,s] for p in model.p if (p,s) in model.ps)

    downgrade_term = sum(model.ldp[s,sp] * model.lswitch[sp] for sp in model.s)
    livestock_term = sum(model.lio[s,r] * model.xliver[r] for r in model.r)

    return crop_term + downgrade_term + livestock_term <= model.landc[s]

model.landb = Constraint(model.s, rule=landb_rule, doc='land balance')

# lbal.. xlive =e= sum(r, xliver(r))
model.lbal = Constraint(expr=model.xlive == sum(model.xliver[r] for r in model.r), doc='livestock balance')

# rliv.. rationr =e= sum(r, rations(r)*xliver(r))
model.rliv = Constraint(expr=model.rationr == sum(model.rations[r] * model.xliver[r] for r in model.r), doc='livestock ration requirements definition')

# mbalc(c).. sum((s,p), yield(p,c,s)*xcrop(p,s))/1000 =g= sales(c) + sum(dr, cbndl(c,dr)*cons(dr))
def mbalc_rule(model, c):
    production = sum(model.yield_param[p,c,s] * model.xcrop[p,s] for p in model.p for s in model.s) / 1000
    consumption = model.sales[c] + sum(model.cbndl[c,dr] * model.cons[dr] for dr in model.dr)
    return production >= consumption

model.mbalc = Constraint(model.c, rule=mbalc_rule, doc='material balance: crops')

# dprod(c).. xprod(c) =e= sum((p,s), yield(p,c,s)*xcrop(p,s))/1000
def dprod_rule(model, c):
    return model.xprod[c] == sum(model.yield_param[p,c,s] * model.xcrop[p,s] for p in model.p for s in model.s) / 1000

model.dprod = Constraint(model.c, rule=dprod_rule, doc='crop production definition')

# labc(tm).. sum((p,s)$ps(p,s), labor(p,tm)*xcrop(p,s)) + sum(r, llab(tm,r)*xliver(r)) =l= flab(tm) + tlab(tm) + dpm*plab
def labc_rule(model, tm):
    crop_labor = sum(model.labor[p,tm] * model.xcrop[p,s] for (p,s) in model.ps)
    livestock_labor = sum(model.llab[tm,r] * model.xliver[r] for r in model.r)
    available_labor = model.flab[tm] + model.tlab[tm] + model.dpm * model.plab
    return crop_labor + livestock_labor <= available_labor

model.labc = Constraint(model.tm, rule=labc_rule, doc='labor supply-demand relation')

# cond.. sum(dr, cons(dr)) =e= 1
model.cond = Constraint(expr=sum(model.cons[dr] for dr in model.dr) == 1, doc='on farm consumption definition')

# ddev(ty).. sum(c, prdev(c,ty)*sales(c)) =e= pdev(ty) - ndev(ty)
def ddev_rule(model, ty):
    return sum(model.prdev[c,ty] * model.sales[c] for c in model.c) == model.pdev[ty] - model.ndev[ty]

model.ddev = Constraint(model.ty, rule=ddev_rule, doc='crop price deviation definition')

# arev.. revenue =e= lprice*xlive + 1000*sum(c, price(c)*sales(c))
model.arev = Constraint(expr=model.revenue == model.lprice * model.xlive + 1000 * sum(model.price[c] * model.sales[c] for c in model.c), doc='accounting: revenue definition')

# acrop.. cropcost =e= sum((p,s)$ps(p,s), pcost(p)*xcrop(p,s))
model.acrop = Constraint(expr=model.cropcost == sum(model.pcost[p] * model.xcrop[p,s] for (p,s) in model.ps), doc='accounting: cropping cost definition')

# alab.. labcost =e= (fwage*sum(tm, flab(tm)) + twage*sum(tm, tlab(tm)))/dpm + pwage*plab
model.alab = Constraint(expr=model.labcost == (model.fwage * sum(model.flab[tm] for tm in model.tm) + model.twage * sum(model.tlab[tm] for tm in model.tm)) / model.dpm + model.pwage * model.plab, doc='accounting: labor cost definition')

# awcc.. cropcost + rationr + vetcost + twage/dpm*sum(tm, tlab(tm)) + pwage*plab =l= wcbar
model.awcc = Constraint(expr=model.cropcost + model.rationr + model.vetcost + model.twage/model.dpm * sum(model.tlab[tm] for tm in model.tm) + model.pwage * model.plab <= model.wcbar, doc='accounting: working capital requirements')

# avet.. vetcost =e= vetpr*xlive
model.avet = Constraint(expr=model.vetcost == model.vetpr * model.xlive, doc='accounting: veterinary costs')

# income.. yfarm =e= revenue + vsc*sum(dr, cons(dr)) - labcost - rationr - vetcost - cropcost - phi*sum(ty, pdev(ty) + ndev(ty))/card(ty)
model.income = Constraint(expr=model.yfarm == model.revenue + model.vsc * sum(model.cons[dr] for dr in model.dr) - model.labcost - model.rationr - model.vetcost - model.cropcost - model.phi * sum(model.pdev[ty] + model.ndev[ty] for ty in model.ty) / len(model.ty), doc='farm income definition')

# Variable bounds (matching GAMS exactly)
# xcrop.up(p,s)$xcropl(p,s) = xcropl(p,s)
def set_xcrop_bounds():
    for p in model.p:
        for s in model.s:
            if (p,s) in data.get('xcropl', {}) and data['xcropl'][(p,s)] > 0:
                model.xcrop[p,s].setub(data['xcropl'][(p,s)])

# flab.up(tm) = famlab
def set_flab_bounds():
    for tm in model.tm:
        model.flab[tm].setub(model.famlab.value)

# OBJ_BLOCK
model.obj = Objective(expr=model.yfarm, sense=maximize, doc='maximize farm income')

# Set bounds after model construction
set_xcrop_bounds()
set_flab_bounds()
