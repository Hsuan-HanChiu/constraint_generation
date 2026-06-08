# converted from models/uimp_profit_lp.py
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

model.i = Set(initialize=data['i'], doc='time periods')
model.j = Set(initialize=data['j'], doc='production mode')
model.k = Set(initialize=data['k'], doc='products')
model.l = Set(initialize=data['l'], doc='machines')

# PARAM_BLOCK

model.mh = Param(model.l, model.k, initialize=data['mh'], mutable=True, doc='machine hours (hours per unit)')
model.mhadd = Param(model.i, model.j, initialize=data['mhadd'], mutable=True, doc='addfactors for mh')
model.av = Param(model.l, model.j, initialize=data['av'], mutable=True, doc='availability (hours)')

def t_init(model, i, j, k, l):
    if value(model.mh[l, k]) != 0:
        return model.mh[l, k] + model.mhadd[i, j]
    else:
        return model.mh[l, k]

model.t = Param(model.i, model.j, model.k, model.l, initialize=t_init, mutable=True, doc='time (hours per unit)')
model.t["winter","overtime","washers","m1"] = 5.0 # Manually fixing a value that was not set in data

def a_init(model, i, j, l):
    if (i == "summer"):
        return model.av[l, j]
    elif (i == "winter"):
        return model.av[l, j] + 10
    else:
        raise ValueError(f"Unknown time period: {i}")

model.a = Param(model.i, model.j, model.l, initialize=a_init, mutable=True, doc='adjusted availability (hours)')

model.tc = Param(model.l, model.k, initialize=data['tc'], mutable=True, doc='production cost data')
model.tcadd = Param(model.i, model.j, initialize=data['tcadd'], mutable=True, doc='addfactors for tc')

def c_init(model, i, j, k, l):
    if value(model.tc[l, k]) != 0:
        return model.tc[l, k] + model.tcadd[i, j]
    else:
        return model.tc[l, k]

model.c = Param(model.i, model.j, model.k, model.l, initialize=c_init, mutable=True, doc='production cost')

model.p = Param(model.i, model.k, initialize=data['p'], mutable=True, doc='selling price')
model.d = Param(model.i, model.k, initialize=data['d'], mutable=True, doc='demand')

model.s = Param(model.k, initialize=data['s'], mutable=True, doc='storage cost')
model.h = Param(model.k, initialize=data['h'], mutable=True, doc='storage capacity')

# VAR_BLOCK
model.x = Var(model.i, model.j, model.k, model.l, domain=NonNegativeReals, doc='production')
model.y = Var(model.i, model.k, domain=NonNegativeReals, doc='products stored')
model.z = Var(model.i, model.k, doc='products sold')
model.cost = Var(doc='cost')  
model.revenue = Var(doc='revenue')
model.profit = Var(doc='profit')


# CONS_BLOCK

def pdef(model):
    return model.profit == model.revenue - model.cost

def cdef(model):
    return sum(model.s[k]*model.y[i,k] + sum(model.c[i,j,k,l]*model.x[i,j,k,l] for j in model.j for l in model.l) for i in model.i for k in model.k) == model.cost

def rdef(model):
    return sum(model.p[i,k]*model.z[i,k] for i in model.i for k in model.k) == model.revenue

def ma(model, i, j, l):
    return sum(model.t[i,j,k,l]*model.x[i,j,k,l] for k in model.k) <= model.a[i,j,l]

def ib(model, i, k):
    if i == "summer":
        y_prev = 0
    else:
        y_prev = model.y["summer", k]

    total = sum(model.x[i,j,k,l] for j in model.j for l in model.l if value(model.mh[l,k]) != 0)

    return total + y_prev == model.z[i,k] + model.y[i,k]

model.pdef = Constraint(rule=pdef, doc='profit definition')
model.cdef = Constraint(rule=cdef, doc='cost definition')
model.rdef = Constraint(rule=rdef, doc='revenue definition')
model.ma = Constraint(model.i, model.j, model.l, rule=ma, doc='machine availability')
model.ib = Constraint(model.i, model.k, rule=ib, doc='inventory balance')

for i in model.i:
    for k in model.k:
        model.z[i,k].setlb((model.d[i,k]))
        model.y[i,k].setub(model.h[k])    

# OBJ_BLOCK
model.min_obj = Objective(expr=model.profit, sense=maximize)
