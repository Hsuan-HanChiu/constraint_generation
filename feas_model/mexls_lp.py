# converted from gamslib mexls (MEXLS, SEQ=17) — Mexico Steel, Large Static LP
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────


def D(name):
    """Fetch a (possibly pipe-keyed) indexed param dict from data."""
    return dict(data[name])


# ── Sets (Python lists, used both for Pyomo Sets and GAMS-style preprocessing) ─
im   = list(data["im"])
ir   = list(data["ir"])
iss  = list(data["isx"])          # 'is' in GAMS (Python keyword → iss)
jj   = list(data["j"])
mm   = list(data["mm"])
mr   = list(data["mr"])
ms   = list(data["ms"])
pm   = list(data["pm"])
pr   = list(data["pr"])
ps   = list(data["ps"])
cs   = list(data["cs"])
craw = list(data["craw"])
cm   = list(data["cm"])
cr   = list(data["cr"])
crv  = list(data["crv"])
cmr  = list(data["cmr"])
cms  = list(data["cms"])
crs  = list(data["crs"])
css  = list(data["css"])
cf   = list(data["cf"])
ce   = list(data["ce"])
cfv  = list(data["cfv"])
o    = list(data["o"])
isex = list(data["isex"])
def _pair(x):
    """Accept a pipe-string 'a|b' or an already-split (a, b) tuple/list."""
    if isinstance(x, str):
        return tuple(x.split("|"))
    return tuple(x)


res  = set(_pair(x) for x in data["res"])                     # res(cm,im)
own  = set(_pair(x) for x in data["own"])                     # own(o,is)

# ── Raw data tables (tuple-keyed) ─────────────────────────────────────────────
am    = D("am")
ar    = D("ar")
asic  = D("asic")
aahm  = D("aahm")
afund = D("afund")
ahyl  = D("ahyl")
ahylp = D("ahylp")
atam  = D("atam")
bm    = D("bm")
br    = D("br")
bs    = D("bs")
km    = D("km")
kr    = D("kr")
ks    = D("ks")
ut    = D("ut")
mc    = D("mc")
mrod  = D("mrod")
demdat = D("demdat")
regdem = D("regdem")
prices = D("prices")
pct    = D("pct")
rdsj = D("rdsj")
rdss = D("rdss")
rdrs = D("rdrs")
rdms = D("rdms")
rdmr = D("rdmr")
rdps = D("rdps")
rdpj = D("rdpj")
sh   = float(data["sh"])
etot = float(data["etot"])


def g(tbl, *key):
    """GAMS-style lookup: missing entry → 0."""
    return tbl.get(key if len(key) > 1 else key[0], 0)


# ── as(cs,ps,is): input-output relations for steel mills ──────────────────────
plant_tbl = {"sicartsa": asic, "ahmsa": aahm, "fundidora": afund,
             "hylsa": ahyl, "hylsap": ahylp, "tamsa": atam}
asp = {}   # as(cs,ps,is)
for plant, tbl in plant_tbl.items():
    for (c, p), v in tbl.items():
        asp[(c, p, plant)] = v

# ── Capacity scaling ──────────────────────────────────────────────────────────
# km = .9*km ; kr = .9*kr ; ks = ut*ks
km = {k: 0.9 * v for k, v in km.items()}
kr = {k: 0.9 * v for k, v in kr.items()}
ks = {(m, i): ut[i] * v for (m, i), v in ks.items()}

# ── Demand derivation ─────────────────────────────────────────────────────────
# demdat(cs,"adj-dem") = demand - semi-int
adj = {}
for c in cs:
    adj[c] = g(demdat, c, "demand") - g(demdat, c, "semi-int")
# demdat(cf,"adj-dem")$sum(cs,mrod(cs,cf)) = sum(cs, mrod(cs,cf)*demdat(cs,"adj-dem"))
for f in cf:
    s = sum(g(mrod, c, f) for c in cs)
    if s != 0:
        adj[f] = sum(g(mrod, c, f) * adj[c] for c in cs)
# regdem(cf,j)$sum(cs,mrod(cs,cf)) = sum(cs$mrod(cs,cf), regdem(cs,j))
for f in cf:
    s = sum(g(mrod, c, f) for c in cs)
    if s != 0:
        for jx in jj:
            regdem[(f, jx)] = sum(g(regdem, c, jx) for c in cs if g(mrod, c, f) != 0)
# d(cf,j) = demdat(cf,"adj-dem")*regdem(cf,j)/100
d = {}
for f in cf:
    for jx in jj:
        d[(f, jx)] = adj[f] * g(regdem, f, jx) / 100.0

# ── Export limits ─────────────────────────────────────────────────────────────
emax = {f: 500.0 for f in cf}      # emax(cf) = 500
# etot = 250 (scalar)

# ── Prices ────────────────────────────────────────────────────────────────────
pd = {c: g(prices, c, "domestic") for c in craw}    # pd(craw)
pv = {}                                              # pv(crv), pv(cfv)
for c in crv:
    pv[c] = g(prices, c, "internat")
for c in cfv:
    pv[c] = g(prices, c, "internat")
pe = {c: 0.8 * g(prices, c, "internat") for c in ce}  # pe(ce) = .8*internat

# ── Transport-cost derivation ─────────────────────────────────────────────────
# rdps("short",is) = min(gulf,pacific) ; rdpj("short",j) = min(gulf,pacific)
for i in iss:
    rdps[("short", i)] = min(g(rdps, "gulf", i), g(rdps, "pacific", i))
for jx in jj:
    rdpj[("short", jx)] = min(g(rdpj, "gulf", jx), g(rdpj, "pacific", jx))
# rdss(is,isp) = max(rdss(is,isp), rdss(isp,is))   (symmetrize)
rdss_sym = {}
for i in iss:
    for ip in iss:
        rdss_sym[(i, ip)] = max(g(rdss, i, ip), g(rdss, ip, i))
rdss = rdss_sym

# mu* = (base + slope*dist)$dist   (only where distance > 0)
mumr = {}      # mines -> raw plants
for i in im:
    for r in ir:
        if g(rdmr, i, r):
            mumr[(i, r)] = 35 + 0.11 * g(rdmr, i, r)
mums = {}      # mines -> mills
for i in im:
    for s in iss:
        if g(rdms, i, s):
            mums[(i, s)] = 35 + 0.11 * g(rdms, i, s)
murs = {}      # raw plants -> mills
for r in ir:
    for s in iss:
        if g(rdrs, r, s):
            murs[(r, s)] = 35 + 0.11 * g(rdrs, r, s)
muss = {}      # between mills
for i in iss:
    for ip in iss:
        if g(rdss, i, ip):
            muss[(i, ip)] = 35 + 0.11 * g(rdss, i, ip)
mupsr = {}     # ports -> mills (raw materials)
for s in iss:
    if g(rdps, "short", s):
        mupsr[s] = 35 + 0.11 * g(rdps, "short", s)
musj = {}      # mills -> markets
for s in iss:
    for jx in jj:
        if g(rdsj, s, jx):
            musj[(s, jx)] = 60 + 0.19 * g(rdsj, s, jx)
muspf = {}     # mills -> ports (final products)
for s in iss:
    if g(rdps, "short", s):
        muspf[s] = 60 + 0.19 * g(rdps, "short", s)
mupj = {}      # ports -> markets
for jx in jj:
    if g(rdpj, "short", jx):
        mupj[jx] = 60 + 0.19 * g(rdpj, "short", jx)

# ── loss(cs): coke shipment correction ────────────────────────────────────────
loss = {c: 1.0 for c in cs}
loss["coke"] = 0.9

# ── Model reduction: productive-unit / process / commodity possibility sets ────
mmpos = {(m, i) for (m, i) in km if km.get((m, i), 0)}     # mmpos(mm,im)=yes$km
mrpos = {(m, i) for (m, i) in kr if kr.get((m, i), 0)}     # mrpos(mr,ir)=yes$kr
mspos = {(m, i) for (m, i) in ks if ks.get((m, i), 0)}     # mspos(ms,is)=yes$ks

# pmpos(pm,im)$sum(cm, am(cm,pm)$res(cm,im) <> 0) =
#              yes$(sum(mm$(not mmpos(mm,im)), bm(mm,pm) <> 0) = 0)
pmpos = set()
for p in pm:
    for i in im:
        ctrl = sum(1 for c in cm if (c, i) in res and g(am, c, p) != 0)
        if ctrl != 0:
            bad = sum(1 for m in mm if (m, i) not in mmpos and g(bm, m, p) != 0)
            if bad == 0:
                pmpos.add((p, i))

# prpos(pr,ir)$sum(cr, ar(cr,pr) <> 0) =
#              yes$(sum(mr$(not mrpos(mr,ir)), br(mr,pr) <> 0) = 0)
prpos = set()
for p in pr:
    for r in ir:
        ctrl = sum(1 for c in cr if g(ar, c, p) != 0)
        if ctrl != 0:
            bad = sum(1 for m in mr if (m, r) not in mrpos and g(br, m, p) != 0)
            if bad == 0:
                prpos.add((p, r))

# pspos(ps,is)$sum(cs, as(cs,ps,is) <> 0) =
#              yes$(sum(ms$(not mspos(ms,is)), bs(ms,ps) <> 0) = 0)
pspos = set()
for p in ps:
    for s in iss:
        ctrl = sum(1 for c in cs if g(asp, c, p, s) != 0)
        if ctrl != 0:
            bad = sum(1 for m in ms if (m, s) not in mspos and g(bs, m, p) != 0)
            if bad == 0:
                pspos.add((p, s))

# commodity production / consumption possibility sets
cmposp = {(c, i) for c in cm for i in im if any((p, i) in pmpos and g(am, c, p) > 0 for p in pm)}
crposp = {(c, r) for c in cr for r in ir if any((p, r) in prpos and g(ar, c, p) > 0 for p in pr)}
csposp = {(c, s) for c in cs for s in iss if any((p, s) in pspos and g(asp, c, p, s) > 0 for p in ps)}
cmposn = {(c, i) for c in cm for i in im if any((p, i) in pmpos and g(am, c, p) < 0 for p in pm)}
crposn = {(c, r) for c in cr for r in ir if any((p, r) in prpos and g(ar, c, p) < 0 for p in pr)}
csposn = {(c, s) for c in cs for s in iss if any((p, s) in pspos and g(asp, c, p, s) < 0 for p in ps)}

# imres / imfree
imres = {"lastruchas"}
imfree = [i for i in im if i not in imres]

# xmpos(cs,im,*): possible shipments of mining products
# dest index ranges over ir ∪ is. Store as set of (c, im, dest).
xmpos = set()
xmpos.add(("coal-d", "coahuila", "esperanzas"))
xmpos.add(("ore-conc", "p-colorada", "penacol"))
xmpos.add(("ore-conc", "la-perla", "laperla"))
xmpos.add(("ore-conc", "el-encino", "alzada"))
for c in cm:
    xmpos.add((c, "lastruchas", "sicartsa"))
for c in cm:
    for i in imfree:
        for s in iss:
            xmpos.add((c, i, s))


# ══════════════════════════════════════════════════════════════════════════════
# Pyomo model
# ══════════════════════════════════════════════════════════════════════════════
model = pyo.ConcreteModel(doc="Mexico Steel - Large Static (MEXLS) — minimize total cost")

# Sets
model.im = pyo.Set(initialize=im, doc="iron ore and coal mines")
model.ir = pyo.Set(initialize=ir, doc="raw material plants")
model.iss = pyo.Set(initialize=iss, doc="steel mills")
model.j = pyo.Set(initialize=jj, doc="domestic market areas")
model.pm = pyo.Set(initialize=pm, doc="production processes at mines")
model.pr = pyo.Set(initialize=pr, doc="production processes at raw material plants")
model.ps = pyo.Set(initialize=ps, doc="production processes at steel mills")
model.cs = pyo.Set(initialize=cs, doc="commodities at steel mills")
model.cm = pyo.Set(initialize=cm, doc="commodities at mines")
model.cr = pyo.Set(initialize=cr, doc="commodities at raw material plants")
model.cf = pyo.Set(initialize=cf, doc="final products")
model.ce = pyo.Set(initialize=ce, doc="commodities for exports")
model.o = pyo.Set(initialize=o, doc="owner numbers")
model.mm = pyo.Set(initialize=mm, doc="productive units at mines")
model.mr = pyo.Set(initialize=mr, doc="productive units at raw material plants")
model.ms = pyo.Set(initialize=ms, doc="productive units at steel mills")

# Mutable parameters (capacities, demand, prices, transport costs, etc.)
model.km = pyo.Param(model.mm, model.im, initialize=km, default=0.0, mutable=True,
                     within=pyo.NonNegativeReals, doc="capacity: mines (1000 tpy)")
model.kr = pyo.Param(model.mr, model.ir, initialize=kr, default=0.0, mutable=True,
                     within=pyo.NonNegativeReals, doc="capacity: raw material plants (1000 tpy)")
model.ks = pyo.Param(model.ms, model.iss, initialize=ks, default=0.0, mutable=True,
                     within=pyo.NonNegativeReals, doc="capacity: steel mills (1000 tpy)")
model.d = pyo.Param(model.cf, model.j, initialize=d, default=0.0, mutable=True,
                    within=pyo.Reals, doc="adjusted demand (1000 tpy)")
model.emax = pyo.Param(model.cf, initialize=emax, default=0.0, mutable=True,
                       within=pyo.NonNegativeReals, doc="export limit by product (1000 tpy)")
model.etot = pyo.Param(initialize=etot, mutable=True, within=pyo.NonNegativeReals,
                       doc="total export limit (1000 tpy)")
model.sh = pyo.Param(initialize=sh, mutable=True, within=pyo.NonNegativeReals,
                     doc="shadow exchange rate (pesos per us$)")

# ── Run-1 capacity modifications (must precede mspos? No: mspos already built; ──
#    GAMS rescales ks AFTER reductions, so reductions use unscaled-by-run ks.) ──
# vs.up("coke",is)=0 ; us.up("scrap",is)=0  → enforced as variable upper bounds.
# ks(ms,"ahmsa")=ks*0.9 ; ks(ms,"fundidora")=ks*0.95
for m in ms:
    if (m, "ahmsa") in ks:
        model.ks[m, "ahmsa"] = pyo.value(model.ks[m, "ahmsa"]) * 0.9
    if (m, "fundidora") in ks:
        model.ks[m, "fundidora"] = pyo.value(model.ks[m, "fundidora"]) * 0.95

# Variables (all nonnegative except the cost accounting vars)
model.zm = pyo.Var(model.pm, model.im, domain=pyo.NonNegativeReals, doc="process level: mines")
model.zr = pyo.Var(model.pr, model.ir, domain=pyo.NonNegativeReals, doc="process level: raw plants")
model.zs = pyo.Var(model.ps, model.iss, domain=pyo.NonNegativeReals, doc="process level: steel mills")

# xm(cs,im,*): dest over ir ∪ is. Index over all (cs, im, dest) in xmpos.
xm_index = sorted(xmpos)
model.xm_idx = pyo.Set(dimen=3, initialize=xm_index)
model.xm = pyo.Var(model.xm_idx, domain=pyo.NonNegativeReals, doc="shipments: mine products")

model.xr = pyo.Var(model.cs, model.ir, model.iss, domain=pyo.NonNegativeReals, doc="shipments from raw plants")
model.xs = pyo.Var(model.cs, model.iss, model.iss, domain=pyo.NonNegativeReals, doc="shipments interplant")
model.xf = pyo.Var(model.cs, model.iss, model.j, domain=pyo.NonNegativeReals, doc="shipments final products")
model.ur = pyo.Var(model.cs, model.ir, domain=pyo.NonNegativeReals, doc="domestic purchase: raw plants")
model.us = pyo.Var(model.cs, model.iss, domain=pyo.NonNegativeReals, doc="domestic purchase: steel mills")
model.e = pyo.Var(model.cs, model.iss, domain=pyo.NonNegativeReals, doc="exports")
model.vs = pyo.Var(model.cs, model.iss, domain=pyo.NonNegativeReals, doc="imports to steel mills")
model.vf = pyo.Var(model.cs, model.j, domain=pyo.NonNegativeReals, doc="import of final products")

model.cost = pyo.Var(domain=pyo.Reals, doc="total cost (mill us$)")
model.recurrent = pyo.Var(domain=pyo.Reals, doc="recurrent cost (mill us$)")
model.transport = pyo.Var(domain=pyo.Reals, doc="transport cost (mill us$)")
model.imp = pyo.Var(domain=pyo.Reals, doc="import cost (mill us$)")
model.exp = pyo.Var(domain=pyo.Reals, doc="export revenue (mill us$)")

# Run-1 variable bounds: vs.up("coke",is)=0, us.up("scrap",is)=0
for s in iss:
    model.vs["coke", s].setub(0.0)
    model.us["scrap", s].setub(0.0)


def xm_has(c, i, dest):
    return (c, i, dest) in xmpos


def _skip_if_trivial(expr):
    """GAMS suppresses balance/capacity rows that contain no variables; mirror
    that by skipping any constraint whose relational expression has both sides
    constant (Pyomo would otherwise raise on a trivial True/False)."""
    if expr is True:
        return pyo.Constraint.Skip
    if expr is False:
        return pyo.Constraint.Infeasible
    return expr


# ── Constraints ───────────────────────────────────────────────────────────────
# mbm(cm,im): material balance at mines
def mbm_rule(model, c, i):
    lhs = sum(g(am, c, p) * model.zm[p, i] for p in pm if (p, i) in pmpos and g(am, c, p) != 0)
    if (c, i) in cmposp:
        rhs = sum(model.xm[c, i, r] for r in ir if xm_has(c, i, r) and (c, r) in crposn)
        rhs += sum(model.xm[c, i, s] for s in iss if xm_has(c, i, s) and (c, s) in csposn)
    else:
        rhs = 0
    return _skip_if_trivial(lhs >= rhs)


model.mbm = pyo.Constraint(model.cm, model.im, rule=mbm_rule, doc="material balance: mines")


# mbr(cr,ir): material balance at raw material plants
def mbr_rule(model, c, r):
    lhs = sum(g(ar, c, p) * model.zr[p, r] for p in pr if (p, r) in prpos and g(ar, c, p) != 0)
    if (c, r) in crposn:
        if c in cmr:
            lhs += sum(model.xm[c, i, r] for i in im if (c, i) in cmposp and xm_has(c, i, r))
        if c in craw:
            lhs += model.ur[c, r]
    rhs = sum(model.xr[c, r, s] for s in iss
              if c in crs and (c, r) in crposp and (c, s) in csposn)
    return _skip_if_trivial(lhs >= rhs)


model.mbr = pyo.Constraint(model.cr, model.ir, rule=mbr_rule, doc="material balance: raw plants")


# mbs(cs,is): material balance at steel mills
def mbs_rule(model, c, s):
    lhs = sum(g(asp, c, p, s) * model.zs[p, s] for p in ps if (p, s) in pspos and g(asp, c, p, s) != 0)
    if (c, s) in csposn:
        if c in cms:
            lhs += sum(model.xm[c, i, s] for i in im if (c, i) in cmposp and xm_has(c, i, s))
        if c in crs:
            lhs += sum(loss[c] * model.xr[c, r, s] for r in ir if (c, r) in crposp)
        if c in css:
            lhs += sum(loss[c] * model.xs[c, sp, s] for sp in iss if (c, sp) in csposp)
        if c in craw:
            lhs += model.us[c, s]
        if c in crv:
            lhs += model.vs[c, s]
    if (c, s) in csposp:
        rhs = 0
        if c in css:
            rhs += sum(model.xs[c, s, sp] for sp in iss if (c, sp) in csposn)
        if c in cf:
            rhs += sum(model.xf[c, s, jx] for jx in jj)
        if c in ce:
            rhs += model.e[c, s]
    else:
        rhs = 0
    return _skip_if_trivial(lhs >= rhs)


model.mbs = pyo.Constraint(model.cs, model.iss, rule=mbs_rule, doc="material balance: steel mills")


# ccm(mm,im)$mmpos: capacity at mines
def ccm_rule(model, m, i):
    if (m, i) not in mmpos:
        return pyo.Constraint.Skip
    return sum(g(bm, m, p) * model.zm[p, i] for p in pm if (p, i) in pmpos and g(bm, m, p) != 0) <= model.km[m, i]


model.ccm = pyo.Constraint(model.mm, model.im, rule=ccm_rule, doc="capacity: mines")


# ccr(mr,ir)$mrpos: capacity at raw material plants
def ccr_rule(model, m, r):
    if (m, r) not in mrpos:
        return pyo.Constraint.Skip
    return sum(g(br, m, p) * model.zr[p, r] for p in pr if (p, r) in prpos and g(br, m, p) != 0) <= model.kr[m, r]


model.ccr = pyo.Constraint(model.mr, model.ir, rule=ccr_rule, doc="capacity: raw plants")


# ccs(ms,is)$mspos: capacity at steel mills
def ccs_rule(model, m, s):
    if (m, s) not in mspos:
        return pyo.Constraint.Skip
    return sum(g(bs, m, p) * model.zs[p, s] for p in ps if (p, s) in pspos and g(bs, m, p) != 0) <= model.ks[m, s]


model.ccs = pyo.Constraint(model.ms, model.iss, rule=ccs_rule, doc="capacity: steel mills")


# mreq(cf,j): market requirements
def mreq_rule(model, c, jx):
    return sum(model.xf[c, s, jx] for s in iss if (c, s) in csposp) + model.vf[c, jx] >= model.d[c, jx]


model.mreq = pyo.Constraint(model.cf, model.j, rule=mreq_rule, doc="market requirements")


# me(cf): export bounds
def me_rule(model, c):
    return sum(model.e[c, s] for s in iss if (c, s) in csposp) <= model.emax[c]


model.me = pyo.Constraint(model.cf, rule=me_rule, doc="export bounds")


# me2: total exports
def me2_rule(model):
    return sum(model.e[c, s] for c in cf for s in iss if (c, s) in csposp) <= model.etot


model.me2 = pyo.Constraint(rule=me2_rule, doc="total exports")


# pelpc(o): pellet shipments from pena colorada by owner
def pelpc_rule(model, oo):
    lhs = sum(model.xr["pellets", "penacol", s] for s in iss
              if (oo, s) in own and ("pellets", s) in csposn)
    return _skip_if_trivial(lhs <= g(pct, oo) * kr.get(("pellet", "penacol"), 0))


model.pelpc = pyo.Constraint(model.o, rule=pelpc_rule, doc="pellet shipments from pena colorada")


# pelal: pellet shipments from alzada = 0
def pelal_rule(model):
    terms = [model.xr["pellets", "alzada", s] for s in isex if ("pellets", s) in csposn]
    if not terms:
        return pyo.Constraint.Skip
    return sum(terms) == 0


model.pelal = pyo.Constraint(rule=pelal_rule, doc="pellet shipments from alzada")


# ── Accounting equations ──────────────────────────────────────────────────────
def acost_rule(model):
    return model.cost == model.recurrent + model.transport + model.sh * (model.imp - model.exp)


model.acost = pyo.Constraint(rule=acost_rule, doc="accounting: total cost")


def arec_rule(model):
    return model.recurrent == (
        sum(g(mc, p) * model.zm[p, i] for p in pm for i in im if (p, i) in pmpos and g(mc, p) != 0)
        + sum(pd[c] * model.ur[c, r] for c in craw for r in ir if (c, r) in crposn)
        + sum(pd[c] * model.us[c, s] for c in craw for s in iss if (c, s) in csposn)
    ) / 1000.0


model.arec = pyo.Constraint(rule=arec_rule, doc="accounting: recurrent cost")


def atrans_rule(model):
    t1 = sum(mumr[(i, r)] * model.xm[c, i, r]
             for c in cmr for i in im for r in ir
             if (c, i) in cmposp and xm_has(c, i, r) and (c, r) in crposn and (i, r) in mumr)
    t2 = sum(mums[(i, s)] * model.xm[c, i, s]
             for c in cms for i in im for s in iss
             if (c, i) in cmposp and (c, s) in csposn and xm_has(c, i, s) and (i, s) in mums)
    t3 = sum(murs[(r, s)] * model.xr[c, r, s]
             for c in crs for r in ir for s in iss
             if (c, r) in crposp and (c, s) in csposn and (r, s) in murs)
    t4 = sum(muss[(s, sp)] * model.xs[c, s, sp]
             for c in css for s in iss for sp in iss
             if (c, s) in csposp and (c, sp) in csposn and (s, sp) in muss)
    t5 = sum(musj[(s, jx)] * model.xf[c, s, jx]
             for c in cf for s in iss for jx in jj
             if (c, s) in csposp and (s, jx) in musj)
    t6 = sum(mupsr[s] * model.vs[c, s]
             for c in crv for s in iss if (c, s) in csposn and s in mupsr)
    t7 = sum(muspf[s] * model.e[c, s]
             for c in cf for s in iss if (c, s) in csposp and s in muspf)
    t8 = sum(mupj[jx] * model.vf[c, jx]
             for c in cf for jx in jj if jx in mupj)
    return model.transport == (t1 + t2 + t3 + t4 + t5 + t6 + t7 + t8) / 1000.0


model.atrans = pyo.Constraint(rule=atrans_rule, doc="accounting: transport cost")


def aimp_rule(model):
    return model.imp == (
        sum(pv[c] * model.vs[c, s] for c in crv for s in iss if (c, s) in csposn and c in pv)
        + sum(pv[c] * model.vf[c, jx] for c in cfv for jx in jj if c in pv)
    ) / 1000.0


model.aimp = pyo.Constraint(rule=aimp_rule, doc="accounting: import cost")


def aexp_rule(model):
    return model.exp == (
        sum(pe[c] * model.e[c, s] for c in ce for s in iss if (c, s) in csposp and c in pe)
    ) / 1000.0


model.aexp = pyo.Constraint(rule=aexp_rule, doc="accounting: export revenue")


# Objective: minimize total cost
model.obj = pyo.Objective(expr=model.cost, sense=pyo.minimize, doc="minimize total cost")
