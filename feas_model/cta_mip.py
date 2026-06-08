# converted from models/cta_mip.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(
    doc="Controlled Tabular Adjustments (CTA)"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.i = Set(
    initialize=data["i"],
    doc="Rows"
)

model.j = Set(
    initialize=data["j"],
    doc="Columns"
)

model.k = Set(
    initialize=data["k"],
    doc="Planes"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------
# dat(k,i,j) - unprotected data table
dat_dict = {}
for key, val in data["dat"].items():
    if isinstance(key, tuple) and len(key) == 3:
        dat_dict[key] = val

model.dat = Param(
    model.k, model.i, model.j,
    initialize=dat_dict,
    mutable=True,
    default=0,
    doc="Unprotected data table"
)

# pro(k,i,j) - information sensitive cells
pro_dict = {}
for key, val in data["pro"].items():
    if isinstance(key, tuple) and len(key) == 3:
        pro_dict[key] = val

model.pro = Param(
    model.k, model.i, model.j,
    initialize=pro_dict,
    mutable=True,
    default=0,
    doc="Information sensitive cells"
)

model.BigM = Param(
    initialize=data["BigM"],
    mutable=True,
    doc="Big M constant"
)

# Build v and s sets from data
# v(i,j,k) = dat(k,i,j) > 0 (non-zero cells)
# s(i,j,k) = pro(k,i,j) > 0 (sensitive cells)
v_set = set()
s_set = set()

for (k, i, j), val in dat_dict.items():
    if val != 0:
        v_set.add((i, j, k))

for (k, i, j), val in pro_dict.items():
    if val > 0:
        s_set.add((i, j, k))

model.v = Set(
    initialize=list(v_set),
    dimen=3,
    doc="Non-zero cells"
)

model.s = Set(
    initialize=list(s_set),
    dimen=3,
    doc="Sensitive cells"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.t = Var(
    model.i, model.j, model.k,
    domain=Reals,
    doc="Adjusted cell value"
)

model.adjN = Var(
    model.i, model.j, model.k,
    domain=NonNegativeReals,
    doc="Negative adjustment"
)

model.adjP = Var(
    model.i, model.j, model.k,
    domain=NonNegativeReals,
    doc="Positive adjustment"
)

model.b = Var(
    model.i, model.j, model.k,
    domain=Binary,
    doc="Binary variable for adjustment direction"
)

model.obj = Var(
    domain=Reals,
    doc="Objective variable"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.obj

model.objective_func = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Minimize total adjustment"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# defadj(v(i,j,k)).. t(v) =e= dat(k,i,j) + adjP(v) - adjN(v)
def defadj_rule(model, i, j, k):
    if (i, j, k) not in v_set:
        return Constraint.Skip
    return model.t[i, j, k] == model.dat[k, i, j] + model.adjP[i, j, k] - model.adjN[i, j, k]

model.defadj = Constraint(
    model.v,
    rule=defadj_rule,
    doc="Define new cell values"
)

# addrow(i,k).. sum(v(i,j,k), t(v)) =e= 2*t(i,'total',k)
def addrow_rule(model, i, k):
    return sum(model.t[ip, j, kp] for (ip, j, kp) in v_set if ip == i and kp == k) == 2 * model.t[i, 'total', k]

model.addrow = Constraint(
    model.i, model.k,
    rule=addrow_rule,
    doc="Add up for rows"
)

# addcol(j,k).. sum(v(i,j,k), t(v)) =e= 2*t('total',j,k)
def addcol_rule(model, j, k):
    return sum(model.t[i, jp, kp] for (i, jp, kp) in v_set if jp == j and kp == k) == 2 * model.t['total', j, k]

model.addcol = Constraint(
    model.j, model.k,
    rule=addcol_rule,
    doc="Add up for columns"
)

# addpla(i,j).. sum(v(i,j,k), t(v)) =e= 2*t(i,j,'total')
def addpla_rule(model, i, j):
    return sum(model.t[ip, jp, k] for (ip, jp, k) in v_set if ip == i and jp == j) == 2 * model.t[i, j, 'total']

model.addpla = Constraint(
    model.i, model.j,
    rule=addpla_rule,
    doc="Add up for planes"
)

# pmin(s(i,j,k)).. adjN(s) =g= pro(k,i,j)*(1 - b(s))
def pmin_rule(model, i, j, k):
    if (i, j, k) not in s_set:
        return Constraint.Skip
    return model.adjN[i, j, k] >= model.pro[k, i, j] * (1 - model.b[i, j, k])

model.pmin = Constraint(
    model.s,
    rule=pmin_rule,
    doc="Small value for sensitive cells"
)

# pmax(s(i,j,k)).. adjP(s) =g= pro(k,i,j)*b(s)
def pmax_rule(model, i, j, k):
    if (i, j, k) not in s_set:
        return Constraint.Skip
    return model.adjP[i, j, k] >= model.pro[k, i, j] * model.b[i, j, k]

model.pmax = Constraint(
    model.s,
    rule=pmax_rule,
    doc="Big value for sensitive cells"
)

# pminx(s(i,j,k)).. adjN(s) =l= BigM*pro(k,i,j)*(1 - b(s))
def pminx_rule(model, i, j, k):
    if (i, j, k) not in s_set:
        return Constraint.Skip
    return model.adjN[i, j, k] <= model.BigM * model.pro[k, i, j] * (1 - model.b[i, j, k])

model.pminx = Constraint(
    model.s,
    rule=pminx_rule,
    doc="Upper bound for negative adjustment"
)

# pmaxx(s(i,j,k)).. adjP(s) =l= BigM*pro(k,i,j)*b(s)
def pmaxx_rule(model, i, j, k):
    if (i, j, k) not in s_set:
        return Constraint.Skip
    return model.adjP[i, j, k] <= model.BigM * model.pro[k, i, j] * model.b[i, j, k]

model.pmaxx = Constraint(
    model.s,
    rule=pmaxx_rule,
    doc="Upper bound for positive adjustment"
)

# defobj.. obj =e= sum(v, adjN(v) + adjP(v))
def defobj_rule(model):
    return model.obj == sum(model.adjN[i, j, k] + model.adjP[i, j, k] for (i, j, k) in v_set)

model.defobj = Constraint(
    rule=defobj_rule,
    doc="Define objective"
)
