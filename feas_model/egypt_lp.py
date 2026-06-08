# converted from gamslib egypt (EGYPT, SEQ=75)
#
# Egypt Agricultural Model. A linear program for irrigation-water investment
# planning. The "sqr(qs)" terms in the GAMS objective act only on the
# precomputed welfare-segment parameter qs(c,g), so the model is a plain LP.
#
# The raw GAMS data tables are stored in egypt_lp_data.json; the derived
# parameters (netcs, yld, qs, ws, beta, alpha, stran, ...) are reconstructed
# below exactly as the GAMS source computes them.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# OptiChat's normalizer flattens the sectioned JSON into flat top-level keys,
# converts pipe-keys ("i|j") into tuple keys, and lists-of-lists into
# tuples-of-tuples (used for the tuple-valued sets zr, sv, cnc).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── raw sets ──────────────────────────────────────────────────────────────────
C   = list(data["c"])
TM  = list(data["tm"])
R   = list(data["r"])
Z   = list(data["z"])
S   = list(data["s"])
NT  = list(data["nt"])
CT  = list(data["ct"])
CFG = list(data["cfg"])
CFD = list(data["cfd"])
G   = list(data["g"])
CUP = list(data["cup"])

ZR  = {tuple(t) for t in data["zr"]}     # (z, r)
SV  = {tuple(t) for t in data["sv"]}     # (s, c)
CNC = {tuple(t) for t in data["cnc"]}    # (c_aggregate, c_component)

# zone for each region (each region maps to exactly one zone in zr)
zone_of = {r: zz for (zz, r) in ZR}

# ── raw indexed params (as plain dicts, with missing entries absent) ──────────
demdat  = dict(data["demdat"])
agrreg  = dict(data["agrreg"])
regwagm = dict(data["regwagm"])
yieldp  = dict(data["yield"])
indprod = dict(data["indprod"])
feed    = dict(data["feed"])
cropdat = dict(data["cropdat"])
land    = dict(data["land"])
laborm  = dict(data["laborm"])
water   = dict(data["water"])
tractor = dict(data["tractor"])
veg     = dict(data["veg"])
upbnds  = dict(data["upbnds"])
tranc   = dict(data["tranc"])
los     = dict(data["los"])
tlimit  = dict(data["tlimit"])
con     = dict(data["con"])

# ── scalars ───────────────────────────────────────────────────────────────────
high   = float(data["high"])
low    = float(data["low"])
day    = float(data["day"])
pnfl   = float(data["pnfl"])
ppfl   = float(data["ppfl"])
ptrl   = 1.5     # cost of one tractor hour (local price)
grdf   = float(data["grdf"])
totmd  = float(data["totmd"])
prnut  = float(data["prnut_val"])
waterlim = float(data["waterlim"])
prby = {"horse-bean": float(data["prby_horsebean"]), "rice": float(data["prby_rice"])}


def g0(d, *idx):
    """Look up a (possibly-missing) param value, returning 0.0 when absent."""
    key = idx[0] if len(idx) == 1 else tuple(idx)
    return float(d.get(key, 0.0))


# ── derived sets ──────────────────────────────────────────────────────────────
# cn(c) = crops sold in national market (have a domes-cons figure)
CN = [c for c in C if (c, "domes-cons") in demdat]
# cf(c) = fodder crops (have a positive feed yield in some zone)
CF = [c for c in C if any((c, zz) in feed for zz in Z)]

# ── price / demand-curve preprocessing (GAMS lines 651-667) ───────────────────
price = {c: g0(demdat, c, "base-p")   for c in CN}
pe    = {c: g0(demdat, c, "export-p") for c in C}
pm    = {c: g0(demdat, c, "import-p") for c in C}

beta, alpha, pmax, pmin, qmin, qmax, incr = {}, {}, {}, {}, {}, {}, {}
qs, ws = {}, {}
ncardg = len(G)
for c in CN:
    base = g0(demdat, c, "base-p")
    dom  = g0(demdat, c, "domes-cons")
    elas = g0(demdat, c, "elas")
    beta[c]  = base / dom / elas
    alpha[c] = base - beta[c] * dom
    pmax[c]  = price[c] * high
    pmin[c]  = price[c] * low
    qmin[c]  = (pmax[c] - alpha[c]) / beta[c]
    qmax[c]  = (pmin[c] - alpha[c]) / beta[c]
    incr[c]  = (qmax[c] - qmin[c]) / (ncardg - 1)
    for gi, gname in enumerate(G):       # ord(g) = gi+1
        q = qmin[c] + incr[c] * gi
        qs[(c, gname)] = q
        ws[(c, gname)] = alpha[c] * q + 0.5 * beta[c] * q * q

# ── stran(r,rp) = tranc(r,rp) (GAMS line 627) ─────────────────────────────────
stran = dict(tranc)

# ── netcs(c,r) (GAMS lines 702-705): defined only where yield(c,r) exists ─────
netcs = {}
for c in C:
    for r in R:
        if (c, r) not in yieldp:
            continue
        zz = zone_of[r]
        val = (g0(tractor, c, zz) * ptrl
               + g0(cropdat, c, "misc") + g0(cropdat, c, "pest")
               + g0(cropdat, c, "n-fer") * pnfl + ppfl * g0(cropdat, c, "p-fer")
               - g0(indprod, c, r) * prby.get(c, 0.0))
        netcs[(c, r)] = val

# ── yld(c,c,r) (GAMS lines 707-710) ───────────────────────────────────────────
# Diagonal yields, veg-oil conversions, and aggregate-crop reclassification.
yld = {}
for c in C:
    for r in R:
        if (c, r) in yieldp:
            yld[(c, c, r)] = yieldp[(c, r)]
# veg-oil row: yld("veg-oil", c, r) = yield(c,r)*con(c)
for c in C:
    if c in con:
        for r in R:
            if (c, r) in yieldp:
                yld[("veg-oil", c, r)] = yieldp[(c, r)] * con[c]
# aggregate crops: yld(cn, c, r) = yield(c,r) for (cn,c) in cnc
for (cagg, ccomp) in CNC:
    for r in R:
        if (ccomp, r) in yieldp:
            yld[(cagg, ccomp, r)] = yieldp[(ccomp, r)]
# zero out the diagonal of any component crop that is folded into an aggregate
folded = {ccomp for (_, ccomp) in CNC}
for ccomp in folded:
    for r in R:
        yld[(ccomp, ccomp, r)] = 0.0

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Egypt Agricultural Model - consumer/producer surplus maximization")

# Sets (Pyomo) -- kept for component visibility
model.c   = pyo.Set(initialize=C, doc="crops")
model.tm  = pyo.Set(initialize=TM, doc="time periods (months)")
model.r   = pyo.Set(initialize=R, doc="regions by barrages")
model.cn  = pyo.Set(initialize=CN, doc="crops sold in national market")
model.cf  = pyo.Set(initialize=CF, doc="fodder crops")
model.ct  = pyo.Set(initialize=CT, doc="transportable fodder crops")
model.nt  = pyo.Set(initialize=NT, doc="livestock nutrients")
model.s   = pyo.Set(initialize=S, doc="agricultural seasons")
model.g   = pyo.Set(initialize=G, doc="welfare-curve grid points")

# ── mutable Params (raw data exposed for OptiChat) ────────────────────────────
# Each indexed Param is declared over an explicit index Set built from its keys
# so Pyomo treats it as an indexed (not scalar) component.
def _pset(name, keys):
    s = pyo.Set(dimen=(len(next(iter(keys))) if keys and isinstance(next(iter(keys)), tuple) else 1),
                initialize=list(keys), doc="index set for " + name)
    setattr(model, name + "_idx", s)
    return s

model.yield_p = pyo.Param(_pset("yield_p", yieldp.keys()), initialize=yieldp,
                          within=pyo.Reals, mutable=True, default=0.0, doc="crop yield (tons per feddan)")
model.land    = pyo.Param(_pset("land", land.keys()), initialize=land,
                          within=pyo.NonNegativeReals, mutable=True, default=0.0, doc="land requirements by crop")
model.laborm  = pyo.Param(_pset("laborm", laborm.keys()), initialize=laborm,
                          within=pyo.NonNegativeReals, mutable=True, default=0.0, doc="labor requirements (man-days)")
model.water   = pyo.Param(_pset("water", water.keys()), initialize=water,
                          within=pyo.NonNegativeReals, mutable=True, default=0.0, doc="water requirements (cm)")
model.veg     = pyo.Param(_pset("veg", veg.keys()), initialize=veg,
                          within=pyo.NonNegativeReals, mutable=True, default=0.0, doc="vegetable area upper limits")
model.feed    = pyo.Param(_pset("feed", feed.keys()), initialize=feed,
                          within=pyo.NonNegativeReals, mutable=True, default=0.0, doc="by-product feed yield")
model.cropdat = pyo.Param(_pset("cropdat", cropdat.keys()), initialize=cropdat,
                          within=pyo.Reals, mutable=True, default=0.0, doc="seed/protein/starch/misc/pest/fertilizer data")
model.agrreg  = pyo.Param(_pset("agrreg", agrreg.keys()), initialize=agrreg,
                          within=pyo.NonNegativeReals, mutable=True, default=0.0, doc="regional agricultural data")
model.regwagm = pyo.Param(_pset("regwagm", regwagm.keys()), initialize=regwagm,
                          within=pyo.NonNegativeReals, mutable=True, default=0.0, doc="average wages for men (le per day)")
model.netcs   = pyo.Param(_pset("netcs", netcs.keys()), initialize=netcs,
                          within=pyo.Reals, mutable=True, default=0.0, doc="cost of crop inputs excl. labor")
model.yld     = pyo.Param(_pset("yld", yld.keys()), initialize=yld,
                          within=pyo.Reals, mutable=True, default=0.0, doc="adjusted crop-yield matrix")
model.qs      = pyo.Param(_pset("qs", qs.keys()), initialize=qs,
                          within=pyo.Reals, mutable=True, default=0.0, doc="welfare-segment quantities")
model.ws      = pyo.Param(_pset("ws", ws.keys()), initialize=ws,
                          within=pyo.Reals, mutable=True, default=0.0, doc="welfare-segment values")
model.pe      = pyo.Param(_pset("pe", pe.keys()), initialize=pe,
                          within=pyo.Reals, mutable=True, default=0.0, doc="commodity export prices (le)")
model.pm      = pyo.Param(_pset("pm", pm.keys()), initialize=pm,
                          within=pyo.Reals, mutable=True, default=0.0, doc="commodity import prices (le)")
model.los     = pyo.Param(_pset("los", los.keys()), initialize=los,
                          within=pyo.NonNegativeReals, mutable=True, default=0.0, doc="commodity storage-loss factors")
model.stran   = pyo.Param(_pset("stran", stran.keys()), initialize=stran,
                          within=pyo.Reals, mutable=True, default=0.0, doc="transfer cost per ton between regions")
model.grdf    = pyo.Param(initialize=grdf, within=pyo.NonNegativeReals, mutable=True,
                          doc="green-to-dry fodder ratio")
model.totmd   = pyo.Param(initialize=totmd, within=pyo.Reals, mutable=True,
                          doc="value of meat and milk (le)")
model.prnut   = pyo.Param(initialize=prnut, within=pyo.NonNegativeReals, mutable=True,
                          doc="cost of artificial protein/starch per ton (le)")
model.day     = pyo.Param(initialize=day, within=pyo.NonNegativeReals, mutable=True,
                          doc="working days per month")
model.waterlim = pyo.Param(initialize=waterlim, within=pyo.NonNegativeReals, mutable=True,
                           doc="total available water (cubic meters)")

# ── Variables ─────────────────────────────────────────────────────────────────
model.xcrop   = pyo.Var(R, C, domain=pyo.NonNegativeReals, doc="cropping activities (1000 feddans)")
model.imports = pyo.Var(C, domain=pyo.NonNegativeReals, doc="national imports (1000 tons)")
model.exports = pyo.Var(C, domain=pyo.NonNegativeReals, doc="national exports (1000 tons)")
model.natq    = pyo.Var(C, G, domain=pyo.NonNegativeReals, doc="domestic consumption segments")
model.anut    = pyo.Var(NT, R, domain=pyo.NonNegativeReals, doc="livestock nutrition (protein/starch)")
model.sales   = pyo.Var(C, domain=pyo.NonNegativeReals, doc="gross production of a commodity")
# trans(c,r,rp): straw transferred between regions (only c in ct, r/rp with tranc link)
TRANS_IDX = [(c, r, rp) for c in CT for (r, rp) in tranc.keys() if r != rp]
model.trans   = pyo.Var(TRANS_IDX, domain=pyo.NonNegativeReals, doc="straw transfered (1000 tons)")
model.fodder  = pyo.Var(R, C, domain=pyo.NonNegativeReals, doc="straw from by-products (1000 tons)")
model.tlab    = pyo.Var(R, TM, domain=pyo.NonNegativeReals, doc="temporary labor (1000 man-months)")
model.flab    = pyo.Var(R, TM, domain=pyo.NonNegativeReals, doc="family labor (1000 man-months)")
model.cps     = pyo.Var(domain=pyo.Reals, doc="consumer and producer surplus (1000 le)")

# ── Variable bounds (GAMS lines 815-818) ──────────────────────────────────────
# xcrop.up(r,cup) = upbnds(cup,r)
for c in CUP:
    for r in R:
        if (c, r) in upbnds:
            model.xcrop[r, c].setub(upbnds[(c, r)])
# imports.up / exports.up = tlimit (missing table entry => 0 in GAMS, i.e. the
# commodity cannot be traded; listed "inf" entries become an effectively-free bound)
for c in C:
    model.imports[c].setub(tlimit.get((c, "imports"), 0.0))
    model.exports[c].setub(tlimit.get((c, "exports"), 0.0))
# flab.up(r,tm) = agrreg(r,"farmers")*0.4
for r in R:
    for tmm in TM:
        model.flab[r, tmm].setub(g0(agrreg, r, "farmers") * 0.4)

# ── Equations ─────────────────────────────────────────────────────────────────
# comb(cn): sales(cn) <= sum((r,c), xcrop(r,c)*yld(cn,c,r))
def comb_rule(m, cn):
    return m.sales[cn] <= sum(
        m.xcrop[r, c] * m.yld[cn, c, r]
        for r in R for c in C if (cn, c, r) in yld)
model.comb = pyo.Constraint(model.cn, rule=comb_rule, doc="commodity balance")

# demb(cn): sales(cn)*(1-los(cn)) + imports(cn) = exports(cn) + sum(g, qs(cn,g)*natq(cn,g))
def demb_rule(m, cn):
    return (m.sales[cn] * (1 - g0(los, cn)) + m.imports[cn]
            == m.exports[cn] + sum(m.qs[cn, g] * m.natq[cn, g] for g in G))
model.demb = pyo.Constraint(model.cn, rule=demb_rule, doc="demand balance")

# conv(cn): sum(g, natq(cn,g)) = 1
def conv_rule(m, cn):
    return sum(m.natq[cn, g] for g in G) == 1
model.conv = pyo.Constraint(model.cn, rule=conv_rule, doc="convexity constraints")

# landb(r,tm): sum((c,z)$zr(z,r), xcrop(r,c)*land(c,z,tm)) <= agrreg(r,"area")
def landb_rule(m, r, tmm):
    zz = zone_of[r]
    return sum(m.xcrop[r, c] * land[(c, zz, tmm)]
               for c in C if (c, zz, tmm) in land) <= g0(agrreg, r, "area")
model.landb = pyo.Constraint(R, TM, rule=landb_rule, doc="land balances")

# labbal(r,tm): sum((c,z)$zr(z,r), xcrop(r,c)*laborm(c,z,tm))/day <= tlab + flab
def labbal_rule(m, r, tmm):
    zz = zone_of[r]
    lhs = sum(m.xcrop[r, c] * laborm[(c, zz, tmm)]
              for c in C if (c, zz, tmm) in laborm) / day
    return lhs <= m.tlab[r, tmm] + m.flab[r, tmm]
model.labbal = pyo.Constraint(R, TM, rule=labbal_rule, doc="labor balance")

# waterb: sum over r,c,tm,z$zr of xcrop(r,c)*water(c,z,tm) <= waterlim
def waterb_rule(m):
    return sum(m.xcrop[r, c] * water[(c, zone_of[r], tmm)]
               for r in R for c in C for tmm in TM
               if (c, zone_of[r], tmm) in water) <= waterlim
model.waterb = pyo.Constraint(rule=waterb_rule, doc="water constraint")

# vegetb(s,r): sum(c$sv(s,c), xcrop(r,c)) <= veg(r,s)*1.5
def vegetb_rule(m, ss, r):
    return sum(m.xcrop[r, c] for c in C if (ss, c) in SV) <= g0(veg, r, ss) * 1.5
model.vegetb = pyo.Constraint(model.s, R, rule=vegetb_rule, doc="vegetables constraints")

# fodb(r,cf): fodder(r,cf) = xcrop(r,cf)*sum(z$zr, feed(cf,z))
#            + [sum(rp$tranc(r,rp), trans(cf,rp,r)-trans(cf,r,rp))]$ct(cf)
def fodb_rule(m, r, cf):
    zz = zone_of[r]
    rhs = m.xcrop[r, cf] * g0(feed, cf, zz)
    if cf in CT:
        for (ri, rp) in tranc.keys():
            if ri == r and ri != rp:
                # +trans(cf,rp,r) - trans(cf,r,rp)
                if (cf, rp, r) in model.trans:
                    rhs += m.trans[cf, rp, r]
                if (cf, r, rp) in model.trans:
                    rhs -= m.trans[cf, r, rp]
    return m.fodder[r, cf] == rhs
model.fodb = pyo.Constraint(R, CF, rule=fodb_rule, doc="fodder balance")

# nutb(nt,r): sum(cf, fodder(r,cf)*cropdat(cf,nt)*.01) + anut(nt,r) >= agrreg(r,nt)
def nutb_rule(m, nt, r):
    return (sum(m.fodder[r, cf] * g0(cropdat, cf, nt) * 0.01 for cf in CF)
            + m.anut[nt, r] >= g0(agrreg, r, nt))
model.nutb = pyo.Constraint(model.nt, R, rule=nutb_rule, doc="nutrition balance")

# gfodb(r): sum(cfg, fodder(r,cfg))*grdf <= sum(cfd, fodder(r,cfd))
def gfodb_rule(m, r):
    return (sum(m.fodder[r, c] for c in CFG) * grdf
            <= sum(m.fodder[r, c] for c in CFD))
model.gfodb = pyo.Constraint(R, rule=gfodb_rule, doc="straw balance constraints")

# obj.. cps = totmd + sum(cn, sum(g, natq*ws) + exports*pe - imports*pm)
#           - sum((ct,r,rp), trans*stran) - sum((r,c), xcrop*netcs)
#           - sum((r,nt), anut*prnut) - sum((r,tm), (flab+2*tlab)*regwagm*day)
def obj_def_rule(m):
    welfare = sum(
        sum(m.natq[cn, g] * m.ws[cn, g] for g in G)
        + m.exports[cn] * g0(pe, cn) - m.imports[cn] * g0(pm, cn)
        for cn in CN)
    transcost = sum(m.trans[c, r, rp] * g0(stran, r, rp)
                    for (c, r, rp) in TRANS_IDX)
    cropcost = sum(m.xcrop[r, c] * netcs[(c, r)]
                   for r in R for c in C if (c, r) in netcs)
    nutcost = sum(m.anut[nt, r] * prnut for nt in NT for r in R)
    labcost = sum((m.flab[r, tmm] + 2 * m.tlab[r, tmm]) * g0(regwagm, r, tmm) * day
                  for r in R for tmm in TM)
    return m.cps == totmd + welfare - transcost - cropcost - nutcost - labcost
model.obj_def = pyo.Constraint(rule=obj_def_rule, doc="objective definition (cps)")

# ── Objective ─────────────────────────────────────────────────────────────────
model.obj = pyo.Objective(expr=model.cps, sense=pyo.maximize,
                          doc="maximize consumer and producer surplus")
