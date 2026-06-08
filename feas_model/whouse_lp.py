# converted from models/whouse_lp.py
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
model.t = Set(initialize=data['t'], ordered=True, doc='time in quarters')


t_list = list(model.t.data())
prev_of = {t_list[i]: (t_list[i-1] if i > 0 else None) for i in range(len(t_list))}

# PARAM_BLOCK
model.price     = Param(model.t, initialize=data['price'], mutable=True, doc='selling price ($/unit)')
def _istock_init(m, tt):
    return data.get('istock', {}).get(tt, 0.0)
model.istock    = Param(model.t, initialize=_istock_init, mutable=True, doc='initial stock injection (units)')
model.storecost = Param(initialize=data['storecost'], mutable=True, doc='storage cost ($/unit/quarter)')
model.storecap  = Param(initialize=data['storecap'],  mutable=True, doc='warehouse capacity (units)')

# VAR_BLOCK
model.stock = Var(model.t, domain=NonNegativeReals, doc='stock at time t (units)')
model.sell  = Var(model.t, domain=NonNegativeReals, doc='units sold at time t')
model.buy   = Var(model.t, domain=NonNegativeReals, doc='units bought at time t')
model.cost  = Var(domain=Reals, doc='total cost ($)')

# OBJ_BLOCK
model.obj = Objective(expr=model.cost, sense=minimize)

# CONS_BLOCK
def stock_balance_rule(m, tt):
    # NOTE: istock moved to RHS so it is con.upper-visible. Mathematically
    # identical to `stock[tt] == stock[prev] + buy[tt] - sell[tt] + istock[tt]`.
    # Exposes istock[tt] as a SENSITIVITY-targetable RHS Param.
    prev = prev_of[tt]
    if prev is None:
        return m.stock[tt] - m.buy[tt] + m.sell[tt] == m.istock[tt]
    return m.stock[tt] - m.stock[prev] - m.buy[tt] + m.sell[tt] == m.istock[tt]
model.stock_balance = Constraint(model.t, rule=stock_balance_rule, doc='stock balance per period')

def capacity_rule(m, tt):
    return m.stock[tt] <= m.storecap
model.capacity = Constraint(model.t, rule=capacity_rule, doc='warehouse capacity')

def accounting_rule(m):
    return m.cost == sum(m.price[tt]*(m.buy[tt] - m.sell[tt]) + m.storecost*m.stock[tt] for tt in m.t)
model.accounting = Constraint(rule=accounting_rule, doc='cost definition')
