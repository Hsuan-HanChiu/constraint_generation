# converted from models/airsp2_lp134.py
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

# PARAM_BLOCK - All parameters made mutable
model.c = Param(model.i, model.j, initialize=data['c'], mutable=True, doc='costs per aircraft (1000s)')
model.pcap = Param(model.i, model.j, initialize=data['pcap'], mutable=True, doc='passenger capacity of aircraft i on route j')
model.aircraft = Param(model.i, initialize=data['aircraft'], mutable=True, doc='aircraft availability')
model.fixeddemand = Param(model.j, initialize=data['fixeddemand'], mutable=True, doc='fixed demand (passengers in hundreds)')
model.costbumped = Param(model.j, initialize=data['costbumped'], mutable=True, doc='costs associated with bumping passengers')

# VAR_BLOCK - Matching GAMS exactly
# Positive Variable x(i,j), bumped(j);
model.x = Var(model.i, model.j, domain=NonNegativeReals, doc='number of aircraft type i assigned to route j')
model.bumped = Var(model.j, domain=NonNegativeReals, doc='passengers bumped')

# Variable z; (Free variable in GAMS)
model.z = Var(doc='objective variable')

# CONSTRAINT BLOCK - Exactly matching GAMS model "fixed"

# cost.. z =e= sum((i,j), c(i,j)*x(i,j)) + sum(j, costbumped(j)*bumped(j));
def cost_rule(model):
    return model.z == (sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j if (i,j) in data['c']) + 
                      sum(model.costbumped[j] * model.bumped[j] for j in model.j))
model.cost = Constraint(rule=cost_rule, doc='objective')

# avail(i).. sum(j, x(i,j)) =l= aircraft(i);
def avail_rule(model, i):
    return sum(model.x[i, j] for j in model.j) <= model.aircraft[i]
model.avail = Constraint(model.i, rule=avail_rule, doc='aircraft availability constraints')

# demand(j).. sum(i, pcap(i,j)*x(i,j)) + bumped(j) =g= fixeddemand(j);
def demand_rule(model, j):
    return (sum(model.pcap[i, j] * model.x[i, j] for i in model.i if (i,j) in data['pcap']) + 
            model.bumped[j] >= model.fixeddemand[j])
model.demand = Constraint(model.j, rule=demand_rule, doc='demand constraints')

# OBJ_BLOCK - Model fixed / cost, avail, demand /; solve fixed using lp minimizing z;
model.obj = Objective(expr=model.z, sense=minimize, doc='minimize objective variable z')
