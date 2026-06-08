# converted from models/korpet_mip.py
# KORPET — Korean petrochemical industry multi-period investment-planning MILP.
# Decide process levels, blending, interplant/region shipments, imports/exports, and
# capacity expansion (with economies of scale) across plants i, periods t, to meet
# growing regional demand at minimum discounted cost.
#
# This converter repairs three faults in the prior conversion:
#   1. The blending equations (mbfr/mbir/qcfl/qcfu) iterated `for (cr,cb) in cfcb`, but
#      cfcb holds (cfr, cb) pairs — so a final product was used in the raw-material slot
#      of at()/w(), zeroing the octane balance and forcing xf[rg]=0 -> demand infeasible.
#      Fixed: blendstocks cb come from cfcb[cfr]; raw material cr ranges over model.cr.
#   2. Import/export prices pv(c)/pe(c) were absent from the data and defaulted to 0,
#      dropping raw-material, import and export terms from the objective. Fixed: derived
#      pv(c)=pr(c,'imports'), pe(c)=pr(c,'exports').
#   3. The investment-segment data ss(m,is)/omega(m,is,i) were empty, freezing capacity
#      at kat1 while demand grows ~5-10x — infeasible in late periods. Reconstructed from
#      inv(size,cost,scale) as a 4-breakpoint economy-of-scale cost: a plant of size
#      ss(m,is)=is*inv_size costs omega(m,is,i)=site(i)*inv_cost*is^scale, selected by the
#      convex-combination (lambda) constraints id/ic.
# Variables are declared over their true (sparse) index sets, matching the GAMS model.
import json
from pyomo.environ import *

data = globals().get("data", {})


def _g(name, default=None):
    v = data.get(name)
    return v if v is not None else ({} if default is None else default)


# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# -----------------------  SETS  -----------------------
model.i = Set(initialize=data["i"], doc="plant locations (i)")
model.j = Set(initialize=data["j"], doc="demand regions (j)")
model.m = Set(initialize=data["m"], doc="productive units (m)")
model.p = Set(initialize=data["p"], doc="processes (p)")
model.c = Set(initialize=data["c"], doc="commodities (c)")
model.q = Set(initialize=data["q"], doc="quality attributes (q)")
model.t = Set(initialize=data["t"], ordered=True, doc="time periods (t)")
model.te = Set(initialize=data["te"], ordered=True, doc="expansion periods (te)")

model.cfr = Set(initialize=data["cfr"], doc="final products from refineries")
model.cfrerf = Set(initialize=data["cfrerf"], doc="refinery products except residual fuel oil")
model.cfrrf = Set(initialize=data["cfrrf"], doc="residual fuel oil only")
model.cfp = Set(initialize=data["cfp"], doc="final products from petrochemical plants")
model.ci = Set(initialize=data["ci"], doc="intermediate products")
model.cs = Set(initialize=data["cs"], doc="interplant shipments")
model.cr = Set(initialize=data["cr"], doc="raw materials")
model.cb = Set(initialize=data["cb"], doc="commodities for blending")
# final products cf = cfr + cfp
cf_list = list(data["cfr"]) + list(data["cfp"])
model.cf = Set(initialize=cf_list, doc="all final products (cfr + cfp)")

model.iset = Set(initialize=data["is"], doc="investment function segments (is)")

# allowed blending combinations cfcb(cfr,cb) and crude combinations crcr
cfcb_keys = list(_g("cfcb", {}).keys())
model.cfcb = Set(dimen=2, initialize=cfcb_keys, doc="allowed blending combinations (cfr,cb)")
# blendstocks available for each final refinery product
cfcb_by_cfr = {}
for (cfrv, cbv) in cfcb_keys:
    cfcb_by_cfr.setdefault(cfrv, []).append(cbv)

cr_list = list(data["cr"])

# -----------------------  SCALAR / DATA PARAMETERS  -----------------------
model.year = Param(initialize=data.get("year", 5), mutable=True, doc="years per time period")
model.life = Param(initialize=data.get("life", 20), mutable=True, doc="life of productive units (years)")
model.discr = Param(initialize=data.get("discr", 0.1), mutable=True, doc="discount rate")

model.a = Param(model.c, model.c, model.p, initialize=_g("a"), default=0.0, mutable=True, doc="input-output coefficients a(c,c,p)")
model.b = Param(model.m, model.p, initialize=_g("b"), default=0.0, mutable=True, doc="capacity utilization b(m,p)")
model.ka = Param(model.m, model.i, initialize=_g("ka"), default=0.0, mutable=True, doc="initial capacity (1000 tpy)")
model.rket1 = Param(model.i, initialize=_g("rket1"), default=0.0, mutable=True, doc="capacity expansion rate, period 1")
model.op = Param(model.p, initialize=_g("op"), default=0.0, mutable=True, doc="operating cost per process")
model.d = Param(model.c, model.j, initialize=_g("d"), default=0.0, mutable=True, doc="regional demand ratio (%) d(c,j)")
model.tqcf = Param(model.c, initialize=_g("tqcf"), default=0.0, mutable=True, doc="total quantity demanded tqcf(c)")
model.grfp = Param(model.c, initialize=_g("grfp"), default=0.0, mutable=True, doc="annual demand growth rate grfp(c)")
model.tc = Param(model.i, model.j | model.i, initialize=_g("tc"), default=0.0, mutable=True, doc="transport cost tc(i,*)")
model.pr = Param(model.c, ["imports", "exports"], initialize=_g("pr"), default=0.0, mutable=True, doc="commodity prices pr(c,*)")
model.eu = Param(initialize=data.get("eu", 400), mutable=True, doc="export upper bound (1000 tpy)")
model.imu = Param(initialize=data.get("imu", 300), mutable=True, doc="import upper bound (1000 tpy)")

# import/export prices derived from the price table (pv = import, pe = export)
pr_raw = _g("pr", {})
pv_init = {c: pr_raw.get((c, "imports"), 0.0) for c in model.c}
pe_init = {c: pr_raw.get((c, "exports"), 0.0) for c in model.c}
model.pv = Param(model.c, initialize=pv_init, default=0.0, mutable=True, doc="import prices pv(c)=pr(c,imports)")
model.pe = Param(model.c, initialize=pe_init, default=0.0, mutable=True, doc="export prices pe(c)=pr(c,exports)")

model.inv = Param(model.m, ["size", "cost", "scale"], initialize=_g("inv"), default=0.0, mutable=True, doc="investment data inv(m,*)")
model.site = Param(model.i, initialize=_g("site"), default=1.0, mutable=True, doc="site factor site(i)")
model.suurf = Param(model.t, initialize=_g("suurf"), default=0.0, mutable=True, doc="upper sulfur limit in rf per period")
model.qll = Param(model.c, model.q, initialize=_g("qll"), default=0.0, mutable=True, doc="quality lower bounds qll(c,q)")
model.quu = Param(model.c, model.q, initialize=_g("quu"), default=0.0, mutable=True, doc="quality upper bounds quu(c,q)")
model.at = Param(model.c, model.c, model.q, initialize=_g("at"), default=0.0, mutable=True, doc="blending attributes at(cr,cb,q)")

# -----------------------  INVESTMENT-SEGMENT PARAMETERS (reconstructed)  -----------------------
# Economy-of-scale cost: a plant of size ss(m,is)=is*inv_size(m) costs
# omega(m,is,i)=site(i)*inv_cost(m)*(ss/inv_size)^scale = site(i)*inv_cost(m)*is^scale.
inv_raw = _g("inv", {})
ss_data = _g("ss", {})
omega_data = _g("omega", {})
iseg_list = list(data["is"])
ss_init, omega_init = {}, {}
for mm in model.m:
    sz = inv_raw.get((mm, "size"), 0.0)
    cst = inv_raw.get((mm, "cost"), 0.0)
    scl = inv_raw.get((mm, "scale"), 1.0) or 1.0
    for seg in iseg_list:
        mult = float(seg)  # is = 1,2,3,4 -> breakpoint multiplier
        ss_init[(mm, seg)] = ss_data.get((mm, seg), sz * mult)
        for ii in model.i:
            if (mm, seg, ii) in omega_data:
                omega_init[(mm, seg, ii)] = omega_data[(mm, seg, ii)]
            else:
                site_i = (_g("site", {}) or {}).get(ii, 1.0)
                omega_init[(mm, seg, ii)] = site_i * cst * (mult ** scl)
model.ss = Param(model.m, model.iset, initialize=ss_init, default=0.0, mutable=True, doc="investment segment size ss(m,is)")
model.omega = Param(model.m, model.iset, model.i, initialize=omega_init, default=0.0, mutable=True, doc="segment cost omega(m,is,i)")

# -----------------------  DERIVED PARAMETERS  -----------------------
t_list = list(model.t)
midyear_init = {tt: 1977 + value(model.year) * (idx + 1) for idx, tt in enumerate(t_list)}
model.midyear = Param(model.t, initialize=midyear_init, mutable=False, doc="midyear(t)=1977+year*ord(t)")

ts_init = {(tt, ttp): (1 if jdx <= idx else 0) for idx, tt in enumerate(t_list) for jdx, ttp in enumerate(t_list)}
model.ts = Param(model.t, model.t, initialize=ts_init, mutable=False, doc="time-summation matrix ts(t,tp)=1 if tp<=t")

# demand r(c,j,t) = tqcf(c)*d(c,j)/100 * (1+grfp(c))**(midyear(t)-1980)
r_init = {}
for cc in model.c:
    for jj in model.j:
        for tt in model.t:
            r_init[(cc, jj, tt)] = (value(model.tqcf[cc]) * value(model.d[cc, jj]) / 100.0
                                    * ((1.0 + value(model.grfp[cc])) ** (value(model.midyear[tt]) - 1980)))
model.r = Param(model.c, model.j, model.t, initialize=r_init, mutable=False, doc="demand r(c,j,t)")

# kat1(m,i) = ka(m,i)*(1+rket1(i)) — planned capacity in period 1
kat1_init = {(mm, ii): value(model.ka[mm, ii]) * (1.0 + value(model.rket1[ii])) for mm in model.m for ii in model.i}
model.kat1 = Param(model.m, model.i, initialize=kat1_init, mutable=False, doc="planned capacity period 1")

# discount + capital recovery factors
discf_init = {tt: (1.0 + value(model.discr)) ** (1980 - value(model.midyear[tt])) for tt in model.t}
model.discf = Param(model.t, initialize=discf_init, mutable=False, doc="discount factor discf(t)")
caprf_val = value(model.discr) / (1.0 - (1.0 + value(model.discr)) ** (-value(model.life)))
model.caprf = Param(initialize=caprf_val, mutable=False, doc="capital recovery factor")

# -----------------------  VARIABLES (over true index sets)  -----------------------
model.z = Var(model.cr, model.p, model.i, model.t, domain=NonNegativeReals, doc="process level z(cr,p,i,t)")
wkeys = [(crv, cbv, cfrv) for (cfrv, cbv) in cfcb_keys for crv in cr_list]
model.wset = Set(dimen=3, initialize=wkeys, doc="valid (cr,cb,cfr) blending triples")
model.w = Var(model.wset, model.i, model.t, domain=NonNegativeReals, doc="blending level w(cr,cb,cfr,i,t)")
model.h = Var(model.m, model.i, model.te, domain=NonNegativeReals, doc="capacity expansion h(m,i,te)")
model.s = Var(model.m, model.iset, model.i, model.te, domain=NonNegativeReals, doc="segment selection s(m,is,i,te)")
model.y = Var(model.m, model.i, model.te, domain=Binary, doc="build indicator y(m,i,te)")

model.xf = Var(model.cf, model.i, model.j, model.t, domain=NonNegativeReals, doc="domestic final shipment xf(cf,i,j,t)")
model.xi = Var(model.cr, model.cs, model.i, model.i, model.t, domain=NonNegativeReals, doc="intermediate shipment xi(cr,cs,i,ip,t)")
model.vf = Var(model.cfp, model.j, model.t, domain=NonNegativeReals, doc="final imports vf(cfp,j,t)")
model.vr = Var(model.cr, model.i, model.t, domain=NonNegativeReals, doc="raw-material imports vr(cr,i,t)")
model.e = Var(model.cfp, model.i, model.t, domain=NonNegativeReals, doc="exports e(cfp,i,t)")

model.tcost = Var(domain=Reals, doc="total discounted cost")
model.rawmat = Var(model.t, domain=Reals, doc="raw-material cost (t)")
model.operat = Var(model.t, domain=Reals, doc="operating cost (t)")
model.trans = Var(model.t, domain=Reals, doc="transportation cost (t)")
model.ccost = Var(model.t, domain=Reals, doc="capital cost (t)")
model.import_ = Var(model.t, domain=Reals, doc="import cost (t)")
model.export = Var(model.t, domain=Reals, doc="export revenue (t)")

# -----------------------  CONSTRAINTS  -----------------------
def _has_tc(ii, ip):
    return ii != ip and value(model.tc[ii, ip]) != 0.0

# mbr(cr,i,t): sum(p, a(cr,cr,p)*z(cr,p,i,t)) + vr(cr,i,t) >= 0
def mbr_rule(mdl, crv, ii, tt):
    return sum(mdl.a[crv, crv, pp] * mdl.z[crv, pp, ii, tt] for pp in mdl.p) + mdl.vr[crv, ii, tt] >= 0
model.mbr = Constraint(model.cr, model.i, model.t, rule=mbr_rule, doc="raw-material balance")

# mbir(cr,cb,i,t): sum(p, a*z) + [cb in cs] sum(ip, xi in - xi out) >= sum(cfr in cfcb[cb], w)
def mbir_rule(mdl, crv, cbv, ii, tt):
    term1 = sum(mdl.a[crv, cbv, pp] * mdl.z[crv, pp, ii, tt] for pp in mdl.p)
    term2 = 0.0
    if cbv in mdl.cs:
        term2 = sum(mdl.xi[crv, cbv, ip, ii, tt] - mdl.xi[crv, cbv, ii, ip, tt] for ip in mdl.i if _has_tc(ii, ip))
    rhs = sum(mdl.w[crv, cbv, cfrv, ii, tt] for cfrv in mdl.cfr if (cfrv, cbv) in mdl.cfcb)
    return term1 + term2 >= rhs
model.mbir = Constraint(model.cr, model.cb, model.i, model.t, rule=mbir_rule, doc="intermediate balance: refinery")

# mbip(cr,ci,i,t): sum(p, a*z) + [ci in cs] interplant >= 0
def mbip_rule(mdl, crv, civ, ii, tt):
    term1 = sum(mdl.a[crv, civ, pp] * mdl.z[crv, pp, ii, tt] for pp in mdl.p)
    term2 = 0.0
    if civ in mdl.cs:
        term2 = sum(mdl.xi[crv, civ, ip, ii, tt] - mdl.xi[crv, civ, ii, ip, tt] for ip in mdl.i if _has_tc(ii, ip))
    return term1 + term2 >= 0
model.mbip = Constraint(model.cr, model.ci, model.i, model.t, rule=mbip_rule, doc="intermediate balance: petrochem")

# mbfr(cfr,i,t): sum((cr,cb) in cfcb[cfr], w) == sum(j, xf)
def mbfr_rule(mdl, cfrv, ii, tt):
    lhs = sum(mdl.w[crv, cbv, cfrv, ii, tt] for crv in mdl.cr for cbv in cfcb_by_cfr.get(cfrv, []))
    return lhs == sum(mdl.xf[cfrv, ii, jj, tt] for jj in mdl.j)
model.mbfr = Constraint(model.cfr, model.i, model.t, rule=mbfr_rule, doc="final balance: refinery")

# mbfp(cfp,i,t): sum((cr,p), a(cr,cfp,p)*z) >= sum(j, xf) + e
def mbfp_rule(mdl, cfpv, ii, tt):
    lhs = sum(mdl.a[crv, cfpv, pp] * mdl.z[crv, pp, ii, tt] for crv in mdl.cr for pp in mdl.p)
    return lhs >= sum(mdl.xf[cfpv, ii, jj, tt] for jj in mdl.j) + mdl.e[cfpv, ii, tt]
model.mbfp = Constraint(model.cfp, model.i, model.t, rule=mbfp_rule, doc="final balance: petrochem")

# qcfl(cfr,q,i,t)$qll: sum((cr,cb) in cfcb[cfr], at(cr,cb,q)*w) >= qll(cfr,q)*sum(j, xf)
def qcfl_rule(mdl, cfrv, qv, ii, tt):
    if (cfrv, qv) not in _g("qll", {}):
        return Constraint.Skip
    lhs = sum(mdl.at[crv, cbv, qv] * mdl.w[crv, cbv, cfrv, ii, tt] for crv in mdl.cr for cbv in cfcb_by_cfr.get(cfrv, []))
    rhs = sum(value(mdl.qll[cfrv, qv]) * mdl.xf[cfrv, ii, jj, tt] for jj in mdl.j)
    return lhs >= rhs
model.qcfl = Constraint(model.cfr, model.q, model.i, model.t, rule=qcfl_rule, doc="quality lower bound")

# qcfu(cfr,q,i,t)$quu: sum(at*w) <= [cfrerf] quu*sum(j,xf) + [cfrrf] suurf(t)*sum(j,xf)
def qcfu_rule(mdl, cfrv, qv, ii, tt):
    if (cfrv, qv) not in _g("quu", {}):
        return Constraint.Skip
    lhs = sum(mdl.at[crv, cbv, qv] * mdl.w[crv, cbv, cfrv, ii, tt] for crv in mdl.cr for cbv in cfcb_by_cfr.get(cfrv, []))
    rhs = 0.0
    if cfrv in mdl.cfrerf:
        rhs += sum(value(mdl.quu[cfrv, qv]) * mdl.xf[cfrv, ii, jj, tt] for jj in mdl.j)
    if cfrv in mdl.cfrrf:
        rhs += sum(value(mdl.suurf[tt]) * mdl.xf[cfrv, ii, jj, tt] for jj in mdl.j)
    return lhs <= rhs
model.qcfu = Constraint(model.cfr, model.q, model.i, model.t, rule=qcfu_rule, doc="quality upper bound")

# cc(m,i,t): sum(p, b(m,p)*sum(cr, z)) <= kat1(m,i) + sum(te in ts(t,te), h(m,i,te))
def cc_rule(mdl, mm, ii, tt):
    lhs = sum(value(mdl.b[mm, pp]) * sum(mdl.z[crv, pp, ii, tt] for crv in mdl.cr) for pp in mdl.p)
    rhs = value(mdl.kat1[mm, ii]) + sum(mdl.h[mm, ii, tep] for tep in mdl.te if value(mdl.ts[tt, tep]) == 1)
    return lhs <= rhs
model.cc = Constraint(model.m, model.i, model.t, rule=cc_rule, doc="capacity constraints")

# id(m,i,te): h == sum(is, ss(m,is)*s(m,is,i,te))
def id_rule(mdl, mm, ii, tep):
    return mdl.h[mm, ii, tep] == sum(value(mdl.ss[mm, seg]) * mdl.s[mm, seg, ii, tep] for seg in mdl.iset)
model.id = Constraint(model.m, model.i, model.te, rule=id_rule, doc="investment definition")

# ic(m,i,te): y == sum(is, s(m,is,i,te))
def ic_rule(mdl, mm, ii, tep):
    return mdl.y[mm, ii, tep] == sum(mdl.s[mm, seg, ii, tep] for seg in mdl.iset)
model.ic = Constraint(model.m, model.i, model.te, rule=ic_rule, doc="0/1 segment selection")

# mdcf(cf,j,t): sum(i, xf(cf,i,j,t)) + [cf in cfp] vf(cf,j,t) >= r(cf,j,t)
def mdcf_rule(mdl, cfv, jj, tt):
    lhs = sum(mdl.xf[cfv, ii, jj, tt] for ii in mdl.i)
    if cfv in mdl.cfp:
        lhs = lhs + mdl.vf[cfv, jj, tt]
    return lhs >= value(mdl.r[cfv, jj, tt])
model.mdcf = Constraint(model.cf, model.j, model.t, rule=mdcf_rule, doc="market demand")

# eub(t): sum((cfp,i), e) <= eu ; imub(t): sum((cfp,j), vf) <= imu
def eub_rule(mdl, tt):
    return sum(mdl.e[cfpv, ii, tt] for cfpv in mdl.cfp for ii in mdl.i) <= value(mdl.eu)
model.eub = Constraint(model.t, rule=eub_rule, doc="export upper bound")

def imub_rule(mdl, tt):
    return sum(mdl.vf[cfpv, jj, tt] for cfpv in mdl.cfp for jj in mdl.j) <= value(mdl.imu)
model.imub = Constraint(model.t, rule=imub_rule, doc="import upper bound")

# obj: tcost == year*sum(t, discf(t)*(rawmat+operat+trans+ccost+import-export))
def obj_rule(mdl):
    return mdl.tcost == value(mdl.year) * sum(
        value(mdl.discf[tt]) * (mdl.rawmat[tt] + mdl.operat[tt] + mdl.trans[tt] + mdl.ccost[tt] + mdl.import_[tt] - mdl.export[tt])
        for tt in mdl.t)
model.obj = Constraint(rule=obj_rule, doc="total cost accounting")

def araw_rule(mdl, tt):
    return mdl.rawmat[tt] == sum(value(mdl.pv[crv]) * mdl.vr[crv, ii, tt] for crv in mdl.cr for ii in mdl.i)
model.araw = Constraint(model.t, rule=araw_rule, doc="raw-material cost")

def aoper_rule(mdl, tt):
    return mdl.operat[tt] == sum(value(mdl.op[pp]) * sum(mdl.z[crv, pp, ii, tt] for crv in mdl.cr for ii in mdl.i) for pp in mdl.p)
model.aoper = Constraint(model.t, rule=aoper_rule, doc="operating cost")

def atrans_rule(mdl, tt):
    term1 = sum(value(mdl.tc[ii, jj]) * mdl.xf[cfv, ii, jj, tt] for cfv in mdl.cf for ii in mdl.i for jj in mdl.j)
    term2 = sum(value(mdl.tc[ii, ip]) * mdl.xi[crv, csv, ii, ip, tt]
                for crv in mdl.cr for csv in mdl.cs for ii in mdl.i for ip in mdl.i if _has_tc(ii, ip))
    return mdl.trans[tt] == term1 + term2
model.atrans = Constraint(model.t, rule=atrans_rule, doc="transportation cost")

def acap_rule(mdl, tt):
    return mdl.ccost[tt] == value(mdl.caprf) * sum(
        value(mdl.omega[mm, seg, ii]) * mdl.s[mm, seg, ii, tep]
        for tep in mdl.te if value(mdl.ts[tt, tep]) == 1
        for mm in mdl.m for seg in mdl.iset for ii in mdl.i)
model.acap = Constraint(model.t, rule=acap_rule, doc="capital cost")

def aim_rule(mdl, tt):
    return mdl.import_[tt] == sum(value(mdl.pv[cfpv]) * mdl.vf[cfpv, jj, tt] for cfpv in mdl.cfp for jj in mdl.j)
model.aim = Constraint(model.t, rule=aim_rule, doc="import cost")

def aex_rule(mdl, tt):
    return mdl.export[tt] == sum(value(mdl.pe[cfpv]) * mdl.e[cfpv, ii, tt] for cfpv in mdl.cfp for ii in mdl.i)
model.aex = Constraint(model.t, rule=aex_rule, doc="export revenue")

# -----------------------  OBJECTIVE  -----------------------
model.obj_f = Objective(expr=model.tcost, sense=minimize, doc="minimize total discounted cost")
