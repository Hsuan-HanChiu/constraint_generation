# converted from models/prodsch_eb2.py
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
model.Q = pyo.Set(initialize=data["q"], ordered=True, doc="quarters")
model.S = pyo.Set(initialize=data["s"], ordered=True, doc="shifts")
model.L = pyo.Set(initialize=data["l"], ordered=True, doc="production levels")

# Helpers for q-1 (non-cyclic, for inventory) and cyclic q--1 (for eb2)
q_list = list(model.Q.ordered_data())
prev_q = {}
prev_cyclic = {}
q_ord = {}
for idx, q in enumerate(q_list):
    q_ord[q] = idx + 1
    prev_q[q] = q_list[idx - 1] if idx > 0 else None
    prev_cyclic[q] = q_list[idx - 1] if idx > 0 else q_list[-1]
model._prev_q = prev_q
model._prev_cyclic = prev_cyclic

# Scalar parameters (mutable)
mc_val = float(data.get("mc", 100.0))
sr_val = float(data.get("sr", 2.0))
hc_val = float(data.get("hc", 900.0))
fc_val = float(data.get("fc", 150.0))
discount_base = float(data.get("discount_base", 1.03))

model.mc = pyo.Param(initialize=mc_val, mutable=True, within=pyo.Reals, doc="material cost")
model.sr = pyo.Param(initialize=sr_val, mutable=True, within=pyo.Reals, doc="space rental")
model.hc = pyo.Param(initialize=hc_val, mutable=True, within=pyo.Reals, doc="hiring cost")
model.fc = pyo.Param(initialize=fc_val, mutable=True, within=pyo.Reals, doc="firing cost")

# Raw indexed data
d_data = data.get("d", {})
lc_data = data.get("lc", {})
ei_data = data.get("ei", {})  # not used in prod2
pr_labor_data = data.get("pr_labor", {})
pr_motor_data = data.get("pr_motor", {})
sc_fixed_data = data.get("sc_fixed", {})
sc_labor_data = data.get("sc_labor", {})

# Indexed parameters (mutable)
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

model.d = pyo.Param(model.Q, initialize=d_init, mutable=True, within=pyo.Reals, doc="demand")
model.lc = pyo.Param(model.Q, initialize=lc_init, mutable=True, within=pyo.Reals, doc="leasing cost")
model.ei = pyo.Param(model.Q, initialize=ei_init, mutable=True, within=pyo.Reals, doc="initial employment")

model.pr_labor = pyo.Param(model.L, initialize=pr_labor_init, mutable=True, within=pyo.Reals, doc="labor per level")
model.pr_motor = pyo.Param(model.L, initialize=pr_motor_init, mutable=True, within=pyo.Reals, doc="motor per level")

model.sc_fixed = pyo.Param(model.S, initialize=sc_fixed_init, mutable=True, within=pyo.Reals, doc="fixed shift cost")
model.sc_labor = pyo.Param(model.S, initialize=sc_labor_init, mutable=True, within=pyo.Reals, doc="labor shift cost")

# Discount factors: delt(q) = 1 / base^(ord(q)-1)
def delt_init(model, q):
    return 1.0 / (discount_base ** (q_ord[q] - 1))

model.delt = pyo.Param(model.Q, initialize=delt_init, mutable=True, within=pyo.Reals, doc="discount factor")

# invmax = sum_q d(q)
invmax_val = sum(float(v) for v in d_data.values())
model.invmax = pyo.Param(initialize=float(invmax_val), mutable=True, within=pyo.Reals, doc="inventory upper bound")

# Variables
model.cost = pyo.Var(within=pyo.Reals, doc="total discounted cost (1000 $)")
model.dpc = pyo.Var(model.Q, within=pyo.Reals, doc="direct production cost (1000 $)")
model.isc = pyo.Var(model.Q, within=pyo.Reals, doc="inventory storage cost (1000 $)")
model.wfc = pyo.Var(model.Q, within=pyo.Reals, doc="workforce fluctuation cost (1000 $)")
model.src = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="space rental cost (1000 $)")

model.p = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="production")
model.ss = pyo.Var(model.L, model.Q, model.S, within=pyo.NonNegativeReals, doc="production segments")
model.ssb = pyo.Var(model.L, model.Q, model.S, within=pyo.Binary, doc="SOS2 binaries")

model.inv = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="inventory")
model.lease = pyo.Var(within=pyo.Binary, doc="lease option")

model.e = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="employment")
model.se = pyo.Var(model.Q, model.S, within=pyo.NonNegativeReals, doc="shift employment")
model.shift = pyo.Var(model.Q, model.S, within=pyo.Binary, doc="shift use")

model.h = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="hirings")
model.f = pyo.Var(model.Q, within=pyo.NonNegativeReals, doc="firings")

model.bpl = pyo.Var(within=pyo.Binary, doc="unused binary bpl")

# Upper bound on spring production
if "spring" in model.Q and pr_motor_data:
    max_pr_motor = max(float(v) for v in pr_motor_data.values())
    ub_spring = 0.8 * len(model.S) * max_pr_motor
    model.p["spring"].setub(float(ub_spring))

# Constraints

# acost: total cost
def acost_rule(model):
    return model.cost == sum(
        model.delt[q] * (model.dpc[q] + model.isc[q] + model.wfc[q])
        for q in model.Q
    )

model.acost = pyo.Constraint(rule=acost_rule)

# ddpc(q): direct production cost
def ddpc_rule(model, q):
    return model.dpc[q] == (
        model.mc * model.p[q]
        + sum(
            model.sc_fixed[s] * model.shift[q, s]
            + model.sc_labor[s] * model.se[q, s]
            for s in model.S
        )
    ) / 1000.0

model.ddpc = pyo.Constraint(model.Q, rule=ddpc_rule)

# sbp(q): production balance
def sbp_rule(model, q):
    return model.p[q] == sum(
        model.pr_motor[l] * model.ss[l, q, s]
        for l in model.L for s in model.S
    )

model.sbp = pyo.Constraint(model.Q, rule=sbp_rule)

# sbse(q,s): shift employment
def sbse_rule(model, q, s):
    return model.se[q, s] == sum(
        model.pr_labor[l] * model.ss[l, q, s]
        for l in model.L
    )

model.sbse = pyo.Constraint(model.Q, model.S, rule=sbse_rule)

# scc(q,s): SOS link
def scc_rule(model, q, s):
    return sum(model.ss[l, q, s] for l in model.L) == model.shift[q, s]

model.scc = pyo.Constraint(model.Q, model.S, rule=scc_rule)

# invb(q): inventory balance (non-cyclic q-1)
def invb_rule(model, q):
    prev = model._prev_q[q]
    if prev is None:
        return model.inv[q] == model.p[q] - model.d[q]
    return model.inv[q] == model.inv[prev] + model.p[q] - model.d[q]

model.invb = pyo.Constraint(model.Q, rule=invb_rule)

# disc(q): inventory storage cost
def disc_rule(model, q):
    return model.isc[q] == (model.lc[q] * model.lease + model.src[q]) / 1000.0

model.disc = pyo.Constraint(model.Q, rule=disc_rule)

# dsrc(q): space rental
def dsrc_rule(model, q):
    return model.src[q] >= model.sr * (model.inv[q] - model.invmax * model.lease)

model.dsrc = pyo.Constraint(model.Q, rule=dsrc_rule)

# dwfc(q): workforce fluctuation cost
def dwfc_rule(model, q):
    return model.wfc[q] == (model.hc * model.h[q] + model.fc * model.f[q]) / 1000.0

model.dwfc = pyo.Constraint(model.Q, rule=dwfc_rule)

# ed(q): total employment
def ed_rule(model, q):
    return model.e[q] == sum(model.se[q, s] for s in model.S)

model.ed = pyo.Constraint(model.Q, rule=ed_rule)

# eb2(q): employment balance type 2 (steady state, cyclic q--1)
def eb2_rule(model, q):
    prev = model._prev_cyclic[q]
    return model.e[q] == model.e[prev] + model.h[q] - model.f[q]

model.eb2 = pyo.Constraint(model.Q, rule=eb2_rule)

# messb(q,s): mutual exclusivity for ssb
def messb_rule(model, q, s):
    return sum(model.ssb[l, q, s] for l in model.L) == 1

model.messb = pyo.Constraint(model.Q, model.S, rule=messb_rule)

# lssb(l,q,s): ss-ssb linkage (SOS2-style)
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

model.lssb = pyo.Constraint(model.L, model.Q, model.S, rule=lssb_rule)

# Objective
model.obj = pyo.Objective(expr=model.cost, sense=pyo.minimize)
