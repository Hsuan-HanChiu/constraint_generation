# converted from models/airsp2_lp87.py
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
model.i = Set(initialize=data['i'], doc='aircraft types and unassigned passengers')
model.j = Set(initialize=data['j'], doc='assigned and unassigned routes')

# PARAM_BLOCK
model.c = Param(model.i, model.j, initialize=data['c'], mutable = True, doc='costs per aircraft (1000s)')
model.pcap = Param(model.i, model.j, initialize=data['pcap'], mutable = True, doc='passenger capacity of aircraft i on route j')
model.aircraft = Param(model.i, initialize=data['aircraft'], mutable = True, doc='aircraft availability')
model.fixeddemand = Param(model.j, initialize=data['fixeddemand'], mutable = True, doc='fixed demand (passengers in hundreds)')
model.costbumped = Param(model.j, initialize=data['costbumped'], mutable = True, doc='costs associated with bumping passengers')

# VAR_BLOCK
model.x = Var(model.i, model.j, domain=NonNegativeReals, doc='number of aircraft type i assigned to route j')
model.bumped = Var(model.j, domain=NonNegativeReals, doc='passengers bumped')
model.z = Var(domain=NonNegativeReals, doc='objective variable')

# OBJ_BLOCK
model.obj = Objective(expr=sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j) +
                           sum(model.costbumped[j] * model.bumped[j] for j in model.j),
                      sense=minimize, doc='objective')

# CONS_BLOCK
def avail_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= model.aircraft[i]
model.avail = Constraint(model.i, rule=avail_rule, doc='aircraft availability constraints')

def demand_rule(model, j):
    return sum(model.pcap[i, j] * model.x[i, j] for i in model.i) + model.bumped[j] >= model.fixeddemand[j]
model.demand = Constraint(model.j, rule=demand_rule, doc='demand constraints')
