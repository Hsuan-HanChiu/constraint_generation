# converted from gamslib cbenders (CBENDERS, SEQ=415)
#
# Source GAMS solves a facility-location MIP via Cplex Benders decomposition.
# The Benders/cut/iteration scaffolding (BendersStrategy option files, the
# cpxOptFile 1..4 loop, the SCIP re-solve) is solver machinery only — the
# underlying single model is the monolithic extensive-form MIP `loc / all /`.
# That monolithic MIP is what is converted here; it converges to totcost = 11661.
#
# The random parameters ck(i,k) and dk(j,k) in the GAMS source are drawn from
# uniform() and rounded; the exact realized values (the ones that yield 11661)
# are extracted from a GAMS run and baked into the data file so the model is
# deterministic. Parameters c(i) and d(j) only seeded those random draws and
# never appear in any constraint, so they are omitted (they would be dead).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "w1|k1": value → (w1, k1): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Facility location MIP (monolithic extensive form of the CBENDERS Benders model)")

# Sets
model.i = pyo.Set(initialize=data["i"], doc="Warehouses")
model.j = pyo.Set(initialize=data["j"], doc="Regions")
model.k = pyo.Set(initialize=data["k"], doc="Goods")

# Parameters
model.f = pyo.Param(model.i, initialize=data["f"], mutable=True, within=pyo.NonNegativeReals,
                    doc="Fixed cost of opening warehouse i")
model.t = pyo.Param(model.j, model.i, initialize=data["t"], mutable=True, within=pyo.NonNegativeReals,
                    doc="Transport cost from warehouse i to region j")
model.ck = pyo.Param(model.i, model.k, initialize=data["ck"], mutable=True, within=pyo.NonNegativeReals,
                     doc="Capacity of warehouse i for good k")
model.dk = pyo.Param(model.j, model.k, initialize=data["dk"], mutable=True, within=pyo.NonNegativeReals,
                     doc="Demand of region j for good k")

# Variables
model.totcost = pyo.Var(domain=pyo.Reals, doc="Total cost")
model.fcost = pyo.Var(domain=pyo.Reals, doc="Fixed cost")
model.tcost = pyo.Var(model.k, domain=pyo.Reals, doc="Transportation cost per good")
model.ow = pyo.Var(model.i, domain=pyo.Binary, doc="Open warehouse i")
model.oa = pyo.Var(model.i, model.j, domain=pyo.Binary, doc="Open shipment arc i→j")
model.x = pyo.Var(model.i, model.j, model.k, domain=pyo.NonNegativeReals,
                  doc="Shipment of good k on arc i→j")

# Constraints
def deftotcost_rule(model):
    return model.totcost == model.fcost + sum(model.tcost[k] for k in model.k)
model.deftotcost = pyo.Constraint(rule=deftotcost_rule, doc="Definition of total cost")

def deffcost_rule(model):
    return model.fcost == sum(model.f[i] * model.ow[i] for i in model.i)
model.deffcost = pyo.Constraint(rule=deffcost_rule, doc="Definition of fixed cost")

def deftcost_rule(model, k):
    return model.tcost[k] == sum(model.t[j, i] * model.x[i, j, k] for i in model.i for j in model.j)
model.deftcost = pyo.Constraint(model.k, rule=deftcost_rule, doc="Definition of transportation cost")

def defwcap_rule(model, i, k):
    return sum(model.x[i, j, k] for j in model.j) <= model.ck[i, k]
model.defwcap = pyo.Constraint(model.i, model.k, rule=defwcap_rule, doc="Warehouse capacity limit")

def defwdem_rule(model, j, k):
    return sum(model.x[i, j, k] for i in model.i) >= model.dk[j, k]
model.defwdem = pyo.Constraint(model.j, model.k, rule=defwdem_rule, doc="Demand satisfaction")

def twow_rule(model, j):
    return sum(model.oa[i, j] for i in model.i) <= 2
model.twow = pyo.Constraint(model.j, rule=twow_rule, doc="At most two warehouses per region")

def defow_rule(model, i, j):
    return model.ow[i] >= model.oa[i, j]
model.defow = pyo.Constraint(model.i, model.j, rule=defow_rule, doc="Warehouse open if any shipment from it")

def defx_rule(model, i, j, k):
    return model.ck[i, k] * model.oa[i, j] >= model.x[i, j, k]
model.defx = pyo.Constraint(model.i, model.j, model.k, rule=defx_rule, doc="Shipment only on open arc")

# Objective
model.obj = pyo.Objective(expr=model.totcost, sense=pyo.minimize, doc="Minimize total cost")
