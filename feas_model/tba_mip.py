# converted from models/tba_mip.py
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
model.p = Set(initialize=data['p'], doc='gnma pools')
model.i = Set(initialize=data['i'], doc='tbas')
model.l = Set(initialize=data['l'], doc='lots')
model.c3 = Set(initialize=data['c3'], doc='class 3 high risk pools')

# SCALAR_PARAMS_BLOCK
model.head = Param(initialize=data['head'], mutable=True, doc='first incremental step for allocation')
model.steps = Param(initialize=data['steps'], mutable=True, doc='incremental step size')

# PARAM_BLOCK
model.pv = Param(model.p, Any, initialize=data['pv'], mutable=True, default=0, doc='value of pools')
model.tbainfo = Param(model.i, Any, initialize=data['tbainfo'], mutable=True, default=0, doc='tba information')

# Computed parameters
def o_init(model, p):
    return model.pv[p, 'original']
model.o = Param(model.p, initialize=o_init, doc='original face value')

def a_init(model, p):
    return model.pv[p, 'adjusted']
model.a = Param(model.p, initialize=a_init, doc='adjusted face value')

# VAR_BLOCK
model.profit = Var(domain=Reals, doc='total profit')
model.v = Var(model.p, model.i, model.l, domain=NonNegativeReals, doc='allocated pool values by tba lot')
model.b = Var(model.p, domain=NonNegativeReals, doc='adjusted face value of pools remaining in box')
model.z = Var(model.p, model.i, model.l, domain=Binary, doc='decision whether to allocate pool to tba lot')
model.w = Var(model.i, model.l, domain=Binary, doc='decision whether to fail tba lot (0=failed)')
model.s = Var(model.p, domain=Binary, doc='decision whether to split pools')

# OBJ_BLOCK
model.obj = Objective(expr=model.profit, sense=maximize, doc='maximize profit')

# Computed lot sizes
l_list = list(data['l'])
lsize = {}
for i_idx in data['i']:
    futamt = data['tbainfo'].get((i_idx, 'quantity'), 0)
    cumsum = 0
    for idx, l_idx in enumerate(l_list):
        lsize[(i_idx, l_idx)] = min(1000, futamt - cumsum)
        cumsum += lsize[(i_idx, l_idx)]

# Computed variation and maxpools
var = {i_idx: data['tbainfo'].get((i_idx, 'variation'), 0.05) for i_idx in data['i']}
futprice = {i_idx: data['tbainfo'].get((i_idx, 'selling'), 100) / 100 for i_idx in data['i']}
mktprice = {i_idx: data['tbainfo'].get((i_idx, 'market'), 100) / 100 for i_idx in data['i']}
maxpools_raw = {i_idx: data['tbainfo'].get((i_idx, 'maxpools'), 3) for i_idx in data['i']}

maxp = {}
for i_idx in data['i']:
    for l_idx in data['l']:
        ls = lsize[(i_idx, l_idx)]
        if ls < 500:
            maxp[(i_idx, l_idx)] = maxpools_raw[i_idx] - 2
        elif ls < 1000:
            maxp[(i_idx, l_idx)] = maxpools_raw[i_idx] - 1
        else:
            maxp[(i_idx, l_idx)] = maxpools_raw[i_idx]

# CONS_BLOCK
def loval_rule(model, i_idx, l_idx):
    """Lower limit on allocated value by tba lot"""
    if lsize[(i_idx, l_idx)] > 0:
        return sum(model.v[p, i_idx, l_idx] for p in model.p) >= (1 - var[i_idx]) * lsize[(i_idx, l_idx)] * model.w[i_idx, l_idx]
    return Constraint.Skip
model.loval = Constraint(model.i, model.l, rule=loval_rule, doc='lower limit on allocated value')

def upval_rule(model, i_idx, l_idx):
    """Upper limit on allocated value by tba lot"""
    if lsize[(i_idx, l_idx)] > 0:
        return sum(model.v[p, i_idx, l_idx] for p in model.p) <= (1 + var[i_idx]) * lsize[(i_idx, l_idx)] * model.w[i_idx, l_idx]
    return Constraint.Skip
model.upval = Constraint(model.i, model.l, rule=upval_rule, doc='upper limit on allocated value')

def supply_rule(model, p):
    """Allocate value and boxed amounts"""
    return sum(model.v[p, i_idx, l_idx] for i_idx in model.i for l_idx in model.l if lsize[(i_idx, l_idx)] > 0) + model.b[p] == model.a[p]
model.supply = Constraint(model.p, rule=supply_rule, doc='allocate value and boxed amounts')

def class3con_rule(model, i_idx, l_idx):
    """Constraint on use of class 3 pools"""
    if lsize[(i_idx, l_idx)] > 0:
        return sum(model.v[p, i_idx, l_idx] for p in model.p if p not in data['c3']) >= model.w[i_idx, l_idx]
    return Constraint.Skip
model.class3con = Constraint(model.i, model.l, rule=class3con_rule, doc='constraint on use of class 3 pools')

def zdet_rule(model, p, i_idx, l_idx):
    """Determination of whether to allocate pool"""
    if lsize[(i_idx, l_idx)] > 0:
        return model.v[p, i_idx, l_idx] <= (1 + var[i_idx]) * lsize[(i_idx, l_idx)] * model.z[p, i_idx, l_idx]
    return Constraint.Skip
model.zdet = Constraint(model.p, model.i, model.l, rule=zdet_rule, doc='determination of whether to allocate pool')

def maxpool_rule(model, i_idx, l_idx):
    """Constraint on maximum pools per lot"""
    if lsize[(i_idx, l_idx)] > 0:
        return sum(model.z[p, i_idx, l_idx] for p in model.p) <= maxp[(i_idx, l_idx)]
    return Constraint.Skip
model.maxpool = Constraint(model.i, model.l, rule=maxpool_rule, doc='maximum pools per lot')

def profitdef_rule(model):
    """Definition of profits"""
    return model.profit == sum(
        (futprice[i_idx] - mktprice[i_idx]) * model.v[p, i_idx, l_idx]
        for p in model.p for i_idx in model.i for l_idx in model.l if lsize[(i_idx, l_idx)] > 0
    ) - sum(0.00001 * model.s[p] for p in model.p)
model.profitdef = Constraint(rule=profitdef_rule, doc='profit definition')
