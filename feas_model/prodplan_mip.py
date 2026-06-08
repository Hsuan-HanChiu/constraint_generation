# converted from gamslib prodplan (PRODPLAN, SEQ=356)
# Uncapacitated lot-sizing problem: least-cost production plan meeting demand.
# Underlying single optimization model = the original MIP ("tiny" in the GAMS
# source). The four GAMS solves (MIP, two tight RMIP reformulations, and an
# RMIP separation algorithm) all describe THIS model; the scenario/reporting
# re-solves and the iterative cut-generation loop are dropped.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params.
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Production Planning - uncapacitated lot-sizing (least cost)")

# Sets
model.t = pyo.Set(initialize=data["t"], ordered=True, doc="Time periods")

# Scalar parameters
model.setupcost = pyo.Param(initialize=data["setupcost"], mutable=True, doc="Setup cost per period")
model.prodcost = pyo.Param(initialize=data["prodcost"], mutable=True, doc="Production cost per unit")
model.invcost = pyo.Param(initialize=data["invcost"], mutable=True, doc="Inventory cost per unit")
model.stockini = pyo.Param(initialize=data["stockini"], mutable=True, doc="Initial stock")

# Indexed parameters
model.demand = pyo.Param(model.t, initialize=data["demand"], mutable=True,
                         within=pyo.NonNegativeReals, doc="Demand per period")
model.bigM = pyo.Param(model.t, initialize=data["bigM"], mutable=True,
                       within=pyo.NonNegativeReals, doc="Max production upper bound (big-M)")

# Per-period inventory-holding cost coefficient: INVCOST for all but the last
# period, INVCOST/2 in the final period (GAMS: ifthen(ord(t)<card(t), INVCOST, INVCOST/2)).
_t_list = list(data["t"])
_last_t = _t_list[-1]
def _invcoef_init(model, t):
    return model.invcost if t != _last_t else model.invcost / 2
model.invcoef = pyo.Param(model.t, initialize=_invcoef_init, mutable=True,
                          doc="Per-period inventory holding cost coefficient")

# Variables
model.s = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="Inventory at end of period t")
model.x = pyo.Var(model.t, domain=pyo.NonNegativeReals, doc="Production in period t")
model.y = pyo.Var(model.t, domain=pyo.Binary, doc="Setup indicator in period t")
model.cost = pyo.Var(domain=pyo.Reals, doc="Total cost")

# Constraints
def production_rule(model, t):
    # x(t) <= BigM(t) * y(t): production only if machine is set up
    return model.x[t] <= model.bigM[t] * model.y[t]
model.production = pyo.Constraint(model.t, rule=production_rule, doc="Production set-up linking")

def balance_rule(model, t):
    # STOCKINI[t=first] + s(t-1) + x(t) =e= DEMAND(t) + s(t)
    prev = model.s[model.t.prev(t)] if t != _t_list[0] else 0
    ini = model.stockini if t == _t_list[0] else 0
    return ini + prev + model.x[t] == model.demand[t] + model.s[t]
model.balance = pyo.Constraint(model.t, rule=balance_rule, doc="Stock balance")

def mincost_rule(model):
    return model.cost == (
        sum(model.invcoef[t] * model.s[t] for t in model.t)
        + sum(model.setupcost * model.y[t] + model.prodcost * model.x[t] for t in model.t)
    )
model.mincost = pyo.Constraint(rule=mincost_rule, doc="Cost accounting")

# Objective
model.obj = pyo.Objective(expr=model.cost, sense=pyo.minimize, doc="Minimize total cost")
