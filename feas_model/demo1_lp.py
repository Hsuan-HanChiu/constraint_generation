# converted from models/demo1_lp.py
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
model.c = Set(initialize=data['c'])
model.t = Set(initialize=data['t'])

# PARAM_BLOCK
model.landreq = Param(model.t, model.c, initialize=data['landreq'], mutable = True, doc='months of land occupation by crop (hectares)')
model.laborreq = Param(model.t, model.c, initialize=data['laborreq'], mutable = True, doc='crop labor requirements (man-days per hectare)')
model.yield_param = Param(model.c, initialize=data['yield'], mutable = True, doc='crop yield (tons per hectare)')
model.price = Param(model.c, initialize=data['price'], mutable = True, doc='crop prices (dollars per ton)')
model.miscost = Param(model.c, initialize=data['miscost'], mutable = True, doc='misc cash costs (dollars per hectare)')
model.land = Param(initialize=data['land'], mutable = True, doc='farm size (hectares)')
model.famlab = Param(initialize=data['famlab'], mutable = True, doc='family labor available (days per month)')
model.owage = Param(initialize=data['owage'], mutable = True, doc='hire-out wage rate (dollars per day)')
model.twage = Param(initialize=data['twage'], mutable = True, doc='temporary labor wage (dollars per day)')
model.dpm = Param(initialize=data['dpm'], mutable = True, doc='number of working days per month')

# VAR_BLOCK
model.xcrop = Var(model.c, domain=NonNegativeReals, doc='cropping activity (hectares)')
model.yfarm = Var(domain=NonNegativeReals, doc='farm income (dollars)')
model.revenue = Var(domain=NonNegativeReals, doc='value of production (dollars)')
model.mcost = Var(domain=NonNegativeReals, doc='misc cash cost (dollars)')
model.labcost = Var(domain=NonNegativeReals, doc='labor cost (dollars)')
model.labearn = Var(domain=NonNegativeReals, doc='labor income (dollars)')
model.flab = Var(model.t, domain=NonNegativeReals, doc='family labor use (days)')
model.fout = Var(model.t, domain=NonNegativeReals, doc='hiring out (days)')
model.tlab = Var(model.t, domain=NonNegativeReals, doc='temporary labor (days)')

# OBJ_BLOCK
model.obj = Objective(expr=model.yfarm, sense=maximize)

# CONS_BLOCK
model.landbal = Constraint(model.t, rule=lambda model, t: 
                           sum(model.xcrop[c] * model.landreq[t, c] for c in model.c) <= model.land)

model.laborbal = Constraint(model.t, rule=lambda model, t: 
                            sum(model.xcrop[c] * model.laborreq[t, c] for c in model.c) <= model.flab[t] + model.tlab[t])

model.flabor = Constraint(model.t, rule=lambda model, t: 
                          model.famlab == model.flab[t] + model.fout[t])

model.arev = Constraint(expr=model.revenue == 
                        sum(model.xcrop[c] * model.yield_param[c] * model.price[c] for c in model.c))

model.acost = Constraint(expr=model.mcost == 
                         sum(model.xcrop[c] * model.miscost[c] for c in model.c))

model.alab = Constraint(expr=model.labcost == 
                        sum(model.tlab[t] * model.twage for t in model.t))

model.aout = Constraint(expr=model.labearn == 
                        sum(model.fout[t] * model.owage for t in model.t))

model.income = Constraint(expr=model.yfarm == 
                          model.revenue + model.labearn - model.labcost - model.mcost)
