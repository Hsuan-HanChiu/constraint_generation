# converted from gamslib alum (ALUM, SEQ=31) — World Aluminum Model, MIP
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "i|j": value → (i, j): value).
# Multi-dim membership sets are stored as lists of pipe-joined tuples.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────


def _tuples(key):
    """Membership set stored as list of 'a|b|...' strings -> list of tuples."""
    return [tuple(s.split("|")) for s in data[key]]


# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="World Aluminum Model - minimize total cost (no levies/tariffs)")

# Sets -------------------------------------------------------------------------
model.i = pyo.Set(initialize=data["i"], doc="mining regions")
model.r = pyo.Set(initialize=data["r"], doc="producing regions")
model.j = pyo.Set(initialize=data["j"], doc="marketing areas")
model.c = pyo.Set(initialize=data["c"], doc="commodities")
model.cm = pyo.Set(initialize=data["cm"], doc="bauxites")
model.ci = pyo.Set(initialize=data["ci"], doc="intermediates (alumina)")
model.cf = pyo.Set(initialize=data["cf"], doc="final products (aluminum)")
model.cl = pyo.Set(initialize=data["cl"], doc="electricity")
model.p = pyo.Set(initialize=data["p"], doc="refining/smelting processes")
model.m = pyo.Set(initialize=data["m"], doc="productive units")
model.mr = pyo.Set(initialize=data["mr"], doc="refining units")
model.ms = pyo.Set(initialize=data["ms"], doc="smelting units")
model.seg = pyo.Set(initialize=data["seg"], doc="investment segments")
model.l = pyo.Set(initialize=data["l"], doc="electricity supply types")

# three-way grouping derived from fr keys
_f = sorted({t[0] for t in _tuples("fr")})
model.f = pyo.Set(initialize=_f, doc="three way grouping")

# multi-dim membership sets (stored as tuple-lists)
model.cpospi = pyo.Set(dimen=2, initialize=_tuples("cpospi"),
                       doc="(mine, bauxite) production possibilities")
model.fr = pyo.Set(dimen=2, initialize=_tuples("fr"), doc="grouping -> producing region")
model.fi = pyo.Set(dimen=2, initialize=_tuples("fi"), doc="grouping -> mining region")
model.fj = pyo.Set(dimen=2, initialize=_tuples("fj"), doc="grouping -> market")

# Parameters -------------------------------------------------------------------
model.interval = pyo.Param(initialize=data["interval"], mutable=True, within=pyo.Reals,
                           doc="time interval for mine resource constraint")
model.utm = pyo.Param(initialize=data["utm"], mutable=True, within=pyo.Reals,
                      doc="capacity utilization for mines")
model.sigma = pyo.Param(initialize=data["sigma"], mutable=True, within=pyo.Reals,
                        doc="capital recovery factor")
model.gamma = pyo.Param(initialize=data["gamma"], mutable=True, within=pyo.Reals,
                        doc="complement of actual trade flow")
model.pl = pyo.Param(initialize=data["pl"], mutable=True, within=pyo.Reals,
                     doc="world market price of aluminum")

model.a = pyo.Param(model.c, model.p, initialize=data["a"], default=0.0,
                    mutable=True, within=pyo.Reals, doc="input-output coefficients")
model.b = pyo.Param(model.m, model.p, initialize=data["b"], default=0.0,
                    mutable=True, within=pyo.Reals, doc="capacity utilization")
model.d = pyo.Param(model.j, initialize=data["d"], default=0.0,
                    mutable=True, within=pyo.Reals, doc="aluminum demand (low forecast)")
model.nmaa2000 = pyo.Param(model.r, initialize=data["nmaa2000"], default=0.0,
                           mutable=True, within=pyo.Reals, doc="non-metal alumina demand")
model.nmba2000 = pyo.Param(model.i, initialize=data["nmba2000"], default=0.0,
                           mutable=True, within=pyo.Reals, doc="non-metal bauxite demand")
model.zmbar = pyo.Param(model.i, initialize=data["zmbar"], default=0.0,
                        mutable=True, within=pyo.Reals, doc="maximum mine output level")
model.capm = pyo.Param(model.i, initialize=data["capm"], default=0.0,
                       mutable=True, within=pyo.Reals, doc="existing+committed mine capacity")
model.capr = pyo.Param(model.r, model.m, initialize=data["capr"], default=0.0,
                       mutable=True, within=pyo.Reals, doc="refinery/smelter capacity")
model.utr = pyo.Param(model.m, initialize=data["utr"], default=0.0,
                      mutable=True, within=pyo.Reals, doc="capacity utilization for refineries")
model.sbm = pyo.Param(model.i, model.seg, initialize=data["sbm"], default=0.0,
                      mutable=True, within=pyo.Reals, doc="mine plant size at segments")
model.sbr = pyo.Param(model.m, model.seg, model.r, initialize=data["sbr"], default=0.0,
                      mutable=True, within=pyo.Reals, doc="refinery/smelter plant size at segments")
model.om = pyo.Param(model.i, initialize=data["om"], default=0.0,
                     mutable=True, within=pyo.Reals, doc="operating cost at mines")
model.ors = pyo.Param(model.r, model.p, initialize=data["ors"], default=0.0,
                      mutable=True, within=pyo.Reals, doc="operating costs at refineries/smelters")
model.muf = pyo.Param(model.r, model.j, initialize=data["muf"], default=0.0,
                      mutable=True, within=pyo.Reals, doc="transport cost: final")
model.mui = pyo.Param(model.r, model.r, initialize=data["mui"], default=0.0,
                      mutable=True, within=pyo.Reals, doc="transport cost: interplant")
model.mur = pyo.Param(model.i, model.r, initialize=data["mur"], default=0.0,
                      mutable=True, within=pyo.Reals, doc="transport cost (mine->refinery)")
model.omegam = pyo.Param(model.i, model.seg, initialize=data["omegam"], default=0.0,
                         mutable=True, within=pyo.Reals, doc="fixed investment cost: mines")
model.omegar = pyo.Param(model.m, model.seg, model.r, initialize=data["omegar"], default=0.0,
                         mutable=True, within=pyo.Reals, doc="fixed investment cost: refineries/smelters")
model.prelec = pyo.Param(model.r, model.l, initialize=data["prelec"], default=0.0,
                         mutable=True, within=pyo.Reals, doc="electricity price")
model.ubar = pyo.Param(model.r, model.l, initialize=data["ubar"], default=0.0,
                       mutable=True, within=pyo.Reals, doc="electricity supply upper bound")

# convenience membership lookups (built from the tuple sets, scenario-invariant)
_cpospi = set(model.cpospi)
_prelec_pos = {(r, l) for (r, l) in model.prelec if pyo.value(model.prelec[r, l]) != 0}

# Variables --------------------------------------------------------------------
model.xf = pyo.Var(model.r, model.j, domain=pyo.NonNegativeReals, doc="shipment: final products")
model.xi = pyo.Var(model.r, model.r, domain=pyo.NonNegativeReals, doc="shipment: intermediates")
model.xm = pyo.Var(model.c, model.i, model.r, domain=pyo.NonNegativeReals, doc="shipment: bauxites")
model.z = pyo.Var(model.p, model.r, domain=pyo.NonNegativeReals, doc="process level")
model.zm = pyo.Var(model.cm, model.i, domain=pyo.NonNegativeReals, doc="mining output level")
model.hm = pyo.Var(model.i, domain=pyo.NonNegativeReals, doc="linear expansion: mines")
model.hr = pyo.Var(model.r, model.m, domain=pyo.NonNegativeReals, doc="linear expansion: refinery/smelter")
model.sm = pyo.Var(model.seg, model.i, domain=pyo.NonNegativeReals, doc="fixed expansion: mines")
model.sr = pyo.Var(model.m, model.seg, model.r, domain=pyo.NonNegativeReals, doc="fixed expansion: refinery/smelter")
model.ym = pyo.Var(model.i, domain=pyo.Binary, doc="binary expansion: mines")
model.yr = pyo.Var(model.r, model.m, domain=pyo.Binary, doc="binary expansion: refineries/smelters")


# u(l,r) electricity supply with upper bounds from ubar; el-hicost is +inf
def _u_bounds(model, l, r):
    if l == "el-hicost":
        return (0, None)
    ub = pyo.value(model.ubar[r, l])
    return (0, ub)


model.u = pyo.Var(model.l, model.r, bounds=_u_bounds, domain=pyo.NonNegativeReals,
                  doc="electricity supply")

# accounting variables (free)
model.phiom = pyo.Var(domain=pyo.Reals, doc="operating cost: mines")
model.phior = pyo.Var(domain=pyo.Reals, doc="operating cost: refineries/smelters")
model.phit = pyo.Var(domain=pyo.Reals, doc="cost: transport")
model.phikm = pyo.Var(domain=pyo.Reals, doc="investment cost: mines")
model.phikr = pyo.Var(domain=pyo.Reals, doc="investment cost: refineries/smelters")
model.phi4 = pyo.Var(domain=pyo.Reals, doc="total cost without levies or tariffs")


# Constraints ------------------------------------------------------------------
# mbm(cm,i)$cpospi(i,cm): zm =g= sum(r, xm) + nmba2000
def mbm_rule(model, cm, i):
    if (i, cm) not in _cpospi:
        return pyo.Constraint.Skip
    return model.zm[cm, i] >= sum(model.xm[cm, i, r] for r in model.r) + model.nmba2000[i]


model.mbm = pyo.Constraint(model.cm, model.i, rule=mbm_rule, doc="material balance: mines")


# mbr(c,r): sum_p a*z + sum_i xm$(cm&cpospi) + sum_rp xi$ci + sum_l u$(prelec&cl)
#           =g= sum_j xf$cf + sum_rp xi$ci + nmaa2000$ci
def mbr_rule(model, c, r):
    lhs = sum(model.a[c, p] * model.z[p, r] for p in model.p)
    if c in model.cm:
        lhs += sum(model.xm[c, i, r] for i in model.i if (i, c) in _cpospi)
    if c in model.ci:
        lhs += sum(model.xi[rp, r] for rp in model.r)
    if c in model.cl:
        lhs += sum(model.u[l, r] for l in model.l if (r, l) in _prelec_pos)
    rhs = 0
    if c in model.cf:
        rhs += sum(model.xf[r, j] for j in model.j)
    if c in model.ci:
        rhs += sum(model.xi[r, rp] for rp in model.r) + model.nmaa2000[r]
    return lhs >= rhs


model.mbr = pyo.Constraint(model.c, model.r, rule=mbr_rule, doc="material balance: refineries/smelters")


# fdb(j): sum_r xf =g= d
def fdb_rule(model, j):
    return sum(model.xf[r, j] for r in model.r) >= model.d[j]


model.fdb = pyo.Constraint(model.j, rule=fdb_rule, doc="final demand balance")


# res(cm,i)$cpospi: interval*zm =l= zmbar
def res_rule(model, cm, i):
    if (i, cm) not in _cpospi:
        return pyo.Constraint.Skip
    return model.interval * model.zm[cm, i] <= model.zmbar[i]


model.res = pyo.Constraint(model.cm, model.i, rule=res_rule, doc="bauxite reserve constraint")


# ccm(i): sum_cm$cpospi zm =l= utm*(capm + hm)
def ccm_rule(model, i):
    return sum(model.zm[cm, i] for cm in model.cm if (i, cm) in _cpospi) <= \
        model.utm * (model.capm[i] + model.hm[i])


model.ccm = pyo.Constraint(model.i, rule=ccm_rule, doc="capacity constraint: mines")


# ccr(r,m): sum_p b*z =l= utr*(capr + hr)
def ccr_rule(model, r, m):
    return sum(model.b[m, p] * model.z[p, r] for p in model.p) <= \
        model.utr[m] * (model.capr[r, m] + model.hr[r, m])


model.ccr = pyo.Constraint(model.r, model.m, rule=ccr_rule, doc="capacity constraint: refineries/smelters")


# i1m(i): hm =e= sum_seg sbm*sm
def i1m_rule(model, i):
    return model.hm[i] == sum(model.sbm[i, seg] * model.sm[seg, i] for seg in model.seg)


model.i1m = pyo.Constraint(model.i, rule=i1m_rule, doc="definition of h: mines")


# i1r(r,m): hr =e= sum_seg sbr*sr
def i1r_rule(model, r, m):
    return model.hr[r, m] == sum(model.sbr[m, seg, r] * model.sr[m, seg, r] for seg in model.seg)


model.i1r = pyo.Constraint(model.r, model.m, rule=i1r_rule, doc="definition of h: refineries/smelters")


# i2m(i): ym =e= sum_seg sm
def i2m_rule(model, i):
    return model.ym[i] == sum(model.sm[seg, i] for seg in model.seg)


model.i2m = pyo.Constraint(model.i, rule=i2m_rule, doc="convex combination 0-1: mines")


# i2r(r,m): yr =e= sum_seg sr
def i2r_rule(model, r, m):
    return model.yr[r, m] == sum(model.sr[m, seg, r] for seg in model.seg)


model.i2r = pyo.Constraint(model.r, model.m, rule=i2r_rule, doc="convex combination 0-1: refineries/smelters")


# tba(f): sum((cm,i,r)$(fr&cpospi), xm$fi - gamma*xm) =g= 0
_fr = set(model.fr)
_fi = set(model.fi)
_fj = set(model.fj)


def tba_rule(model, f):
    expr = 0
    for cm in model.cm:
        for i in model.i:
            if (i, cm) not in _cpospi:
                continue
            for r in model.r:
                if (f, r) not in _fr:
                    continue
                term = -model.gamma * model.xm[cm, i, r]
                if (f, i) in _fi:
                    term += model.xm[cm, i, r]
                expr += term
    return expr >= 0


model.tba = pyo.Constraint(model.f, rule=tba_rule, doc="trade restrictions: bauxite")


# taa(f): (1-gamma)*sum((ci,r)$fr, -a(ci,smelting)*z(smelting,r))
#         =g= sum((r,rp)$fr(f,rp), xi(r,rp)$(not fr(f,r)))
def taa_rule(model, f):
    lhs = (1 - model.gamma) * sum(
        -model.a[ci, "smelting"] * model.z["smelting", r]
        for ci in model.ci for r in model.r if (f, r) in _fr
    )
    rhs = sum(
        model.xi[r, rp]
        for r in model.r for rp in model.r
        if (f, rp) in _fr and (f, r) not in _fr
    )
    return lhs >= rhs


model.taa = pyo.Constraint(model.f, rule=taa_rule, doc="trade restrictions: alumina")


# tal(f): sum((r,j)$fj, xf$fr - gamma*xf) =g= 0
def tal_rule(model, f):
    expr = 0
    for r in model.r:
        for j in model.j:
            if (f, j) not in _fj:
                continue
            term = -model.gamma * model.xf[r, j]
            if (f, r) in _fr:
                term += model.xf[r, j]
            expr += term
    return expr >= 0


model.tal = pyo.Constraint(model.f, rule=tal_rule, doc="trade restrictions: aluminum")


# aom: phiom =e= sum((cm,i)$cpospi, om*zm)/1000
def aom_rule(model):
    return model.phiom == sum(
        model.om[i] * model.zm[cm, i]
        for cm in model.cm for i in model.i if (i, cm) in _cpospi
    ) / 1000


model.aom = pyo.Constraint(rule=aom_rule, doc="accounting: mine operating costs")


# aor: phior =e= (sum((r,p), ors*z) + sum((r,l), prelec*u))/1000
def aor_rule(model):
    return model.phior == (
        sum(model.ors[r, p] * model.z[p, r] for r in model.r for p in model.p)
        + sum(model.prelec[r, l] * model.u[l, r] for r in model.r for l in model.l)
    ) / 1000


model.aor = pyo.Constraint(rule=aor_rule, doc="accounting: refinery/smelter operating costs")


# at: phit =e= sum(r, sum(j, muf*xf) + sum(rp, mui*xi) + sum((cm,i)$cpospi, mur*xm))/1000
def at_rule(model):
    return model.phit == sum(
        sum(model.muf[r, j] * model.xf[r, j] for j in model.j)
        + sum(model.mui[r, rp] * model.xi[r, rp] for rp in model.r)
        + sum(model.mur[i, r] * model.xm[cm, i, r]
              for cm in model.cm for i in model.i if (i, cm) in _cpospi)
        for r in model.r
    ) / 1000


model.at = pyo.Constraint(rule=at_rule, doc="accounting: transport cost")


# akm: phikm =e= sigma*sum((seg,i), omegam*sm)
def akm_rule(model):
    return model.phikm == model.sigma * sum(
        model.omegam[i, seg] * model.sm[seg, i] for seg in model.seg for i in model.i
    )


model.akm = pyo.Constraint(rule=akm_rule, doc="accounting: mine investments")


# akr: phikr =e= sigma*sum((seg,r,m), omegar*sr)
def akr_rule(model):
    return model.phikr == model.sigma * sum(
        model.omegar[m, seg, r] * model.sr[m, seg, r]
        for seg in model.seg for r in model.r for m in model.m
    )


model.akr = pyo.Constraint(rule=akr_rule, doc="accounting: refinery/smelter investments")


# a4: phi4 =e= phit + phiom + phior + phikm + phikr
def a4_rule(model):
    return model.phi4 == model.phit + model.phiom + model.phior + model.phikm + model.phikr


model.a4 = pyo.Constraint(rule=a4_rule, doc="accounting: total cost (no levies/tariffs)")

# Objective --------------------------------------------------------------------
model.obj = pyo.Objective(expr=model.phi4, sense=pyo.minimize,
                          doc="minimize total cost without levies or tariffs")
