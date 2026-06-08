# converted from models/nemhaus_nlp.py
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

# model.j = Set(initialize=[data["jj"][:4]], doc="active facilities (1 facility)")
model.j = Set(initialize=["fac-1", "fac-2", "fac-3", "fac-4"], doc="active facilities (1 facility)")

model.k = Set(initialize=data["i"], doc="alias of i")

# =========================
# PARAM_BLOCK
# =========================

model.a = Param(model.i, model.k, initialize=data['a'], default=0, doc="interaction cost a(i,k)")

# =========================
# VAR_BLOCK
# =========================
model.x = Var(model.i, model.j, domain=NonNegativeReals, doc="assignment variable")
model.z = Var(doc="total interaction cost")

# =========================
# OBJ_BLOCK
# =========================

model.obj = Objective(expr=model.z, sense=minimize) 

# =========================
# CONS_BLOCK
# =========================
def zdef_rule(model):
    return model.z == sum(
        model.x[i, j] * model.a[i, k] * model.x[k, j]
        for i in model.i for k in model.k for j in model.j
    )

model.zdef = Constraint(rule=zdef_rule, doc="objective definition")

def sch_rule(model, i):
    return sum(model.x[i, j] for j in model.j) == 1

model.sch = Constraint(model.i, rule=sch_rule, doc="each activity is assigned")
