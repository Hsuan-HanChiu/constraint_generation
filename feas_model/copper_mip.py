# converted from gamslib copper (COPPER, SEQ=45)
# Static (year-2000) base case of the world copper sector investment MIP.
# Time index t={2000} is a singleton with period=dis=ts=1, so it is folded out;
# the reserve-horizon factor rph(2000)=20 is kept as the scalar `rph`.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "shop|desk": value → (shop, desk): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────


def _split(d):
    """Normalize keys to tuples. OptiChat's normalizer already converts pipe
    strings to tuples; raw pipe-string keys (direct exec) are split here."""
    out = {}
    for k, v in d.items():
        out[tuple(k.split("|")) if isinstance(k, str) else k] = v
    return out


model = pyo.ConcreteModel(doc="World copper sector investment MIP (base case, year 2000)")

# ── Sets ──────────────────────────────────────────────────────────────────────
model.i = pyo.Set(initialize=data["i"], doc="mine smelter and refinery locations")
model.j = pyo.Set(initialize=data["j"], doc="wire tube and sheet plant and market locations")
model.cm = pyo.Set(initialize=data["cm"], doc="commodities in mining and processing")
model.cs = pyo.Set(initialize=data["cs"], doc="commodities at wire tube & sheet plants")
model.cf = pyo.Set(initialize=data["cf"], doc="final products")
model.cfr = pyo.Set(initialize=data["cfr"], doc="final products from processing (refined-cu)")
model.cfs = pyo.Set(initialize=data["cfs"], doc="final products from semi-manufacture")
model.cim = pyo.Set(initialize=data["cim"], doc="final products at mines and smelters (ore, blister)")
model.cil = pyo.Set(initialize=data["cil"], doc="scrap types")
model.pm = pyo.Set(initialize=data["pm"], doc="process at mines smelters and refineries")
model.pmm = pyo.Set(initialize=data["pmm"], doc="mining processes")
model.pmh = pyo.Set(initialize=data["pmh"], doc="high grade ore mining processes")
model.ps = pyo.Set(initialize=data["ps"], doc="smelting processes")
model.pr = pyo.Set(initialize=data["pr"], doc="refining processes")
model.psm = pyo.Set(initialize=data["psm"], doc="semi-manufacturing processes")
model.m = pyo.Set(initialize=data["m"], doc="productive units")
model.mm = pyo.Set(initialize=data["mm"], doc="productive units at mining and processing plants")
model.ms = pyo.Set(initialize=data["ms"], doc="productive units at semi-manufacture plants")

# ── Scalars ───────────────────────────────────────────────────────────────────
model.sigma = pyo.Param(initialize=data["sigma"], mutable=True, doc="capital recovery factor")
model.rph = pyo.Param(initialize=data["rph"], mutable=True, doc="reserve-horizon period length (years)")

# ── Parameters ────────────────────────────────────────────────────────────────
model.a = pyo.Param(model.cm | model.cs, model.pm | model.psm,
                    initialize=_split(data["a"]), default=0.0, mutable=True,
                    doc="input-output coefficients")
model.b = pyo.Param(model.m, model.pm | model.psm,
                    initialize=_split(data["b"]), default=0.0, mutable=True,
                    doc="capacity utilization matrix")
model.mapic = pyo.Param(model.i, model.cm, initialize=_split(data["mapic"]), default=0.0,
                        mutable=True, doc="commodities present at mines/refineries/smelters")
model.mapip = pyo.Param(model.i, model.pm, initialize=_split(data["mapip"]), default=0.0,
                        mutable=True, doc="processes present at mines/refineries/smelters")
model.mapjc = pyo.Param(model.j, model.cs, initialize=_split(data["mapjc"]), default=0.0,
                        mutable=True, doc="commodities present at wire/tube/sheet plants")
model.mapjp = pyo.Param(model.j, model.psm, initialize=_split(data["mapjp"]), default=0.0,
                        mutable=True, doc="processes present at wire/tube/sheet plants")
model.demand = pyo.Param(model.j, model.cf, initialize=_split(data["demand"]), default=0.0,
                         mutable=True, doc="demand for refined copper and semi-manufactures")
model.capm = pyo.Param(model.i, model.mm, initialize=_split(data["capm"]), default=0.0,
                       mutable=True, doc="existing mine/smelter/refinery capacity")
model.caps = pyo.Param(model.j, model.ms, initialize=_split(data["caps"]), default=0.0,
                       mutable=True, doc="existing semi-manufacturing capacity")
model.hhatm = pyo.Param(model.i, model.mm, initialize=_split(data["hhatm"]), default=0.0,
                        mutable=True, doc="maximum plant size: mines/smelters/refineries")
model.hhats = pyo.Param(model.j, model.ms, initialize=_split(data["hhats"]), default=0.0,
                        mutable=True, doc="maximum plant size: semi-manufacturing")
model.hbarm = pyo.Param(model.i, model.mm, initialize=_split(data["hbarm"]), default=0.0,
                        mutable=True, doc="economies-of-scale size: mines/smelters/refineries")
model.hbars = pyo.Param(model.j, model.ms, initialize=_split(data["hbars"]), default=0.0,
                        mutable=True, doc="economies-of-scale size: semi-manufacturing")
model.omegam = pyo.Param(model.i, model.mm, initialize=_split(data["omegam"]), default=0.0,
                         mutable=True, doc="scale cost: mines/smelters/refineries")
model.num = pyo.Param(model.i, model.mm, initialize=_split(data["num"]), default=0.0,
                      mutable=True, doc="proportional capital cost: mines/smelters/refineries")
model.omegas = pyo.Param(model.j, model.ms, initialize=_split(data["omegas"]), default=0.0,
                         mutable=True, doc="scale cost: semi-manufacturing")
model.nus = pyo.Param(model.j, model.ms, initialize=_split(data["nus"]), default=0.0,
                      mutable=True, doc="proportional capital cost: semi-manufacturing")
model.opm = pyo.Param(model.i, model.pm, initialize=_split(data["opm"]), default=0.0,
                      mutable=True, doc="operating cost: mining and processing")
model.ops = pyo.Param(model.j, model.psm, initialize=_split(data["ops"]), default=0.0,
                      mutable=True, doc="operating cost: semi-manufacturing")
model.mur = pyo.Param(model.i, model.i, model.cim, initialize=_split(data["mur"]), default=0.0,
                      mutable=True, doc="transport cost: ore and blister")
model.mufs = pyo.Param(model.j, model.j, initialize=_split(data["mufs"]), default=0.0,
                       mutable=True, doc="transport cost: semi-manufactures to markets")
model.mui = pyo.Param(model.i, model.j, initialize=_split(data["mui"]), default=0.0,
                      mutable=True, doc="transport cost: refined copper to plants and markets")
model.tariffr = pyo.Param(model.i, model.j, initialize=_split(data["tariffr"]), default=0.0,
                          mutable=True, doc="tariffs on refined copper")
model.tariffs = pyo.Param(model.j, model.j, initialize=_split(data["tariffs"]), default=0.0,
                          mutable=True, doc="tariffs on semi-manufactured goods")
model.reserves = pyo.Param(model.i, model.pmm, initialize=_split(data["reserves"]), default=0.0,
                           mutable=True, doc="ore reserves (million tons)")

# bound-defining parameters
_resc = _split(data["resc"])
_scrapi = _split(data["scrapi"])
_scrapj = dict(data["scrapj_scrap"])

# ── Variables ─────────────────────────────────────────────────────────────────
model.zm = pyo.Var(model.pm, model.i, domain=pyo.NonNegativeReals, doc="process level: mines/smelters/refineries")
model.zs = pyo.Var(model.psm, model.j, domain=pyo.NonNegativeReals, doc="process level: wire/sheet/tube plants")
model.xi = pyo.Var(model.cim, model.i, model.i, domain=pyo.NonNegativeReals, doc="interplant shipments of ore and blister")
model.xir = pyo.Var(model.i, model.j, domain=pyo.NonNegativeReals, doc="refined copper: smelters to semi-manufacturers")
model.xfr = pyo.Var(model.i, model.j, domain=pyo.NonNegativeReals, doc="refined copper: to markets for end use")
model.xfs = pyo.Var(model.cfs, model.j, model.j, domain=pyo.NonNegativeReals, doc="semi-manufactures to markets")
model.ssr = pyo.Var(model.cil, model.i, domain=pyo.NonNegativeReals, doc="scrap supply: smelters and refineries")
model.ssm = pyo.Var(model.cil, model.j, domain=pyo.NonNegativeReals, doc="scrap supply: sheet and tube plants")
model.ssa = pyo.Var(model.j, domain=pyo.NonNegativeReals, doc="scrap supply: semi-manufacturing")
model.hm = pyo.Var(model.m, model.i, domain=pyo.NonNegativeReals, doc="capacity expansion: mines/smelters/refineries")
model.sm = pyo.Var(model.m, model.i, domain=pyo.NonNegativeReals, doc="unused economies-of-scale: mines/smelters/refineries")
model.hs = pyo.Var(model.m, model.j, domain=pyo.NonNegativeReals, doc="capacity expansion: wire/tube/sheet plants")
model.ss = pyo.Var(model.m, model.j, domain=pyo.NonNegativeReals, doc="unused economies-of-scale: wire/tube/sheet plants")
model.ym = pyo.Var(model.m, model.i, domain=pyo.Binary, doc="expansion decision: mines/smelters/refineries")
model.ys = pyo.Var(model.m, model.j, domain=pyo.Binary, doc="expansion decision: wire/tube/sheet plants")

# accounting (free) variables
model.phikm = pyo.Var(domain=pyo.Reals, doc="capital charges: mines/smelters/refineries")
model.phiks = pyo.Var(domain=pyo.Reals, doc="capital charges: wire/tube/sheet plants")
model.phiom = pyo.Var(domain=pyo.Reals, doc="operating cost: mines/smelters/refineries")
model.phios = pyo.Var(domain=pyo.Reals, doc="operating cost: wire/tube/sheet plants")
model.phit = pyo.Var(domain=pyo.Reals, doc="transport costs")
model.phitf = pyo.Var(domain=pyo.Reals, doc="tariff costs")
model.phiutf = pyo.Var(domain=pyo.Reals, doc="total annual undiscounted cost with tariffs")
model.phi2 = pyo.Var(domain=pyo.Reals, doc="total cost with tariffs")

# ── Variable bounds ───────────────────────────────────────────────────────────
# zm.up(pmh,i) = resc(i,pmh)
for ii in model.i:
    for pp in model.pmh:
        if (ii, pp) in _resc:
            model.zm[pp, ii].setub(_resc[(ii, pp)])
# zs.lo("wire-ref-c",j) = caps(j,"wire")
for jj in model.j:
    cw = pyo.value(model.caps[jj, "wire"])
    model.zs["wire-ref-c", jj].setlb(cw)
# ssr.up(cil,i) = scrapi(i,cil)
for ii in model.i:
    for cc in model.cil:
        model.ssr[cc, ii].setub(_scrapi.get((ii, cc), 0.0))
# ssa.up(j) = scrapj(j,"scrap")
for jj in model.j:
    model.ssa[jj].setub(_scrapj.get(jj, 0.0))

# ── Constraints ───────────────────────────────────────────────────────────────
# Material balance at mines/smelters/refineries (only where mapic(i,cm) present)
def mbm_rule(model, cm, i):
    if pyo.value(model.mapic[i, cm]) == 0:
        return pyo.Constraint.Skip
    lhs = sum(model.a[cm, pm] * model.zm[pm, i] for pm in model.pm if pyo.value(model.mapip[i, pm]) != 0)
    if cm in model.cim:
        lhs += sum(model.xi[cm, ip, i] for ip in model.i)
    if cm in model.cil:
        lhs += model.ssr[cm, i]
    rhs = 0
    if cm in model.cfr:
        rhs += sum(model.xfr[i, j] for j in model.j)
        rhs += sum(model.xir[i, j] for j in model.j)
    if cm in model.cim:
        rhs += sum(model.xi[cm, i, ip] for ip in model.i)
    return lhs >= rhs
model.mbm = pyo.Constraint(model.cm, model.i, rule=mbm_rule, doc="material balance: mines/smelters/refineries")

# Material balance at semi-manufacturing (only where mapjc(j,cs) present)
def mbs_rule(model, cs, j):
    if pyo.value(model.mapjc[j, cs]) == 0:
        return pyo.Constraint.Skip
    lhs = sum(model.a[cs, psm] * model.zs[psm, j] for psm in model.psm if pyo.value(model.mapjp[j, psm]) != 0)
    if cs in model.cfr:
        lhs += sum(model.xir[i, j] for i in model.i)
    if cs in model.cil:
        lhs += model.ssm[cs, j]
    rhs = 0
    if cs in model.cfs:
        rhs += sum(model.xfs[cs, j, jp] for jp in model.j)
    return lhs >= rhs
model.mbs = pyo.Constraint(model.cs, model.j, rule=mbs_rule, doc="material balance: semi-manufacturing")

# Market requirements
def mr_rule(model, cf, j):
    lhs = 0
    if cf in model.cfr:
        lhs += sum(model.xfr[i, j] for i in model.i)
    if cf in model.cfs:
        lhs += sum(model.xfs[cf, jp, j] for jp in model.j)
    return lhs >= model.demand[j, cf]
model.mr = pyo.Constraint(model.cf, model.j, rule=mr_rule, doc="market requirements")

# Capacity constraint: mines/smelters/refineries (ts(t,tp)=1 → expansion adds directly)
def ccm_rule(model, mm, i):
    lhs = sum(model.b[mm, pm] * model.zm[pm, i] for pm in model.pm if pyo.value(model.mapip[i, pm]) != 0)
    return lhs <= model.capm[i, mm] + model.hm[mm, i]
model.ccm = pyo.Constraint(model.mm, model.i, rule=ccm_rule, doc="capacity constraint: mines/smelters/refineries")

# Capacity constraint: semi-manufacturing
def ccs_rule(model, ms, j):
    lhs = sum(model.b[ms, psm] * model.zs[psm, j] for psm in model.psm if pyo.value(model.mapjp[j, psm]) != 0)
    return lhs <= model.caps[j, ms] + model.hs[ms, j]
model.ccs = pyo.Constraint(model.ms, model.j, rule=ccs_rule, doc="capacity constraint: semi-manufacturing")

# Maximum expansion (links hm to binary ym)
def icm1_rule(model, mm, i):
    return model.hm[mm, i] <= model.hhatm[i, mm] * model.ym[mm, i]
model.icm1 = pyo.Constraint(model.mm, model.i, rule=icm1_rule, doc="maximum expansion: mines/smelters/refineries")

def ics1_rule(model, ms, j):
    return model.hs[ms, j] <= model.hhats[j, ms] * model.ys[ms, j]
model.ics1 = pyo.Constraint(model.ms, model.j, rule=ics1_rule, doc="maximum expansion: wire/tube/sheet plants")

# Limits to economies of scale
def icm2_rule(model, mm, i):
    return model.hm[mm, i] + model.sm[mm, i] >= model.hbarm[i, mm] * model.ym[mm, i]
model.icm2 = pyo.Constraint(model.mm, model.i, rule=icm2_rule, doc="economies-of-scale limit: mines/smelters/refineries")

def ics2_rule(model, ms, j):
    return model.hs[ms, j] + model.ss[ms, j] >= model.hbars[j, ms] * model.ys[ms, j]
model.ics2 = pyo.Constraint(model.ms, model.j, rule=ics2_rule, doc="economies-of-scale limit: wire/tube/sheet plants")

# High-grade ore mining limitations (uses rph * zm <= 1000*reserves)
def orec_rule(model, pmm, i):
    return model.rph * model.zm[pmm, i] <= 1000 * model.reserves[i, pmm]
model.orec = pyo.Constraint(model.pmm, model.i, rule=orec_rule, doc="ore mining reserve limit")

# Scrap balance at semi-manufacturing locations
def sbs_rule(model, j):
    return model.ssa[j] == sum(model.ssm[cil, j] for cil in model.cil)
model.sbs = pyo.Constraint(model.j, rule=sbs_rule, doc="scrap balance at semi-manufacturing")

# Accounting: capital charges (sigma * sum over (i,mm) and (j,ms))
def akm_rule(model):
    return model.phikm == model.sigma * sum(
        model.omegam[i, mm] * model.sm[mm, i] + model.num[i, mm] * model.hm[mm, i]
        for i in model.i for mm in model.mm)
model.akm = pyo.Constraint(rule=akm_rule, doc="accounting: capital charges (mines/smelters/refineries)")

def aks_rule(model):
    return model.phiks == model.sigma * sum(
        model.omegas[j, ms] * model.ss[ms, j] + model.nus[j, ms] * model.hs[ms, j]
        for j in model.j for ms in model.ms)
model.aks = pyo.Constraint(rule=aks_rule, doc="accounting: capital charges (semi-manufacturing)")

# Accounting: operating costs (opi=opj=1)
def aom_rule(model):
    return model.phiom == sum(
        model.opm[i, pm] * model.zm[pm, i]
        for pm in model.pm for i in model.i if pyo.value(model.mapip[i, pm]) != 0) / 1000.0
model.aom = pyo.Constraint(rule=aom_rule, doc="accounting: operating cost (mines/smelters/refineries)")

def aos_rule(model):
    return model.phios == sum(
        model.ops[j, psm] * model.zs[psm, j] for psm in model.psm for j in model.j)
model.aos = pyo.Constraint(rule=aos_rule, doc="accounting: operating cost (semi-manufacturing)")

# Accounting: transport
def aot_rule(model):
    expr = (
        sum(model.mur[i, ip, cim] * model.xi[cim, i, ip] for cim in model.cim for i in model.i for ip in model.i)
        + sum(model.mufs[j, jp] * model.xfs[cfs, j, jp] for cfs in model.cfs for j in model.j for jp in model.j)
        + sum(model.mui[i, j] * (model.xir[i, j] + model.xfr[i, j]) for i in model.i for j in model.j)
    )
    return model.phit == expr / 1000.0
model.aot = pyo.Constraint(rule=aot_rule, doc="accounting: transport")

# Accounting: tariffs
def aotf_rule(model):
    expr = (
        sum(model.tariffr[i, j] * (model.xfr[i, j] + model.xir[i, j]) for i in model.i for j in model.j)
        + sum(model.tariffs[jp, j] * model.xfs[cfs, jp, j] for cfs in model.cfs for jp in model.j for j in model.j)
    )
    return model.phitf == expr / 1000.0
model.aotf = pyo.Constraint(rule=aotf_rule, doc="accounting: tariffs")

# Accounting: total undiscounted cost with tariffs
def autf_rule(model):
    return model.phiutf == model.phikm + model.phiks + model.phiom + model.phios + model.phit + model.phitf
model.autf = pyo.Constraint(rule=autf_rule, doc="accounting: undiscounted annual cost with tariffs")

# Objective accounting (period=dis=1)
def aobjtf_rule(model):
    return model.phi2 == model.phiutf
model.aobjtf = pyo.Constraint(rule=aobjtf_rule, doc="objective accounting with tariffs")

# ── Objective ─────────────────────────────────────────────────────────────────
model.obj = pyo.Objective(expr=model.phi2, sense=pyo.minimize,
                          doc="Minimize total cost with tariffs (million US$)")
