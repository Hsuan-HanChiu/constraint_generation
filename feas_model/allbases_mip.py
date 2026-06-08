# converted from models/allbases_mip.py
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel()

# =====================
# Sets
# =====================
I_list = list(data["i"])
J_list = list(data["j"])

model.i = pyo.Set(initialize=I_list, doc="canning plants")
model.j = pyo.Set(initialize=J_list, doc="markets")

# =====================
# Parameters (from data)
# =====================
# a(i), b(j)
a_raw = data["a"]
b_raw = data["b"]

def a_init(model, i):
    return float(a_raw[i])

def b_init(model, j):
    return float(b_raw[j])

model.a = pyo.Param(model.i, initialize=a_init, mutable=True, doc="capacity of plant i")
model.b = pyo.Param(model.j, initialize=b_init, mutable=True, doc="demand at market j")

# distance d(i,j): keys may be tuples ("seattle","new-york")
d_raw = data["d"]

def d_init(model, i, j):
    key = (i, j)
    return float(d_raw[key])

model.d = pyo.Param(model.i, model.j, initialize=d_init, mutable=True, doc="distance in thousand miles")

# freight f
f_val = float(data["f"])
model.f = pyo.Param(initialize=f_val, mutable=True, doc="freight in dollars/case/1000 miles")

# transport cost c(i,j) = f * d(i,j) / 1000 (thousands of dollars per case)
def c_init(model, i, j):
    return model.f * model.d[i, j] / 1000.0

model.c = pyo.Param(model.i, model.j, initialize=c_init, mutable=True,
                doc="transport cost in thousands of dollars per case")

# Precompute min(a(i), b(j)) for defximp
min_ab = {(ii, jj): min(float(a_raw[ii]), float(b_raw[jj])) for ii in I_list for jj in J_list}

def min_ab_init(model, i, j):
    return float(min_ab[(i, j)])

model.min_ab = pyo.Param(model.i, model.j, initialize=min_ab_init, mutable=True,
                     doc="min(a(i), b(j)) for basis bound")

# =====================
# Variables
# =====================
model.x = pyo.Var(model.i, model.j, domain=pyo.NonNegativeReals,
              doc="shipment quantities in cases")
model.sslack = pyo.Var(model.i, domain=pyo.NonNegativeReals,
                   doc="slack for supply constraint")
model.dslack = pyo.Var(model.j, domain=pyo.NonNegativeReals,
                   doc="slack for demand constraint")
model.z = pyo.Var(domain=pyo.Reals,
              doc="total transportation cost in thousands of dollars")

# Basis indicator variables
model.xind = pyo.Var(model.i, model.j, domain=pyo.Binary,
                 doc="x basis indicator")
model.sslind = pyo.Var(model.i, domain=pyo.Binary,
                   doc="sslack basis indicator")
model.dslind = pyo.Var(model.j, domain=pyo.Binary,
                   doc="dslack basis indicator")

# =====================
# Constraints
# =====================
# cost.. z =e= sum((i,j), c(i,j)*x(i,j));
def cost_rule(model):
    return model.z == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)

model.cost = pyo.Constraint(rule=cost_rule, doc="define objective function")

# supply(i).. sum(j, x(i,j)) =e= a(i) - sslack(i);
def supply_rule(model, i):
    return sum(model.x[i, j] for j in model.j) == model.a[i] - model.sslack[i]

model.supply = pyo.Constraint(model.i, rule=supply_rule,
                          doc="observe supply limit at plant i")

# demand(j).. sum(i, x(i,j)) =e= b(j) + dslack(j);
def demand_rule(model, j):
    return sum(model.x[i, j] for i in model.i) == model.b[j] + model.dslack[j]

model.demand = pyo.Constraint(model.j, rule=demand_rule,
                          doc="satisfy demand at market j")

# defbasis.. card(i) + card(j)
#            =e= sum((i,j), xind(i,j)) + sum(i, sslind(i)) + sum(j, dslind(j));
card_i = len(I_list)
card_j = len(J_list)

defbasis_rhs = card_i + card_j

model.defbasis = pyo.Constraint(
    expr=defbasis_rhs ==
    sum(model.xind[i, j] for i in model.i for j in model.j)
    + sum(model.sslind[i] for i in model.i)
    + sum(model.dslind[j] for j in model.j),
    doc="basis definition"
)

# defximp(i,j).. x(i,j) =l= min(a(i),b(j))*xind(i,j);
def defximp_rule(model, i, j):
    return model.x[i, j] <= model.min_ab[i, j] * model.xind[i, j]

model.defximp = pyo.Constraint(model.i, model.j, rule=defximp_rule,
                           doc="xind=0 => x=0")

# defsslimp(i).. sslack(i) =l= a(i)*sslind(i);
def defsslimp_rule(model, i):
    return model.sslack[i] <= model.a[i] * model.sslind[i]

model.defsslimp = pyo.Constraint(model.i, rule=defsslimp_rule,
                             doc="sslind=0 => sslack=0")

# defdslimp(j).. dslack(j) =l= b(j)*dslind(j);
def defdslimp_rule(model, j):
    return model.dslack[j] <= model.b[j] * model.dslind[j]

model.defdslimp = pyo.Constraint(model.j, rule=defdslimp_rule,
                             doc="dslind=0 => dslack=0")

# =====================
# Objective
# =====================
model.obj = pyo.Objective(expr=model.z, sense=pyo.minimize)
