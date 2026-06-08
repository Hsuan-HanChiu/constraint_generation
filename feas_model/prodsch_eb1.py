# converted from models/prodsch_eb1.py
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
model = pyo.ConcreteModel(doc="APEX Production Scheduling Model - prod1")

# Sets
model.Q = pyo.Set(initialize=data["q"], ordered=True, doc="Quarters")
model.S = pyo.Set(initialize=data["s"], ordered=True, doc="Shifts")
model.L = pyo.Set(initialize=data["l"], ordered=True, doc="Production levels")

# Ordered helpers for previous/next quarter
q_list = list(model.Q.ordered_data())
prev_q = {}
q_ord = {}
for idx, q in enumerate(q_list):
    q_ord[q] = idx + 1
    prev_q[q] = q_list[idx - 1] if idx > 0 else None
model._prev_q = prev_q

# Scalar params
mc_val = float(data.get("mc", 100.0))
sr_val = float(data.get("sr", 2.0))
hc_val = float(data.get("hc", 900.0))
fc_val = float(data.get("fc", 150.0))
discount_base = float(data.get("discount_base", 1.03))

model.mc = pyo.Param(initialize=mc_val, mutable=True, within=pyo.Reals, doc="Material cost per motor")
model.sr = pyo.Param(initialize=sr_val, mutable=True, within=pyo.Reals, doc="Space rental per motor")
model.hc = pyo.Param(initialize=hc_val, mutable=True, within=pyo.Reals, doc="Hiring cost per employee")
model.fc = pyo.Param(initialize=fc_val, mutable=True, within=pyo.Reals, doc="Firing cost per employee")

# Raw indexed data
d_data = data.get("d", {})
lc_data = data.get("lc", {})
ei_data = data.get("ei", {})
pr_labor_data = data.get("pr_labor", {})
pr_motor_data = data.get("pr_motor", {})
sc_fixed_data = data.get("sc_fixed", {})
sc_labor_data = data.get("sc_labor", {})

# Indexed params
def d_init(model, q):
    return float(d_data.get(q, 0.0))

def lc_init(model, q):
    return float(lc_data.get(q, 0.0))

def ei_init(model, q):
    return float(ei_data.get(q, 0.0))

def pr_labor_init(model, l):
    return float(pr_labor_data.get(l, pr_labor_data.get(str(l), 0.0)))

def pr_motor_init(model, l):
    return float(pr_motor_data.get(l, pr_motor_data.get(str(l), 0.0)))

def sc_fixed_init(model, s):
    return float(sc_fixed_data.get(s, 0.0))

def sc_labor_init(model, s):
    return float(sc_labor_data.get(s, 0.0))

model.d = pyo.Param(model.Q, initialize=d_init, mutable=True, within=pyo.Reals, doc="Demand per season (motors)")
model.lc = pyo.Param(model.Q, initialize=lc_init, mutable=True, within=pyo.Reals, doc="Leasing cost per season")
model.ei = pyo.Param(model.Q, initialize=ei_init, mutable=True, within=pyo.Reals, doc="Initial employment")

model.pr_labor = pyo.Param(model.L, initialize=pr_labor_init, mutable=True, within=pyo.Reals,
                       doc="Labor requirement per production level")
model.pr_motor = pyo.Param(model.L, initialize=pr_motor_init, mutable=True, within=pyo.Reals,
                       doc="Motor output per production level")

model.sc_fixed = pyo.Param(model.S, initialize=sc_fixed_init, mutable=True, within=pyo.Reals,
                       doc="Fixed shift cost")
model.sc_labor = pyo.Param(model.S, initialize=sc_labor_init, mutable=True, within=pyo.Reals,
                       doc="Labor shift cost")

# Discount factors delt(q) = 1 / base^(ord(q)-1)
def delt_init(model, q):
    return 1.0 / (discount_base ** (q_ord[q] - 1))

model.delt = pyo.Param(model.Q, initialize=delt_init, mutable=True, within=pyo.Reals,
                   doc="Discount factor per quarter")

# invmax = sum_q d(q)
invmax_val = sum(float(v) for v in d_data.values())
model.invmax = pyo.Param(initialize=float(invmax_val), mutable=True, within=pyo.Reals,
                     doc="Upper bound on inventory (motors)")

# Variables
model.cost = pyo.Var(within=pyo.Reals, doc="Total discounted cost per year (1000 $)")
model.dpc = pyo.Var(model.Q, within=pyo.Reals, doc="Direct production cost (1000 $ per season)")
model.isc = pyo.Var(model.Q, within=pyo.Reals, doc="Inventory storage cost (1000 $ per season)")
model.wfc = pyo.Var(model.Q, within=pyo.Reals, doc="Workforce fluctuation cost (1000 $ per season)")
model.src = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="Space rental cost (1000 $ per season)")

model.p = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="Production (motors per season)")
model.ss = pyo.Var(model.L, model.Q, model.S, within=pyo.NonNegativeReals, doc="Production segments")
model.ssb = pyo.Var(model.L, model.Q, model.S, within=pyo.Binary, doc="SOS2 binaries for ss")

model.inv = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="Inventory (motors per season)")
model.lease = pyo.Var(within=pyo.Binary, doc="Lease-rent option")

model.e = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="Total employment (employees)")
model.se = pyo.Var(model.Q, model.S, within=pyo.NonNegativeReals, doc="Shift employment (employees per shift)")
model.shift = pyo.Var(model.Q, model.S, within=pyo.Binary, doc="Shift use indicator")

model.h = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="Hirings in quarter (employees)")
model.f = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="Firings in quarter (employees)")

model.bpl = pyo.Var(within=pyo.Binary, doc="Unused binary bpl (kept for naming consistency)")

# Upper bound on spring production: p.up("spring") = 0.8*card(s)*smax_l pr_motor(l)
if "spring" in model.Q and pr_motor_data:
    max_pr_motor = max(float(v) for v in pr_motor_data.values())
    ub_spring = 0.8 * len(model.S) * max_pr_motor
    model.p["spring"].setub(float(ub_spring))

# Constraints
def acost_rule(model):
    return model.cost == sum(
        model.delt[q] * (model.dpc[q] + model.isc[q] + model.wfc[q])
        for q in model.Q
    )

model.acost = pyo.Constraint(rule=acost_rule, doc="Total cost definition")

def ddpc_rule(model, q):
    return model.dpc[q] == (
        model.mc * model.p[q]
        + sum(
            model.sc_fixed[s] * model.shift[q, s]
            + model.sc_labor[s] * model.se[q, s]
            for s in model.S
        )
    ) / 1000.0

model.ddpc = pyo.Constraint(model.Q, rule=ddpc_rule, doc="Direct production cost")

def sbp_rule(model, q):
    return model.p[q] == sum(
        model.pr_motor[l] * model.ss[l, q, s]
        for l in model.L for s in model.S
    )

model.sbp = pyo.Constraint(model.Q, rule=sbp_rule, doc="SOS product balance")

def sbse_rule(model, q, s):
    return model.se[q, s] == sum(
        model.pr_labor[l] * model.ss[l, q, s]
        for l in model.L
    )

model.sbse = pyo.Constraint(model.Q, model.S, rule=sbse_rule, doc="Shift employment balance")

def scc_rule(model, q, s):
    return sum(model.ss[l, q, s] for l in model.L) == model.shift[q, s]

model.scc = pyo.Constraint(model.Q, model.S, rule=scc_rule, doc="SOS shift link")

def invb_rule(model, q):
    prev = model._prev_q[q]
    if prev is None:
        return model.inv[q] == model.p[q] - model.d[q]
    return model.inv[q] == model.inv[prev] + model.p[q] - model.d[q]

model.invb = pyo.Constraint(model.Q, rule=invb_rule, doc="Inventory balance")

def disc_rule(model, q):
    return model.isc[q] == (model.lc[q] * model.lease + model.src[q]) / 1000.0

model.disc = pyo.Constraint(model.Q, rule=disc_rule, doc="Inventory storage cost")

def dsrc_rule(model, q):
    return model.src[q] >= model.sr * (model.inv[q] - model.invmax * model.lease)

model.dsrc = pyo.Constraint(model.Q, rule=dsrc_rule, doc="Space rental definition")

def dwfc_rule(model, q):
    return model.wfc[q] == (model.hc * model.h[q] + model.fc * model.f[q]) / 1000.0

model.dwfc = pyo.Constraint(model.Q, rule=dwfc_rule, doc="Workforce fluctuation cost")

def ed_rule(model, q):
    return model.e[q] == sum(model.se[q, s] for s in model.S)

model.ed = pyo.Constraint(model.Q, rule=ed_rule, doc="Total employment")

# eb1: e(q) = e(q-1) + h(q) - f(q) + ei(q)
def eb1_rule(model, q):
    prev = model._prev_q[q]
    if prev is None:
        return model.e[q] == model.h[q] - model.f[q] + model.ei[q]
    return model.e[q] == model.e[prev] + model.h[q] - model.f[q] + model.ei[q]

model.eb1 = pyo.Constraint(model.Q, rule=eb1_rule, doc="Employment balance type 1 (prod1)")

def messb_rule(model, q, s):
    return sum(model.ssb[l, q, s] for l in model.L) == 1

model.messb = pyo.Constraint(model.Q, model.S, rule=messb_rule, doc="Mutual exclusivity for ssb")

def lssb_rule(model, l, q, s):
    lhs = model.ss[l, q, s]
    if (l - 1) in model.L:
        lhs += model.ss[l - 1, q, s]

    rhs = model.ssb[l, q, s]
    if (l - 1) in model.L:
        rhs += model.ssb[l - 1, q, s]
    if (l - 2) in model.L:
        rhs += model.ssb[l - 2, q, s]

    return lhs <= rhs

model.lssb = pyo.Constraint(model.L, model.Q, model.S, rule=lssb_rule, doc="ss-ssb SOS2 linkage")

model.obj = pyo.Objective(expr=model.cost, sense=pyo.minimize,
                      doc="Minimize total discounted cost")
