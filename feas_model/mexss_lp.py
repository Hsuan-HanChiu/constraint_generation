# converted from gamslib mexss (MEXSS, SEQ=15)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "c|p": value → (c, p): value).
#
# Derived GAMS parameters (muf, muv, mue, pd/pv/pe, d(steel,j), eb) are
# precomputed and stored directly in the JSON as mutable Params, mirroring the
# GAMS assignment statements that fill them once from the raw data tables.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Mexico Steel - small static production & distribution LP")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="steel plants")
model.j = pyo.Set(initialize=data["j"], doc="markets")
model.c = pyo.Set(initialize=data["c"], doc="commodities")
model.cf = pyo.Set(initialize=data["cf"], within=model.c, doc="final products")
model.ci = pyo.Set(initialize=data["ci"], within=model.c, doc="intermediate products")
model.cr = pyo.Set(initialize=data["cr"], within=model.c, doc="raw materials")
model.p = pyo.Set(initialize=data["p"], doc="processes")
model.m = pyo.Set(initialize=data["m"], doc="productive units")

# Parameters
model.a = pyo.Param(
    model.c, model.p,
    initialize=data["a"], default=0.0,
    mutable=True, within=pyo.Reals,
    doc="input-output coefficients",
)
model.b = pyo.Param(
    model.m, model.p,
    initialize=data["b"], default=0.0,
    mutable=True, within=pyo.Reals,
    doc="capacity utilization",
)
model.k = pyo.Param(
    model.m, model.i,
    initialize=data["k"], default=0.0,
    mutable=True, within=pyo.NonNegativeReals,
    doc="capacities of productive units (mill tpy)",
)
model.d = pyo.Param(
    model.c, model.j,
    initialize=data["d"], default=0.0,
    mutable=True, within=pyo.NonNegativeReals,
    doc="demand for steel in 1979 (mill tpy)",
)
model.muf = pyo.Param(
    model.i, model.j,
    initialize=data["muf"], default=0.0,
    mutable=True, within=pyo.NonNegativeReals,
    doc="transport rate: final products (us$ per ton)",
)
model.muv = pyo.Param(
    model.j,
    initialize=data["muv"], default=0.0,
    mutable=True, within=pyo.NonNegativeReals,
    doc="transport rate: imports (us$ per ton)",
)
model.mue = pyo.Param(
    model.i,
    initialize=data["mue"], default=0.0,
    mutable=True, within=pyo.NonNegativeReals,
    doc="transport rate: exports (us$ per ton)",
)
model.pd = pyo.Param(
    model.c,
    initialize=data["pd"], default=0.0,
    mutable=True, within=pyo.NonNegativeReals,
    doc="domestic prices (us$ per unit)",
)
model.pv = pyo.Param(
    model.c,
    initialize=data["pv"], default=0.0,
    mutable=True, within=pyo.NonNegativeReals,
    doc="import prices (us$ per unit)",
)
model.pe = pyo.Param(
    model.c,
    initialize=data["pe"], default=0.0,
    mutable=True, within=pyo.NonNegativeReals,
    doc="export prices (us$ per unit)",
)
model.eb = pyo.Param(
    initialize=data["eb"],
    mutable=True, within=pyo.NonNegativeReals,
    doc="export bound (mill tpy)",
)

# Variables
model.z = pyo.Var(model.p, model.i, domain=pyo.NonNegativeReals,
                  doc="process level (mill tpy)")
model.x = pyo.Var(model.c, model.i, model.j, domain=pyo.NonNegativeReals,
                  doc="shipment of final products (mill tpy)")
model.u = pyo.Var(model.c, model.i, domain=pyo.NonNegativeReals,
                  doc="purchase of domestic materials (mill units per year)")
model.v = pyo.Var(model.c, model.j, domain=pyo.NonNegativeReals,
                  doc="imports (mill tpy)")
model.e = pyo.Var(model.c, model.i, domain=pyo.NonNegativeReals,
                  doc="exports (mill tpy)")
model.phi = pyo.Var(domain=pyo.Reals, doc="total cost (mill us$)")
model.phipsi = pyo.Var(domain=pyo.Reals, doc="raw material cost (mill us$)")
model.philam = pyo.Var(domain=pyo.Reals, doc="transport cost (mill us$)")
model.phipi = pyo.Var(domain=pyo.Reals, doc="import cost (mill us$)")
model.phieps = pyo.Var(domain=pyo.Reals, doc="export revenue (mill us$)")

# Constraints
def mbf_rule(model, cf, i):
    return sum(model.a[cf, p] * model.z[p, i] for p in model.p) \
        >= sum(model.x[cf, i, j] for j in model.j) + model.e[cf, i]
model.mbf = pyo.Constraint(model.cf, model.i, rule=mbf_rule,
                           doc="material balances: final products")

def mbi_rule(model, ci, i):
    return sum(model.a[ci, p] * model.z[p, i] for p in model.p) >= 0
model.mbi = pyo.Constraint(model.ci, model.i, rule=mbi_rule,
                           doc="material balances: intermediates")

def mbr_rule(model, cr, i):
    return sum(model.a[cr, p] * model.z[p, i] for p in model.p) + model.u[cr, i] >= 0
model.mbr = pyo.Constraint(model.cr, model.i, rule=mbr_rule,
                           doc="material balances: raw materials")

def cc_rule(model, m, i):
    return sum(model.b[m, p] * model.z[p, i] for p in model.p) <= model.k[m, i]
model.cc = pyo.Constraint(model.m, model.i, rule=cc_rule,
                          doc="capacity constraint")

def mr_rule(model, cf, j):
    return sum(model.x[cf, i, j] for i in model.i) + model.v[cf, j] >= model.d[cf, j]
model.mr = pyo.Constraint(model.cf, model.j, rule=mr_rule,
                          doc="market requirements")

def me_rule(model, cf):
    return sum(model.e[cf, i] for i in model.i) <= model.eb
model.me = pyo.Constraint(model.cf, rule=me_rule, doc="maximum export")

def apsi_rule(model):
    return model.phipsi == sum(model.pd[cr] * model.u[cr, i]
                               for cr in model.cr for i in model.i)
model.apsi = pyo.Constraint(rule=apsi_rule, doc="accounting: raw material cost")

def alam_rule(model):
    return model.philam == (
        sum(model.muf[i, j] * model.x[cf, i, j]
            for cf in model.cf for i in model.i for j in model.j)
        + sum(model.muv[j] * model.v[cf, j]
              for cf in model.cf for j in model.j)
        + sum(model.mue[i] * model.e[cf, i]
              for cf in model.cf for i in model.i)
    )
model.alam = pyo.Constraint(rule=alam_rule, doc="accounting: transport cost")

def api_rule(model):
    return model.phipi == sum(model.pv[cf] * model.v[cf, j]
                              for cf in model.cf for j in model.j)
model.api = pyo.Constraint(rule=api_rule, doc="accounting: import cost")

def aeps_rule(model):
    return model.phieps == sum(model.pe[cf] * model.e[cf, i]
                               for cf in model.cf for i in model.i)
model.aeps = pyo.Constraint(rule=aeps_rule, doc="accounting: export revenue")

def obj_rule(model):
    return model.phi == model.phipsi + model.philam + model.phipi - model.phieps
model.obj_def = pyo.Constraint(rule=obj_rule, doc="accounting: total cost")

# Objective
model.obj = pyo.Objective(expr=model.phi, sense=pyo.minimize,
                          doc="minimize total cost (mill us$)")
