# converted from models/yemcem_mip.py
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

# Sets
model.I = pyo.Set(initialize=data["i"], doc="plants")
model.J = pyo.Set(initialize=data["j"], doc="markets")
model.M = pyo.Set(initialize=data["m"], doc="productive units")
model.P = pyo.Set(initialize=data["p"], doc="processes")
model.C = pyo.Set(initialize=data["c"], doc="commodities for material balance")
model.CF = pyo.Set(initialize=data["cf"], doc="final products")
model.CI = pyo.Set(initialize=data["ci"], doc="imported intermediates")
model.T = pyo.Set(initialize=data["t"], doc="time periods")
model.TE = pyo.Set(initialize=data["te"], doc="expansion periods")
model.S = pyo.Set(initialize=data["s"], doc="kiln sizes")
model.MS = pyo.Set(initialize=data["ms"], doc="units with scale economies")
model.MP = pyo.Set(initialize=data["mp"], doc="units without scale economies")

# Parameters

def a_init(m, c, p):
    return data["a"].get((c, p), 0.0)

model.a = pyo.Param(
    model.C, model.P, mutable=True, initialize=a_init, doc="input-output coeff"
)

def b_init(m, mm, p):
    return data["b"].get((mm, p), 0.0)

model.b = pyo.Param(
    model.M, model.P, mutable=True, initialize=b_init, doc="capacity utilization"
)

def k_init(m, mm, i):
    return data["k"].get((mm, i), 0.0)

model.k = pyo.Param(
    model.M, model.I, mutable=True, initialize=k_init, doc="base capacity 1982"
)

def ts_init(m, t, tp):
    return data["ts"].get((t, tp), 0.0)

model.ts = pyo.Param(
    model.T, model.TE, mutable=True, initialize=ts_init, doc="time summation matrix"
)

model.klim = pyo.Param(
    model.I, mutable=True, initialize=data["klim"], doc="kiln capacity limit"
)

model.rc = pyo.Param(
    model.P, mutable=True, initialize=data["rc"], doc="recurrent process cost"
)
model.fc = pyo.Param(
    model.M, mutable=True, initialize=data["fc"], doc="fixed cost per ton"
)

model.sigma = pyo.Param(
    mutable=True, initialize=data["sigma"], doc="capital recovery factor"
)

model.delta = pyo.Param(
    model.T, mutable=True, initialize=data["delta"], doc="discount factors"
)

model.site = pyo.Param(
    model.I, mutable=True, initialize=data["site"], doc="site factor"
)

model.size = pyo.Param(
    model.S, mutable=True, initialize=data["size"], doc="kiln size"
)

def inv_cost_init(m, mm):
    return data["inv"].get((mm, "cost"), 0.0)

def inv_size_init(m, mm):
    return data["inv"].get((mm, "size"), 1.0)

def inv_scale_init(m, mm):
    return data["inv"].get((mm, "scale"), 1.0)

model.inv_cost = pyo.Param(
    model.M, mutable=True, initialize=inv_cost_init, doc="investment cost"
)
model.inv_size = pyo.Param(
    model.M, mutable=True, initialize=inv_size_init, doc="investment size base"
)
model.inv_scale = pyo.Param(
    model.M, mutable=True, initialize=inv_scale_init, doc="investment scale factor"
)

def muf_init(m, i, j):
    return data["muf"].get((i, j), 0.0)

model.muf = pyo.Param(
    model.I, model.J, mutable=True, initialize=muf_init, doc="cement transport cost"
)

model.muv = pyo.Param(
    model.J, mutable=True, initialize=data["muv"], doc="import transport cost"
)

model.mue = pyo.Param(
    model.I, mutable=True, initialize=data["mue"], doc="export transport cost"
)

def mui_init(m, c, i):
    return data["mui"].get((c, i), 0.0)

model.mui = pyo.Param(
    model.CI,
    model.I,
    mutable=True,
    initialize=mui_init,
    doc="intermediate import transport cost",
)

model.ebu = pyo.Param(
    model.T, mutable=True, initialize=data["ebu"], doc="export upper bound"
)
model.vbu = pyo.Param(
    model.T, mutable=True, initialize=data["vbu"], doc="cement import upper bound"
)
model.vibu = pyo.Param(
    model.T, mutable=True, initialize=data["vibu"], doc="clinker import upper bound"
)

model.pv = pyo.Param(
    model.CF | model.CI,
    mutable=True,
    initialize=data["pv"],
    doc="import prices",
)

def d_init(m, j, t, cf):
    return data["d"].get((j, t, cf), 0.0)

model.d = pyo.Param(
    model.J,
    model.T,
    model.CF,
    mutable=True,
    initialize=d_init,
    doc="regional demand",
)

# Variables
model.z = pyo.Var(
    model.P, model.I, model.T, domain=pyo.NonNegativeReals, doc="process level"
)
model.x = pyo.Var(
    model.CF, model.I, model.J, model.T,
    domain=pyo.NonNegativeReals,
    doc="cement shipments",
)
model.v = pyo.Var(
    model.CF, model.J, model.T,
    domain=pyo.NonNegativeReals,
    doc="cement imports",
)
model.vi = pyo.Var(
    model.CI, model.I, model.T,
    domain=pyo.NonNegativeReals,
    doc="imports of intermediates",
)
model.e = pyo.Var(
    model.CF, model.I, model.T,
    domain=pyo.NonNegativeReals,
    doc="cement exports",
)
model.h = pyo.Var(
    model.M, model.I, model.TE,
    domain=pyo.NonNegativeReals,
    doc="capacity expansion",
)
model.y = pyo.Var(
    model.MS, model.I, model.S, model.TE,
    domain=pyo.Binary,
    doc="binary investment",
)

model.phi = pyo.Var(domain=pyo.Reals, doc="total discounted cost")

model.phikap = pyo.Var(model.T, domain=pyo.Reals, doc="capital investment")
model.phipsi = pyo.Var(model.T, domain=pyo.Reals, doc="recurrent cost")
model.philam = pyo.Var(model.T, domain=pyo.Reals, doc="transport cost")
model.phipi = pyo.Var(model.T, domain=pyo.Reals, doc="import cost")
model.phieps = pyo.Var(model.T, domain=pyo.Reals, doc="export revenue")
model.phiw = pyo.Var(model.T, domain=pyo.Reals, doc="working capital")

# Constraints

# Material balances (GAMS: mb(c,i,t).. sum(p,a(c,p)*z) + vi(c,i,t)$ci(c) =g= (sum(j,x(c,i,j,t))+e(c,i,t))$cf(c);)
def mb_rule(m, c, i, t):
    lhs = sum(m.a[c, p] * m.z[p, i, t] for p in m.P)
    if c in m.CI:
        lhs += m.vi[c, i, t]
    rhs = 0.0
    if c in m.CF:
        rhs = sum(m.x[c, i, j, t] for j in m.J) + m.e[c, i, t]
    return lhs >= rhs

model.mb = pyo.Constraint(
    model.C, model.I, model.T, rule=mb_rule, doc="material balances"
)

# Capacity constraints
# cc(m,i,t).. sum(p, b(m,p)*z(p,i,t)) =l= k(m,i) + sum(tp$ts(t,tp), h(m,i,tp));
def cc_rule(m, mm, i, t):
    lhs = sum(m.b[mm, p] * m.z[p, i, t] for p in m.P)
    rhs = m.k[mm, i] + sum(m.ts[t, tp] * m.h[mm, i, tp] for tp in m.TE)
    return lhs <= rhs

model.cc = pyo.Constraint(
    model.M, model.I, model.T, rule=cc_rule, doc="capacity constraints"
)

# Investment definition (ms)
# id(ms,i,te)..  h(ms,i,te) =e= sum(s, size(s)*y(ms,i,s,te));
def id_rule(m, mm, i, te):
    return m.h[mm, i, te] == sum(m.size[s] * m.y[mm, i, s, te] for s in m.S)

model.id = pyo.Constraint(
    model.MS, model.I, model.TE, rule=id_rule, doc="investment definition"
)

# At most one size per expansion decision
# ich(ms,i,te).. sum(s, y(ms,i,s,te)) =l= 1.0;
def ich_rule(m, mm, i, te):
    return sum(m.y[mm, i, s, te] for s in m.S) <= 1.0

model.ich = pyo.Constraint(
    model.MS, model.I, model.TE, rule=ich_rule, doc="investment choice"
)

# Capacity limit per plant
# limit(i).. sum(ms, k(ms,i) + sum(te, h(ms,i,te))) =l= klim(i);
def limit_rule(m, i):
    return sum(
        m.k[mm, i] + sum(m.h[mm, i, te] for te in m.TE)
        for mm in m.MS
    ) <= m.klim[i]

model.limit = pyo.Constraint(model.I, rule=limit_rule, doc="capacity limit")

# Market requirements
# mr(cf,j,t)..   sum(i, x(cf,i,j,t)) + v(cf,j,t) =g= d(j,t,cf);
def mr_rule(m, cf, j, t):
    return sum(m.x[cf, i, j, t] for i in m.I) + m.v[cf, j, t] >= m.d[j, t, cf]

model.mr = pyo.Constraint(
    model.CF, model.J, model.T, rule=mr_rule, doc="market requirements"
)

# Export limit
# eb(t)..        sum((cf,i), e(cf,i,t))    =l= ebu(t);
def eb_rule(m, t):
    return sum(m.e[cf, i, t] for cf in m.CF for i in m.I) <= m.ebu[t]

model.eb = pyo.Constraint(model.T, rule=eb_rule, doc="export limit")

# Cement import limit
# vb(t)..        sum((cf,j), v(cf,j,t))    =l= vbu(t);
def vb_rule(m, t):
    return sum(m.v[cf, j, t] for cf in m.CF for j in m.J) <= m.vbu[t]

model.vb = pyo.Constraint(model.T, rule=vb_rule, doc="cement import limit")

# Clinker import limit
# vib(t)..       sum(i, vi("clinker",i,t)) =l= vibu(t);
def vib_rule(m, t):
    return sum(m.vi["clinker", i, t] for i in m.I) <= m.vibu[t]

model.vib = pyo.Constraint(model.T, rule=vib_rule, doc="clinker import limit")

# Objective definition
# obj..  phi =e= sum(t, delta(t)*(phikap(t)+phipsi(t)+philam(t)+phipi(t)+phiw(t)-phieps(t)));
def obj_def_rule(m):
    return m.phi == sum(
        m.delta[t]
        * (
            m.phikap[t]
            + m.phipsi[t]
            + m.philam[t]
            + m.phipi[t]
            + m.phiw[t]
            - m.phieps[t]
        )
        for t in m.T
    )

model.obj_def = pyo.Constraint(rule=obj_def_rule, doc="objective definition")

# Recurrent cost account
# apsi(t).. phipsi(t) =e= .001*(sum((p,i), rc(p)*z(p,i,t))
#                  +  sum((i,m), fc(m)*(k(m,i) + sum(tp$ts(t,tp), h(m,i,tp))));
def apsi_rule(m, t):
    proc_cost = sum(m.rc[p] * m.z[p, i, t] for p in m.P for i in m.I)
    fixed_cost = sum(
        m.fc[mm]
        * (
            m.k[mm, i]
            + sum(m.ts[t, tp] * m.h[mm, i, tp] for tp in m.TE)
        )
        for mm in m.M for i in m.I
    )
    return m.phipsi[t] == 0.001 * (proc_cost + fixed_cost)

model.apsi = pyo.Constraint(
    model.T, rule=apsi_rule, doc="recurrent cost account"
)

# Investment cost account
# akap(t).. phikap(t) =e= sigma*sum(tp$ts(t,tp),
#      sum((ms,i,s), site(i)*inv(ms,s)*y(ms,i,s,tp))
#    + sum((mp,i),   site(i)*inv(mp,"prop")*h(mp,i,tp)));
def akap_rule(m, t):
    inv_ms = sum(
        m.site[i]
        * (
            m.inv_cost[mm]
            * (m.size[s] / m.inv_size[mm]) ** m.inv_scale[mm]
        )
        * m.y[mm, i, s, tp]
        * m.ts[t, tp]
        for mm in m.MS
        for i in m.I
        for s in m.S
        for tp in m.TE
    )
    inv_mp = sum(
        m.site[i]
        * (m.inv_cost[mm] / m.inv_size[mm])
        * m.h[mm, i, tp]
        * m.ts[t, tp]
        for mm in m.MP
        for i in m.I
        for tp in m.TE
    )
    return m.phikap[t] == m.sigma * (inv_ms + inv_mp)

model.akap = pyo.Constraint(
    model.T, rule=akap_rule, doc="investment cost account"
)

# Transport cost account
# alam(t).. philam(t) =e= .001*(sum(cf,  sum((i,j), muf(i,j)*x(cf,i,j,t))
#                                   + sum(j, muv(j)*v(cf,j,t))
#                                   + sum(i, mue(i)*e(cf,i,t)))
#                          + sum((ci,i), mui(ci,i)*vi(ci,i,t)));
def alam_rule(m, t):
    cement_part = (
        sum(
            m.muf[i, j] * m.x[cf, i, j, t]
            for cf in m.CF for i in m.I for j in m.J
        )
        + sum(
            m.muv[j] * m.v[cf, j, t]
            for cf in m.CF for j in m.J
        )
        + sum(
            m.mue[i] * m.e[cf, i, t]
            for cf in m.CF for i in m.I
        )
    )
    interm_part = sum(
        m.mui[c, i] * m.vi[c, i, t]
        for c in m.CI for i in m.I
    )
    return m.philam[t] == 0.001 * (cement_part + interm_part)

model.alam = pyo.Constraint(
    model.T, rule=alam_rule, doc="transport cost account"
)

# Export revenue account
# aeps(t)..  phieps(t) =e= .001*sum((cf,i), e(cf,i,t));
def aeps_rule(m, t):
    return m.phieps[t] == 0.001 * sum(
        m.e[cf, i, t] for cf in m.CF for i in m.I
    )

model.aeps = pyo.Constraint(
    model.T, rule=aeps_rule, doc="export revenue account"
)

# Import cost account
# api(t)..   phipi(t)  =e= .001*(sum((cf,j), pv(cf)*v(cf,j,t))
#                               + sum((ci,i), pv(ci)*vi(ci,i,t)));
def api_rule(m, t):
    cement_imports = sum(
        m.pv[cf] * m.v[cf, j, t]
        for cf in m.CF for j in m.J
    )
    interm_imports = sum(
        m.pv[c] * m.vi[c, i, t]
        for c in m.CI for i in m.I
    )
    return m.phipi[t] == 0.001 * (cement_imports + interm_imports)

model.api = pyo.Constraint(
    model.T, rule=api_rule, doc="import cost account"
)

# Working capital account
# aw(t)..    phiw(t)   =e= .25*.1*(phipsi(t) + phipi(t));
def aw_rule(m, t):
    return m.phiw[t] == 0.25 * 0.1 * (m.phipsi[t] + m.phipi[t])

model.aw = pyo.Constraint(
    model.T, rule=aw_rule, doc="working capital account"
)

# Objective
model.obj = pyo.Objective(expr=model.phi, sense=pyo.minimize)

# Scenario fix in GAMS: y("dry-kiln","mafrak","small","1986-88") = 1;
try:
    model.y["dry-kiln", "mafrak", "small", "1986-88"].fix(1)
except KeyError:
    pass
