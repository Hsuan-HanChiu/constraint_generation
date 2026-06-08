# converted from gamslib tabora (TABORA, SEQ=57)
# Tabora Rural Development - Fuelwood Production
# A 30-year dynamic LP for a Tanzanian village choosing between a managed
# forest and harvesting from the natural forest (with growing travel time).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "tobacco|jan": value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

model = pyo.ConcreteModel(doc="Tabora Rural Development - fuelwood production (30-year dynamic LP)")

# ── Sets (ordinal integers mirror GAMS ord(): t=y01..y30, a=a01..a24, i=1..9) ──
model.t = pyo.Set(initialize=data["t"], ordered=True, doc="time periods (years)")
model.a = pyo.Set(initialize=data["a"], ordered=True, doc="age of trees")
model.m = pyo.Set(initialize=data["m"], ordered=True, doc="month")
model.mc = pyo.Set(initialize=data["mc"], within=model.m, doc="cutting months")
model.i = pyo.Set(initialize=data["i"], ordered=True, doc="annuli")
model.c = pyo.Set(initialize=data["c"], doc="annual crops")

CARD_T = len(data["t"])  # 30

# ── Base parameters (all mutable, sparse tables default to 0 as in GAMS) ──────
model.ld = pyo.Param(
    pyo.Any, model.m,
    initialize=data["ld"], default=0.0, mutable=True, within=pyo.Reals,
    doc="labor requirements (man-hours) by activity and month",
)
model.tmd = pyo.Param(
    pyo.Any, model.c,
    initialize=data["tmd"], default=0.0, mutable=True, within=pyo.Reals,
    doc="crop data (input-cost, yield, price) by crop",
)
# JSON object keys are strings; the normalizer only int-coerces pipe-keys, so
# coerce yv's age keys to int to match the integer-ordinal set `a`.
_yv_init = {int(k): v for k, v in data["yv"].items()}
model.yv = pyo.Param(
    model.a,
    initialize=_yv_init, default=0.0, mutable=True, within=pyo.NonNegativeReals,
    doc="yield of planted timber (m3 per ha) by tree age",
)

model.nfam    = pyo.Param(initialize=data["nfam"], mutable=True, within=pyo.NonNegativeReals, doc="number of families in village")
model.sfam    = pyo.Param(initialize=data["sfam"], mutable=True, within=pyo.NonNegativeReals, doc="size of family (adult equiv)")
model.resw    = pyo.Param(initialize=data["resw"], mutable=True, within=pyo.NonNegativeReals, doc="reservation wage (tsh per hour)")
model.fdmaize = pyo.Param(initialize=data["fdmaize"], mutable=True, within=pyo.NonNegativeReals, doc="domestic maize demand (kg per family)")
model.tob     = pyo.Param(initialize=data["tob"], mutable=True, within=pyo.NonNegativeReals, doc="steady state tobacco (ha)")
model.sr      = pyo.Param(initialize=data["sr"], mutable=True, within=pyo.NonNegativeReals, doc="starting radius of annulus (km)")
model.width   = pyo.Param(initialize=data["width"], mutable=True, within=pyo.NonNegativeReals, doc="width of annulus (km)")
model.ws      = pyo.Param(initialize=data["ws"], mutable=True, within=pyo.NonNegativeReals, doc="walking speed (km per hour)")
model.whd     = pyo.Param(initialize=data["whd"], mutable=True, within=pyo.NonNegativeReals, doc="work hours per day")
model.wdm     = pyo.Param(initialize=data["wdm"], mutable=True, within=pyo.NonNegativeReals, doc="working days per month")
model.tr      = pyo.Param(initialize=data["tr"], mutable=True, within=pyo.NonNegativeReals, doc="transport cost (tsh per m3 per km)")
model.tc      = pyo.Param(initialize=data["tc"], mutable=True, within=pyo.NonNegativeReals, doc="timber planting cost (tsh per ha)")
model.wrc     = pyo.Param(initialize=data["wrc"], mutable=True, within=pyo.NonNegativeReals, doc="wood for curing (m3 per ha)")
model.dwr     = pyo.Param(initialize=data["dwr"], mutable=True, within=pyo.NonNegativeReals, doc="domestic wood requirement (m3 per family)")
model.labwc   = pyo.Param(initialize=data["labwc"], mutable=True, within=pyo.NonNegativeReals, doc="labor for cutting forest (man-days per m3)")
model.labvc   = pyo.Param(initialize=data["labvc"], mutable=True, within=pyo.NonNegativeReals, doc="labor for cutting timber (man-days per m3)")
model.yw      = pyo.Param(initialize=data["yw"], mutable=True, within=pyo.NonNegativeReals, doc="yield of existing forest (m3 per ha)")
model.rho     = pyo.Param(initialize=data["rho"], mutable=True, within=pyo.NonNegativeReals, doc="discount rate")
model.matr    = pyo.Param(initialize=data["matr"], mutable=True, within=pyo.NonNegativeReals, doc="improvement in maize yield after tobacco")

# ── Derived parameters (GAMS assignment statements) ───────────────────────────
nfam = pyo.value(model.nfam); sfam = pyo.value(model.sfam); resw = pyo.value(model.resw)
fdmaize = pyo.value(model.fdmaize); tob = pyo.value(model.tob); sr = pyo.value(model.sr)
width = pyo.value(model.width); ws = pyo.value(model.ws); whd = pyo.value(model.whd)
wdm = pyo.value(model.wdm); tr = pyo.value(model.tr); tc = pyo.value(model.tc)
wrc = pyo.value(model.wrc); dwr = pyo.value(model.dwr); labwc = pyo.value(model.labwc)
labvc = pyo.value(model.labvc); yw = pyo.value(model.yw); rho = pyo.value(model.rho)
matr = pyo.value(model.matr)

def _ld(r, mm):
    return pyo.value(model.ld[r, mm]) if (r, mm) in model.ld else 0.0
def _yv(a):
    return pyo.value(model.yv[a])

dmaize = fdmaize * nfam                       # domestic maize demand in village (kg)
wr     = tob * wrc + dwr * nfam               # wood requirements for domestic use and tobacco curing (m3)
delt   = {t: (1 + rho) ** (-t) for t in model.t}          # discount factor
delta  = {a: (1 + rho) ** (-a) for a in model.a}          # discount factor for tree age
vr     = {t: tr * sr * sum(_yv(a) * delta[a] for a in model.a if t + a > CARD_T) for t in model.t}  # residual value of timber
dist   = {i: sr - width / 2 + width * i for i in model.i}                  # average distance of annulus
fa     = {i: 100 * 3.1416 * dist[i] * width for i in model.i}              # area of annulus
labor  = {mm: nfam * (sfam * wdm - _ld("other", mm)) for mm in model.m}    # village labor supply (man-days)
labw   = {i: yw * labwc * whd / (whd - 2 * dist[i] / ws) for i in model.i} # labor for cutting forest (man-days)
cc     = {c: pyo.value(model.tmd["input-cost", c]) for c in model.c}       # input cost (tsh per ha)
yc     = {c: pyo.value(model.tmd["yield", c]) for c in model.c}            # crop yields (kg per ha)
pc     = {c: pyo.value(model.tmd["price", c]) for c in model.c}            # crop prices (tsh per kg)
cr     = {c: yc[c] * pc[c] for c in model.c}                               # crop revenues (tsh per ha)

# ── Variables ─────────────────────────────────────────────────────────────────
model.w      = pyo.Var(model.t, model.i, domain=pyo.NonNegativeReals, doc="cutting of existing forest (ha)")
model.v      = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="management of planted timber (ha)")
model.x      = pyo.Var(model.t, model.c, domain=pyo.NonNegativeReals, doc="cropping activity (ha)")
model.mat    = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="maize after tobacco (ha)")
model.lc     = pyo.Var(model.t, model.m, domain=pyo.NonNegativeReals, doc="labor for wood cutting (man-days)")
model.rev    = pyo.Var(model.t, domain=pyo.Reals, doc="revenue (1000 tsh)")
model.cost   = pyo.Var(model.t, domain=pyo.Reals, doc="annual cost (1000 tsh)")
model.income = pyo.Var(domain=pyo.Reals, doc="discounted income (discounted 1000 tsh)")

# mat.up("y01") = tob
model.mat[1].setub(tob)


def _v(mo, t):
    """v(t) with GAMS lag/lead semantics: 0 when the period index is out of range."""
    return mo.v[t] if 1 <= t <= CARD_T else 0.0


# ── Equations ─────────────────────────────────────────────────────────────────
def wb_rule(mo, t):
    # wood balance
    return yw * sum(mo.w[t, i] for i in mo.i) + sum(_yv(a) * _v(mo, t - a) for a in mo.a) \
        >= wrc * mo.x[t, "tobacco"] + dwr * nfam
model.wb = pyo.Constraint(model.t, rule=wb_rule, doc="wood balance (m3)")


def wa_rule(mo, i):
    # wood availability
    return sum(mo.w[t, i] for t in mo.t) <= fa[i]
model.wa = pyo.Constraint(model.i, rule=wa_rule, doc="wood availability (ha)")


def lb_rule(mo, t, mm):
    # labor balance
    expr = _ld("timber-1", mm) * _v(mo, t) + _ld("timber-2", mm) * _v(mo, t - 1) \
        + sum(_ld(c, mm) * mo.x[t, c] for c in mo.c)
    if mm in mo.mc:
        expr = expr + mo.lc[t, mm]
    return expr <= labor[mm]
model.lb = pyo.Constraint(model.t, model.m, rule=lb_rule, doc="labor balance (man-days)")


def lw_rule(mo, t):
    # labor constraint for wood cutting
    return sum(mo.lc[t, mc] for mc in mo.mc) == \
        sum(labw[i] * mo.w[t, i] for i in mo.i) + sum(labvc * _yv(a) * _v(mo, t - a) for a in mo.a)
model.lw = pyo.Constraint(model.t, rule=lw_rule, doc="labor constraint for wood cutting (man-days)")


def mm_rule(mo, t):
    # minimum maize demand
    return yc["maize"] * (mo.x[t, "maize"] + matr * mo.mat[t]) >= dmaize
model.mm = pyo.Constraint(model.t, rule=mm_rule, doc="minimum maize demand (kg)")


def ttb_rule(mo, t):
    # post terminal timber bounds; LHS can vanish for late t (GAMS keeps a trivial row)
    expr = sum(_yv(a) * _v(mo, t + (CARD_T - a)) for a in mo.a)
    if not hasattr(expr, "is_expression_type"):
        return pyo.Constraint.Feasible
    return expr <= wr
model.ttb = pyo.Constraint(model.t, rule=ttb_rule, doc="post terminal timber bounds (m3)")


def matd1_rule(mo, t):
    # maize after tobacco: type 1 -- matd1(t-1): mat(t) =l= x(t-1,tobacco)
    if t - 1 < 1:
        return pyo.Constraint.Skip
    return mo.mat[t] <= mo.x[t - 1, "tobacco"]
model.matd1 = pyo.Constraint(model.t, rule=matd1_rule, doc="maize after tobacco: type 1 (ha)")


def matd2_rule(mo, t):
    # maize after tobacco: type 2
    return mo.mat[t] <= mo.x[t, "maize"]
model.matd2 = pyo.Constraint(model.t, rule=matd2_rule, doc="maize after tobacco: type 2 (ha)")


def rd_rule(mo, t):
    # revenue definition
    return mo.rev[t] == (sum(cr[c] * mo.x[t, c] for c in mo.c) + matr * cr["maize"] * mo.mat[t]) / 1000
model.rd = pyo.Constraint(model.t, rule=rd_rule, doc="revenue definition (1000 tsh)")


def cd_rule(mo, t):
    # cost definition
    return mo.cost[t] == (sum(cc[c] * mo.x[t, c] for c in mo.c) + tc * mo.v[t]
                          + resw * whd * sum(mo.lc[t, mc] for mc in mo.mc)
                          + sum(tr * yw * dist[i] * mo.w[t, i] for i in mo.i)) / 1000
model.cd = pyo.Constraint(model.t, rule=cd_rule, doc="cost definition (1000 tsh)")


def od_rule(mo):
    # objective definition
    return mo.income == sum(delt[t] * (mo.rev[t] - mo.cost[t] + vr[t] * mo.v[t] / 1000) for t in mo.t)
model.od = pyo.Constraint(rule=od_rule, doc="objective definition (discounted 1000 tsh)")

# ── Objective ─────────────────────────────────────────────────────────────────
model.obj = pyo.Objective(expr=model.income, sense=pyo.maximize, doc="maximize discounted income")
