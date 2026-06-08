# converted from gamslib turkpow (TURKPOW, SEQ=54)
# Turkey Power Planning Model - least-cost capacity expansion LP for the
# Turkish electricity sector (Turvey & Anderson, 1977).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "gas-t|1978": value → ("gas-t", 1978)).
# OptiChat's normalizer flattens the sections, so we read FLAT keys here.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

model = pyo.ConcreteModel(doc="Turkey Power Planning Model - least-cost capacity expansion")

# ── Sets ──────────────────────────────────────────────────────────────────────
model.time = pyo.Set(initialize=data["time"], ordered=True, doc="time periods 1975-2005")
model.te   = pyo.Set(initialize=data["te"], ordered=True, doc="extended time horizon")
model.t    = pyo.Set(initialize=data["t"], ordered=True, doc="time periods excluding base year")
model.b    = pyo.Set(initialize=data["b"], ordered=True, doc="load blocks")
model.mh   = pyo.Set(initialize=data["mh"], ordered=True, doc="hydro units")
model.mt   = pyo.Set(initialize=data["mt"], ordered=True, doc="thermal units")

# Alias-like helper iterables (v ~ t, bp ~ b) for readability in rules.
T  = list(data["t"])
TE = list(data["te"])
B  = list(data["b"])
MH = list(data["mh"])
MT = list(data["mt"])

# ── Raw-data Params (mutable for OptiChat) ────────────────────────────────────
model.mdatah_initcap = pyo.Param(model.mh, initialize=data["mdatah_initcap"], mutable=True, within=pyo.NonNegativeReals, doc="hydro initial capacity (mw)")
model.mdatah_avail   = pyo.Param(model.mh, initialize=data["mdatah_avail"],   mutable=True, within=pyo.NonNegativeReals, doc="hydro operational availability")
model.mdatah_efact   = pyo.Param(model.mh, initialize=data["mdatah_efact"],   mutable=True, within=pyo.NonNegativeReals, doc="hydro energy factor")
model.mdatah_opcost  = pyo.Param(model.mh, initialize=data["mdatah_opcost"],  mutable=True, within=pyo.NonNegativeReals, doc="hydro operating cost (mill tl per mw-yr)")
model.mdatah_capcost = pyo.Param(model.mh, initialize=data["mdatah_capcost"], mutable=True, within=pyo.NonNegativeReals, doc="hydro capital cost (mill tl per mw)")
model.mdatah_life    = pyo.Param(model.mh, initialize=data["mdatah_life"],    mutable=True, within=pyo.NonNegativeReals, doc="hydro life (years)")
model.mdatah_maxcap  = pyo.Param(model.mh, initialize=data["mdatah_maxcap"],  mutable=True, within=pyo.NonNegativeReals, doc="hydro maximum new capacity (mw)")

model.mdatat_initcap  = pyo.Param(model.mt, initialize=data["mdatat_initcap"],  mutable=True, within=pyo.NonNegativeReals, doc="thermal initial capacity (mw)")
model.mdatat_avail    = pyo.Param(model.mt, initialize=data["mdatat_avail"],    mutable=True, within=pyo.NonNegativeReals, doc="thermal operational availability")
model.mdatat_opcost   = pyo.Param(model.mt, initialize=data["mdatat_opcost"],   mutable=True, within=pyo.NonNegativeReals, doc="thermal operating cost (mill tl per mw-yr)")
model.mdatat_opcostg  = pyo.Param(model.mt, initialize=data["mdatat_opcostg"],  mutable=True, within=pyo.Reals,           doc="thermal annual rate of decrease in operating cost")
model.mdatat_capcost  = pyo.Param(model.mt, initialize=data["mdatat_capcost"],  mutable=True, within=pyo.NonNegativeReals, doc="thermal capital cost (mill tl per mw)")
model.mdatat_capcostg = pyo.Param(model.mt, initialize=data["mdatat_capcostg"], mutable=True, within=pyo.Reals,           doc="thermal annual rate of decrease in capital cost")
model.mdatat_life     = pyo.Param(model.mt, initialize=data["mdatat_life"],     mutable=True, within=pyo.NonNegativeReals, doc="thermal life (years)")
# maxcap only defined for lignite units (others are +inf and omitted in data)
model.mdatat_maxcap   = pyo.Param(model.mt, initialize=data["mdatat_maxcap"],   mutable=True, within=pyo.NonNegativeReals, default=float("inf"), doc="thermal maximum new capacity (mw)")

model.dd_duration = pyo.Param(model.b, initialize=data["dd_duration"], mutable=True, within=pyo.NonNegativeReals, doc="load duration (hrs per yr)")
model.dd_demand   = pyo.Param(model.b, initialize=data["dd_demand"],   mutable=True, within=pyo.NonNegativeReals, doc="block demand for 1975 (mw)")

# Scalars
model.rho = pyo.Param(initialize=data["rho"], mutable=True, within=pyo.NonNegativeReals, doc="interest rate")
model.prr = pyo.Param(initialize=data["prr"], mutable=True, within=pyo.NonNegativeReals, doc="peak reserve requirement")
model.r   = pyo.Param(initialize=data["r"],   mutable=True, within=pyo.NonNegativeReals, doc="maximum aggregate hydro capacity fraction")
model.g   = pyo.Param(initialize=data["g"],   mutable=True, within=pyo.NonNegativeReals, doc="demand growth rate (annual)")

# Bound Params. In GAMS these come from parameters/tables whose UNLISTED entries
# default to 0, so an omitted upper bound FIXES the variable to 0 (e.g. nuclear/
# lignite-3 in early vintages, hydro-8..13 at 1978/1983). The explicit GAMS "inf"
# entries are stored in the data as Infinity and translate to "no upper bound".
model.hlo = pyo.Param(model.mh, model.te, initialize=data.get("hlo", {}), mutable=True, within=pyo.NonNegativeReals, default=0.0, doc="lower bound on hydro expansions (mw)")
model.hup = pyo.Param(model.mh, model.te, initialize=data.get("hup", {}), mutable=True, within=pyo.NonNegativeReals, default=0.0, doc="upper bound on hydro expansions (mw)")
model.tlo = pyo.Param(model.mt, model.te, initialize=data.get("tlo", {}), mutable=True, within=pyo.NonNegativeReals, default=0.0, doc="lower bound on thermal expansions (mw)")
model.tup = pyo.Param(model.mt, model.te, initialize=data.get("tup", {}), mutable=True, within=pyo.NonNegativeReals, default=0.0, doc="upper bound on thermal expansions (mw)")

# ── Derived parameters (computed from raw data, mirroring GAMS) ────────────────
rho = pyo.value(model.rho)
prr = pyo.value(model.prr)
r_v = pyo.value(model.r)
g_v = pyo.value(model.g)

# length(time) = ord(time) - 1
length = {yr: i for i, yr in enumerate(data["time"])}

# bs(b,bp) = ord(b) >= ord(bp)
ordb = {bb: i + 1 for i, bb in enumerate(B)}
bs = {(bb, bbp): (ordb[bb] >= ordb[bbp]) for bb in B for bbp in B}

# vs(t,v) = ord(t) >= ord(v)   (ord within set t; v aliases t)
ordt = {tt: i + 1 for i, tt in enumerate(T)}
vs = {(tt, vv): (ordt[tt] >= ordt[vv]) for tt in T for vv in T}

# opcostt(m,v,t)$vs(t,v) and capcostt(m,v,t)$vs(t,v)
opcostt, capcostt = {}, {}
for mm in MT:
    oc  = pyo.value(model.mdatat_opcost[mm])
    ocg = pyo.value(model.mdatat_opcostg[mm])
    cc  = pyo.value(model.mdatat_capcost[mm])
    ccg = pyo.value(model.mdatat_capcostg[mm])
    for vv in T:
        for tt in T:
            if vs[(tt, vv)]:
                opcostt[(mm, vv, tt)]  = oc * (1 + ocg) ** length[vv]
                capcostt[(mm, vv, tt)] = cc * (1 + ccg) ** length[vv]

# d(b,te) = round(dd(b,demand)*(1+g)**length(te))
d = {}
for bb in B:
    dem = pyo.value(model.dd_demand[bb])
    for tee in TE:
        d[(bb, tee)] = round(dem * (1 + g_v) ** length[tee])

# dur(b) = sum(bp$bs(b,bp), dd(bp,duration)) / sum(bp, dd(bp,duration))
totdur = sum(pyo.value(model.dd_duration[bbp]) for bbp in B)
dur = {bb: sum(pyo.value(model.dd_duration[bbp]) for bbp in B if bs[(bb, bbp)]) / totdur for bb in B}

# delta(t) = (1+rho)**(-length(t))
delta = {tt: (1 + rho) ** (-length[tt]) for tt in T}

# sigma(m): capital recovery factor
sigma = {}
for mm in MT:
    life = pyo.value(model.mdatat_life[mm])
    sigma[mm] = rho / (1 - (1 + rho) ** (-life))
for mm in MH:
    life = pyo.value(model.mdatah_life[mm])
    sigma[mm] = rho / (1 - (1 + rho) ** (-life))

# kit(mt,"1978") = mdatat(mt,initcap); zero elsewhere
kit = {(mm, vv): 0.0 for mm in MT for vv in T}
for mm in MT:
    kit[(mm, 1978)] = pyo.value(model.mdatat_initcap[mm])

# ── Variables ─────────────────────────────────────────────────────────────────
model.phi  = pyo.Var(domain=pyo.Reals, doc="total discounted cost (million tl)")
model.phic = pyo.Var(model.te, domain=pyo.Reals, doc="capital charges (million tl)")
model.phio = pyo.Var(model.te, domain=pyo.Reals, doc="operating costs (million tl)")
model.hh   = pyo.Var(model.mh, model.te, domain=pyo.NonNegativeReals, doc="hydro capacity additions (mw)")
model.ht   = pyo.Var(model.mt, model.t,  domain=pyo.NonNegativeReals, doc="thermal capacity additions (mw)")
model.htt  = pyo.Var(model.mt, domain=pyo.Reals, doc="total thermal capacity additions (mw)")
model.zh   = pyo.Var(model.mh, model.b, model.t, domain=pyo.NonNegativeReals, doc="hydro power output (mw)")
model.zt   = pyo.Var(model.mt, model.t, model.b, model.t, domain=pyo.NonNegativeReals, doc="thermal power output (mw)")

# Variable bounds (hh, ht, htt) from the bound params. GAMS sets bounds only
# over t (1978-2005), leaving the base-year column at its default (lo=0, up=+inf);
# hh(mh,1975) never enters any constraint, so it is left untouched here too.
for mm in MH:
    for tt in T:
        lo = pyo.value(model.hlo[mm, tt])
        up = pyo.value(model.hup[mm, tt])
        if lo > 0:
            model.hh[mm, tt].setlb(lo)
        if up != float("inf"):
            model.hh[mm, tt].setub(up)
for mm in MT:
    for tt in T:
        lo = pyo.value(model.tlo[mm, tt])
        up = pyo.value(model.tup[mm, tt])
        if lo > 0:
            model.ht[mm, tt].setlb(lo)
        if up != float("inf"):
            model.ht[mm, tt].setub(up)
for mm in MT:
    mx = pyo.value(model.mdatat_maxcap[mm])
    if mx != float("inf"):
        model.htt[mm].setub(mx)

# ── Constraints ───────────────────────────────────────────────────────────────
# db(b,t): demand balance
def db_rule(model, bb, tt):
    return (sum(model.zh[mhh, bbp, tt] for mhh in MH for bbp in B if bs[(bbp, bb)])
            + sum(model.zt[mtt, vv, bbp, tt] for mtt in MT for vv in T for bbp in B
                  if bs[(bbp, bb)] and vs[(tt, vv)])) >= d[(bb, tt)]
model.db = pyo.Constraint(model.b, model.t, rule=db_rule, doc="demand balance (mw)")

# pr(t): peak and reserve requirements
def pr_rule(model, tt):
    lhs = (sum(pyo.value(model.mdatah_avail[mhh]) * (pyo.value(model.mdatah_initcap[mhh])
                + sum(model.hh[mhh, vv] for vv in T if vs[(tt, vv)])) for mhh in MH)
           + sum(pyo.value(model.mdatat_avail[mtt]) * sum(kit[(mtt, vv)] + model.ht[mtt, vv]
                for vv in T if vs[(tt, vv)]) for mtt in MT))
    return lhs >= (1 + prr) * d[("peak", tt)]
model.pr = pyo.Constraint(model.t, rule=pr_rule, doc="peak and reserve requirements (mw)")

# cch(mh,t): hydro capacity constraint
def cch_rule(model, mhh, tt):
    return (sum(model.zh[mhh, bb, tt] for bb in B)
            <= pyo.value(model.mdatah_avail[mhh]) * (pyo.value(model.mdatah_initcap[mhh])
               + sum(model.hh[mhh, vv] for vv in T if vs[(tt, vv)])))
model.cch = pyo.Constraint(model.mh, model.t, rule=cch_rule, doc="capacity constraint: hydro (mw)")

# cct(mt,v,t)$vs(t,v): thermal capacity constraint
def cct_rule(model, mtt, vv, tt):
    if not vs[(tt, vv)]:
        return pyo.Constraint.Skip
    return sum(model.zt[mtt, vv, bb, tt] for bb in B) <= pyo.value(model.mdatat_avail[mtt]) * (kit[(mtt, vv)] + model.ht[mtt, vv])
model.cct = pyo.Constraint(model.mt, model.t, model.t, rule=cct_rule, doc="capacity constraint: thermal (mw)")

# ech(mh,t): hydro energy constraint
def ech_rule(model, mhh, tt):
    return (sum(dur[bb] * model.zh[mhh, bb, tt] for bb in B)
            <= pyo.value(model.mdatah_efact[mhh]) * (pyo.value(model.mdatah_initcap[mhh])
               + sum(model.hh[mhh, vv] for vv in T if vs[(tt, vv)])))
model.ech = pyo.Constraint(model.mh, model.t, rule=ech_rule, doc="hydro energy constraint (mw-yr)")

# hcc(t): hydro capacity constraint (aggregate)
def hcc_rule(model, tt):
    return (sum(pyo.value(model.mdatah_initcap[mhh]) + sum(model.hh[mhh, vv] for vv in T if vs[(tt, vv)]) for mhh in MH)
            <= r_v * d[("peak", tt)])
model.hcc = pyo.Constraint(model.t, rule=hcc_rule, doc="aggregate hydro capacity constraint (mw)")

# rch(mh): resource constraint - maximum new hydro capacity
def rch_rule(model, mhh):
    return sum(model.hh[mhh, tt] for tt in T) <= pyo.value(model.mdatah_maxcap[mhh])
model.rch = pyo.Constraint(model.mh, rule=rch_rule, doc="resource constraint: max new hydro capacity (mw)")

# cat(mt): capacity accounting - total new thermal capacity
def cat_rule(model, mtt):
    return model.htt[mtt] == sum(model.ht[mtt, vv] for vv in T)
model.cat = pyo.Constraint(model.mt, rule=cat_rule, doc="capacity accounting: total new thermal capacity (mw)")

# ak(t): accounting - capital charges
def ak_rule(model, tt):
    return model.phic[tt] == (
        sum(sigma[mhh] * pyo.value(model.mdatah_capcost[mhh]) * sum(model.hh[mhh, vv] for vv in T if vs[(tt, vv)]) for mhh in MH)
        + sum(sigma[mtt] * sum(capcostt.get((mtt, vv, tt), 0.0) * model.ht[mtt, vv] for vv in T) for mtt in MT))
model.ak = pyo.Constraint(model.t, rule=ak_rule, doc="accounting: capital charges (million tl)")

# ao(t): accounting - operating costs
def ao_rule(model, tt):
    return model.phio[tt] == (
        sum(pyo.value(model.mdatah_opcost[mhh]) * sum(dur[bb] * model.zh[mhh, bb, tt] for bb in B) for mhh in MH)
        + sum(opcostt.get((mtt, vv, tt), 0.0) * sum(dur[bb] * model.zt[mtt, vv, bb, tt] for bb in B)
              for mtt in MT for vv in T if vs[(tt, vv)]))
model.ao = pyo.Constraint(model.t, rule=ao_rule, doc="accounting: operating costs (million tl)")

# obj: total discounted cost defining equation
def objdef_rule(model):
    return model.phi == sum(delta[tt] * (model.phic[tt] + model.phio[tt]) for tt in T)
model.objdef = pyo.Constraint(rule=objdef_rule, doc="total discounted cost accounting (million tl)")

# ── Objective ─────────────────────────────────────────────────────────────────
model.obj = pyo.Objective(expr=model.phi, sense=pyo.minimize, doc="minimize total discounted cost")
