# converted from models/prodschx_2S1_mip.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# SET_BLOCK
model.q = Set(initialize=data['q'], doc='quarters')
model.s = Set(initialize=data['s'], doc='shifts')
model.l = Set(initialize=data['l'], doc='production levels')
model.i = Set(initialize=data['i'], doc='production intervals')

# PARAM_BLOCK
model.d = Param(model.q, initialize=data['d'], mutable=True, doc='demand per season')
model.lc = Param(model.q, initialize=data['lc'], mutable=True, doc='leasing cost per season')
model.ei = Param(model.q, initialize=data['ei'], mutable=True, doc='initial employment')
model.delt = Param(model.q, initialize=data['delt'], mutable=True, doc='discount factor')

model.mc = Param(initialize=data['mc'], mutable=True, doc='material cost per motor')
model.sr = Param(initialize=data['sr'], mutable=True, doc='space rental cost per motor')
model.hc = Param(initialize=data['hc'], mutable=True, doc='hiring cost per employee')
model.fc = Param(initialize=data['fc'], mutable=True, doc='firing cost per employee')
model.invmax = Param(initialize=sum(data['d'].values()), mutable=True, doc='max inventory')

model.pr_motor = Param(['labor','motor'], model.l, initialize=data['pr_motor'], mutable=True)
model.sc = Param(['fixed','labor'], model.s, initialize=data['sc'], mutable=True)

# VAR_BLOCK
model.cost = Var(domain=NonNegativeReals, doc='total discounted cost')
model.dpc = Var(model.q, domain=NonNegativeReals, doc='direct production cost')
model.isc = Var(model.q, domain=NonNegativeReals, doc='inventory cost')
model.wfc = Var(model.q, domain=NonNegativeReals, doc='workforce cost')
model.src = Var(model.q, domain=NonNegativeReals, doc='space rental cost')
model.p = Var(model.q, domain=NonNegativeReals, doc='production')
model.ss = Var(model.q, model.s, model.l, domain=NonNegativeReals, doc='production segment (SOS2 type)')
model.ssb = Var(model.q, model.s, model.l, domain=Binary, doc='binary for SOS2 segment')
model.inv = Var(model.q, domain=NonNegativeReals, doc='inventory')
model.lease = Var(domain=Binary, doc='lease option')
model.e = Var(model.q, domain=NonNegativeReals, doc='total employment')
model.se = Var(model.q, model.s, domain=NonNegativeReals, doc='shift employment')
model.shift = Var(model.q, model.s, domain=Binary, doc='shift indicator')
model.h = Var(model.q, domain=NonNegativeReals, doc='hirings')
model.f = Var(model.q, domain=NonNegativeReals, doc='firings')

# OBJ_BLOCK
model.obj = Objective(expr=model.cost, sense=minimize)

# CONS_BLOCK

# Total discounted cost
def acost_rule(m):
    return m.cost == sum(m.delt[q] * (m.dpc[q] + m.isc[q] + m.wfc[q]) for q in m.q)
model.acost = Constraint(rule=acost_rule)

# Direct production cost
def ddpc_rule(m, q):
    return m.dpc[q] == (m.mc * m.p[q] + sum(m.sc['fixed', s]*m.shift[q,s] + m.sc['labor', s]*m.se[q,s] for s in m.s)) / 1000
model.ddpc = Constraint(model.q, rule=ddpc_rule)

# Production balance
def sbp_rule(m, q):
    return m.p[q] == sum(m.pr_motor['motor', l]*m.ss[q,s,l] for s in m.s for l in m.l)
model.sbp = Constraint(model.q, rule=sbp_rule)

# Shift employment balance
def sbse_rule(m, q, s):
    return m.se[q,s] == sum(m.pr_motor['labor', l]*m.ss[q,s,l] for l in m.l)
model.sbse = Constraint(model.q, model.s, rule=sbse_rule)

# Shift linkage
def scc_rule(m, q, s):
    return sum(m.ss[q,s,l] for l in m.l) == m.shift[q,s]
model.scc = Constraint(model.q, model.s, rule=scc_rule)

# Inventory balance
def invb_rule(m, q):
    qlist = list(m.q)
    idx = qlist.index(q)
    prev = m.inv[qlist[idx-1]] if idx > 0 else 0
    return m.inv[q] == prev + m.p[q] - m.d[q]
model.invb = Constraint(model.q, rule=invb_rule)

# Inventory cost
def disc_rule(m, q):
    return m.isc[q] == (m.lc[q]*m.lease + m.src[q])/1000
model.disc = Constraint(model.q, rule=disc_rule)

# Space rental
def dsrc_rule(m, q):
    return m.src[q] >= m.sr*(m.inv[q] - m.invmax*m.lease)
model.dsrc = Constraint(model.q, rule=dsrc_rule)

# Workforce fluctuation
def dwfc_rule(m, q):
    return m.wfc[q] == (m.hc*m.h[q] + m.fc*m.f[q])/1000
model.dwfc = Constraint(model.q, rule=dwfc_rule)

# Total employment
def ed_rule(m, q):
    return m.e[q] == sum(m.se[q,s] for s in m.s)
model.ed = Constraint(model.q, rule=ed_rule)

# Employment balance type 2 (eb2)
def eb2_rule(model, q):
    """
    e(q) = e(q-1) + h(q) - f(q)
    Initial quarter has no previous quarter, use 0
    """
    qlist = list(model.q)
    idx = qlist.index(q)
    prev_e = model.e[qlist[idx-1]] if idx > 0 else 0
    return model.e[q] == prev_e + model.h[q] - model.f[q]
model.eb2 = Constraint(model.q, rule=eb2_rule)


def lss1_rule(model, q, s, l):
    """
    ss(q,s,l-1) + ss(q,s,l) <= ss(q,s,l-2) + ss(q,s,l-1) + ss(q,s,l)
    Handle bounds carefully
    """
    llist = list(model.l)
    lidx = llist.index(l)
    lhs = model.ss[q, s, l]
    if lidx > 0:
        lhs += model.ss[q, s, llist[lidx-1]]

    rhs = model.ss[q, s, l]
    if lidx > 0:
        rhs += model.ss[q, s, llist[lidx-1]]
    if lidx > 1:
        rhs += model.ss[q, s, llist[lidx-2]]

    return lhs <= rhs

model.lss1 = Constraint(model.q, model.s, model.l, rule=lss1_rule)

def mess1_rule(m, q, s):
    return sum(m.ss[q, s, l] for l in m.l) == 1

model.mess1 = Constraint(model.q, model.s, rule=mess1_rule)
