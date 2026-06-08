# converted from models/coexx_mip.py
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
model.i = Set(initialize=data['i'], doc='size of chess board')
model.s = Set(initialize=data['s'], doc='diagonal offsets')
model.j = Set(initialize=data['i'], doc='alias for i')

# Computed parameters
n = len(data['i'])

# sh(s) = ord(s) - card(i) + 1
sh = {s: int(s) - n + 1 for s in data['s']}

# rev(s,i) = card(i) + 1 - 2*ord(i) + sh(s)
rev = {}
for s in data['s']:
    for i in data['i']:
        rev[(s, i)] = n + 1 - 2*int(i) + sh[s]

# VAR_BLOCK
model.xw = Var(model.i, model.j, domain=Binary, doc='has a white queen')
model.xb = Var(model.i, model.j, domain=Binary, doc='has a black queen')
model.wa = Var(model.i, domain=Binary, doc='white in row i')
model.wb = Var(model.i, domain=Binary, doc='white in column j')
model.wc = Var(model.s, domain=Binary, doc='white in diagonal s')
model.wd = Var(model.s, domain=Binary, doc='white in backward diagonal s')
model.tot = Var(domain=NonNegativeReals, doc='total queens per army')

# OBJ_BLOCK
model.obj = Objective(expr=model.tot, sense=maximize, doc='maximize army size')

# CONS_BLOCK
def aw_rule(model, i, j):
    """White in row i"""
    return model.wa[i] >= model.xw[i, j]
model.aw = Constraint(model.i, model.j, rule=aw_rule, doc='white in row i')

def bw_rule(model, j, i):
    """White in column j"""
    return model.wb[j] >= model.xw[i, j]
model.bw = Constraint(model.j, model.i, rule=bw_rule, doc='white in column j')

def cw_rule(model, s, i):
    """White in diagonal s"""
    j_val = int(i) + sh[s]
    if 1 <= j_val <= n:
        return model.wc[s] >= model.xw[i, str(j_val)]
    return Constraint.Skip
model.cw = Constraint(model.s, model.i, rule=cw_rule, doc='white in diagonal s')

def dw_rule(model, s, i):
    """White in backward diagonal s"""
    j_val = int(i) + rev[(s, i)]
    if 1 <= j_val <= n:
        return model.wd[s] >= model.xw[i, str(j_val)]
    return Constraint.Skip
model.dw = Constraint(model.s, model.i, rule=dw_rule, doc='white in backward diagonal s')

def ab_rule(model, i, j):
    """Black in row i - no overlap with white"""
    return 1 - model.wa[i] >= model.xb[i, j]
model.ab = Constraint(model.i, model.j, rule=ab_rule, doc='black in row i')

def bb_rule(model, j, i):
    """Black in column j - no overlap with white"""
    return 1 - model.wb[j] >= model.xb[i, j]
model.bb = Constraint(model.j, model.i, rule=bb_rule, doc='black in column j')

def cb_rule(model, s, i):
    """Black in diagonal s - no overlap with white"""
    j_val = int(i) + sh[s]
    if 1 <= j_val <= n:
        return 1 - model.wc[s] >= model.xb[i, str(j_val)]
    return Constraint.Skip
model.cb = Constraint(model.s, model.i, rule=cb_rule, doc='black in diagonal s')

def db_rule(model, s, i):
    """Black in backward diagonal s - no overlap with white"""
    j_val = int(i) + rev[(s, i)]
    if 1 <= j_val <= n:
        return 1 - model.wd[s] >= model.xb[i, str(j_val)]
    return Constraint.Skip
model.db = Constraint(model.s, model.i, rule=db_rule, doc='black in backward diagonal s')

def eb_rule(model):
    """Total black queens"""
    return model.tot == sum(model.xb[i, j] for i in model.i for j in model.j)
model.eb = Constraint(rule=eb_rule, doc='total black')

def ew_rule(model):
    """Total white queens equals total black"""
    return model.tot == sum(model.xw[i, j] for i in model.i for j in model.j)
model.ew = Constraint(rule=ew_rule, doc='total white')

# Fix one position in the NW corner
model.xb['1', '1'].fix(1)
