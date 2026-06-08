# converted from gamslib tfordy (TFORDY, SEQ=62)
# Antalya Forestry Model - Dynamic. Single core LP (case "antalb":
# all equations except the optional sustained-yield variants sy1/sy3/sy4
# and the cutting restriction wbnd). Scenario/reporting re-solves dropped.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "te|at|s|cl": value → tuple key).
# wpos / vpos are sparse 2-tuple index sets (lists of [a, b] pairs).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Antalya Forestry Model - dynamic forest management LP")

# Sets
model.c = pyo.Set(initialize=data["c"], doc="commodities")
model.cf = pyo.Set(initialize=data["cf"], doc="final products")
model.cl = pyo.Set(initialize=data["cl"], doc="log types")
model.s = pyo.Set(initialize=data["s"], doc="species")
model.k = pyo.Set(initialize=data["k"], doc="site classes")
model.at = pyo.Set(initialize=data["at"], doc="tree age")
model.u = pyo.Set(initialize=data["u"], doc="initial age")
model.p = pyo.Set(initialize=data["p"], doc="processes")
model.m = pyo.Set(initialize=data["m"], doc="productive units")
model.te = pyo.Set(initialize=data["te"], doc="extended horizon")
model.t = pyo.Set(initialize=data["t"], doc="model horizon")

# Sparse possibility sets (2-tuples)
model.wpos = pyo.Set(dimen=2, initialize=[tuple(x) for x in data["wpos"]], doc="w possibility (u,te)")
model.vpos = pyo.Set(dimen=2, initialize=[tuple(x) for x in data["vpos"]], doc="v possibility (t,te)")

# Ordered list of horizon periods for the "previous period" (te-1) logic.
_te_list = list(data["te"])
_te_prev = {_te_list[i]: _te_list[i - 1] for i in range(1, len(_te_list))}

# Scalar parameters
model.mup = pyo.Param(initialize=data["mup"], mutable=True, doc="planting cost (us$ per ha)")
model.muc = pyo.Param(initialize=data["muc"], mutable=True, doc="cutting cost (us$ per m3)")
model.sgm = pyo.Param(initialize=data["sgm"], mutable=True, doc="capital recovery factor")

# Indexed parameters
model.scd = pyo.Param(model.k, initialize=data["scd"], mutable=True, doc="site class distribution")
model.land = pyo.Param(model.s, initialize=data["land"], mutable=True, doc="land available (1000ha)")
model.pc = pyo.Param(model.p, initialize=data["pc"], mutable=True, doc="process cost (us$ per m3 input)")
model.pd = pyo.Param(model.cf, initialize=data["pd"], mutable=True, doc="sales price (us$ per unit)")
model.nu = pyo.Param(model.m, initialize=data["nu"], mutable=True, doc="investment cost (us$ per m3 input)")
model.delt = pyo.Param(model.t, initialize=data["delt"], mutable=True, doc="discount factors")

model.a = pyo.Param(model.c, model.p, initialize=data["a"], default=0.0, mutable=True, doc="input output matrix")
model.b = pyo.Param(model.m, model.p, initialize=data["b"], default=0.0, mutable=True, doc="capacity utilization")
model.avl = pyo.Param(model.t, model.te, initialize=data["avl"], default=0.0, mutable=True, doc="plant live in periods")
model.iad = pyo.Param(model.at, model.s, initialize=data["iad"], default=0.0, mutable=True, doc="initial age distribution (proportions)")

model.yw = pyo.Param(model.te, model.at, model.s, model.cl, initialize=data["yw"], default=0.0, mutable=True, doc="yield of existing forest (m3 per ha)")
model.yv = pyo.Param(model.t, model.te, model.s, model.cl, model.k, initialize=data["yv"], default=0.0, mutable=True, doc="yield of managed forest (m3 per ha)")

# Variables (Positive). w/v defined only over sparse possibility sets.
model.w = pyo.Var(model.s, model.k, model.wpos, domain=pyo.NonNegativeReals, doc="cutting of existing forest (1000ha/yr)")
model.v = pyo.Var(model.s, model.k, model.vpos, domain=pyo.NonNegativeReals, doc="management of new forest (1000ha/yr)")
model.r = pyo.Var(model.cl, model.te, domain=pyo.NonNegativeReals, doc="supply of logs to industry (1000m3/yr)")
model.z = pyo.Var(model.p, model.t, domain=pyo.NonNegativeReals, doc="process level (1000m3 input/yr)")
model.h = pyo.Var(model.m, model.t, domain=pyo.NonNegativeReals, doc="capacity expansion (1000m3 input/yr)")
model.x = pyo.Var(model.c, model.t, domain=pyo.NonNegativeReals, doc="final shipments (1000 units/yr)")
model.phik = pyo.Var(model.t, domain=pyo.Reals, doc="investment cost (1000us$/yr)")
model.phir = pyo.Var(model.t, domain=pyo.Reals, doc="process cost (1000us$/yr)")
model.phix = pyo.Var(model.t, domain=pyo.Reals, doc="sales revenue (1000us$/yr)")
model.phil = pyo.Var(model.t, domain=pyo.Reals, doc="cutting cost (1000us$/yr)")
model.phip = pyo.Var(model.t, domain=pyo.Reals, doc="planting cost (1000us$/yr)")
model.phi = pyo.Var(domain=pyo.Reals, doc="total benefits (discounted)")

# Helper membership sets for fast lookups
_wpos = set(model.wpos)
_vpos = set(model.vpos)


# ── Constraints ──────────────────────────────────────────────────────────────

# efs(s,k,u): existing forest stock
def efs_rule(model, s, k, u):
    return 10 * sum(model.w[s, k, u, t] for t in model.t if (u, t) in _wpos) \
        <= model.iad[u, s] * model.scd[k] * model.land[s]
model.efs = pyo.Constraint(model.s, model.k, model.u, rule=efs_rule, doc="existing forest stock (1000ha)")


# pfs(s,k,t): planted forest stock
def pfs_rule(model, s, k, t):
    lhs = sum(model.v[s, k, t, te] for te in model.te if (t, te) in _vpos)
    rhs = sum(model.w[s, k, u, t] for u in model.u if (u, t) in _wpos) \
        + sum(model.v[s, k, tp, t] for tp in model.t if (tp, t) in _vpos)
    return lhs <= rhs
model.pfs = pyo.Constraint(model.s, model.k, model.t, rule=pfs_rule, doc="planted forest stock (1000ha)")


# lbal(cl,te): log balances
def lbal_rule(model, cl, te):
    managed = sum(model.yv[t, te, s, cl, k] * model.v[s, k, t, te]
                  for k in model.k for s in model.s for t in model.t if (t, te) in _vpos)
    existing = sum(model.yw[te, u, s, cl] * model.w[s, k, u, te]
                   for k in model.k for s in model.s for u in model.u if (u, te) in _wpos)
    return model.r[cl, te] == managed + existing
model.lbal = pyo.Constraint(model.cl, model.te, rule=lbal_rule, doc="log balances")


# sy2(cl, te-1): sustained yield by log type. For each te that has a previous
# period, r(cl,te) >= r(cl,te-1).
def sy2_rule(model, cl, te):
    if te not in _te_prev:
        return pyo.Constraint.Skip
    return model.r[cl, te] >= model.r[cl, _te_prev[te]]
model.sy2 = pyo.Constraint(model.cl, model.te, rule=sy2_rule, doc="sustained yield - log type")


# bal(c,t): material balances of wood processing
def bal_rule(model, c, t):
    expr = sum(model.a[c, p] * model.z[p, t] for p in model.p)
    if c in model.cl:
        expr = expr + model.r[c, t]
    rhs = model.x[c, t] if c in model.cf else 0
    return expr >= rhs
model.bal = pyo.Constraint(model.c, model.t, rule=bal_rule, doc="material balances of wood processing")


# cap(m,t): wood processing capacities
def cap_rule(model, m, t):
    return sum(model.b[m, p] * model.z[p, t] for p in model.p) \
        <= sum(model.h[m, tp] for tp in model.t if (t, tp) in model.avl and pyo.value(model.avl[t, tp]) != 0)
model.cap = pyo.Constraint(model.m, model.t, rule=cap_rule, doc="wood processing capacities")


# ainvc(t): investment cost
def ainvc_rule(model, t):
    return model.phik[t] == model.sgm * sum(
        model.nu[m] * model.h[m, tp]
        for tp in model.t if pyo.value(model.avl[t, tp]) != 0 for m in model.m)
model.ainvc = pyo.Constraint(model.t, rule=ainvc_rule, doc="investment cost")


# aproc(t): process cost
def aproc_rule(model, t):
    return model.phir[t] == sum(model.pc[p] * model.z[p, t] for p in model.p)
model.aproc = pyo.Constraint(model.t, rule=aproc_rule, doc="process cost")


# asales(t): sales revenue
def asales_rule(model, t):
    return model.phix[t] == sum(model.pd[cf] * model.x[cf, t] for cf in model.cf)
model.asales = pyo.Constraint(model.t, rule=asales_rule, doc="sales revenue")


# acutc(t): cutting cost
def acutc_rule(model, t):
    return model.phil[t] == model.muc * sum(model.r[cl, t] for cl in model.cl)
model.acutc = pyo.Constraint(model.t, rule=acutc_rule, doc="cutting cost")


# aplnt(t): planting cost
def aplnt_rule(model, t):
    return model.phip[t] == model.mup * sum(
        model.v[s, k, t, te] for s in model.s for k in model.k
        for te in model.te if (t, te) in _vpos)
model.aplnt = pyo.Constraint(model.t, rule=aplnt_rule, doc="planting cost")


# benefit: total discounted net benefit
def benefit_rule(model):
    return model.phi == sum(
        model.delt[t] * (model.phix[t] - model.phik[t] - model.phir[t]
                         - model.phil[t] - model.phip[t]) for t in model.t)
model.benefit = pyo.Constraint(rule=benefit_rule, doc="total benefits")


# Objective: maximize total discounted net benefit
model.obj = pyo.Objective(expr=model.phi, sense=pyo.maximize, doc="Maximize total discounted net benefit")
