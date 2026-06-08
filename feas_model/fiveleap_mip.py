# converted from models/fiveleap_mip.py
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
model.r = Set(initialize=data['r'], doc='rows')
model.c = Set(initialize=data['c'], doc='columns')

# Get dimensions
nrow = len(data['r'])
ncol = len(data['c'])
n_squares = nrow * ncol

# Start square
ss = data.get('ss', [('1', '1')])
start_r, start_c = ss[0] if ss else ('1', '1')

def is_legal_move(r1, c1, r2, c2):
    dr = abs(int(r1) - int(r2))
    dc = abs(int(c1) - int(c2))
    return dr * dr + dc * dc == 25

# Build legal moves set
legal_moves = []
for r1 in data['r']:
    for c1 in data['c']:
        for r2 in data['r']:
            for c2 in data['c']:
                if is_legal_move(r1, c1, r2, c2):
                    legal_moves.append((r1, c1, r2, c2))

model.m = Set(initialize=legal_moves, doc='legal moves')

# VAR_BLOCK
model.xm = Var(model.r, model.c, model.r, model.c, domain=Binary, 
               doc='moves of a tour')
model.nm = Var(model.r, model.c, domain=NonNegativeReals, 
               doc='number of move (position in tour)')
model.z = Var(domain=Reals, doc='dummy objective variable')

# OBJ_BLOCK
def obj_rule(model):
    return model.z == sum(model.xm[r, c, rp, cp] for (r, c, rp, cp) in model.m)
model.obj_def = Constraint(rule=obj_rule, doc='dummy objective')
model.obj = Objective(expr=model.z, sense=minimize, doc='minimize dummy')

# CONS_BLOCK
def deffrom_rule(model, r, c):
    """Each square precedes one other"""
    return sum(model.xm[r, c, rp, cp] for (r1, c1, rp, cp) in model.m 
               if r1 == r and c1 == c) == 1
model.deffrom = Constraint(model.r, model.c, rule=deffrom_rule, 
                           doc='each square precedes one other')

def defto_rule(model, rp, cp):
    """Each square is preceded by one other"""
    return sum(model.xm[r, c, rp, cp] for (r, c, r1, c1) in model.m 
               if r1 == rp and c1 == cp) == 1
model.defto = Constraint(model.r, model.c, rule=defto_rule, 
                         doc='each square is preceded by one other')

def deforder_rule(model, r, c, rp, cp):
    """Order the moves (MTZ subtour elimination)"""
    if (r, c, rp, cp) not in model.m:
        return Constraint.Skip
    # Skip if destination is start square
    if rp == start_r and cp == start_c:
        return Constraint.Skip
    return model.nm[r, c] - model.nm[rp, cp] <= n_squares * (1 - model.xm[r, c, rp, cp]) - 1
model.deforder = Constraint(model.r, model.c, model.r, model.c, 
                            rule=deforder_rule, doc='order the moves')

# Fix start square position
model.nm[start_r, start_c].fix(1)

# Fix non-legal moves to 0
for r in model.r:
    for c in model.c:
        for rp in model.r:
            for cp in model.c:
                if (r, c, rp, cp) not in model.m:
                    model.xm[r, c, rp, cp].fix(0)
