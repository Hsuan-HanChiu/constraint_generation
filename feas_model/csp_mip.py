# converted from models/csp_mip.py
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
model.n = Set(initialize=data['n'], doc='strings')
model.m = Set(initialize=data['m'], doc='character sequence')
model.a = Set(initialize=data['a'], doc='alphabet')

# PARAM_BLOCK
model.x = Param(model.n, model.m, initialize=data['x'], mutable=True, default=0, 
                doc='string values')

# Compute ma(m,a) - possible characters by position
ma = {}
for m_idx in data['m']:
    for a_idx in data['a']:
        a_ord = int(a_idx[1:])  # Extract number from 'a1', 'a2', etc.
        for n_idx in data['n']:
            if data['x'].get((n_idx, m_idx), 0) == a_ord:
                ma[(m_idx, a_idx)] = True
                break

model.ma = Set(initialize=list(ma.keys()), dimen=2, doc='possible characters by position')

# VAR_BLOCK
model.d = Var(domain=NonNegativeReals, doc='maximum difference between t and x')
model.v = Var(model.m, model.a, domain=Binary, doc='selection of characters')

# OBJ_BLOCK
model.obj = Objective(expr=model.d, sense=minimize, doc='minimize maximum Hamming distance')

# CONS_BLOCK
def e4_rule(model, m_idx):
    """Select only one character per position"""
    return sum(model.v[m_idx, a_idx] for a_idx in model.a if (m_idx, a_idx) in ma) == 1
model.e4 = Constraint(model.m, rule=e4_rule, doc='select only one character')

def e6_rule(model, n_idx):
    """Count matching characters - Hamming distance constraint"""
    card_m = len(data['m'])
    matching = sum(
        model.v[m_idx, a_idx] 
        for m_idx in model.m 
        for a_idx in model.a 
        if (m_idx, a_idx) in ma and data['x'].get((n_idx, m_idx), 0) == int(a_idx[1:])
    )
    return card_m - matching <= model.d
model.e6 = Constraint(model.n, rule=e6_rule, doc='count matching characters')
