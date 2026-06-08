# converted from models/chance_lp.py
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
model.f = Set(initialize=data['f'])
model.n = Set(initialize=data['n'])

# PARAM_BLOCK
model.price = Param(model.f, initialize=data['price'], mutable = True, doc='Feed prices (fgld per ton)')
model.req = Param(model.n, initialize=data['req'], mutable = True, doc='Requirements (pct)')
model.char_mean = Param(model.n, model.f, initialize= {(n, f): data['char']['mean', n, f] for n in model.n for f in model.f}, mutable = True, doc='Feed characteristics mean (pct)')
model.char_variance = Param(model.n, model.f, initialize={(n, f): data['char']['mean', n, f] for n in ['protein'] for f in model.f}, mutable = True, doc='Feed characteristics variance (pct)')

# VAR_BLOCK
model.cost = Var(domain=NonNegativeReals, doc='Total cost per ton')
model.x = Var(model.f, domain=NonNegativeReals, doc='Feed mix (pct)')

# OBJ_BLOCK
model.obj = Objective(expr=model.cost, sense=minimize, doc='Minimize total cost per ton')

# CONS_BLOCK
def cost_definition_rule(model):
    return model.cost == sum(model.price[f] * model.x[f] for f in model.f)
model.cdef = Constraint(rule=cost_definition_rule, doc='Cost definition')

def mix_constraint_rule(model):
    return sum(model.x[f] for f in model.f) == 1
model.mc = Constraint(rule=mix_constraint_rule, doc='Mix constraint')

def nutrient_balance_rule(model, n):
    return sum(model.char_mean[n, f] * model.x[f] for f in model.f) >= model.req[n]
model.nbal = Constraint(model.n, rule=nutrient_balance_rule, doc='Nutrient balance')
