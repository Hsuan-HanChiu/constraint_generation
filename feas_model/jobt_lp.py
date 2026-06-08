# converted from models/jobt_lp.py
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
model.t = Set(initialize=data['t'], ordered=True, doc='time periods (weeks)')

# PARAM_BLOCK
model.rho = Param(initialize=data['rho'], mutable=True, doc='worker productivity (units per worker)')
model.alpha = Param(initialize=data['alpha'], mutable=True, doc='trainer capability (workers per trainer)')
model.wage = Param(initialize=data['wage'], mutable=True, doc='worker wages ($ per week per worker)')

# Convert string keys to integers for indexed params
def convert_keys(d):
    return {int(k) if isinstance(k, str) and k.isdigit() else k: v for k, v in d.items()}

si_data = convert_keys(data['si'])
wi_data = convert_keys(data['wi'])
sf_data = convert_keys(data['sf'])
d_data = convert_keys(data['d'])

model.si = Param(model.t, initialize=si_data, mutable=True, default=0, doc='initial stock of goods (units)')
model.wi = Param(model.t, initialize=wi_data, mutable=True, default=0, doc='initial number of workers (workers)')
model.sf = Param(model.t, initialize=sf_data, mutable=True, default=0, doc='salary on firing ($)')
model.d = Param(model.t, initialize=d_data, mutable=True, doc='demand schedule (units)')

# VAR_BLOCK
model.p = Var(model.t, domain=NonNegativeReals, doc='production level in period t (units)')
model.s = Var(model.t, domain=NonNegativeReals, doc='goods stored in period t (units)')
model.u = Var(model.t, domain=NonNegativeReals, doc='unmet demand in period t (units)')
model.w = Var(model.t, domain=NonNegativeReals, doc='total potential productive workers (workers)')
model.h = Var(model.t, domain=NonNegativeReals, doc='workers hired (workers)')
model.f = Var(model.t, domain=NonNegativeReals, doc='workers fired (workers)')
model.phi = Var(domain=Reals, doc='total cost ($)')

# CONS_BLOCK
def commodity_balance_rule(model, t):
    """Commodity balance (units)"""
    t_prev = model.t.prev(t) if t != model.t.first() else None
    s_prev = model.s[t_prev] if t_prev else 0
    u_prev = model.u[t_prev] if t_prev else 0
    return model.s[t] == s_prev + model.p[t] - model.d[t] - u_prev + model.u[t] + model.si[t]
model.cb = Constraint(model.t, rule=commodity_balance_rule, doc='commodity balance (units)')

def worker_balance_rule(model, t):
    """Worker balance between periods (workers)"""
    t_prev = model.t.prev(t) if t != model.t.first() else None
    w_prev = model.w[t_prev] if t_prev else 0
    return model.w[t] == w_prev - model.f[t] + model.h[t] + model.wi[t]
model.wb = Constraint(model.t, rule=worker_balance_rule, doc='worker balance - between periods (workers)')

def worker_differentiation_rule(model, t):
    """Worker balance for job differentiation (workers)"""
    return model.w[t] >= model.p[t] / model.rho + (1 + 1 / model.alpha) * model.h[t]
model.wd = Constraint(model.t, rule=worker_differentiation_rule, doc='worker balance - job differentiation (workers)')

def cost_definition_rule(model):
    """Total cost definition ($)"""
    return model.phi == sum(10 * model.s[t] + 30 * model.u[t] + (model.wage + model.sf[t]) * model.w[t] for t in model.t)
model.cost_def = Constraint(rule=cost_definition_rule, doc='cost definition ($)')

# OBJ_BLOCK
model.obj = Objective(expr=model.phi, sense=minimize)
