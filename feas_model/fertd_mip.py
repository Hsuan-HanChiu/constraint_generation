# converted from gamslib fertd (FERTD, SEQ=14)
# EGYPT - Dynamic Fertilizer Model: investment planning MIP for the Egyptian
# fertilizer sector (Choksi, Meeraus & Stoutjesdijk, 1980).
#
# All GAMS preprocessing (derived parameters and the partially-reduced index
# possibility sets mpos/ppos/cposp/cposn/cposi/cposr/cposd/cpose/fpos/hpos)
# has been pre-computed and shipped in the JSON data file, so the Pyomo model
# below is a direct transcription of the *reduced* model1 that GAMS solves
# (solve model1 minimizing psi using mip).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "sulf-a-s|assiout": value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────


def _tuples(keys):
    """Convert a list of pipe-joined membership keys into a set of tuples."""
    return {tuple(k.split("|")) for k in keys}


# membership sets (used to control where variables/terms appear, as in GAMS $)
mpos = _tuples(data["mpos"])     # (m, i)
ppos = _tuples(data["ppos"])     # (p, i)
cposp = _tuples(data["cposp"])   # (c, i)  production possibilities
cposn = _tuples(data["cposn"])   # (c, i)  consumption possibilities
cposi = _tuples(data["cposi"])   # (c, ip, i) interplant (produce at ip, consume at i)
cposr = _tuples(data["cposr"])   # (c, i)  imported raw-material consumption
cposd = _tuples(data["cposd"])   # (c, i)  domestic purchase
cpose = _tuples(data["cpose"])   # (c, i)  export
fpos = _tuples(data["fpos"])     # (g, i)  upgrading
hpos = _tuples(data["hpos"])     # (m, i)  expansion

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Egypt Dynamic Fertilizer investment planning MIP")

# Sets
model.j = pyo.Set(initialize=data["j"], doc="demand regions")
model.i = pyo.Set(initialize=data["i"], doc="plant locations")
model.m = pyo.Set(initialize=data["m"], doc="productive units")
model.me = pyo.Set(initialize=data["me"], doc="productive units: expansion possibilities")
model.p = pyo.Set(initialize=data["p"], doc="processes")
model.g = pyo.Set(initialize=data["g"], doc="upgrading (conversion) activities")
model.cq = pyo.Set(initialize=data["cq"], doc="nutrients")
model.c = pyo.Set(initialize=data["c"], doc="commodities")
model.cf = pyo.Set(initialize=data["cf"], doc="final products")
model.ci = pyo.Set(initialize=data["ci"], doc="intermediate products")
model.cs = pyo.Set(initialize=data["cs"], doc="intermediates for shipment")
model.cr = pyo.Set(initialize=data["cr"], doc="raw materials")
model.cd = pyo.Set(initialize=data["cd"], doc="domestic materials")
model.q = pyo.Set(initialize=data["q"], doc="cost categories")
model.t = pyo.Set(initialize=data["t"], doc="time periods", ordered=True)

# Parameters
model.alpha = pyo.Param(model.c, model.cq, initialize=data["alpha"], default=0.0,
                        mutable=True, doc="nutrient content")
model.eta = pyo.Param(model.t, initialize=data["eta"], mutable=True,
                      doc="urea consumption restriction")
model.db = pyo.Param(model.cq, model.j, model.t, initialize=data["db"], default=0.0,
                     mutable=True, doc="demand in nutrients (1000 tpy)")
model.eb = pyo.Param(model.t, initialize=data["eb"], mutable=True,
                     doc="maximum export by product (1000 tpy)")
model.eh = pyo.Param(model.t, initialize=data["eh"], mutable=True,
                     doc="total export restriction (1000 tpy)")
model.muf = pyo.Param(model.i, model.j, initialize=data["muf"], default=0.0,
                      mutable=True, doc="transport cost (le/ton): final products")
model.mufv = pyo.Param(model.j, initialize=data["mufv"], default=0.0,
                       mutable=True, doc="transport cost (le/ton): imported final products")
model.mue = pyo.Param(model.i, initialize=data["mue"], default=0.0,
                      mutable=True, doc="transport cost (le/ton): exports")
model.mui = pyo.Param(model.i, model.i, initialize=data["mui"], default=0.0,
                      mutable=True, doc="transport cost (le/ton): interplant shipment")
model.mur = pyo.Param(model.i, initialize=data["mur"], default=0.0,
                      mutable=True, doc="transport cost (le/ton): imported raw materials")
model.a = pyo.Param(model.c, model.p, initialize=data["a"], default=0.0,
                    mutable=True, doc="input-output coefficients")
model.b = pyo.Param(model.m, model.p, initialize=data["b"], default=0.0,
                    mutable=True, doc="capacity utilization matrix")
model.oc = pyo.Param(model.cd, model.p, initialize=data["oc"], default=0.0,
                     mutable=True, doc="process operating cost for misc inputs")
model.pv = pyo.Param(model.c, initialize=data["pv"], default=0.0,
                     mutable=True, doc="import price (cif us$/ton 1975)")
model.pe = pyo.Param(model.cf, initialize=data["pe"], default=0.0,
                     mutable=True, doc="export price (us$/ton 1975)")
model.pd = pyo.Param(model.i, model.c, initialize=data["pd"], default=0.0,
                     mutable=True, doc="domestic raw material prices")
model.k = pyo.Param(model.m, model.i, initialize=data["k"], default=0.0,
                    mutable=True, doc="initial capacity (1000 tpy)")
model.omega = pyo.Param(model.m, initialize=data["omega"], default=0.0,
                        mutable=True, doc="fixed-charge portion of investment (mill le/yr)")
model.omegag = pyo.Param(model.g, initialize=data["omegag"], default=0.0,
                         mutable=True, doc="fixed-charge for capacity conversion (mill le/yr)")
model.nu = pyo.Param(model.m, initialize=data["nu"], default=0.0,
                     mutable=True, doc="variable portion of investment (mill le/1000 tpy)")
model.hb = pyo.Param(model.m, initialize=data["hb"], mutable=True,
                     doc="maximum capacity expansion (1000 tpy)")
model.f = pyo.Param(model.m, model.g, model.i, initialize=data["f"], default=0.0,
                    mutable=True, doc="capacity conversion (1000 tpy)")
model.delta = pyo.Param(model.t, initialize=data["delta"], mutable=True,
                        doc="discount factor")
model.ts = pyo.Param(model.t, model.t, initialize=data["ts"], default=0.0,
                     mutable=True, doc="time summation matrix")

# scalar params
model.nul = pyo.Param(initialize=data["nul"], mutable=True,
                      doc="variable charge portion for labor (units/1000 tpy)")
model.omegal = pyo.Param(initialize=data["omegal"], mutable=True,
                         doc="fixed-charge portion for labor (units)")
model.plab = pyo.Param(initialize=data["plab"], mutable=True,
                       doc="price of labor (le per man year)")
model.sigma = pyo.Param(initialize=data["sigma"], mutable=True,
                        doc="capital recovery factor")

# constants
OER = 0.4  # official exchange rate (le per us$)

# ── helper membership tests ───────────────────────────────────────────────────
def has_pv(c):
    return value(model.pv[c]) != 0.0

# ── Variables ─────────────────────────────────────────────────────────────────
# z(p,i,t): process level, defined where ppos(p,i)
z_index = [(p, i, t) for (p, i) in ppos for t in model.t]
model.z = pyo.Var(z_index, domain=pyo.NonNegativeReals, doc="process level (1000 tpy)")

# xf(c,i,j,t): domestic shipment of final products, where cposp(c,i)
xf_index = [(c, i, j, t) for (c, i) in cposp if c in model.cf
            for j in model.j for t in model.t]
model.xf = pyo.Var(xf_index, domain=pyo.NonNegativeReals,
                   doc="domestic shipment: final products (1000 tpy)")

# xi(c,i,ip,t): interplant shipment, produce at i consume at ip -> cposi(c,i,ip)
xi_index = [(c, i, ip, t) for (c, i, ip) in cposi for t in model.t]
model.xi = pyo.Var(xi_index, domain=pyo.NonNegativeReals,
                   doc="domestic shipment: intermediates (1000 tpy)")

# vf(c,j,t): imports of final products, where pv(c)
vf_index = [(c, j, t) for c in model.cf if has_pv(c)
            for j in model.j for t in model.t]
model.vf = pyo.Var(vf_index, domain=pyo.NonNegativeReals,
                   doc="imports: final products (1000 tpy)")

# vr(c,i,t): imports of raw materials, where cposr(c,i)
vr_index = [(c, i, t) for (c, i) in cposr for t in model.t]
model.vr = pyo.Var(vr_index, domain=pyo.NonNegativeReals,
                   doc="imports: raw materials (1000 tpy)")

# e(c,i,t): exports, where cpose(c,i); upper bound eb(t)
e_index = [(c, i, t) for (c, i) in cpose for t in model.t]
model.e = pyo.Var(e_index, domain=pyo.NonNegativeReals,
                  doc="exports (1000 tpy)")

# et(t): total exports in year; upper bound eh(t)
model.et = pyo.Var(model.t, domain=pyo.NonNegativeReals,
                   doc="total exports in year (1000 tpy)")

# u(c,i,t): domestic raw material purchases, where cposd(c,i)
u_index = [(c, i, t) for (c, i) in cposd for t in model.t]
model.u = pyo.Var(u_index, domain=pyo.NonNegativeReals,
                  doc="domestic raw material purchases (units)")

# h(m,i,t): capacity expansion, where hpos(m,i)
h_index = [(m, i, t) for (m, i) in hpos for t in model.t]
model.h = pyo.Var(h_index, domain=pyo.NonNegativeReals,
                  doc="capacity expansion (1000 tpy)")

# up(g,i,t): binary upgrading, where fpos(g,i)
up_index = [(g, i, t) for (g, i) in fpos for t in model.t]
model.up = pyo.Var(up_index, domain=pyo.Binary, doc="binary variable: upgrading")

# y(m,i,t): binary expansion, where hpos(m,i)  (all other y fixed to 0 in GAMS)
y_index = [(m, i, t) for (m, i) in hpos for t in model.t]
model.y = pyo.Var(y_index, domain=pyo.Binary, doc="binary variable: expansion")

model.psi = pyo.Var(domain=pyo.Reals, doc="total cost (discounted) (million le)")
model.psic = pyo.Var(model.q, model.t, domain=pyo.Reals,
                     doc="total cost components (undiscounted) (mill le/yr)")

# ── variable bounds / fixes (applied before solve in GAMS) ────────────────────
for (c, i, t) in e_index:
    model.e[c, i, t].setub(value(model.eb[t]))         # e.up = eb(t) on cpose
for t in model.t:
    model.et[t].setub(value(model.eh[t]))              # et.up = eh(t)
# y.fx(me,i,t)=0 then y.fx("phos-acid","abu-zaabal","1979-81")=1
for (m, i, t) in y_index:
    if (m, i, t) == ("phos-acid", "abu-zaabal", "1979-81"):
        model.y[m, i, t].fix(1)
    else:
        model.y[m, i, t].fix(0)

# ── helper accessors honoring sparse variable indices ─────────────────────────
def Z(p, i, t):
    return model.z[p, i, t] if (p, i, t) in model.z else 0.0

def XF(c, i, j, t):
    return model.xf[c, i, j, t] if (c, i, j, t) in model.xf else 0.0

def XI(c, i, ip, t):
    return model.xi[c, i, ip, t] if (c, i, ip, t) in model.xi else 0.0

def VF(c, j, t):
    return model.vf[c, j, t] if (c, j, t) in model.vf else 0.0

def VR(c, i, t):
    return model.vr[c, i, t] if (c, i, t) in model.vr else 0.0

def E(c, i, t):
    return model.e[c, i, t] if (c, i, t) in model.e else 0.0

def U(c, i, t):
    return model.u[c, i, t] if (c, i, t) in model.u else 0.0

def H(m, i, t):
    return model.h[m, i, t] if (m, i, t) in model.h else 0.0

def UP(g, i, t):
    return model.up[g, i, t] if (g, i, t) in model.up else 0.0

def Y(m, i, t):
    return model.y[m, i, t] if (m, i, t) in model.y else 0.0


# ── Constraints ───────────────────────────────────────────────────────────────
# mbd(cq,j,t): material balance demand
def mbd_rule(model, cq, j, t):
    lhs = sum(
        model.alpha[cf, cq] * (
            (VF(cf, j, t) if has_pv(cf) else 0.0)
            + sum(XF(cf, i, j, t) for i in model.i if (cf, i) in cposp)
        )
        for cf in model.cf
    )
    return lhs >= model.db[cq, j, t]
model.mbd = pyo.Constraint(model.cq, model.j, model.t, rule=mbd_rule,
                           doc="material balance: demand")

# mbu(j,t): urea consumption restriction
def mbu_rule(model, j, t):
    return (model.alpha["urea", "n"] * (
        VF("urea", j, t)
        + sum(XF("urea", i, j, t) for i in model.i if ("urea", i) in cposp)
    ) <= model.eta[t] * model.db["n", j, t])
model.mbu = pyo.Constraint(model.j, model.t, rule=mbu_rule,
                           doc="material balance: urea consumption")

# mb(c,i,t): plant material balance
def mb_rule(model, c, i, t):
    lhs = sum(model.a[c, p] * Z(p, i, t) for p in model.p if (p, i) in ppos)
    lhs += sum(
        (XI(c, ip, i, t) if (c, ip, i) in cposi else 0.0)
        - (XI(c, i, ip, t) if (c, i, ip) in cposi else 0.0)
        for ip in model.i
    )
    if (c, i) in cposd:
        lhs += U(c, i, t)
    if (c, i) in cposr:
        lhs += VR(c, i, t)
    rhs = 0.0
    if (c, i) in cposp:
        rhs += sum(XF(c, i, j, t) for j in model.j)
    if (c, i) in cpose:
        rhs += E(c, i, t)
    return lhs >= rhs
model.mb = pyo.Constraint(model.c, model.i, model.t, rule=mb_rule,
                          doc="material balance: plants")

# cc(i,m,t)$mpos(m,i): capacity constraint
def cc_rule(model, i, m, t):
    if (m, i) not in mpos:
        return pyo.Constraint.Skip
    lhs = sum(model.b[m, p] * Z(p, i, t) for p in model.p if (p, i) in ppos)
    rhs = model.k[m, i]
    for tp in model.t:
        if value(model.ts[t, tp]) >= 1:
            if (m, i) in hpos:
                rhs += 0.9 * H(m, i, tp)
            rhs += sum(model.f[m, g, i] * UP(g, i, tp) for g in model.g)
    return lhs <= rhs
model.cc = pyo.Constraint(model.i, model.m, model.t, rule=cc_rule,
                          doc="capacity constraint")

# mm(i,me,t)$hpos(me,i): maximum capacity expansion
def mm_rule(model, i, me, t):
    if (me, i) not in hpos:
        return pyo.Constraint.Skip
    return H(me, i, t) <= model.hb[me] * Y(me, i, t)
model.mm = pyo.Constraint(model.i, model.me, model.t, rule=mm_rule,
                          doc="maximum capacity expansion")

# ex(g,i)$fpos(g,i): mutual exclusivity
def ex_rule(model, g, i):
    if (g, i) not in fpos:
        return pyo.Constraint.Skip
    return sum(UP(g, i, t) for t in model.t) <= 1
model.ex = pyo.Constraint(model.g, model.i, rule=ex_rule,
                          doc="mutual exclusivity constraint")

# eca(t): aggregate export accounting
def eca_rule(model, t):
    return model.et[t] == sum(E(cf, i, t) for (cf, i) in cpose if cf in model.cf)
model.eca = pyo.Constraint(model.t, rule=eca_rule, doc="aggregate export constraint")

# ── accounting equations ──────────────────────────────────────────────────────
# ak(t): capital cost charges
def ak_rule(model, t):
    acc = 0.0
    for tp in model.t:
        if value(model.ts[t, tp]) >= 1:
            inner = sum(
                model.omega[me] * Y(me, i, tp) + model.nu[me] * H(me, i, tp)
                for (me, i) in hpos if me in model.me
            )
            inner += sum(model.omegag[g] * UP(g, i, tp) for (g, i) in fpos)
            acc += model.sigma * inner
    return model.psic["capital-ch", t] == OER * acc / 1000
model.ak = pyo.Constraint(model.t, rule=ak_rule, doc="accounting: capital cost charges")

# ap(t): domestic recurrent cost
def ap_rule(model, t):
    return model.psic["d-r-c", t] == sum(
        model.pd[i, c] * U(c, i, t) for (c, i) in cposd) / 1000
model.ap = pyo.Constraint(model.t, rule=ap_rule, doc="accounting: domestic recurrent cost")

# ao(t): operating cost
def ao_rule(model, t):
    op = sum(model.oc[cd, p] * Z(p, i, t)
             for cd in model.cd for (p, i) in ppos)
    lab = sum(
        model.omegal * Y(me, i, tp) + model.nul * H(me, i, tp)
        for tp in model.t if value(model.ts[t, tp]) >= 1
        for (me, i) in hpos if me in model.me
    )
    return model.psic["operating", t] == (op + model.plab * lab) / 1000
model.ao = pyo.Constraint(model.t, rule=ao_rule, doc="accounting: operating cost")

# al(t): transport cost
def al_rule(model, t):
    tr = 0.0
    for cf in model.cf:
        tr += sum(model.muf[i, j] * XF(cf, i, j, t)
                  for (c, i) in cposp if c == cf for j in model.j)
        tr += sum(model.mufv[j] * VF(cf, j, t) for j in model.j)
        tr += sum(model.mue[i] * E(cf, i, t)
                  for (c, i) in cpose if c == cf)
    tr += sum(model.mui[i, ip] * XI(cs, i, ip, t)
              for cs in model.cs for (c, i, ip) in cposi if c == cs)
    tr += sum(model.mur[i] * VR(cr, i, t)
              for cr in model.cr for (c, i) in cposr if c == cr)
    return model.psic["transport", t] == tr / 1000
model.al = pyo.Constraint(model.t, rule=al_rule, doc="accounting: transport cost")

# am(t): working capital
def am_rule(model, t):
    return model.psic["work-cap", t] == 0.025 * (
        model.psic["d-r-c", t] + model.psic["operating", t]
        + model.psic["import-raw", t])
model.am = pyo.Constraint(model.t, rule=am_rule, doc="accounting: working capital")

# air(t): import cost for raw materials  (GAMS: cposn(cr,i) with pv condition)
def air_rule(model, t):
    return model.psic["import-raw", t] == OER * sum(
        model.pv[cr] * VR(cr, i, t)
        for cr in model.cr for i in model.i if (cr, i) in cposn) / 1000
model.air = pyo.Constraint(model.t, rule=air_rule, doc="accounting: import cost raw materials")

# aif(t): import cost for final products
def aif_rule(model, t):
    return model.psic["import-fp", t] == OER * sum(
        model.pv[cf] * VF(cf, j, t)
        for cf in model.cf for j in model.j) / 1000
model.aif = pyo.Constraint(model.t, rule=aif_rule, doc="accounting: import cost final products")

# ae(t): export revenue
def ae_rule(model, t):
    return model.psic["export", t] == - OER * sum(
        model.pe[cf] * E(cf, i, t)
        for (cf, i) in cpose if cf in model.cf) / 1000
model.ae = pyo.Constraint(model.t, rule=ae_rule, doc="accounting: export revenue")

# obj: total discounted cost
def obj_rule(model):
    return model.psi == sum(
        model.delta[t] * sum(model.psic[q, t] for q in model.q) for t in model.t)
model.objdef = pyo.Constraint(rule=obj_rule, doc="objective accounting")

# Objective
model.obj = pyo.Objective(expr=model.psi, sense=pyo.minimize,
                          doc="minimize total discounted cost (million le)")
