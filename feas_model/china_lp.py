# converted from models/china_lp.py
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
model.ca = Set(initialize=data['ca'], doc='all commodities')
model.c = Set(initialize=data['c'], doc='crops')
model.g = Set(initialize=data['g'], doc='grains')
model.cu = Set(initialize=data['cu'], doc='upland crops')
model.cp = Set(initialize=data['cp'], doc='commodities purchased')
model.cs = Set(initialize=data['cs'], doc='commodities sold')
model.s = Set(initialize=data['s'], doc='crop sequence')
model.sh = Set(initialize=data['sh'], doc='sequences with higher fertilizer application')
model.cf = Set(initialize=data['cf'], doc='fertilizers')
model.nh = Set(initialize=data['nh'], doc='nutrients and humus')
model.n = Set(initialize=data['n'], doc='nutrients')
model.en = Set(initialize=data['en'], doc='effective nutrients')
model.f = Set(initialize=data['f'], doc='fertilization intensity')
model.p = Set(initialize=data['p'], doc='pig raising activities')
model.ss = Set(initialize=data['ss'], dimen=2, doc='sequence possibilities')
model.t = Set(initialize=data['t'], doc='time periods')

# SCALAR_PARAMS_BLOCK
model.paddy = Param(initialize=data['paddy'], mutable=True, doc='paddy land available (mu)')
model.upland = Param(initialize=data['upland'], mutable=True, doc='upland available (mu)')
model.muperha = Param(initialize=data['muperha'], mutable=True, doc='conversion of mu to hectares')
model.jinperkg = Param(initialize=data['jinperkg'], mutable=True, doc='conversion of jin to kg')
model.yperd = Param(initialize=data['yperd'], mutable=True, doc='exchange rate (yuan per dollar)')
model.grainquota = Param(initialize=data['grainquota'], mutable=True, doc='grain sales quota (tons)')
model.tday = Param(initialize=data['tday'], mutable=True, doc='total number of days')
model.lsup = Param(initialize=data['lsup'], mutable=True, doc='labor supply (gongs per day)')
model.kc = Param(initialize=data['kc'], mutable=True, doc='k2o content of irrigation water (ppm)')
model.hdr = Param(initialize=data['hdr'], mutable=True, doc='humus decomposition rate')

# PARAM_BLOCK
model.mcp = Param(model.s, model.c, initialize=data['mcp'], mutable=True, default=0, doc='multi cropping patterns (mu)')
model.cdata = Param(model.ca, Any, initialize=data['cdata'], mutable=True, default=0, doc='crop data')
model.yield_ = Param(model.ca, initialize=data['yield'], mutable=True, default=0, doc='paddy land crop yields (ton per mu)')
model.yieldu = Param(model.ca, initialize=data['yieldu'], mutable=True, default=0, doc='upland yields (ton per mu)')
model.cxcrop = Param(model.s, initialize=data['cxcrop'], mutable=True, doc='cash cost by sequence (yuan per mu)')
model.aqsprice = Param(model.ca, initialize=data['aqsprice'], mutable=True, default=0, doc='above quota sales price (yuan per ton)')
model.purdata = Param(model.ca, Any, initialize=data['purdata'], mutable=True, default=0, doc='purchase prices and limits')
model.pigio = Param(model.ca, model.p, initialize=data['pigio'], mutable=True, default=0, doc='pig raising input output relations')
model.cxpig = Param(model.p, initialize=data['cxpig'], mutable=True, doc='pig raising cash cost (yuan per ton)')
model.gio = Param(model.ca, model.g, initialize=data['gio'], mutable=True, default=0, doc='grain feed mixing recipes')
model.lu = Param(model.t, model.c, initialize=data['lu'], mutable=True, default=0, doc='labor use for crops')
model.lab = Param(model.t, model.s, initialize=data['lab'], mutable=True, default=0, doc='labor requirements for crop sequences')
model.dlab = Param(model.t, model.c, initialize=data['dlab'], mutable=True, default=0, doc='daily labor requirements')
model.labj = Param(model.t, initialize=data['labj'], mutable=True, default=0, doc='labor adjustment coefficient')
model.days = Param(model.t, initialize=data['days'], mutable=True, doc='number of days in periods')
model.nc = Param(model.cf, model.nh, initialize=data['nc'], mutable=True, default=0, doc='nutrient composition (pct weight)')
model.nu = Param(model.cf, model.nh, model.en, initialize=data['nu'], mutable=True, default=0, doc='fertilizer utilization rates (pct)')
model.pno = Param(model.c, model.n, initialize=data['pno'], mutable=True, default=0, doc='plant nutrient offtake (pct weight)')
model.nup = Param(model.cu, model.en, initialize=data['nup'], mutable=True, default=0, doc='upland cropping nutrient requirement')
model.soil = Param(model.c, Any, initialize=data['soil'], mutable=True, default=0, doc='soil data')
model.cno = Param(model.c, model.n, initialize=data['cno'], mutable=True, default=0, doc='crop nutrient offtake (ton per mu)')
model.enc = Param(model.cf, model.en, initialize=data['enc'], mutable=True, default=0, doc='effective nutrient content (pct weight)')
model.freq = Param(model.c, model.en, initialize=data['freq'], mutable=True, default=0, doc='effective nutrient requirements (ton per mu)')
model.sreq = Param(model.s, model.en, model.f, initialize=data['sreq'], mutable=True, default=0, doc='crop sequence nutrient requirements')
model.cxfert = Param(model.cf, initialize=data['cxfert'], mutable=True, default=0, doc='fertilization cash cost (yuan per ton)')
model.mult = Param(model.en, initialize=data['mult'], mutable=True, doc='nutrient requirement factor')
model.hyield = Param(model.c, initialize=data['hyield'], mutable=True, default=0, doc='yield for high fertilizer applications')
model.hreq = Param(model.c, model.en, initialize=data['hreq'], mutable=True, default=0, doc='nutrient requirements for high application')
model.syield = Param(model.ca, model.s, model.f, initialize=data['syield'], mutable=True, default=0, doc='yield of crop sequence (ton per mu)')
model.sys = Param(model.s, model.f, initialize=data['sys'], mutable=True, default=0, doc='straw yield of crop sequences')
model.crec = Param(model.ca, model.cf, initialize=data['crec'], mutable=True, default=0, doc='composting and fertilizing recipes')
model.chemnall = Param(model.ca, Any, initialize=data['chemnall'], mutable=True, default=0, doc='chemical nitrogen allocations')
model.schem = Param(model.s, initialize=data['schem'], mutable=True, doc='chemical fertilizer allocation')

# VAR_BLOCK
model.xcrop = Var(model.s, model.f, domain=NonNegativeReals, doc='paddy land cropping activities (mu)')
model.xupland = Var(model.ca, domain=NonNegativeReals, doc='upland cropping activities (mu)')
model.xpig = Var(model.p, domain=NonNegativeReals, doc='pig raising activities (ton)')
model.xfeed = Var(model.g, domain=NonNegativeReals, doc='grain feed mixing (ton)')
model.xfert = Var(model.cf, domain=NonNegativeReals, doc='fertilization activities (kg)')
model.purchase = Var(model.ca, domain=NonNegativeReals, doc='purchasing activities (ton)')
model.sales = Var(model.ca, domain=NonNegativeReals, doc='quota sales (ton)')
model.aqsales = Var(model.ca, domain=NonNegativeReals, doc='above quota sales (ton)')
model.ccost = Var(domain=Reals, doc='cash cost (yuan)')
model.income = Var(domain=Reals, doc='brigade income (yuan)')

# OBJ_BLOCK
model.obj = Objective(expr=model.income, sense=maximize, doc='maximize income')

# CONS_BLOCK
def mb_rule(model, ca):
    """Material balance constraint (ton)"""
    return sum(model.syield[ca, s_idx, f_idx] * model.xcrop[s_idx, f_idx] for (s_idx, f_idx) in model.ss) + \
           sum(model.pigio[ca, p_idx] * model.xpig[p_idx] for p_idx in model.p) + \
           (model.purchase[ca] if ca in model.cp else 0) + \
           sum(model.gio[ca, g_idx] * model.xfeed[g_idx] for g_idx in model.g) + \
           (model.yieldu[ca] * model.xupland[ca] if ca in model.cu else 0) >= \
           ((model.sales[ca] + model.aqsales[ca]) if ca in model.cs else 0) + \
           sum(model.crec[ca, cf_idx] * model.xfert[cf_idx] for cf_idx in model.cf)
model.mb = Constraint(model.ca, rule=mb_rule, doc='material balance (ton)')

def labor_rule(model, t):
    """Labor balance constraint (gong per day)"""
    return sum(model.lab[t, s_idx] * model.xcrop[s_idx, f_idx] for (s_idx, f_idx) in model.ss) <= (1 + model.labj[t]) * model.lsup
model.labor = Constraint(model.t, rule=labor_rule, doc='labor balance (gong per day)')

def fert_rule(model, en):
    """Nutrient and humus balance constraint (ton)"""
    return sum(model.sreq[s_idx, en, f_idx] * model.xcrop[s_idx, f_idx] for (s_idx, f_idx) in model.ss) + \
           0.001 * sum(model.nup[cu_idx, en] * model.xupland[cu_idx] for cu_idx in model.cu) <= \
           0.01 * sum(model.enc[cf_idx, en] * model.xfert[cf_idx] for cf_idx in model.cf)
model.fert = Constraint(model.en, rule=fert_rule, doc='nutrient and humus balance (ton)')

def chemn_rule(model):
    """Chemical nitrogen allocation constraint (ton)"""
    return sum(model.schem[s_idx] * model.xcrop[s_idx, f_idx] for (s_idx, f_idx) in model.ss) + \
           sum(model.chemnall[cs_idx, 'qsa'] * model.sales[cs_idx] + model.chemnall[cs_idx, 'aqsa'] * model.aqsales[cs_idx] for cs_idx in model.cs) >= \
           model.purchase['amm-bi']
model.chemn = Constraint(rule=chemn_rule, doc='chemical nitrogen allocation (ton)')

def landp_rule(model):
    """Paddy land constraint (mu)"""
    return sum(model.xcrop[s_idx, f_idx] for (s_idx, f_idx) in model.ss) <= model.paddy
model.landp = Constraint(rule=landp_rule, doc='paddy land constraint (mu)')

def landu_rule(model):
    """Upland land constraint (mu)"""
    return sum(model.xupland[cu_idx] for cu_idx in model.cu) <= model.upland
model.landu = Constraint(rule=landu_rule, doc='upland land constraint (mu)')

def gmseed_rule(model):
    """Green manure seed requirements constraint (mu)"""
    return sum(((1 - 0.16) * model.mcp[s_idx, 'gm-seeds'] - 0.16 * model.mcp[s_idx, 'g-manure']) * model.xcrop[s_idx, f_idx] for (s_idx, f_idx) in model.ss) >= 0
model.gmseed = Constraint(rule=gmseed_rule, doc='green manure seed requirements (mu)')

def grainq_rule(model):
    """Grain quota sales constraint (ton)"""
    return sum(model.sales[g_idx] for g_idx in model.g) >= model.grainquota
model.grainq = Constraint(rule=grainq_rule, doc='grain quota sales (ton)')

def cdef_rule(model):
    """Cash cost definition constraint (yuan)"""
    return model.ccost == sum(model.cxcrop[s_idx] * model.xcrop[s_idx, f_idx] for (s_idx, f_idx) in model.ss) + \
                          sum(model.cxpig[p_idx] * model.xpig[p_idx] for p_idx in model.p) + \
                          sum(model.cxfert[cf_idx] * model.xfert[cf_idx] for cf_idx in model.cf) + \
                          sum(model.purdata[cp_idx, 'price'] * model.purchase[cp_idx] for cp_idx in model.cp)
model.cdef = Constraint(rule=cdef_rule, doc='cash cost definition (yuan)')

def incdef_rule(model):
    """Income definition constraint (yuan)"""
    return model.income == sum(model.cdata[cs_idx, 'proc-price'] * model.sales[cs_idx] + model.aqsprice[cs_idx] * model.aqsales[cs_idx] for cs_idx in model.cs) - model.ccost
model.incdef = Constraint(rule=incdef_rule, doc='income definition (yuan)')

# BOUNDS
# sales.lo(cs) = cdata(cs,"quota-sale") - lower bound on sales
for cs_idx in model.cs:
    quota_sale = data['cdata'].get((cs_idx, 'quota-sale'), 0)
    if quota_sale:
        model.sales[cs_idx].setlb(quota_sale)

# purchase.up(cp)$purdata(cp,"quantity") = purdata(cp,"quantity") - upper bound on purchase
for cp_idx in model.cp:
    quantity = data['purdata'].get((cp_idx, 'quantity'), 0)
    if quantity:
        model.purchase[cp_idx].setub(quantity)
