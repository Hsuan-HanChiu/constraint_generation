# converted from gamslib shale (SHALE, SEQ=46)
# Investment Planning in the Oil Shale Industry (Piceance basin syncrude model).
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "c|p": value → (c, p): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── raw set members (ordered, as in GAMS) ─────────────────────────────────────
C    = list(data["c"])
CF   = list(data["cf"])
CRS  = list(data["crs"])
CRR  = list(data["crr"])
CRRS = list(data["crrs"])
CRRM = list(data["crrm"])
CRG  = list(data["crg"])
CI   = list(data["ci"])
CC   = list(data["cc"])
CD   = list(data["cd"])
ER   = list(data["er"])
P    = list(data["p"])
PRWS = list(data["prws"])
PRWM = list(data["prwm"])
PGW  = list(data["pgw"])
PD   = list(data["pd"])
PDU  = list(data["pdu"])
PMU  = list(data["pmu"])
PP   = list(data["pp"])
M    = list(data["m"])
MRS  = list(data["mrs"])
MRM  = list(data["mrm"])
MRG  = list(data["mrg"])
MP   = list(data["mp"])
MS   = list(data["ms"])
MD   = list(data["md"])
I    = list(data["i"])
TF   = list(data["tf"])
T    = list(data["t"])
T1   = list(data["t1"])

# ── raw data dicts (defaults to 0 where GAMS leaves entries blank) ─────────────
a_raw   = data["a"]
b_raw   = data["b"]
prm     = data["prm"]
rw1     = data["rw1"]
rwesc   = data["rwesc"]
num     = data["num"]
nud     = data["nud"]
opc_d   = data["opc"]
bc      = data["bc"]
esa     = data["esa"]
po      = data["po"]
ycf     = data["ycf"]
bts     = data["bts"]
bra     = data["bra"]
bga     = data["bga"]
bd      = data["bd"]
indcap  = data["indcap"]

theta  = float(data["theta"])
ps     = float(data["ps"])
prga   = float(data["prga"])
nutot  = float(data["nutot"])
days   = float(data["days"])
boxh   = float(data["boxh"])
boxw   = float(data["boxw"])
boxl   = float(data["boxl"])
rfs    = float(data["rfs"])
rho    = float(data["rho"])
zeta   = float(data["zeta"])


def A(c, p):
    return float(a_raw.get((c, p), 0.0))


def B(m, p):
    return float(b_raw.get((m, p), 0.0))


# ── GAMS presolve computations ────────────────────────────────────────────────
# ordinals (1-based) within the full tf set
ord_tf = {tf: k + 1 for k, tf in enumerate(TF)}
card_i = len(I)
ord_i  = {ix: k + 1 for k, ix in enumerate(I)}

# midyear(tf) = 1982 + theta*ord(tf)
midyear = {tf: 1982 + theta * ord_tf[tf] for tf in TF}

# prra(crr,t) = rw1(crr)*(1+rwesc(crr))**(midyear(t)-1982)   ; rwesc 0 if absent
prra = {}
for cr in CRR:
    for tt in T:
        prra[(cr, tt)] = rw1.get(cr, 0.0) * (1 + rwesc.get(cr, 0.0)) ** (midyear[tt] - 1982)

# prr(crr,t) = prra/7762
prr = {(cr, tt): prra[(cr, tt)] / 7762 for cr in CRR for tt in T}

# prg = prga/7762
prg = prga / 7762

# nu(m) = 1e9*nutot*num(m)/(nud(m)*days)
nu = {m: 1e9 * nutot * num[m] / (nud[m] * days) for m in M}

# pf(cf,t) = po(cf)*(1+ycf(cf))**(midyear(t)-1982)   ; ycf 0 if absent
pf = {}
for cc in CF:
    for tt in T:
        pf[(cc, tt)] = po[cc] * (1 + ycf.get(cc, 0.0)) ** (midyear[tt] - 1982)

# bs(crs) = bts(crs)*rfs
bs = {cr: bts[cr] * rfs for cr in CRS}

# br(crr) = 7762*bra(crr)
br = {cr: 7762 * bra[cr] for cr in CRR}

# bg(crg) = 7762*bga(crg)
bg = {cr: 7762 * bga[cr] for cr in CRG}

# bbr(crr) = br/card(i) ; bbg(crg) = bg/card(i)
bbr = {cr: br[cr] / card_i for cr in CRR}
bbg = {cr: bg[cr] / card_i for cr in CRG}

# bbrcum(crr,i) = ord(i)*bbr ; bbgcum(crg,i) = ord(i)*bbg
bbrcum = {(cr, ix): ord_i[ix] * bbr[cr] for cr in CRR for ix in I}
bbgcum = {(cr, ix): ord_i[ix] * bbg[cr] for cr in CRG for ix in I}

# dr(crr,i,t) = prr*bbrcum + .5*bbrcum^2*(prm-1)*prr/br
dr = {}
for cr in CRR:
    for ix in I:
        for tt in T:
            dr[(cr, ix, tt)] = (prr[(cr, tt)] * bbrcum[(cr, ix)]
                                + 0.5 * bbrcum[(cr, ix)] ** 2 * (prm[cr] - 1) * prr[(cr, tt)] / br[cr])

# dg(crg,i) = prg*bbgcum + .5*bbgcum^2*(prm-1)*prg/bg
dg = {}
for cr in CRG:
    for ix in I:
        dg[(cr, ix)] = (prg * bbgcum[(cr, ix)]
                        + 0.5 * bbgcum[(cr, ix)] ** 2 * (prm[cr] - 1) * prg / bg[cr])

# drd(crr,i,t) = dr(i) - dr(i-1)   (dr at i-1 outside range -> 0)
drd = {}
for cr in CRR:
    for k, ix in enumerate(I):
        for tt in T:
            cur = dr[(cr, ix, tt)]
            prv = dr[(cr, I[k - 1], tt)] if k >= 1 else 0.0
            drd[(cr, ix, tt)] = cur - prv

# dgd(crg,i) = dg(i) - dg(i-1)
dgd = {}
for cr in CRG:
    for k, ix in enumerate(I):
        cur = dg[(cr, ix)]
        prv = dg[(cr, I[k - 1])] if k >= 1 else 0.0
        dgd[(cr, ix)] = cur - prv

# newcap(t) = 50*.33*indcap(t)
newcap = {tt: 50 * 0.33 * indcap[tt] for tt in T}

# ts(tf,tfp)$(ord(tfp) < ord(tf)) = 1
ts = {(tf, tfp): (1.0 if ord_tf[tfp] < ord_tf[tf] else 0.0) for tf in TF for tfp in TF}

# del(tf) = (1+rho)**(1982-midyear(tf))
delf = {tf: (1 + rho) ** (1982 - midyear[tf]) for tf in TF}

# sigma = (1+rho)^2*rho/(1-(1+rho)^(-zeta))
sigma = (1 + rho) ** 2 * rho / (1 - (1 + rho) ** (-zeta))

# ebm = 1e6/(boxh*boxw*boxl*24*330)
ebm = (1e6) / (boxh * boxw * boxl * 24 * 330)

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Investment planning in the oil shale industry (LP)")

# Sets
model.c   = pyo.Set(initialize=C,   doc="commodities")
model.cf  = pyo.Set(initialize=CF,  doc="final products")
model.crs = pyo.Set(initialize=CRS, doc="shale")
model.crr = pyo.Set(initialize=CRR, doc="renewable water supply")
model.crg = pyo.Set(initialize=CRG, doc="non-renewable groundwater")
model.ci  = pyo.Set(initialize=CI,  doc="intermediate products")
model.cc  = pyo.Set(initialize=CC,  doc="canyon space")
model.er  = pyo.Set(initialize=ER,  doc="reduced air pollution emissions")
model.p   = pyo.Set(initialize=P,   doc="processes")
model.m   = pyo.Set(initialize=M,   doc="productive units")
model.i   = pyo.Set(initialize=I,   doc="break points for raw material purchases")
model.tf  = pyo.Set(initialize=TF,  doc="expansion time periods")
model.t   = pyo.Set(initialize=T,   doc="time periods")

# Parameters (base mutable inputs; derived quantities folded into constraints)
model.a = pyo.Param(model.c, model.p, initialize=lambda mdl, cc, pp: A(cc, pp),
                    mutable=True, within=pyo.Reals, doc="input-output for processes and commodities")
model.b = pyo.Param(model.m, model.p, initialize=lambda mdl, mm, pp: B(mm, pp),
                    mutable=True, within=pyo.Reals, doc="productive unit capacity utilization")
model.bd = pyo.Param(model.cc, initialize=lambda mdl, cc: float(bd[cc]),
                     mutable=True, within=pyo.NonNegativeReals, doc="available canyon space")
model.bs = pyo.Param(model.crs, initialize=lambda mdl, cr: float(bs[cr]),
                     mutable=True, within=pyo.NonNegativeReals, doc="recoverable shale (million tons)")
model.pf = pyo.Param(model.cf, model.t, initialize=lambda mdl, cc, tt: float(pf[(cc, tt)]),
                     mutable=True, within=pyo.NonNegativeReals, doc="price of final products")
model.newcap = pyo.Param(model.t, initialize=lambda mdl, tt: float(newcap[tt]),
                         mutable=True, within=pyo.NonNegativeReals, doc="new capacity allowed each period")
model.bc = pyo.Param(model.er, initialize=lambda mdl, e: float(bc[e]),
                     mutable=True, within=pyo.NonNegativeReals, doc="background concentration")
model.esa = pyo.Param(model.er, initialize=lambda mdl, e: float(esa[e]),
                      mutable=True, within=pyo.NonNegativeReals, doc="standards for ambient concentration")
model.ps = pyo.Param(initialize=ps, mutable=True, within=pyo.NonNegativeReals, doc="royalty for lease ($/bbl)")

# Variables
model.z   = pyo.Var(model.p, model.tf, domain=pyo.NonNegativeReals, doc="process level")
model.x   = pyo.Var(model.cf, model.tf, domain=pyo.NonNegativeReals, doc="output of final products")
model.us  = pyo.Var(model.crs, model.tf, domain=pyo.NonNegativeReals, doc="purchases of shale")
model.ur  = pyo.Var(model.crr, model.t, domain=pyo.NonNegativeReals, doc="purchases of renewable water")
model.ug  = pyo.Var(model.crg, domain=pyo.NonNegativeReals, doc="purchases of groundwater")
model.h   = pyo.Var(model.m, model.tf, domain=pyo.NonNegativeReals, doc="investment levels")
model.uur = pyo.Var(model.crr, model.i, model.tf, domain=pyo.NonNegativeReals, doc="renewable water purchases between points")
model.uug = pyo.Var(model.crg, model.i, domain=pyo.NonNegativeReals, doc="groundwater purchases between points")

model.pi   = pyo.Var(domain=pyo.Reals, doc="discounted profit (million $)")
model.r    = pyo.Var(model.tf, domain=pyo.Reals, doc="revenue from sales")
model.phiy = pyo.Var(model.tf, domain=pyo.Reals, doc="shale cost")
model.phir = pyo.Var(model.tf, domain=pyo.Reals, doc="renewable water cost")
model.phig = pyo.Var(domain=pyo.Reals, doc="groundwater cost")
model.phik = pyo.Var(model.tf, domain=pyo.Reals, doc="cost of capital")
model.phio = pyo.Var(model.tf, domain=pyo.Reals, doc="operating cost other than rawmat")

# Variable upper bounds (uur.up / uug.up)
for cr in CRR:
    for ix in I:
        for tf in TF:
            model.uur[cr, ix, tf].setub(bbr[cr])
for cr in CRG:
    for ix in I:
        model.uug[cr, ix].setub(bbg[cr])

# ── Equations ─────────────────────────────────────────────────────────────────
# msu(crs,t).. sum(p, a(crs,p)*z(p,t)) =e= -us(crs,t)
def msu_rule(mdl, cr, tt):
    return sum(mdl.a[cr, pp] * mdl.z[pp, tt] for pp in mdl.p) == -mdl.us[cr, tt]
model.msu = pyo.Constraint(model.crs, model.t, rule=msu_rule, doc="material balance on shale usage")

# mrw(crr,t).. sum(p, a(crr,p)*z(p,t)) =e= -ur(crr,t)
def mrw_rule(mdl, cr, tt):
    return sum(mdl.a[cr, pp] * mdl.z[pp, tt] for pp in mdl.p) == -mdl.ur[cr, tt]
model.mrw = pyo.Constraint(model.crr, model.t, rule=mrw_rule, doc="material balance on renewable water purchases")

# mgw(crg).. sum((p,t), a(crg,p)*z(p,t)) =e= -ug(crg)
def mgw_rule(mdl, cr):
    return sum(mdl.a[cr, pp] * mdl.z[pp, tt] for pp in mdl.p for tt in mdl.t) == -mdl.ug[cr]
model.mgw = pyo.Constraint(model.crg, rule=mgw_rule, doc="material balance on groundwater usage")

# mi(ci,t).. sum(p, a(ci,p)*z(p,t)) =e= 0
def mi_rule(mdl, cc, tt):
    return sum(mdl.a[cc, pp] * mdl.z[pp, tt] for pp in mdl.p) == 0
model.mi = pyo.Constraint(model.ci, model.t, rule=mi_rule, doc="material balance on intermediate products")

# mf(cf,t).. sum(p, a(cf,p)*z(p,t)) =e= x(cf,t)
def mf_rule(mdl, cc, tt):
    return sum(mdl.a[cc, pp] * mdl.z[pp, tt] for pp in mdl.p) == mdl.x[cc, tt]
model.mf = pyo.Constraint(model.cf, model.t, rule=mf_rule, doc="material balance on final products")

# mnmr.. sum((pdu,t1), z(pdu,t1)) =e= 0
def mnmr_rule(mdl):
    return sum(mdl.z[pp, tt] for pp in PDU for tt in T1) == 0
model.mnmr = pyo.Constraint(rule=mnmr_rule, doc="no mine refilling in first two periods")

# mmr3("2000-04").. sum(pdu, z(pdu,"2000-04")) =l= .413*sum(pmu, z(pmu,"1990-94"))
def mmr3_rule(mdl):
    return sum(mdl.z[pp, "2000-04"] for pp in PDU) <= 0.413 * sum(mdl.z[pp, "1990-94"] for pp in PMU)
model.mmr3 = pyo.Constraint(rule=mmr3_rule, doc="mine refilling in third period")

# mmr4("2005-09").. sum(pdu, z(pdu,"2005-09")) =l=
#     .413*sum(pmu, z(pmu,"1990-94")+z(pmu,"1995-99")) - sum(pdu, z(pdu,"2000-04"))
def mmr4_rule(mdl):
    return (sum(mdl.z[pp, "2005-09"] for pp in PDU)
            <= 0.413 * sum(mdl.z[pp, "1990-94"] + mdl.z[pp, "1995-99"] for pp in PMU)
               - sum(mdl.z[pp, "2000-04"] for pp in PDU))
model.mmr4 = pyo.Constraint(rule=mmr4_rule, doc="mine refilling in fourth period")

# cdc(cc).. theta*sum((p,t), a(cc,p)*z(p,t)) =l= bd(cc)
def cdc_rule(mdl, cc):
    return theta * sum(mdl.a[cc, pp] * mdl.z[pp, tt] for pp in mdl.p for tt in mdl.t) <= mdl.bd[cc]
model.cdc = pyo.Constraint(model.cc, rule=cdc_rule, doc="aboveground spoils disposal in canyons")

# cs(crs).. theta*sum(t, us(crs,t)) =l= bs(crs)
def cs_rule(mdl, cr):
    return theta * sum(mdl.us[cr, tt] for tt in mdl.t) <= mdl.bs[cr]
model.cs = pyo.Constraint(model.crs, rule=cs_rule, doc="limits on total shale purchases")

# mrwb(crr,t).. ur(crr,t) =e= sum(i, uur(crr,i,t))
def mrwb_rule(mdl, cr, tt):
    return mdl.ur[cr, tt] == sum(mdl.uur[cr, ix, tt] for ix in mdl.i)
model.mrwb = pyo.Constraint(model.crr, model.t, rule=mrwb_rule, doc="renewable water purchases over all breaks")

# mgwb(crg).. ug(crg) =e= sum(i, uug(crg,i))
def mgwb_rule(mdl, cr):
    return mdl.ug[cr] == sum(mdl.uug[cr, ix] for ix in mdl.i)
model.mgwb = pyo.Constraint(model.crg, rule=mgwb_rule, doc="groundwater purchases over all breaks")

# cae(er,t).. ebm*sum(p, a(er,p)*z(p,t)) + bc(er) =l= esa(er)
def cae_rule(mdl, e, tt):
    return ebm * sum(mdl.a[e, pp] * mdl.z[pp, tt] for pp in mdl.p) + mdl.bc[e] <= mdl.esa[e]
model.cae = pyo.Constraint(model.er, model.t, rule=cae_rule, doc="limits on air pollution")

# cpu(m,t).. sum(p, b(m,p)*z(p,t)) =l= sum(tf$ts(t,tf), h(m,tf))
def cpu_rule(mdl, mm, tt):
    return (sum(mdl.b[mm, pp] * mdl.z[pp, tt] for pp in mdl.p)
            <= sum(mdl.h[mm, tf] for tf in TF if ts[(tt, tf)] > 0.5))
model.cpu = pyo.Constraint(model.m, model.t, rule=cpu_rule, doc="capacity constraints")

# cind(t).. x("syncrude",t) =l= x("syncrude",t-1) + newcap(t)
# The lag t-1 is taken within set t's own ordering; for the first member of t
# it falls off the edge, so GAMS drops the x("syncrude",t-1) term (see .lst).
def cind_rule(mdl, tt):
    k = T.index(tt)
    prev = T[k - 1] if k >= 1 else None
    lhs = mdl.x["syncrude", tt]
    rhs = mdl.newcap[tt]
    if prev is not None:
        rhs = rhs + mdl.x["syncrude", prev]
    return lhs <= rhs
model.cind = pyo.Constraint(model.t, rule=cind_rule, doc="limit on new syncrude capacity by period")

# arev(t).. r(t) =e= sum(cf, pf(cf,t)*x(cf,t))
def arev_rule(mdl, tt):
    return mdl.r[tt] == sum(mdl.pf[cc, tt] * mdl.x[cc, tt] for cc in mdl.cf)
model.arev = pyo.Constraint(model.t, rule=arev_rule, doc="revenue accounting")

# aroy(t).. phiy(t) =e= ps*sum(p, a("syncrude",p)*z(p,t))
def aroy_rule(mdl, tt):
    return mdl.phiy[tt] == mdl.ps * sum(mdl.a["syncrude", pp] * mdl.z[pp, tt] for pp in mdl.p)
model.aroy = pyo.Constraint(model.t, rule=aroy_rule, doc="royalty accounting")

# arw(t).. phir(t) =e= sum(crr, sum(i, drd(crr,i,t)*uur(crr,i,t))/bbr(crr))
def arw_rule(mdl, tt):
    return mdl.phir[tt] == sum(
        sum(drd[(cr, ix, tt)] * mdl.uur[cr, ix, tt] for ix in mdl.i) / bbr[cr]
        for cr in mdl.crr)
model.arw = pyo.Constraint(model.t, rule=arw_rule, doc="renewable water accounting")

# agw.. phig =e= sum(crg, sum(i, uug(crg,i)*dgd(crg,i))/bbg(crg))
def agw_rule(mdl):
    return mdl.phig == sum(
        sum(mdl.uug[cr, ix] * dgd[(cr, ix)] for ix in mdl.i) / bbg[cr]
        for cr in mdl.crg)
model.agw = pyo.Constraint(rule=agw_rule, doc="groundwater accounting")

# acap(t).. phik(t) =e= sigma*sum((m,tf)$ts(t,tf), nu(m)*h(m,tf))
def acap_rule(mdl, tt):
    return mdl.phik[tt] == sigma * sum(
        nu[mm] * mdl.h[mm, tf]
        for mm in mdl.m for tf in TF if ts[(tt, tf)] > 0.5)
model.acap = pyo.Constraint(model.t, rule=acap_rule, doc="capital costs")

# aopc(t).. phio(t) =e= sum(p, opc(p)*z(p,t))
def aopc_rule(mdl, tt):
    return mdl.phio[tt] == sum(opc_d.get(pp, 0.0) * mdl.z[pp, tt] for pp in mdl.p)
model.aopc = pyo.Constraint(model.t, rule=aopc_rule, doc="operating cost accounting")

# aprof.. pi =e= theta*sum(t, del(t)*(r(t)-phir(t)-phio(t)-phiy(t)-phik(t))) - phig
def aprof_rule(mdl):
    return mdl.pi == theta * sum(
        delf[tt] * (mdl.r[tt] - mdl.phir[tt] - mdl.phio[tt] - mdl.phiy[tt] - mdl.phik[tt])
        for tt in mdl.t) - mdl.phig
model.aprof = pyo.Constraint(rule=aprof_rule, doc="profit accounting")

# Objective: maximize pi
model.obj = pyo.Objective(expr=model.pi, sense=pyo.maximize, doc="maximize discounted profit")
