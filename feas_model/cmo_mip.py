# converted from models/cmo_mip.py
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel()

# =====================
# Sets
# =====================
I_list = list(data["i"])
N_list = list(data["n"])
M_list = list(data["m"])
TP_list = sorted(data["tp"])
T_list = sorted(data["t"])
TS_list = list(data["ts"])
TL_list = list(data["tl"])
TL = TL_list[0]

model.I = pyo.Set(initialize=I_list, doc="tranches")
model.N = pyo.Set(within=model.I, initialize=N_list, doc="normal tranches")
model.M = pyo.Set(within=model.I, initialize=M_list, doc="M tranches")
model.TP = pyo.Set(ordered=True, initialize=TP_list, doc="time periods including settlement")
model.T = pyo.Set(within=model.TP, ordered=True, initialize=T_list, doc="payment periods")
model.TS = pyo.Set(within=model.TP, initialize=TS_list, doc="settlement dates")
model.TL = pyo.Set(within=model.TP, initialize=TL_list, doc="last payment periods")

ord_tp = {tp: idx for idx, tp in enumerate(TP_list, start=1)}
ord_t = {t: idx for idx, t in enumerate(T_list, start=1)}
card_tp = len(TP_list)

# =====================
# Scalars from data
# =====================
cg = float(data["cg"])
nom = float(data["nom"])
s = float(data["s"])
psa = float(data["psa"])
d = float(data["d"])
minn = float(data["minn"])
minm = float(data["minm"])

# tranches table
tr = {}
for key, val in data["tranches"].items():
    if isinstance(key, tuple):
        row, col = key
    else:
        row, col = str(key).split("|")
    tr[(row, col)] = float(val)

# =====================
# Preprocessing (GAMS style)
# =====================
tmax = max(T_list)
age = (360.0 - tmax * 12.0 / d) / 12.0

b = {}
for t in T_list:
    b[t] = 0.06 * (psa / 100.0) * min((ord_t[t] + age * d) / (d * 2.5), 1.0)

cd = (1.0 + cg / 12.0) ** (12.0 / d) - 1.0
sd = (1.0 + s / 12.0) ** (12.0 / d) - 1.0
yr = (1.0 + tr[("r", "yield")] / 12.0) ** (12.0 / d) - 1.0

coupon = {}
yld_tr = {}
for i in I_list:
    cpn = tr[(i, "coupon")]
    yld = tr[(i, "yield")]
    coupon[i] = (1.0 + cpn / 12.0) ** (12.0 / d) - 1.0
    yld_tr[i] = (1.0 + yld / 12.0) ** (12.0 / d) - 1.0

wallo = {n: tr[(n, "low-wal")] * d for n in N_list}
walup = {n: tr[(n, "up-wal")] * d for n in N_list}

cmax = max(coupon.values())
a = nom * cd / (1.0 - (1.0 + cd) ** (-tmax))

po = {}
for tp in TP_list:
    j = ord_tp[tp]
    po[tp] = nom * (1.0 - (1.0 + cd) ** (j - 1 - tmax)) / (1.0 - (1.0 + cd) ** (-tmax))

rev = {tp: card_tp - 2 * ord_tp[tp] + 1 for tp in TP_list}

def shift_tp(tp, k):
    j = ord_tp[tp] + k
    if 1 <= j <= card_tp:
        return TP_list[j - 1]
    return None

bv = {tp: 0.0 for tp in TP_list}
bv[TL] = 0.0

for tp in TP_list:
    r = rev[tp]
    i1 = shift_tp(tp, r - 1)
    i2 = shift_tp(tp, r)
    if i1 is None or i2 is None:
        continue
    bv[i1] = (bv[i2] + (a - sd * po[i1])) / (1.0 + cmax)

bvf = {}
for tp in TP_list:
    if abs(po[tp]) > 1e-8:
        bvf[tp] = min(bv[tp] / po[tp], 1.0)
    else:
        bvf[tp] = 1.0
bvf[TL] = 1.0

pe_coll = {}
ts0 = TS_list[0]
pe_coll[ts0] = nom
for t in T_list:
    prev = t - 1
    pe_coll[t] = pe_coll[prev] * (1.0 - b[t]) ** (1.0 / d) * po[t] / po[prev]

cflow = {}
prin = {}
for t in T_list:
    cflow[t] = (1.0 + cd - sd) * pe_coll[t - 1] - pe_coll[t]
    prin[t] = pe_coll[t - 1] * bvf[t - 1] - pe_coll[t] * bvf[t]

sump = sum(prin.values())
bign = sump * 0.7
smalln = sump * 0.03

psum = {ts0: 0.0}
tpsum = {ts0: 0.0}
walp = {ts0: 0.0}
for t in T_list:
    psum[t] = psum[t - 1] + prin[t]
    tpsum[t] = tpsum[t - 1] + (ord_t[t] - 1) * prin[t]
    walp[t] = tpsum[t] / psum[t] if psum[t] != 0 else 0.0

ZPOS_dict = {}
for i in I_list:
    for tp in TP_list:
        ok = True
        if i in N_list and tp in T_list:
            if walp[tp] > walup[i]:
                ok = False
        ZPOS_dict[(i, tp)] = ok

# =====================
# Params
# =====================
model.coupon = pyo.Param(model.I, initialize=coupon, mutable=True)
model.yield_tr = pyo.Param(model.I, initialize=yld_tr, mutable=True)
model.yr = pyo.Param(initialize=yr, mutable=True)
model.cflow = pyo.Param(model.T, initialize=cflow, mutable=True)
model.prin = pyo.Param(model.T, initialize=prin, mutable=True)
model.wallo = pyo.Param(model.N, initialize=wallo, mutable=True)
model.walup = pyo.Param(model.N, initialize=walup, mutable=True)
model.bign = pyo.Param(initialize=bign, mutable=True)
model.smalln = pyo.Param(initialize=smalln, mutable=True)
model.b = pyo.Param(model.T, initialize=b, mutable=True)
model.walp = pyo.Param(
    model.TP,
    initialize=lambda _m, tp: walp.get(tp, 0.0),
    mutable=True,
)

model.ZPOS = pyo.Set(
    dimen=2,
    initialize=[k for k, v in ZPOS_dict.items() if v],
    doc="allowed tranche-period combinations",
)

# =====================
# Variables
# =====================
model.x = pyo.Var(model.I, model.TP, domain=pyo.NonNegativeReals, doc="outstanding principal")

model.p = pyo.Var(model.I, model.TP, domain=pyo.Reals, doc="principal payments")
model.c = pyo.Var(model.I, model.TP, domain=pyo.NonNegativeReals, doc="cashflow in each tranche")
model.r = pyo.Var(model.T, domain=pyo.NonNegativeReals, doc="residual payments")
model.tpp = pyo.Var(model.I, domain=pyo.NonNegativeReals, doc="time * principal product")
model.z = pyo.Var(model.I, model.TP, domain=pyo.Binary, doc="tranche utilization")
model.y = pyo.Var(model.I, model.TP, domain=pyo.NonNegativeReals, doc="upper triangular structure")
model.tin = pyo.Var(model.I, domain=pyo.Binary, doc="tranche in structure")
model.pv = pyo.Var(model.I, domain=pyo.Reals, doc="PV of tranches")
model.pvres = pyo.Var(domain=pyo.Reals, doc="PV of residuals")
model.proceeds = pyo.Var(domain=pyo.Reals, doc="gross proceeds")

# p(n,t) >= 0  (matches p.lo(n,tp)=0 in GAMS)
def p_nonneg_rule(m_, n, tp):
    return m_.p[n, tp] >= 0.0

model.p_nonneg = pyo.Constraint(model.N, model.TP, rule=p_nonneg_rule)

# =====================
# Constraints
# =====================
def defpv_rule(m_, i):
    return m_.pv[i] == sum(
        m_.c[i, t] * (1.0 + m_.yield_tr[i]) ** (-ord_t[t])
        for t in m_.T
        if (i, t) in m_.ZPOS
    )

model.defpv = pyo.Constraint(model.I, rule=defpv_rule)

def defpvres_rule(m_):
    return m_.pvres == sum(m_.r[t] * (1.0 + m_.yr) ** (-ord_t[t]) for t in m_.T)

model.defpvres = pyo.Constraint(rule=defpvres_rule)

def pdef_rule(m_, i, tp):
    if tp not in m_.T or (i, tp) not in m_.ZPOS:
        return pyo.Constraint.Skip
    prev = tp - 1
    return m_.p[i, tp] == m_.x[i, prev] - m_.x[i, tp]

model.pdef = pyo.Constraint(model.I, model.TP, rule=pdef_rule)

def cdef_rule(m_, i, tp):
    if tp not in m_.T or (i, tp) not in m_.ZPOS:
        return pyo.Constraint.Skip
    prev = tp - 1
    return m_.c[i, tp] == m_.coupon[i] * m_.x[i, prev] + m_.p[i, tp]

model.cdef = pyo.Constraint(model.I, model.TP, rule=cdef_rule)

def retiren1_rule(m_, tp):
    return sum(m_.p[n, tp] for n in m_.N if (n, tp) in m_.ZPOS) == m_.prin[tp] + sum(
        m_.x[mi, tp - 1] * m_.coupon[mi] - m_.c[mi, tp]
        for mi in m_.M
        if (mi, tp) in m_.ZPOS
    )

model.retiren1 = pyo.Constraint(model.T, rule=retiren1_rule)

def retire_rule(m_, n, tp):
    if (n, tp) not in m_.ZPOS:
        return pyo.Constraint.Skip
    return m_.p[n, tp] <= m_.cflow[tp] * m_.z[n, tp]

model.retire = pyo.Constraint(model.N, model.T, rule=retire_rule)

def retirem_rule(m_, mi, tp):
    if (mi, tp) not in m_.ZPOS:
        return pyo.Constraint.Skip
    return m_.c[mi, tp] <= m_.cflow[tp] * m_.z[mi, tp]

model.retirem = pyo.Constraint(model.M, model.T, rule=retirem_rule)

def retirem1_rule(m_, mi, tp):
    if (mi, tp) not in m_.ZPOS:
        return pyo.Constraint.Skip
    return m_.p[mi, tp] <= m_.prin[tp] * m_.z[mi, tp]

model.retirem1 = pyo.Constraint(model.M, model.T, rule=retirem1_rule)

def cbal_rule(m_, tp):
    return sum(m_.c[i, tp] for i in m_.I if (i, tp) in m_.ZPOS) + m_.r[tp] == m_.cflow[tp]

model.cbal = pyo.Constraint(model.T, rule=cbal_rule)

def tppdef_rule(m_, n):
    return m_.tpp[n] == sum(
        ord_t[t] * m_.p[n, t]
        for t in m_.T
        if (n, t) in m_.ZPOS
    )

model.tppdef = pyo.Constraint(model.N, rule=tppdef_rule)

# Now use sum(ts, x(n,ts)) as in GAMS
def lowal_rule(m_, n):
    return m_.wallo[n] * sum(m_.x[n, ts] for ts in m_.TS) <= m_.tpp[n]

model.lowal = pyo.Constraint(model.N, rule=lowal_rule)

def upwal_rule(m_, n):
    return m_.walup[n] * sum(m_.x[n, ts] for ts in m_.TS) >= m_.tpp[n]

model.upwal = pyo.Constraint(model.N, rule=upwal_rule)

def seq1_rule(m_, tp):
    return sum(m_.z[i, tp] for i in m_.I if (i, tp) in m_.ZPOS) == 1.0

model.seq1 = pyo.Constraint(model.T, rule=seq1_rule)

I_order = {i: idx for idx, i in enumerate(I_list)}

def seq2_rule(m_, i, tp):
    if tp not in m_.T or tp == TL or (i, tp) not in m_.ZPOS:
        return pyo.Constraint.Skip
    return m_.y[i, tp] >= m_.y[i, tp + 1]

model.seq2 = pyo.Constraint(model.I, model.TP, rule=seq2_rule)

def ydef_rule(m_, i, tp):
    if tp not in m_.T or (i, tp) not in m_.ZPOS:
        return pyo.Constraint.Skip
    idx = I_order[i]
    if idx == 0:
        return m_.y[i, tp] == m_.z[i, tp]
    prev_i = I_list[idx - 1]
    return m_.y[i, tp] == m_.y[prev_i, tp] + m_.z[i, tp]

model.ydef = pyo.Constraint(model.I, model.TP, rule=ydef_rule)

def tindef1_rule(m_, i):
    return sum(m_.x[i, ts] for ts in m_.TS) <= m_.tin[i] * m_.bign

model.tindef1 = pyo.Constraint(model.I, rule=tindef1_rule)

def tindef2_rule(m_, i):
    return sum(m_.x[i, ts] for ts in m_.TS) >= m_.tin[i] * m_.smalln

model.tindef2 = pyo.Constraint(model.I, rule=tindef2_rule)

def ncon_rule(m_):
    return sum(m_.tin[n] for n in m_.N) >= minn

model.ncon = pyo.Constraint(rule=ncon_rule)

def mcon_rule(m_):
    return sum(m_.tin[mi] for mi in m_.M) >= minm

model.mcon = pyo.Constraint(rule=mcon_rule)

def proceeds_rule(m_):
    return m_.proceeds == sum(m_.pv[i] for i in m_.I) + m_.pvres

model.proceeds_def = pyo.Constraint(rule=proceeds_rule)

model.obj = pyo.Objective(expr=model.proceeds, sense=pyo.maximize)

# =====================
# Fixes (x,z)
# =====================
for i in I_list:
    model.x[i, TL].fix(0.0)
    for tp in T_list:
        if tp < TL and (i, tp + 1) not in model.ZPOS:
            model.x[i, tp].fix(0.0)

for i in I_list:
    for tp in TP_list:
        if (i, tp) not in model.ZPOS:
            model.z[i, tp].fix(0)

for tp in TP_list:
    if all((n, tp) not in model.ZPOS for n in N_list):
        for mi in M_list:
            model.z[mi, tp].fix(1)
