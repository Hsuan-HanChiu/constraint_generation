# converted from models/nemhaus_mip.py
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

# =========================
# SET_BLOCK
# =========================
model.i = Set(initialize=data["i"], doc="activities")
model.jj = Set(initialize=data["jj"], doc="all facilities")
model.j = Set(initialize=["fac-1", "fac-2", "fac-3", "fac-4"], doc="active facilities (1 facility)")

model.k = Set(initialize=data["i"], doc="alias of i")

# =========================
# PARAM_BLOCK
# =========================

model.a = Param(model.i, model.k, initialize=data['a'], default=0, doc="interaction cost a(i,k)")

# =========================
# VAR_BLOCK
# =========================
model.xb = Var(model.i, model.j, domain=Binary, doc="binary assignment")
model.y = Var(model.i, model.j, model.k, domain=NonNegativeReals, doc="product x(i,j)*x(k,j)")
model.z = Var(doc="total interaction cost")

# =========================
# OBJ_BLOCK
# =========================
def obj_rule(model):
    return model.z

model.obj = Objective(rule=obj_rule, sense=minimize)

# =========================
# CONS_BLOCK
# =========================
def bsch_rule(model, i):
    return sum(model.xb[i, j] for j in model.j) == 1

model.bsch = Constraint(model.i, rule=bsch_rule, doc="binary scheduling")

def bzdef_rule(model):
    return model.z == sum(
        model.a[i, k] * model.y[i, j, k]
        for i in model.i for k in model.k for j in model.j
    )

model.bzdef = Constraint(rule=bzdef_rule, doc="linearized objective")

def ydef_rule(model, i, j, k):
    if model.a[i, k] == 0:
        return Constraint.Skip
    return model.y[i, j, k] >= model.xb[i, j] + model.xb[k, j] - 1

model.ydef = Constraint(model.i, model.j, model.k, rule=ydef_rule, doc="linearization constraint")
