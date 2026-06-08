# converted from gamslib indus (INDUS, SEQ=90)
# Indus Agricultural Model (Pakistan). Single LP model "indus1" (the full
# model including the groundwater balance gwbl). Maximizes utility of income.
#
# All of the model's heavy derived-data preprocessing (power-law fertilizer
# response, interpolated water-loss / seepage / sub-irrigation curves, LES
# consumption coefficients, groundwater seepage, underflow, etc.) was computed
# by GAMS and exported to GDX, then baked into indus_lp_data.json as exact
# numeric values. This file only references those derived parameters; it does
# NOT re-derive the preprocessing.
#
# The set "tech" (the 46 valid crop,technology,sequence,water-stress activities)
# replaces the `$tech(c,t,s,w)` conditional that restricts every sum and the
# x variable in the GAMS source.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# JSON uses the {sets, scalar_params, indexed_params} format with pipe keys.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

model = pyo.ConcreteModel(doc="Indus Basin agricultural planning LP (Pakistan)")

# ── Sets ──────────────────────────────────────────────────────────────────────
model.c = pyo.Set(initialize=data["c"], doc="crop types")
model.cf = pyo.Set(initialize=data["cf"], doc="fodder crops")
model.cri = pyo.Set(initialize=data["cri"], doc="rice crops")
model.cc = pyo.Set(initialize=data["cc"], doc="non-consumption crops")
model.cnf = pyo.Set(initialize=data["cnf"], doc="non-fodder crops")
model.g = pyo.Set(initialize=data["g"], doc="polygons")
model.l = pyo.Set(initialize=data["l"], doc="types of livestock")
model.q = pyo.Set(initialize=data["q"], doc="livestock commodities")
model.sea = pyo.Set(initialize=data["sea"], doc="seasons")
model.m = pyo.Set(initialize=data["m"], doc="months")
# normalize_model_data coerces integer-like pipe-key tokens to int, so dev's
# year index becomes int (e.g. 1960). Match the y set members to int here.
model.y = pyo.Set(initialize=[int(yy) for yy in data["y"]], doc="years (risk deviations)")
model.sg = pyo.Set(initialize=data["sg"], doc="polygon with saline groundwater")
model.fsg = pyo.Set(initialize=data["fsg"], doc="polygon with fresh groundwater")

# tech: the 46 valid (crop, technology, sequence, water-stress) activities.
# tuple keys come from pipe-delimited JSON keys via normalize_model_data.
_tech_keys = sorted(data["tech_p"].keys())
model.tech = pyo.Set(dimen=4, initialize=_tech_keys,
                     doc="valid crop-technology-sequence-stress activities")

# ── Scalar parameters ───────────────────────────────────────────────────────
model.fc = pyo.Param(initialize=data["fc"], mutable=True, doc="maunds to pounds conversion factor")
model.kl = pyo.Param(initialize=data["kl"], mutable=True, doc="normalizing constant for risk")
model.cdrwell = pyo.Param(initialize=data["cdrwell"], mutable=True, doc="annualized cost of public drainage well (rs/well)")
model.drcap = pyo.Param(initialize=data["drcap"], mutable=True, doc="drainage well capacity (af/year)")
model.trcap = pyo.Param(initialize=data["trcap"], mutable=True, doc="tractor capacity (tractor hours/month)")
model.twcap = pyo.Param(initialize=data["twcap"], mutable=True, doc="private tubewell capacity (af/month)")
model.gr = pyo.Param(initialize=data["gr"], mutable=True, doc="required proportion of green fodder in total fodder")
model.repco = pyo.Param(initialize=data["repco"], mutable=True, doc="reproductive coefficient")
model.pp = pyo.Param(initialize=data["pp"], mutable=True, doc="purchase price of protein concentrate (rs/lb)")
model.misc_twopc = pyo.Param(initialize=data["misc_twopc"], mutable=True, doc="private tubewell operating cost")
model.misc_tropc = pyo.Param(initialize=data["misc_tropc"], mutable=True, doc="tractor operating cost")
model.misc_twinvt = pyo.Param(initialize=data["misc_twinvt"], mutable=True, doc="tubewell investment cost")
model.misc_trinvt = pyo.Param(initialize=data["misc_trinvt"], mutable=True, doc="tractor investment cost")

_ncard_y = len(data["y"])  # card(y)

# ── Indexed parameters (derived values baked from GAMS GDX) ──────────────────
model.psc = pyo.Param(model.c, initialize=data["psc"], default=0.0, mutable=True, doc="selling price for crop commodities (rs/maund)")
model.pbc = pyo.Param(model.c, initialize=data["pbc"], default=0.0, mutable=True, doc="buying price for crop commodities (rs/maund)")
model.psq = pyo.Param(model.q, initialize=data["psq"], default=0.0, mutable=True, doc="livestock commodity selling prices")
model.pbq = pyo.Param(model.q, initialize=data["pbq"], default=0.0, mutable=True, doc="livestock commodity buying prices")
model.r = pyo.Param(model.g, initialize=data["r"], mutable=True, doc="risk aversion coefficient")
model.bp = pyo.Param(model.m, initialize=data["bp"], mutable=True, doc="bullock pair draft power capacity (pair-hours/month)")
model.wage = pyo.Param(model.m, initialize=data["wage"], mutable=True, doc="wage rates (rs/man-hour) by month")

model.dev = pyo.Param(model.c, model.y, initialize=data["dev"], default=0.0, mutable=True, doc="revenue deviation")
model.alphc = pyo.Param(model.g, model.c, initialize=data["alphc"], default=0.0, mutable=True, doc="autonomous consumption of crop commodity")
model.betac = pyo.Param(model.g, model.c, initialize=data["betac"], default=0.0, mutable=True, doc="induced consumption, crop")
model.alphq = pyo.Param(model.g, model.q, initialize=data["alphq"], default=0.0, mutable=True, doc="autonomous consumption of livestock commodities")
model.betaq = pyo.Param(model.g, model.q, initialize=data["betaq"], default=0.0, mutable=True, doc="induced consumption, livestock")
model.yq = pyo.Param(model.l, model.q, initialize=data["yq"], default=0.0, mutable=True, doc="livestock commodity yields")
model.lbq = pyo.Param(model.l, model.m, initialize=data["lbq"], default=0.0, mutable=True, doc="livestock labor requirement (man-hours/month)")

# crop activity coefficients indexed over tech (c,t,s,w)
model.cwcaptl = pyo.Param(model.tech, initialize=data["cwcaptl"], default=0.0, mutable=True, doc="total working capital by crop/technology (rs/acre)")
model.yc = pyo.Param(model.tech, initialize=data["yc"], default=0.0, mutable=True, doc="crop yield (maunds/acre)")

# (c,t,s,w,m) coefficients restricted to tech combos at solve time
model.bpr = pyo.Param(model.c, data["t"], data["s"], data["w"], model.m, initialize=data["bpr"], default=0.0, mutable=True, doc="bullock power requirements (pair-hrs)")
model.tr = pyo.Param(model.c, data["t"], data["s"], data["w"], model.m, initialize=data["tr"], default=0.0, mutable=True, doc="tractor requirements (tractor-hrs/acre)")
model.labor = pyo.Param(model.c, data["t"], data["s"], data["w"], model.m, initialize=data["labor"], default=0.0, mutable=True, doc="labor requirements (man-hours)")
model.land = pyo.Param(model.c, data["t"], data["s"], data["w"], model.m, initialize=data["land"], default=0.0, mutable=True, doc="land requirements (acres)")

# (c,t,s,w,sea) fodder/protein yields
model.tdy = pyo.Param(model.c, data["t"], data["s"], data["w"], model.sea, initialize=data["tdy"], default=0.0, mutable=True, doc="crop tdn yield")
model.dpy = pyo.Param(model.c, data["t"], data["s"], data["w"], model.sea, initialize=data["dpy"], default=0.0, mutable=True, doc="crop dp yield")
model.wtd = pyo.Param(model.c, data["t"], data["s"], data["w"], model.sea, initialize=data["wtd"], default=0.0, mutable=True, doc="tdn yield from weeds")
model.wdp = pyo.Param(model.c, data["t"], data["s"], data["w"], model.sea, initialize=data["wdp"], default=0.0, mutable=True, doc="dp yield from weeds")

# (g,c,t,s,w,m) crop water requirement net of rainfall and sub-irrigation
model.wn = pyo.Param(model.g, model.c, data["t"], data["s"], data["w"], model.m, initialize=data["wn"], default=0.0, mutable=True, doc="crop water req net of rainfall/subirrigation")

# (g,sea) grazing availability (all zero in this scenario but kept for fidelity)
model.gfd = pyo.Param(model.g, model.sea, initialize=data["gfd"], default=0.0, mutable=True, doc="green fodder available from grazing")
model.gdp = pyo.Param(model.g, model.sea, initialize=data["gdp"], default=0.0, mutable=True, doc="protein available from grazing")

# (g,m) water parameters
model.wr = pyo.Param(model.g, model.m, initialize=data["wr"], default=0.0, mutable=True, doc="canal water netted to root zone (kaf)")
model.twdeleff = pyo.Param(model.g, model.m, initialize=data["twdeleff"], default=0.0, mutable=True, doc="delivery eff. tubewell to root zone")
model.gtw1 = pyo.Param(model.g, model.m, initialize=data["gtw1"], default=0.0, mutable=True, doc="govt tubewell pumping routed to root zone (af/month)")
model.gtw = pyo.Param(model.g, model.m, initialize=data["gtw"], default=0.0, mutable=True, doc="govt tubewell pumping (af/month)")
model.efs = pyo.Param(model.g, model.m, initialize=data["efs"], default=0.0, mutable=True, doc="effective seepage of rainfall from slack land (feet)")
model.ws_pg = pyo.Param(model.g, model.m, initialize=data["ws_pg"], default=0.0, mutable=True, doc="private-tubewell seepage coefficient")
model.wl_pg = pyo.Param(model.g, model.m, initialize=data["wl_pg"], default=0.0, mutable=True, doc="private-tubewell water-loss coefficient")
model.ws_fd = pyo.Param(model.g, model.m, initialize=data["ws_fd"], default=0.0, mutable=True, doc="field seepage coefficient")
model.rivseep = pyo.Param(model.g, model.m, initialize=data["rivseep_gm"], default=0.0, mutable=True, doc="river seepage to aquifer (af)")

# (g) groundwater/area parameters
model.seepcgw = pyo.Param(model.g, initialize=data["seepcgw"], default=0.0, mutable=True, doc="canal-water seepage to groundwater (kaf)")
model.seepgtw = pyo.Param(model.g, initialize=data["seepgtw"], default=0.0, mutable=True, doc="seepage from public tubewells (kaf)")
model.qggw = pyo.Param(model.g, initialize=data["qggw"], default=0.0, mutable=True, doc="inflow from neighbouring polygons (kaf)")
model.seeprain = pyo.Param(model.g, initialize=data["seeprain"], default=0.0, mutable=True, doc="seepage of rain to groundwater (kaf)")
model.etgw = pyo.Param(model.g, initialize=data["etgw"], default=0.0, mutable=True, doc="evapotranspiration from groundwater")
model.delgw = pyo.Param(model.g, initialize=data["delgw"], default=0.0, mutable=True, doc="annual change in groundwater (kaf)")
model.ntw = pyo.Param(model.g, initialize=data["ntw"], default=0.0, mutable=True, doc="number of existing tubewells")
model.ntr = pyo.Param(model.g, initialize=data["ntr"], default=0.0, mutable=True, doc="number of existing tractors")
model.lwcaptl = pyo.Param(model.l, initialize=data["lwcaptl"], default=0.0, mutable=True, doc="livestock misc cash requirement (rs)")
model.areac_trg1 = pyo.Param(model.g, initialize=data["areac_trg1"], default=0.0, mutable=True, doc="installed tractor capacity polygon (tractor-hrs)")
model.areac_alg = pyo.Param(model.g, initialize=data["areac_alg"], default=0.0, mutable=True, doc="irrigated land in polygon (acres)")
model.areac_twg = pyo.Param(model.g, initialize=data["areac_twg"], default=0.0, mutable=True, doc="installed tubewell capacity polygon (af)")
model.areac_sra = pyo.Param(model.g, initialize=data["areac_sra"], default=0.0, mutable=True, doc="area within sugar-mill transport radius (acres)")
model.livio_tn = pyo.Param(model.l, initialize=data["livio_tn"], default=0.0, mutable=True, doc="seasonal tdn requirement (lbs/season)")
model.livio_pr = pyo.Param(model.l, initialize=data["livio_pr"], default=0.0, mutable=True, doc="seasonal dp requirement (lbs/season)")

# ── Variables (all Positive except yfa, yva, utl which are free) ─────────────
model.yfa = pyo.Var(model.g, domain=pyo.Reals, doc="farm income (1000 rs)")
model.yva = pyo.Var(model.g, domain=pyo.Reals, doc="normal farm income (1000 rs)")
model.mad = pyo.Var(model.g, domain=pyo.NonNegativeReals, doc="mean absolute revenue deviation")
model.dr = pyo.Var(model.g, domain=pyo.NonNegativeReals, doc="public drainage from groundwater (kaf)")
model.inj = pyo.Var(model.g, domain=pyo.NonNegativeReals, doc="public injection to groundwater (kaf)")
model.tw = pyo.Var(model.g, model.m, domain=pyo.NonNegativeReals, doc="private tubewell water use (kaf)")
model.ts = pyo.Var(model.g, model.m, domain=pyo.NonNegativeReals, doc="private tractor services use (1000 hrs)")
model.scc = pyo.Var(model.g, model.c, domain=pyo.NonNegativeReals, doc="sales of crop commodities (1000 lbs)")
model.ccc = pyo.Var(model.g, model.c, domain=pyo.NonNegativeReals, doc="on-farm consumption of crops (1000 lbs)")
model.pcc = pyo.Var(model.g, model.c, domain=pyo.NonNegativeReals, doc="farm purchases of crop commodities (1000 lbs)")
model.slc = pyo.Var(model.g, model.q, domain=pyo.NonNegativeReals, doc="sales of livestock commodities")
model.clc = pyo.Var(model.g, model.q, domain=pyo.NonNegativeReals, doc="farm consumption of livestock commodities")
model.plc = pyo.Var(model.g, model.q, domain=pyo.NonNegativeReals, doc="farm purchases of livestock commodities")
model.acost = pyo.Var(model.g, domain=pyo.NonNegativeReals, doc="farm cost (1000 rs)")
# x defined only over polygons x valid tech activities
model.x = pyo.Var(model.g, model.tech, domain=pyo.NonNegativeReals, doc="area of crop using a technology (1000 acres)")
model.xca = pyo.Var(model.g, model.c, domain=pyo.NonNegativeReals, doc="area of crop by polygon")
model.animal = pyo.Var(model.g, model.l, domain=pyo.NonNegativeReals, doc="production of livestock type (1000)")
model.ppc = pyo.Var(model.g, model.sea, domain=pyo.NonNegativeReals, doc="purchases of protein concentrate (1000 lbs)")
model.esl = pyo.Var(model.g, model.m, domain=pyo.NonNegativeReals, doc="employment of seasonal labor (1000 man-hrs)")
model.itw = pyo.Var(model.g, domain=pyo.NonNegativeReals, doc="investment in private tubewell capacity (kaf/month)")
model.itr = pyo.Var(model.g, domain=pyo.NonNegativeReals, doc="investment in tractor capacity (1000 tractor-hrs/month)")
model.efl = pyo.Var(model.g, model.m, domain=pyo.NonNegativeReals, doc="employment of family labor (1000 man-hrs)")
model.pdev = pyo.Var(model.g, model.y, domain=pyo.NonNegativeReals, doc="positive revenue deviation (1000 rs)")
model.ndev = pyo.Var(model.g, model.y, domain=pyo.NonNegativeReals, doc="negative revenue deviation (1000 rs)")
model.utl = pyo.Var(domain=pyo.Reals, doc="utility of income (million rs)")
model.slkland = pyo.Var(model.g, model.m, domain=pyo.NonNegativeReals, doc="slack land (1000 acres)")
model.slkwater = pyo.Var(model.g, model.m, domain=pyo.NonNegativeReals, doc="slack water (kaf)")

# ── Variable bounds (GAMS .up assignments) ──────────────────────────────────
# xca.up(g,"sc-mill") = areac(g,"sra")/1000
for gg in model.g:
    model.xca[gg, "sc-mill"].setub(value(model.areac_sra[gg]) / 1000.0)
# efl.up(g,m) = flab(g,"fh") ; esl.up(g,m) = flab(g,"lh")
_flab = data["flab"]  # keys "g|hht"
for gg in model.g:
    for mm in model.m:
        model.efl[gg, mm].setub(_flab[(gg, "fh")])
        model.esl[gg, mm].setub(_flab[(gg, "lh")])

# ── Membership / helper sets ─────────────────────────────────────────────────
_tech = set(_tech_keys)                       # (c,t,s,w) tuples
_cnf = set(data["cnf"])
_cc = set(data["cc"])
_cf = set(data["cf"])
_cri = set(data["cri"])
_sg = set(data["sg"])
_fsg = set(data["fsg"])
# tech activities grouped by crop, for fast inner sums over (t,s,w) given c
_tech_by_c = {}
for (cc_, tt_, ss_, ww_) in _tech_keys:
    _tech_by_c.setdefault(cc_, []).append((tt_, ss_, ww_))


# ── Equations / Constraints ──────────────────────────────────────────────────

# objt: utl = sum_g [ yfa - r*kl*sum_y(pdev+ndev)/card(y)
#                       - cdrwell*(dr+inj)/drcap (only saline polygons) ] / 1000
def objt_rule(m):
    tot = 0
    for gg in m.g:
        gexpr = m.yfa[gg] - m.r[gg] * m.kl * sum(m.pdev[gg, yy] + m.ndev[gg, yy] for yy in m.y) / _ncard_y
        if gg in _sg:
            gexpr -= m.cdrwell * (m.dr[gg] + m.inj[gg]) / m.drcap
        tot += gexpr
    return m.utl == tot / 1000.0
model.objt = pyo.Constraint(rule=objt_rule, doc="objective definition (utility of income)")

# Objective: maximize utl
model.obj = pyo.Objective(expr=model.utl, sense=pyo.maximize, doc="maximize utility of income")

# inbl: yfa = sum_{c in cnf} psc*scc + sum_{c in cc} (psc*ccc - pbc*pcc)
#            + sum_q (psq*slc - pbq*plc + psq*clc) - acost
def inbl_rule(m, gg):
    e = sum(m.psc[cc_] * m.scc[gg, cc_] for cc_ in m.c if cc_ in _cnf)
    e += sum(m.psc[cc_] * m.ccc[gg, cc_] - m.pbc[cc_] * m.pcc[gg, cc_] for cc_ in m.c if cc_ in _cc)
    e += sum(m.psq[qq] * m.slc[gg, qq] - m.pbq[qq] * m.plc[gg, qq] + m.psq[qq] * m.clc[gg, qq] for qq in m.q)
    e -= m.acost[gg]
    return m.yfa[gg] == e
model.inbl = pyo.Constraint(model.g, rule=inbl_rule, doc="income accounting balance")

# nfin: yva = yfa - sum_{c in cc}(pbc-psc)*pcc + sum_q (pbq-psq)*plc
def nfin_rule(m, gg):
    e = m.yfa[gg]
    e -= sum((m.pbc[cc_] - m.psc[cc_]) * m.pcc[gg, cc_] for cc_ in m.c if cc_ in _cc)
    e += sum((m.pbq[qq] - m.psq[qq]) * m.plc[gg, qq] for qq in m.q)
    return m.yva[gg] == e
model.nfin = pyo.Constraint(model.g, rule=nfin_rule, doc="normal farm income constraint")

# ddev: sum_c dev*xca = pdev - ndev
def ddev_rule(m, gg, yy):
    return sum(m.dev[cc_, yy] * m.xca[gg, cc_] for cc_ in m.c) == m.pdev[gg, yy] - m.ndev[gg, yy]
model.ddev = pyo.Constraint(model.g, model.y, rule=ddev_rule, doc="definition of revenue deviation by year")

# cost: acost = sum_{(c,t,s,w) in tech} cwcaptl*x
#             + sum_m (twopc*tw + tropc*ts + wage*esl)
#             + sum_l lwcaptl*animal + sum_sea pp*ppc
#             + twinvt*(itw+ntw)[fsg] + trinvt*(itr+ntr)
def cost_rule(m, gg):
    e = sum(m.cwcaptl[k] * m.x[gg, k] for k in m.tech)
    e += sum(m.misc_twopc * m.tw[gg, mm] + m.misc_tropc * m.ts[gg, mm] + m.wage[mm] * m.esl[gg, mm] for mm in m.m)
    e += sum(m.lwcaptl[ll] * m.animal[gg, ll] for ll in m.l)
    e += sum(m.pp * m.ppc[gg, ss] for ss in m.sea)
    if gg in _fsg:
        e += m.misc_twinvt * (m.itw[gg] + m.ntw[gg])
    e += m.misc_trinvt * (m.itr[gg] + m.ntr[gg])
    return m.acost[gg] == e
model.cost = pyo.Constraint(model.g, rule=cost_rule, doc="annual farm cost")

# cmbc (c in cnf): sum_{tech} yc*fc*x - scc - (ccc-pcc)[cc] = 0
def cmbc_rule(m, gg, cc_):
    if cc_ not in _cnf:
        return pyo.Constraint.Skip
    e = sum(m.yc[(cc_, tt_, ss_, ww_)] * m.fc * m.x[gg, cc_, tt_, ss_, ww_]
            for (tt_, ss_, ww_) in _tech_by_c.get(cc_, []))
    e -= m.scc[gg, cc_]
    if cc_ in _cc:
        e -= (m.ccc[gg, cc_] - m.pcc[gg, cc_])
    return e == 0
model.cmbc = pyo.Constraint(model.g, model.c, rule=cmbc_rule, doc="commodity balances for crops")

# cmbq: sum_l yq*animal - slc - clc + plc = 0
def cmbq_rule(m, gg, qq):
    return sum(m.yq[ll, qq] * m.animal[gg, ll] for ll in m.l) - m.slc[gg, qq] - m.clc[gg, qq] + m.plc[gg, qq] == 0.0
model.cmbq = pyo.Constraint(model.g, model.q, rule=cmbq_rule, doc="commodity balances for livestock")

# cblc (c in cc): ccc >= alphc + betac*yva
def cblc_rule(m, gg, cc_):
    if cc_ not in _cc:
        return pyo.Constraint.Skip
    return m.ccc[gg, cc_] >= m.alphc[gg, cc_] + m.betac[gg, cc_] * m.yva[gg]
model.cblc = pyo.Constraint(model.g, model.c, rule=cblc_rule, doc="farm consumption of crop commodity")

# cblq: clc >= alphq + betaq*yva
def cblq_rule(m, gg, qq):
    return m.clc[gg, qq] >= m.alphq[gg, qq] + m.betaq[gg, qq] * m.yva[gg]
model.cblq = pyo.Constraint(model.g, model.q, rule=cblq_rule, doc="farm consumption of livestock commodity")

# fdsp: sum_l tn*animal <= gfd + sum_{tech}(tdy+wtd)*x
def fdsp_rule(m, gg, ss):
    lhs = sum(m.livio_tn[ll] * m.animal[gg, ll] for ll in m.l)
    rhs = m.gfd[gg, ss] + sum((m.tdy[(cc_, tt_, sq_, ww_, ss)] + m.wtd[(cc_, tt_, sq_, ww_, ss)]) * m.x[gg, cc_, tt_, sq_, ww_]
                              for (cc_, tt_, sq_, ww_) in _tech)
    return lhs <= rhs
model.fdsp = pyo.Constraint(model.g, model.sea, rule=fdsp_rule, doc="seasonal maintenance of fodder supplies")

# slsk: sum_l pr*animal <= ppc + gdp + sum_{tech}(dpy+wdp)*x
def slsk_rule(m, gg, ss):
    lhs = sum(m.livio_pr[ll] * m.animal[gg, ll] for ll in m.l)
    rhs = m.ppc[gg, ss] + m.gdp[gg, ss] + sum((m.dpy[(cc_, tt_, sq_, ww_, ss)] + m.wdp[(cc_, tt_, sq_, ww_, ss)]) * m.x[gg, cc_, tt_, sq_, ww_]
                                              for (cc_, tt_, sq_, ww_) in _tech)
    return lhs <= rhs
model.slsk = pyo.Constraint(model.g, model.sea, rule=slsk_rule, doc="protein requirements of livestock by season")

# sgfd: gr*sum_l tn*animal <= gfd + sum_{cf,tech} tdy*x + sum_{tech} wtd*x
def sgfd_rule(m, gg, ss):
    lhs = m.gr * sum(m.livio_tn[ll] * m.animal[gg, ll] for ll in m.l)
    rhs = m.gfd[gg, ss]
    rhs += sum(m.tdy[(cc_, tt_, sq_, ww_, ss)] * m.x[gg, cc_, tt_, sq_, ww_]
               for (cc_, tt_, sq_, ww_) in _tech if cc_ in _cf)
    rhs += sum(m.wtd[(cc_, tt_, sq_, ww_, ss)] * m.x[gg, cc_, tt_, sq_, ww_]
               for (cc_, tt_, sq_, ww_) in _tech)
    return lhs <= rhs
model.sgfd = pyo.Constraint(model.g, model.sea, rule=sgfd_rule, doc="requirement for green fodder by livestock")

# bupw: sum_{tech} bpr*x <= bp*animal[bullock]
def bupw_rule(m, gg, mm):
    lhs = sum(m.bpr[(cc_, tt_, ss_, ww_, mm)] * m.x[gg, cc_, tt_, ss_, ww_] for (cc_, tt_, ss_, ww_) in _tech)
    return lhs <= m.bp[mm] * m.animal[gg, "bullock"]
model.bupw = pyo.Constraint(model.g, model.m, rule=bupw_rule, doc="bullock draft power constraint")

# buca: animal[bullock] <= repco*animal[cattle]
def buca_rule(m, gg):
    return m.animal[gg, "bullock"] <= m.repco * m.animal[gg, "cattle"]
model.buca = pyo.Constraint(model.g, rule=buca_rule, doc="bullock reproduction constraint")

# trpw: sum_{tech} tr*x - ts = 0
def trpw_rule(m, gg, mm):
    lhs = sum(m.tr[(cc_, tt_, ss_, ww_, mm)] * m.x[gg, cc_, tt_, ss_, ww_] for (cc_, tt_, ss_, ww_) in _tech)
    return lhs - m.ts[gg, mm] == 0.0
model.trpw = pyo.Constraint(model.g, model.m, rule=trpw_rule, doc="tractor draft power balance")

# trcp: ts <= areac(g,trg1)/1000 + trcap*itr
def trcp_rule(m, gg, mm):
    return m.ts[gg, mm] <= m.areac_trg1[gg] / 1000.0 + m.trcap * m.itr[gg]
model.trcp = pyo.Constraint(model.g, model.m, rule=trcp_rule, doc="tractor capacity constraint")

# labr: sum_{tech} labor*x + sum_l lbq*animal = efl + esl
def labr_rule(m, gg, mm):
    lhs = sum(m.labor[(cc_, tt_, ss_, ww_, mm)] * m.x[gg, cc_, tt_, ss_, ww_] for (cc_, tt_, ss_, ww_) in _tech)
    lhs += sum(m.lbq[ll, mm] * m.animal[gg, ll] for ll in m.l)
    return lhs == m.efl[gg, mm] + m.esl[gg, mm]
model.labr = pyo.Constraint(model.g, model.m, rule=labr_rule, doc="labor requirements constraint")

# landc: sum_{tech} land*x + slkland = areac(g,alg)/1000
def landc_rule(m, gg, mm):
    lhs = sum(m.land[(cc_, tt_, ss_, ww_, mm)] * m.x[gg, cc_, tt_, ss_, ww_] for (cc_, tt_, ss_, ww_) in _tech)
    return lhs + m.slkland[gg, mm] == m.areac_alg[gg] / 1000.0
model.landc = pyo.Constraint(model.g, model.m, rule=landc_rule, doc="land constraint")

# cacr: xca = sum_{(t,s,w):(c,t,s,w) in tech} x
def cacr_rule(m, gg, cc_):
    return m.xca[gg, cc_] == sum(m.x[gg, cc_, tt_, ss_, ww_] for (tt_, ss_, ww_) in _tech_by_c.get(cc_, []))
model.cacr = pyo.Constraint(model.g, model.c, rule=cacr_rule, doc="crop acreage")

# watr: sum_{tech} wn*x + slkwater = wr + twdeleff*tw[fsg] + gtw1/1000
def watr_rule(m, gg, mm):
    lhs = sum(m.wn[(gg, cc_, tt_, ss_, ww_, mm)] * m.x[gg, cc_, tt_, ss_, ww_] for (cc_, tt_, ss_, ww_) in _tech)
    lhs += m.slkwater[gg, mm]
    rhs = m.wr[gg, mm] + m.gtw1[gg, mm] / 1000.0
    if gg in _fsg:
        rhs += m.twdeleff[gg, mm] * m.tw[gg, mm]
    return lhs == rhs
model.watr = pyo.Constraint(model.g, model.m, rule=watr_rule, doc="water requirements for cropping activities")

# tbcp (fsg only): tw <= areac(g,twg)/1000 + twcap*itw
def tbcp_rule(m, gg, mm):
    if gg not in _fsg:
        return pyo.Constraint.Skip
    return m.tw[gg, mm] <= m.areac_twg[gg] / 1000.0 + m.twcap * m.itw[gg]
model.tbcp = pyo.Constraint(model.g, model.m, rule=tbcp_rule, doc="tubewell capacity constraint")

# gwbl: annual groundwater balance
def gwbl_rule(m, gg):
    lhs = sum(m.efs[gg, mm] * m.slkland[gg, mm] + m.rivseep[gg, mm] / 1000.0 for mm in m.m)
    if gg in _fsg:
        lhs += sum((m.ws_pg[gg, mm] + (1 - m.wl_pg[gg, mm]) * m.ws_fd[gg, mm]) * m.tw[gg, mm] for mm in m.m)
    lhs += sum(m.xca[gg, cc_] for cc_ in m.c if cc_ in _cri) * 1.5
    lhs += m.seepcgw[gg] + m.seepgtw[gg] + m.qggw[gg] + m.seeprain[gg]

    rhs = sum(m.gtw[gg, mm] / 1000.0 for mm in m.m)
    if gg in _fsg:
        rhs += sum(m.tw[gg, mm] for mm in m.m)
    rhs += m.etgw[gg]
    if gg in _sg:
        rhs += (m.dr[gg] - m.inj[gg])
    rhs += m.delgw[gg]
    return lhs == rhs
model.gwbl = pyo.Constraint(model.g, rule=gwbl_rule, doc="annual groundwater balance")
