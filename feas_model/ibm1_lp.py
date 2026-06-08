# converted from models/ibm1_lp.py
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
model.s = Set(initialize=data['s'], doc='scrap metals for blending')
model.sl = Set(initialize=data['sl'], doc='locally available blends')
model.e = Set(initialize=data['e'], doc='chemical elements')

# PARAM_BLOCK
model.prop = Param(model.e, model.s, initialize=data['prop'], 
                   mutable=True, default=0.0, doc='chemical properties (proportions)')
model.sup = Param(model.s, ['inventory', 'min-use', 'cost'], initialize=data['sup'], 
                  mutable=True, default=0.0, doc='supply and cost data')
model.target_weight = Param(initialize=data['target_weight'], 
                            mutable=True, doc='final blend requirements (lb)')

# Store bspec as dict
bspec_data = data['bspec']

# VAR_BLOCK
model.x = Var(model.s, domain=NonNegativeReals, doc='blending components (lb)')
model.bc = Var(model.e, domain=NonNegativeReals, doc='elements in blend (lb)')
model.cost = Var(domain=NonNegativeReals, doc='total material cost ($)')

# Set bounds on x using .get() with default 0.0 for min-use
for s in data['s']:
    min_use = data['sup'].get((s, 'min-use'), 0.0)
    inventory = data['sup'][(s, 'inventory')]
    model.x[s].setlb(min_use)
    model.x[s].setub(inventory)

# Set bounds on bc
for e in data['e']:
    min_val = bspec_data.get((e, 'minimum'), None)
    max_val = bspec_data.get((e, 'maximum'), None)
    if min_val is not None:
        model.bc[e].setlb(min_val)
    if max_val is not None and max_val < 1e100:
        model.bc[e].setub(max_val)

# OBJ_BLOCK
model.obj = Objective(expr=model.cost, sense=minimize, doc='minimize total cost')

# CONS_BLOCK
def yield_rule(model):
    return sum(model.x[s] for s in model.s) == model.target_weight
model.yield_con = Constraint(rule=yield_rule, doc='final blend requirements (lb)')

def ebal_rule(model, e):
    return model.bc[e] == sum(model.prop[e, s] * model.x[s] for s in model.s)
model.ebal = Constraint(model.e, rule=ebal_rule, doc='element balance (lb)')

def cdef_rule(model):
    return model.cost == sum(model.sup[s, 'cost'] * model.x[s] for s in model.s)
model.cdef = Constraint(rule=cdef_rule, doc='cost definition ($)')
