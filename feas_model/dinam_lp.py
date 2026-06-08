# converted from gamslib dinam (DINAM, SEQ=35)
# Dinamico - dynamic multi-sector, multi-skill LP model of the Mexican economy.
# Base case "din0": maximize initial (1971) consumption.
#
# All structural data tables of the GAMS source are pre-derived into the data
# JSON (i-o matrices a/b/k/bk, consumption coeffs apc/apz, labor coeffs lreq,
# trade bounds elo/eup/zlo/zup, etc.).  Year labels carry a "y" prefix and lag
# labels an "l" prefix so the data normalizer keeps them as strings.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "i|j|te": value → (i, j, te): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Dinamico - multi-sector multi-skill planning model of Mexico (din0 base case)")

# Sets (ordered) -------------------------------------------------------------
model.te    = pyo.Set(initialize=list(data["te"]), ordered=True, doc="Plan horizon (years)")
model.t     = pyo.Set(initialize=list(data["t"]), ordered=True, doc="Optimization horizon (years)")
model.j     = pyo.Set(initialize=list(data["j"]), ordered=True, doc="Input-output sectors of destination")
model.i     = pyo.Set(initialize=list(data["i"]), ordered=True, doc="Input-output sectors of origin")
model.idset = pyo.Set(initialize=list(data["idset"]), ordered=True, doc="Sectors of origin incl. imports")
model.jd    = pyo.Set(initialize=list(data["jd"]), ordered=True, doc="Sectors-of-destination used in data")
model.s     = pyo.Set(initialize=list(data["s"]), ordered=True, doc="Labor skill categories")
model.im    = pyo.Set(initialize=list(data["im"]), ordered=True, doc="Merchandize commodities")
model.inc   = pyo.Set(initialize=list(data["inc"]), ordered=True, doc="Non-competitive foreign commodity")
model.sun   = pyo.Set(initialize=list(data["sun"]), ordered=True, doc="Unskilled agricultural workers")
model.lset  = pyo.Set(initialize=list(data["lset"]), ordered=True, doc="Lag structure for human capital")
model.eit   = pyo.Set(initialize=list(data["eit"]), ordered=True, doc="Education input types")

te   = list(data["te"])
t    = set(data["t"])
sun  = set(data["sun"])
lset = list(data["lset"])
ord_te = {y: k + 1 for k, y in enumerate(te)}
ord_l  = {l: k + 1 for k, l in enumerate(lset)}

# Scalar parameters ----------------------------------------------------------
model.interval = pyo.Param(initialize=data["interval"], mutable=True, within=pyo.PositiveReals, doc="Years per period")
model.pvv      = pyo.Param(initialize=data["pvv"], mutable=True, within=pyo.Reals, doc="Producers price value")
model.pci      = pyo.Param(initialize=data["pci"], mutable=True, within=pyo.Reals, doc="Income payments for capital inflows")
model.cfdp     = pyo.Param(initialize=data["cfdp"], mutable=True, within=pyo.Reals, doc="Cap on cumulative foreign direct inflows")
model.mps      = pyo.Param(initialize=data["mps"], mutable=True, within=pyo.Reals, doc="Marginal propensity to save")
model.gamma    = pyo.Param(initialize=data["gamma"], mutable=True, within=pyo.Reals, doc="Growth factor (3-year)")
model.gv3      = pyo.Param(initialize=data["gv3"], mutable=True, within=pyo.Reals, doc="Growth rate (3-year)")
model.con68    = pyo.Param(initialize=data["con68"], mutable=True, within=pyo.Reals, doc="Aggregate consumption 1968")
model.inv68    = pyo.Param(initialize=data["inv68"], mutable=True, within=pyo.Reals, doc="Aggregate investment 1968")
model.sav68    = pyo.Param(initialize=data["sav68"], mutable=True, within=pyo.Reals, doc="Aggregate savings 1968")
model.gdp68    = pyo.Param(initialize=data["gdp68"], mutable=True, within=pyo.Reals, doc="GDP 1968")
model.infdpt   = pyo.Param(initialize=data["infdpt"], mutable=True, within=pyo.Reals, doc="Interest/profit remittances prior")
LAST    = int(data["last"])
INITIAL = int(data["initial"])
INTERVAL = int(data["interval"])

# Indexed parameters ---------------------------------------------------------
model.a       = pyo.Param(model.idset, model.j, model.te, initialize=data["a"], mutable=True, default=0.0, within=pyo.Reals, doc="i-o matrix over optimization horizon")
model.b       = pyo.Param(model.idset, model.j, model.te, initialize=data["b"], mutable=True, default=0.0, within=pyo.Reals, doc="Capital-output ratios over horizon")
model.k       = pyo.Param(model.j, model.te, initialize=data["k"], mutable=True, default=0.0, within=pyo.Reals, doc="Capital coefficients of sector j")
model.bk_agri = pyo.Param(model.idset, model.te, initialize=data["bk_agri"], mutable=True, default=0.0, within=pyo.Reals, doc="Sector-of-origin ratios for agriculture")
model.apc     = pyo.Param(model.idset, model.te, initialize=data["apc"], mutable=True, default=0.0, within=pyo.Reals, doc="Average propensity to consume")
model.apz     = pyo.Param(model.idset, model.te, initialize=data["apz"], mutable=True, default=0.0, within=pyo.Reals, doc="Tourist consumption propensity")
model.lreq    = pyo.Param(model.s, model.j, model.te, initialize=data["lreq"], mutable=True, default=0.0, within=pyo.Reals, doc="Labor requirement per unit output")
model.alr     = pyo.Param(model.te, initialize=data["alr"], mutable=True, default=0.0, within=pyo.Reals, doc="Agricultural labor released per unit capital")
model.es      = pyo.Param(model.idset, initialize=data["es"], mutable=True, default=0.0, within=pyo.Reals, doc="Export share of subsidized high-cost manufactures")
model.csm     = pyo.Param(model.idset, initialize=data["csm"], mutable=True, default=0.0, within=pyo.Reals, doc="Commerce and service margins")
model.ssr     = pyo.Param(model.idset, model.s, initialize=data["ssr"], mutable=True, default=0.0, within=pyo.Reals, doc="Service requirement to convert rural to urban labor")
model.ldg     = pyo.Param(model.s, model.s, initialize=data["ldg"], mutable=True, default=0.0, within=pyo.Reals, doc="Labor downgrading coefficients")
model.lugt    = pyo.Param(model.s, model.s, model.te, initialize=data["lugt"], mutable=True, default=0.0, within=pyo.Reals, doc="Time-allowed labor upgrading coefficients")
model.sf      = pyo.Param(model.eit, model.s, model.lset, model.s, initialize=data["sf"], mutable=True, default=0.0, within=pyo.Reals, doc="Human capital formation coefficients")
model.length  = pyo.Param(model.s, initialize=data["length"], mutable=True, default=0.0, within=pyo.Reals, doc="Education lag length per skill")
model.x0      = pyo.Param(model.j, initialize=data["x0"], mutable=True, default=0.0, within=pyo.Reals, doc="Base (1968) output of sector j")
model.zmi     = pyo.Param(model.t, model.t, initialize=data["zmi"], mutable=True, default=0.0, within=pyo.Reals, doc="Implicit protection rate factor")
model.deltae  = pyo.Param(model.idset, initialize=data["deltae"], mutable=True, default=0.0, within=pyo.Reals, doc="Post-terminal export increment")
model.deltaz  = pyo.Param(model.idset, initialize=data["deltaz"], mutable=True, default=0.0, within=pyo.Reals, doc="Post-terminal tourist increment")
model.infc    = pyo.Param(model.t, initialize=data["infc"], mutable=True, default=0.0, within=pyo.Reals, doc="Interest on concessional capital")
model.pfc     = pyo.Param(model.t, initialize=data["pfc"], mutable=True, default=0.0, within=pyo.Reals, doc="Concessional capital inflows")
model.fdpup   = pyo.Param(model.t, initialize=data["fdpup"], mutable=True, default=0.0, within=pyo.Reals, doc="Upper bound on direct foreign inflows")
model.w1      = pyo.Param(model.te, initialize=data["w1"], mutable=True, default=0.0, within=pyo.Reals, doc="Objective-1 weight (initial consumption)")
model.elo     = pyo.Param(model.im, model.t, initialize=data["elo"], mutable=True, default=0.0, within=pyo.Reals, doc="Lower bound on export levels")
model.eup     = pyo.Param(model.im, model.t, initialize=data["eup"], mutable=True, default=0.0, within=pyo.Reals, doc="Upper bound on export levels")
model.zlo     = pyo.Param(model.t, initialize=data["zlo"], mutable=True, default=0.0, within=pyo.Reals, doc="Lower bound on tourism earnings")
model.zup     = pyo.Param(model.t, initialize=data["zup"], mutable=True, default=0.0, within=pyo.Reals, doc="Upper bound on tourism earnings")
model.ls      = pyo.Param(model.te, model.s, initialize=data["ls"], mutable=True, default=0.0, within=pyo.Reals, doc="Labor supply projection")

# membership/ordering helpers ------------------------------------------------
def prev_te(y):
    return te[ord_te[y] - 2]

def ts(y, yp):     # ts(te,tep) = ord(te) >= ord(tep)
    return ord_te[y] >= ord_te[yp]

def ts2(y, yp):    # ts2(te,tep) = ord(te) > ord(tep)
    return ord_te[y] > ord_te[yp]

# Variables (all positive except rgap, infdp, max1) --------------------------
model.x   = pyo.Var(model.jd, model.te, domain=pyo.NonNegativeReals, doc="Gross output of sector j in year t")
model.v   = pyo.Var(model.jd, model.te, domain=pyo.NonNegativeReals, doc="One-year increase in capacity (investment)")
model.ld  = pyo.Var(model.s, model.te, domain=pyo.NonNegativeReals, doc="Labor downgraded from category s")
model.ul  = pyo.Var(model.s, model.te, domain=pyo.NonNegativeReals, doc="Labor upgraded into category s")
model.ka  = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Capital added to agriculture substituting labor")
model.ed  = pyo.Var(model.s, model.te, domain=pyo.NonNegativeReals, doc="Education processes for human capital")
model.rql = pyo.Var(model.s, model.te, domain=pyo.NonNegativeReals, doc="Requirements for labor skill s")
model.e   = pyo.Var(model.i, model.te, domain=pyo.NonNegativeReals, doc="Exports of item i")
model.em  = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Exports of high-cost manufactures")
model.ea  = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Aggregate merchandize exports")
model.zt  = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Earnings from tourism")
model.fdp = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Foreign direct private capital inflows")
model.inv = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Gross domestic investment")
model.sav = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Gross domestic savings")
model.con = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Aggregate consumption")
model.gdp = pyo.Var(model.te, domain=pyo.NonNegativeReals, doc="Gross domestic product")
model.fc  = pyo.Var(model.te, domain=pyo.Reals, doc="Concessional foreign capital inflows (fixed)")
model.rgap = pyo.Var(model.te, domain=pyo.Reals, doc="Resource gap in year t")
model.infdp = pyo.Var(domain=pyo.Reals, doc="Interest/profit remittances on prior foreign capital")
model.max1 = pyo.Var(domain=pyo.Reals, doc="Maximand: initial consumption")

# bounds / fixed initial conditions ------------------------------------------
model.con["y1968"].fix(pyo.value(model.con68))
model.inv["y1968"].fix(pyo.value(model.inv68))
model.sav["y1968"].fix(pyo.value(model.sav68))
model.gdp["y1968"].fix(pyo.value(model.gdp68))
model.infdp.fix(pyo.value(model.infdpt))
for y in t:
    model.fc[y].fix(pyo.value(model.pfc[y]))
    model.fdp[y].setub(pyo.value(model.fdpup[y]))
for r in model.im:
    for y in t:
        model.e[r, y].setlb(pyo.value(model.elo[r, y]))
        model.e[r, y].setub(pyo.value(model.eup[r, y]))
for y in t:
    model.zt[y].setlb(pyo.value(model.zlo[y]))
    model.zt[y].setub(pyo.value(model.zup[y]))

# Equations ------------------------------------------------------------------
def mb_rule(mm, ii, y):  # material balance
    expr = sum(mm.a[ii, jj, y] * mm.x[jj, y] + mm.b[ii, jj, y] * mm.v[jj, y] for jj in mm.j)
    expr += mm.bk_agri[ii, y] * mm.ka[y] + mm.apc[ii, y] * mm.con[y] + mm.apz[ii, y] * mm.zt[y]
    expr += mm.es[ii] * sum(mm.zmi[y, yp] * mm.em[yp] for yp in mm.t if ts(y, yp))
    if ii in mm.im:
        expr += mm.e[ii, y]
    expr += mm.csm[ii] * mm.ea[y] + sum(mm.ssr[ii, ss] * mm.ul[ss, y] for ss in mm.s)
    return expr <= 0
model.mb = pyo.Constraint(model.i, model.t, rule=mb_rule, doc="Material balance constraint")

def cap_rule(mm, jj, y):  # capacity constraint
    return mm.x[jj, y] <= mm.x0[jj] + INTERVAL * sum(mm.v[jj, yy] for yy in mm.te if ts2(y, yy))
model.cap = pyo.Constraint(model.j, model.t, rule=cap_rule, doc="Capacity constraint")

def tic_rule(mm, ii, y):  # terminal year investment constraint (ord(te) > last)
    if ord_te[y] <= LAST:
        return pyo.Constraint.Skip
    ym1 = prev_te(y)
    lhs = mm.apc[ii, ym1] * (mm.con[y] - mm.con[ym1])
    lhs += mm.gv3 * sum(mm.b[ii, jj, ym1] * mm.v[jj, ym1] for jj in mm.j) + mm.deltae[ii] + mm.deltaz[ii]
    rhs = INTERVAL * sum(-mm.a[ii, jj, ym1] * mm.v[jj, ym1] for jj in mm.j)
    return lhs <= rhs
model.tic = pyo.Constraint(model.i, model.te, rule=tic_rule, doc="Terminal year investment constraint")

def drql_rule(mm, ss, y):  # definition of labor requirements
    expr = sum(mm.lreq[ss, jj, y] * mm.x[jj, y] for jj in mm.j)
    if ss in sun:
        expr -= mm.alr[y] * (mm.ka[y] + INTERVAL * sum(mm.ka[yy] for yy in mm.te if ts2(y, yy)))
    return expr == mm.rql[ss, y]
model.drql = pyo.Constraint(model.s, model.t, rule=drql_rule, doc="Definition of labor requirements")

def trql_rule(mm, ss, y):  # terminal year labor requirements (ord(te) > last)
    if ord_te[y] <= LAST:
        return pyo.Constraint.Skip
    ym1 = prev_te(y)
    expr = sum(mm.lreq[ss, jj, y] * (mm.x[jj, ym1] + INTERVAL * mm.v[jj, ym1]) for jj in mm.j)
    if ss in sun:
        expr -= INTERVAL * mm.alr[y] * sum(mm.ka[yp] for yp in mm.te if ts2(y, yp))
    return expr == mm.rql[ss, y]
model.trql = pyo.Constraint(model.s, model.te, rule=trql_rule, doc="Terminal year labor requirements")

def ldsc_rule(mm, ss, y):  # labor demand and supply constraint (ord(te) > initial)
    if ord_te[y] <= INITIAL:
        return pyo.Constraint.Skip
    rhs = mm.ls[y, ss]
    rhs += sum(mm.ldg[ss, sp] * mm.ld[sp, y] + mm.lugt[ss, sp, y] * mm.ul[sp, y] for sp in mm.s)
    edterm = 0
    for yp in mm.te:
        if not ts(y, yp):
            continue
        for sp in mm.s:
            for ll in lset:
                if (ord_te[yp] + (ord_l[ll] - 1)) > pyo.value(mm.length[sp]):
                    coeff = pyo.value(mm.sf["change", ss, ll, sp])
                    if coeff != 0:
                        tgt = ord_te[yp] + (ord_l[ll] - 1)
                        if 1 <= tgt <= len(te):
                            edterm += mm.sf["change", ss, ll, sp] * mm.ed[sp, te[tgt - 1]]
    rhs += edterm
    inpterm = 0
    for sp in mm.s:
        for ll in lset:
            if (ord_te[y] + (ord_l[ll] - 1)) > pyo.value(mm.length[sp]):
                coeff = pyo.value(mm.sf["input", ss, ll, sp])
                if coeff != 0:
                    tgt = ord_te[y] + (ord_l[ll] - 1)
                    if 1 <= tgt <= len(te):
                        inpterm += mm.sf["input", ss, ll, sp] * mm.ed[sp, te[tgt - 1]]
    rhs += inpterm
    return mm.rql[ss, y] <= rhs
model.ldsc = pyo.Constraint(model.s, model.te, rule=ldsc_rule, doc="Labor demand and supply constraint")

def exdef_rule(mm, y):  # exports definition
    return mm.pvv * mm.ea[y] == sum(mm.e[r, y] for r in mm.im) + sum(mm.em[yp] for yp in mm.t if ts(y, yp))
model.exdef = pyo.Constraint(model.t, rule=exdef_rule, doc="Exports definition")

def fexch_rule(mm, y):  # foreign exchange constraint
    lhs = sum(mm.apc[r, y] * mm.con[y] + mm.bk_agri[r, y] * mm.ka[y]
              + sum(mm.a[r, jj, y] * mm.x[jj, y] + mm.b[r, jj, y] * mm.v[jj, y] for jj in mm.j)
              for r in mm.inc)
    return lhs == mm.ea[y] + mm.zt[y] + mm.rgap[y]
model.fexch = pyo.Constraint(model.t, rule=fexch_rule, doc="Foreign exchange constraint")

def fgap_rule(mm, y):  # resource gap definition
    return (mm.rgap[y] - mm.fc[y] - mm.fdp[y] + mm.infdp
            + mm.pci * sum(mm.fdp[yp] for yp in mm.t if ts2(y, yp)) == mm.infc[y])
model.fgap = pyo.Constraint(model.t, rule=fgap_rule, doc="Resource gap definition")

model.ffdp = pyo.Constraint(expr=sum(model.fdp[y] for y in model.t) <= model.cfdp,
                            doc="Bound on cumulative direct private capital inflows")

def ginv_rule(mm, y):  # aggregate investment definition (ord(te) <= last)
    if ord_te[y] > LAST:
        return pyo.Constraint.Skip
    return sum(mm.k[jj, y] * mm.v[jj, y] for jj in mm.j) + mm.ka[y] == mm.inv[y]
model.ginv = pyo.Constraint(model.te, rule=ginv_rule, doc="Aggregate investment definition")

def gsav_rule(mm, y):  # gross savings definition
    return mm.inv[y] == mm.sav[y] + mm.rgap[y]
model.gsav = pyo.Constraint(model.t, rule=gsav_rule, doc="Gross savings definition")

def ggdp_rule(mm, y):  # gross domestic product definition
    return mm.con[y] + mm.sav[y] == mm.gdp[y]
model.ggdp = pyo.Constraint(model.t, rule=ggdp_rule, doc="Gross domestic product definition")

def dsc_rule(mm, y):  # domestic savings constraint (te in optimization horizon)
    if y not in t:
        return pyo.Constraint.Skip
    ym1 = prev_te(y)
    return mm.sav[y] - mm.sav[ym1] <= mm.mps * (mm.gdp[y] - mm.gdp[ym1])
model.dsc = pyo.Constraint(model.te, rule=dsc_rule, doc="Domestic savings constraint")

def h_rule(mm, y):  # gradualist consumption path (te in optimization horizon)
    if y not in t:
        return pyo.Constraint.Skip
    yp1 = te[ord_te[y]]      # next year
    ym1 = prev_te(y)
    return mm.con[yp1] - mm.con[y] == mm.gamma * (mm.con[y] - mm.con[ym1])
model.h = pyo.Constraint(model.te, rule=h_rule, doc="Gradualist consumption path")

model.obj1 = pyo.Constraint(expr=model.max1 == sum(model.w1[y] * model.con[y] for y in model.te),
                            doc="Objective accounting: initial consumption")

# Objective ------------------------------------------------------------------
model.obj = pyo.Objective(expr=model.max1, sense=pyo.maximize,
                          doc="Maximize initial (1971) consumption")
