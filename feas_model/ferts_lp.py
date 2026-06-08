# converted from gamslib ferts (FERTS, SEQ=13)
# EGYPT - Static Fertilizer Model: production & distribution of the Egyptian
# fertilizer sector (1975). Minimize discounted total cost (1000 le).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "i|j": value → (i, j): value);
# OptiChat's normalizer flattens it to FLAT top-level keys (data["setname"], ...).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── base sets (from GAMS Set definitions) ─────────────────────────────────────
i_set = list(data["i"])      # plant locations
j_set = list(data["j"])      # demand regions
m_set = list(data["m"])      # productive units
p_set = list(data["p"])      # processes
cq_set = list(data["cq"])    # nutrients
c_set = list(data["c"])      # commodities
cf_set = list(data["cf"])    # final products
ci_set = list(data["ci"])    # intermediate products
cs_set = list(data["cs"])    # intermediates for shipment
cr_set = list(data["cr"])    # domestic raw materials & misc inputs

# ── base parameters (as dicts keyed by tuples / scalars) ──────────────────────
cf75 = {k: float(v) for k, v in data["cf75"].items()}     # (j,c)
alpha = {k: float(v) for k, v in data["alpha"].items()}   # (c,cq)
road = {k: float(v) for k, v in data["road"].items()}     # (j,*)
rail = {k: float(v) for k, v in data["rail"].items()}     # (i,i)
impd = {k: float(v) for k, v in data["impd"].items()}     # (i,*)
a = {k: float(v) for k, v in data["a"].items()}           # (c,p)
b = {k: float(v) for k, v in data["b"].items()}           # (m,p)
pv = {k: float(v) for k, v in data["pv"].items()}         # (c)
pd = {k: float(v) for k, v in data["pd"].items()}         # (i,c)  raw table
pmisc = {k: float(v) for k, v in data["pmisc"].items()}   # (c)
dcap = {k: float(v) for k, v in data["dcap"].items()}     # (i,m)
er = float(data["er"])
util = float(data["util"])

# ── derived parameters (mirror GAMS preprocessing) ────────────────────────────
# cn75(j,cq) = sum(cf, alpha(cf,cq)*cf75(j,cf))
cn75 = {}
for jj in j_set:
    for cq in cq_set:
        s = sum(alpha.get((cf, cq), 0.0) * cf75.get((jj, cf), 0.0) for cf in cf_set)
        if s != 0.0:
            cn75[(jj, cq)] = s

# rail(i,ip) = rail(i,ip) + rail(ip,i)  -> symmetrize
rail_sym = {}
all_pairs = set(rail.keys()) | set((y, x) for (x, y) in rail.keys())
for (x, y) in all_pairs:
    v = rail.get((x, y), 0.0) + rail.get((y, x), 0.0)
    if v != 0.0:
        rail_sym[(x, y)] = v
rail = rail_sym

# road(j,"import-pts") = road(j,"abu-kir")
for jj in j_set:
    if (jj, "abu-kir") in road:
        road[(jj, "import-pts")] = road[(jj, "abu-kir")]

# muf(i,j) = (.5 + .0144*road(j,i)) $ road(j,i)
muf = {}
for ii in i_set:
    for jj in j_set:
        if (jj, ii) in road:
            muf[(ii, jj)] = 0.5 + 0.0144 * road[(jj, ii)]

# mufv(j) = (.5 + .0144*road(j,"import-pts")) $ road(j,"import-pts")
mufv = {}
for jj in j_set:
    if (jj, "import-pts") in road:
        mufv[jj] = 0.5 + 0.0144 * road[(jj, "import-pts")]

# mui(i,ip) = (3.5 + .03*rail(i,ip)) $ rail(i,ip)
mui = {}
for ii in i_set:
    for ip in i_set:
        if (ii, ip) in rail:
            mui[(ii, ip)] = 3.5 + 0.03 * rail[(ii, ip)]

# mur(i) = (1.0 + .003*impd(i,"barge"))$impd(i,"barge")
#        + ( .5 + .0144*impd(i,"road"))$impd(i,"road")
mur = {}
for ii in i_set:
    v = 0.0
    if (ii, "barge") in impd:
        v += 1.0 + 0.003 * impd[(ii, "barge")]
    if (ii, "road") in impd:
        v += 0.5 + 0.0144 * impd[(ii, "road")]
    if v != 0.0:
        mur[ii] = v

# pd(i,cr)$pmisc(cr) = pmisc(cr)
for ii in i_set:
    for cr in cr_set:
        if cr in pmisc:
            pd[(ii, cr)] = pmisc[cr]

# k(m,i) = .33*dcap(i,m)
k = {}
for ii in i_set:
    for m in m_set:
        if (ii, m) in dcap:
            k[(m, ii)] = 0.33 * dcap[(ii, m)]

# ── derived sets (dollar-condition possibility sets) ──────────────────────────
# mpos(m,i) = yes$k(m,i)
mpos = set(k.keys())

# ppos(p,i) = yes$( sum(m$(not mpos(m,i)), b(m,p) ne 0) eq 0 )
ppos = set()
for p in p_set:
    for ii in i_set:
        blocked = any((m, ii) not in mpos and b.get((m, p), 0.0) != 0.0 for m in m_set)
        if not blocked:
            ppos.add((p, ii))
ppos.discard(("can-310", "helwan"))
ppos.discard(("can-335", "aswan"))

# cposp(c,i) = yes$sum(p$ppos(p,i), a(c,p) gt 0)
cposp = set()
for c in c_set:
    for ii in i_set:
        if any((p, ii) in ppos and a.get((c, p), 0.0) > 0.0 for p in p_set):
            cposp.add((c, ii))

# cposn(c,i) = yes$sum(p$ppos(p,i), a(c,p) lt 0)
cposn = set()
for c in c_set:
    for ii in i_set:
        if any((p, ii) in ppos and a.get((c, p), 0.0) < 0.0 for p in p_set):
            cposn.add((c, ii))

# cposi(cs,i,ip) = cposp(cs,i)*cposn(cs,ip)
cposi = set()
for cs in cs_set:
    for ii in i_set:
        for ip in i_set:
            if (cs, ii) in cposp and (cs, ip) in cposn:
                cposi.add((cs, ii, ip))

# cposd(cr,i) = yes$(cposn(cr,i)$pd(i,cr))
cposd = set()
for cr in cr_set:
    for ii in i_set:
        if (cr, ii) in cposn and pd.get((ii, cr), 0.0) != 0.0:
            cposd.add((cr, ii))

# cposr(cr,i) = yes$(cposn(cr,i)$pv(cr))
cposr = set()
for cr in cr_set:
    for ii in i_set:
        if (cr, ii) in cposn and pv.get(cr, 0.0) != 0.0:
            cposr.add((cr, ii))

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="EGYPT static fertilizer model: min discounted total cost")

# Sets (kept as Pyomo Sets for component visibility)
model.i = pyo.Set(initialize=i_set, doc="plant locations")
model.j = pyo.Set(initialize=j_set, doc="demand regions")
model.m = pyo.Set(initialize=m_set, doc="productive units")
model.p = pyo.Set(initialize=p_set, doc="processes")
model.cq = pyo.Set(initialize=cq_set, doc="nutrients")
model.c = pyo.Set(initialize=c_set, doc="commodities")
model.cf = pyo.Set(initialize=cf_set, doc="final products")
model.ci = pyo.Set(initialize=ci_set, doc="intermediate products")
model.cs = pyo.Set(initialize=cs_set, doc="intermediates for shipment")
model.cr = pyo.Set(initialize=cr_set, doc="domestic raw materials and misc inputs")

# Parameters (mutable, as required by OptiChat)
model.cf75 = pyo.Param(model.j, model.c, initialize=cf75, default=0.0, mutable=True,
                       within=pyo.NonNegativeReals, doc="fertilizer consumption 1974-75 (1000 tpy)")
model.alpha = pyo.Param(model.c, model.cq, initialize=alpha, default=0.0, mutable=True,
                        within=pyo.NonNegativeReals, doc="nutrient content")
model.a = pyo.Param(model.c, model.p, initialize=a, default=0.0, mutable=True,
                    within=pyo.Reals, doc="input-output coefficients")
model.bcap = pyo.Param(model.m, model.p, initialize=b, default=0.0, mutable=True,
                       within=pyo.Reals, doc="capacity utilization coefficients")
model.pv = pyo.Param(model.c, initialize=pv, default=0.0, mutable=True,
                     within=pyo.NonNegativeReals, doc="import prices (cif us$ per ton 1975)")
model.pd = pyo.Param(model.i, model.c, initialize=pd, default=0.0, mutable=True,
                     within=pyo.NonNegativeReals, doc="domestic raw material prices")
model.k = pyo.Param(model.m, model.i, initialize=k, default=0.0, mutable=True,
                    within=pyo.NonNegativeReals, doc="initial capacity (1000 tpy)")
model.cn75 = pyo.Param(model.j, model.cq, initialize=cn75, default=0.0, mutable=True,
                       within=pyo.NonNegativeReals, doc="consumption of nutrients 1974-75 (1000 tpy)")
model.muf = pyo.Param(model.i, model.j, initialize=muf, default=0.0, mutable=True,
                      within=pyo.NonNegativeReals, doc="transport cost: final products (le per ton)")
model.mufv = pyo.Param(model.j, initialize=mufv, default=0.0, mutable=True,
                       within=pyo.NonNegativeReals, doc="transport cost: imported final products")
model.mui = pyo.Param(model.i, model.i, initialize=mui, default=0.0, mutable=True,
                      within=pyo.NonNegativeReals, doc="transport cost: interplant shipment")
model.mur = pyo.Param(model.i, initialize=mur, default=0.0, mutable=True,
                      within=pyo.NonNegativeReals, doc="transport cost: imported raw materials")
model.er = pyo.Param(initialize=er, mutable=True, within=pyo.NonNegativeReals, doc="exchange rate")
model.util = pyo.Param(initialize=util, mutable=True, within=pyo.NonNegativeReals, doc="utilization")

# Variables
model.z = pyo.Var(model.p, model.i, domain=pyo.Reals, doc="process level (1000 tpy)")
model.xf = pyo.Var(model.cf, model.i, model.j, domain=pyo.NonNegativeReals,
                   doc="domestic shipment: final products (1000 tpy)")
model.xi = pyo.Var(model.cs, model.i, model.i, domain=pyo.NonNegativeReals,
                   doc="domestic shipment: intermediates (1000 tpy)")
model.vf = pyo.Var(model.cf, model.j, domain=pyo.NonNegativeReals,
                   doc="imports: final products (1000 tpy)")
model.vr = pyo.Var(model.cr, model.i, domain=pyo.NonNegativeReals,
                   doc="imports: raw materials (1000 tpy)")
model.u = pyo.Var(model.cr, model.i, domain=pyo.NonNegativeReals,
                  doc="domestic raw material purchases (units)")
model.psi = pyo.Var(domain=pyo.Reals, doc="discounted total cost (1000 le)")
model.psip = pyo.Var(domain=pyo.Reals, doc="domestic recurrent cost (1000 le per year)")
model.psil = pyo.Var(domain=pyo.Reals, doc="transport cost (1000 le per year)")
model.psii = pyo.Var(domain=pyo.Reals, doc="import cost (1000 le per year)")

# Scenario 1: no interplant shipments -> xi.fx(cs,i,ip) = 0
for cs in cs_set:
    for ii in i_set:
        for ip in i_set:
            model.xi[cs, ii, ip].fix(0.0)

# ── equations ─────────────────────────────────────────────────────────────────
# ap: psip = sum((cr,i)$cposd, pd(i,cr)*u(cr,i))
def ap_rule(model):
    return model.psip == sum(model.pd[ii, cr] * model.u[cr, ii]
                             for (cr, ii) in cposd)
model.ap = pyo.Constraint(rule=ap_rule, doc="accounting: domestic recurrent cost")

# al: psil = transport cost (final + imported final + interplant + imported raw)
def al_rule(model):
    e = 0.0
    for cf in cf_set:
        e += sum(model.muf[ii, jj] * model.xf[cf, ii, jj]
                 for ii in i_set for jj in j_set if (cf, ii) in cposp and (ii, jj) in muf)
        e += sum(model.mufv[jj] * model.vf[cf, jj] for jj in j_set if jj in mufv)
    e += sum(model.mui[ii, ip] * model.xi[cs, ii, ip]
             for (cs, ii, ip) in cposi if (ii, ip) in mui)
    e += sum(model.mur[ii] * model.vr[cr, ii]
             for (cr, ii) in cposr if ii in mur)
    return model.psil == e
model.al = pyo.Constraint(rule=al_rule, doc="accounting: transport cost")

# ai: psii/er = sum((cf,j), pv(cf)*vf(cf,j)) + sum((cr,i)$cposr, pv(cr)*vr(cr,i))
def ai_rule(model):
    e = sum(model.pv[cf] * model.vf[cf, jj] for cf in cf_set for jj in j_set if cf in pv)
    e += sum(model.pv[cr] * model.vr[cr, ii] for (cr, ii) in cposr if cr in pv)
    return model.psii / model.er == e
model.ai = pyo.Constraint(rule=ai_rule, doc="accounting: import cost")

# mbdb(cf,j)$cf75(j,cf): sum(i$cposp, xf) + vf$pv =g= cf75(j,cf)
mbdb_index = [(cf, jj) for cf in cf_set for jj in j_set if (jj, cf) in cf75]
def mbdb_rule(model, cf, jj):
    e = sum(model.xf[cf, ii, jj] for ii in i_set if (cf, ii) in cposp)
    if cf in pv:
        e += model.vf[cf, jj]
    return e >= model.cf75[jj, cf]
model.mbdb = pyo.Constraint(mbdb_index, rule=mbdb_rule, doc="material balance on demand: material")

# mb(c,i): production - net interplant out + imports + domestic purchase - final shipment =g= 0
mb_index = [(c, ii) for c in c_set for ii in i_set]
def mb_rule(model, c, ii):
    e = sum(model.a[c, p] * model.z[p, ii] for p in p_set if (p, ii) in ppos and (c, p) in a)
    if c in cs_set:
        e += sum(model.xi[c, ip, ii] for ip in i_set if (c, ip, ii) in cposi)
        e -= sum(model.xi[c, ii, ip] for ip in i_set if (c, ii, ip) in cposi)
    if c in cr_set and (c, ii) in cposr:
        e += model.vr[c, ii]
    if c in cr_set and (c, ii) in cposd:
        e += model.u[c, ii]
    if c in cf_set and (c, ii) in cposp:
        e -= sum(model.xf[c, ii, jj] for jj in j_set)
    if not hasattr(e, "is_expression_type") and not hasattr(e, "is_variable_type"):
        return pyo.Constraint.Skip
    return e >= 0
model.mb = pyo.Constraint(mb_index, rule=mb_rule, doc="material balance (1000 tpy)")

# cc(m,i)$mpos(m,i): sum(p$ppos, b(m,p)*z(p,i)) =l= util*k(m,i)
cc_index = [(m, ii) for (m, ii) in mpos]
def cc_rule(model, m, ii):
    return sum(model.bcap[m, p] * model.z[p, ii]
               for p in p_set if (p, ii) in ppos and (m, p) in b) <= model.util * model.k[m, ii]
model.cc = pyo.Constraint(cc_index, rule=cc_rule, doc="capacity constraint (1000 tpy)")

# obj: psi = psip + psil + psii
def obj_def_rule(model):
    return model.psi == model.psip + model.psil + model.psii
model.objdef = pyo.Constraint(rule=obj_def_rule, doc="accounting: discounted total cost")

# Objective
model.obj = pyo.Objective(expr=model.psi, sense=pyo.minimize,
                          doc="minimize discounted total cost (1000 le)")
