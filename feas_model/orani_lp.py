# converted from models/orani_lp.py
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
model.ca = Set(initialize=data['ca'], doc='agricultural commodities')
model.cm = Set(initialize=data['cm'], doc='manufacturing commodities')
model.f = Set(initialize=data['f'], doc='factors')
model.h = Set(initialize=data['h'], doc='households')
model.i = Set(initialize=data['i'], doc='industries')
model.s = Set(initialize=data['s'], doc='sources')
model.ce = Set(initialize=data['ce'], dimen=2, doc='diagonal set for commodities')
# Aliases
model.cp = Set(initialize=data['cp'], doc='alias for c')
model.sp = Set(initialize=data['sp'], doc='alias for s')
model.ip = Set(initialize=data['ip'], doc='alias for i')

# SCALAR_PARAMS_BLOCK
model.theta = Param(initialize=data['theta'], mutable=True, 
                    doc='wage rate adjustment parameter')
model.elevel = Param(initialize=data['elevel'], mutable=True, 
                     doc='base period export level')
model.mlevel = Param(initialize=data['mlevel'], mutable=True, 
                     doc='base period import level')

# PARAM_BLOCK
model.amc = Param(model.c, model.s, Any, initialize=data['amc'], mutable=True, default=0,
                  doc='accounting matrix for commodities')
model.amf = Param(model.f, model.i, initialize=data['amf'], mutable=True, default=0,
                  doc='accounting matrix for factors')
model.amq = Param(model.c, model.i, initialize=data['amq'], mutable=True, default=0,
                  doc='accounting matrix for outputs')
model.epsilon = Param(model.c, model.s, initialize=data['epsilon'], mutable=True, default=0,
                      doc='income elasticities')
model.amt = Param(model.i, initialize=data['amt'], mutable=True,
                  doc='accounting matrix column totals')
model.gamma = Param(model.c, initialize=data['gamma'], mutable=True, default=0,
                    doc='export demand parameters')
model.wl = Param(model.i, initialize=data['wl'], mutable=True, 
                 doc='share of total employment')
model.alpha = Param(model.c, model.s, model.i, initialize=data['alpha'], mutable=True, default=0,
                    doc='share of expenditure by industry')
model.alphak = Param(model.i, initialize=data['alphak'], mutable=True,
                     doc='share of expenditure on capital')
model.alphal = Param(model.i, initialize=data['alphal'], mutable=True,
                     doc='share of expenditure on labor')
model.alphae = Param(model.c, model.s, initialize=data['alphae'], mutable=True, default=0,
                     doc='share of good cs in expenditure on commodity c')
model.etabar = Param(model.c, model.s, model.cp, model.sp, initialize=data['etabar'], 
                     mutable=True, default=0, doc='compensated price elasticities')
model.sb = Param(model.c, model.s, initialize=data['sb'], mutable=True, default=0,
                 doc='share of good cs in household budget')
model.eta = Param(model.c, model.s, model.cp, model.sp, initialize=data['eta'], 
                  mutable=True, default=0, doc='uncompensated price elasticities')
model.m = Param(model.c, model.i, initialize=data['m'], mutable=True, default=0,
                doc='industry market share')
model.mu = Param(model.c, model.s, initialize=data['mu'], mutable=True, default=0,
                 doc='weights for cpi')
model.nm = Param(model.c, initialize=data['nm'], mutable=True, default=0,
                 doc='share in total imports')
model.nx = Param(model.c, initialize=data['nx'], mutable=True, default=0,
                 doc='share in total exports')
model.r = Param(model.c, model.i, initialize=data['r'], mutable=True, default=0,
                doc='revenue share')
model.sc = Param(model.c, model.s, model.i, initialize=data['sc'], mutable=True, default=0,
                 doc='cost share')
model.sk = Param(model.i, initialize=data['sk'], mutable=True,
                 doc='cost share for capital')
model.sl = Param(model.i, initialize=data['sl'], mutable=True,
                 doc='cost share for labor')
model.wc = Param(model.c, model.s, initialize=data['wc'], mutable=True, default=0,
                 doc='share of consumption in demand')
model.we = Param(model.c, initialize=data['we'], mutable=True, default=0,
                 doc='share of exports in demand')
model.wi = Param(model.c, model.s, model.i, initialize=data['wi'], mutable=True, default=0,
                 doc='share of intermediates in demand')

# VAR_BLOCK - all variables are rates of change unless otherwise noted
model.b = Var(domain=Reals, doc='balance of trade')
model.cn = Var(model.c, model.s, domain=Reals, doc='consumption - nominal')
model.cr = Var(domain=Reals, doc='consumption - real')
model.df = Var(model.c, domain=Reals, doc='foreign demand shift')
model.e = Var(model.c, domain=Reals, doc='exports')
model.et = Var(domain=Reals, doc='total exports')
model.k = Var(model.i, domain=Reals, doc='capital demand')
model.kappa = Var(model.i, domain=Reals, doc='sectoral capital stocks')
model.l = Var(domain=Reals, doc='total employment')
model.li = Var(model.i, domain=Reals, doc='labor demand by industry')
model.mt = Var(domain=Reals, doc='total imports')
model.p = Var(model.c, model.s, domain=Reals, doc='prices for commodities in domestic currency')
model.pc = Var(domain=Reals, doc='consumer price index')
model.phi = Var(domain=Reals, doc='exchange rate')
model.pk = Var(model.i, domain=Reals, doc='price of capital')
model.px = Var(model.c, domain=Reals, doc='export price in foreign currency')
model.pm = Var(model.c, domain=Reals, doc='import price in foreign currency')
model.q = Var(model.c, model.i, domain=Reals, doc='output')
model.t = Var(model.c, domain=Reals, doc='import duty')
model.v = Var(model.c, domain=Reals, doc='export subsidy')
model.w = Var(domain=Reals, doc='wage rate')
model.ws = Var(domain=Reals, doc='wage shift')
model.x = Var(model.c, model.s, model.i, domain=Reals, doc='intermediate commodity demands')
model.ye = Var(domain=Reals, doc='household expenditure')
model.z = Var(model.i, domain=Reals, doc='industry activity level')

# FIXED VARIABLES (exogenous)
for c in model.c:
    model.df[c].fix(1)
for c in model.cm:
    model.e[c].fix(1)
for i in model.i:
    model.kappa[i].fix(3)
model.phi.fix(0)
for c in model.c:
    model.pm[c].fix(-2)
    model.t[c].fix(0)
for c in model.ca:
    model.v[c].fix(0)
model.ws.fix(0)
model.ye.fix(2)

# OBJ_BLOCK
model.obj = Objective(expr=model.pc, sense=minimize, doc='minimize consumer price index')

# CONS_BLOCK
# con(c,s): consumption
def con_rule(model, c, s):
    return model.cn[c, s] == (model.epsilon[c, s] * model.ye + 
            sum(model.eta[c, s, cp_idx, sp_idx] * model.p[cp_idx, sp_idx] 
                for cp_idx in model.cp for sp_idx in model.sp))
model.con = Constraint(model.c, model.s, rule=con_rule, doc='consumption equation')

# expd(c): export demands
def expd_rule(model, c):
    return model.px[c] == -model.gamma[c] * model.e[c] + model.df[c]
model.expd = Constraint(model.c, rule=expd_rule, doc='export demand equation')

# supply(c,i): supply relations
def supply_rule(model, c, i):
    return model.q[c, i] == (model.z[i] + 
            (model.p[c, "domestic"] - sum(model.r[cp_idx, i] * model.p[cp_idx, "domestic"] 
                                          for cp_idx in model.cp)))
model.supply = Constraint(model.c, model.i, rule=supply_rule, doc='supply relation')

# indc(c,s,i): input demand for commodities
def indc_rule(model, c, s, i):
    return model.x[c, s, i] == (model.z[i] - 
            (model.p[c, s] - sum(model.alpha[c, sp_idx, i] * model.p[c, sp_idx] 
                                 for sp_idx in model.sp)))
model.indc = Constraint(model.c, model.s, model.i, rule=indc_rule, 
                        doc='input demand for commodities')

# indcap(i): input demand for capital
def indcap_rule(model, i):
    return model.k[i] == model.z[i] - (model.pk[i] - model.alphal[i] * model.w - 
                                        model.alphak[i] * model.pk[i])
model.indcap = Constraint(model.i, rule=indcap_rule, doc='input demand for capital')

# indlab(i): input demand for labor
def indlab_rule(model, i):
    return model.li[i] == model.z[i] - (model.w - model.alphal[i] * model.w - 
                                         model.alphak[i] * model.pk[i])
model.indlab = Constraint(model.i, rule=indlab_rule, doc='input demand for labor')

# pric(i): price equations for commodities
def pric_rule(model, i):
    return (sum(model.r[c_idx, i] * model.p[c_idx, "domestic"] for c_idx in model.c) == 
            sum(model.sc[c_idx, sp_idx, i] * model.p[c_idx, sp_idx] 
                for c_idx in model.c for sp_idx in model.sp) + 
            model.sk[i] * model.pk[i] + model.sl[i] * model.w)
model.pric = Constraint(model.i, rule=pric_rule, doc='price equation for commodities')

# priexp(c): price equations for exports
def priexp_rule(model, c):
    return model.p[c, "domestic"] == model.px[c] + model.v[c] + model.phi
model.priexp = Constraint(model.c, rule=priexp_rule, doc='price equation for exports')

# priimp(c): price equations for imports
def priimp_rule(model, c):
    return model.p[c, "imported"] == model.pm[c] + model.t[c] + model.phi
model.priimp = Constraint(model.c, rule=priimp_rule, doc='price equation for imports')

# bald(c): balance equation for domestic commodities
def bald_rule(model, c):
    return (sum(model.m[c, i_idx] * model.q[c, i_idx] for i_idx in model.i) == 
            sum(model.wi[c, "domestic", i_idx] * model.x[c, "domestic", i_idx] 
                for i_idx in model.i) + 
            model.wc[c, "domestic"] * model.cn[c, "domestic"] + 
            model.we[c] * model.e[c])
model.bald = Constraint(model.c, rule=bald_rule, doc='balance equation for domestic commodities')

# ballab: balance equation for labor
def ballab_rule(model):
    return sum(model.wl[i_idx] * model.li[i_idx] for i_idx in model.i) == model.l
model.ballab = Constraint(rule=ballab_rule, doc='balance equation for labor')

# balcap(i): balance equation for capital
def balcap_rule(model, i):
    return model.k[i] == model.kappa[i]
model.balcap = Constraint(model.i, rule=balcap_rule, doc='balance equation for capital')

# imports: total imports
def imports_rule(model):
    return model.mt == sum(model.nm[c_idx] * (model.pm[c_idx] + 
            sum(model.wi[c_idx, "imported", i_idx] * model.x[c_idx, "imported", i_idx] 
                for i_idx in model.i) + 
            model.wc[c_idx, "imported"] * model.cn[c_idx, "imported"]) 
            for c_idx in model.c)
model.imports = Constraint(rule=imports_rule, doc='total imports equation')

# exports: total exports
def exports_rule(model):
    return model.et == sum(model.nx[c_idx] * model.px[c_idx] + model.nx[c_idx] * model.e[c_idx] 
                           for c_idx in model.c)
model.exports = Constraint(rule=exports_rule, doc='total exports equation')

# baltrade: balance of trade
def baltrade_rule(model):
    return model.b == (model.elevel * model.et - model.mlevel * model.mt) / 100
model.baltrade = Constraint(rule=baltrade_rule, doc='balance of trade equation')

# cpi: consumer price index
def cpi_rule(model):
    return model.pc == sum(model.mu[c_idx, s_idx] * model.p[c_idx, s_idx] 
                           for c_idx in model.c for s_idx in model.s)
model.cpi = Constraint(rule=cpi_rule, doc='consumer price index equation')

# wage: wage rate
def wage_rule(model):
    return model.w == model.theta * model.pc + model.ws
model.wage_eq = Constraint(rule=wage_rule, doc='wage rate equation')

# realc: real consumption
def realc_rule(model):
    return model.cr == model.ye - model.pc
model.realc = Constraint(rule=realc_rule, doc='real consumption equation')

# dummy: nonbinding constraint to get nonzero rhs
def dummy_rule(model):
    return model.pc <= 100000
model.dummy = Constraint(rule=dummy_rule, doc='nonbinding constraint for nonzero rhs')
