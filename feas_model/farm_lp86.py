# converted from models/farm_lp86.py
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
model.crop = Set(initialize=data['crop'])
model.cropr = Set(initialize=data['cropr'])
model.cropx = Set(initialize=data['cropx'])

# PARAM_BLOCK
model.yield_param = Param(model.crop, initialize=data['yield'], mutable = True, doc='tons per acre')
model.plantcost = Param(model.crop, initialize=data['plantcost'], mutable = True, doc='dollars per acre')
model.sellprice = Param(model.cropx, initialize=data['sellprice'], mutable = True, doc='dollars per ton')
model.purchprice = Param(model.cropr, initialize=data['purchprice'], mutable = True, doc='dollars per ton')
model.minreq = Param(model.cropr, initialize=data['minreq'], mutable = True, doc='minimum requirements in ton')
model.maxbuy = Param(model.cropr, initialize=data['maxbuy'], mutable = True, doc='per-supplier purchase cap in ton')
model.land = Param(initialize=data['land'], mutable = True, doc='available land')
model.maxbeets1 = Param(initialize=data['maxbeets1'], mutable = True, doc='max allowed')

# VAR_BLOCK
model.x = Var(model.crop, domain=NonNegativeReals, doc='acres of land')
model.w = Var(model.cropx, bounds=(0, None), domain=NonNegativeReals, doc='crops sold')
model.y = Var(model.cropr, domain=NonNegativeReals, doc='crops purchased')
model.yld = Var(model.crop, domain=NonNegativeReals, doc='yield')
model.profit = Var(domain=NonNegativeReals, doc='objective variable')

# OBJ_BLOCK
model.obj = Objective(
    expr=-sum(model.plantcost[c] * model.x[c] for c in model.crop)
         - sum(model.purchprice[r] * model.y[r] for r in model.cropr)
         + sum(model.sellprice[x] * model.w[x] for x in model.cropx),
    sense=maximize
)

# CONS_BLOCK
model.landuse = Constraint(expr=sum(model.x[c] for c in model.crop) <= model.land)
model.ylddef = Constraint(model.crop, 
                          rule=lambda m, c: m.yld[c] == m.yield_param[c] * m.x[c])
model.req = Constraint(model.cropr,
                       rule=lambda m, r: m.yld[r] + m.y[r] - sum(m.w[x] for x in m.cropx if x == r) >= m.minreq[r])
model.buy_cap = Constraint(model.cropr,
                           rule=lambda m, r: m.y[r] <= m.maxbuy[r])
model.beets = Constraint(expr=model.w['beets1'] + model.w['beets2'] <= model.yld['sugarbeets'])
model.beets1_limit = Constraint(expr=model.w['beets1'] <= model.maxbeets1)
