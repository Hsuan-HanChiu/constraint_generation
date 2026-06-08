# converted from models/icut_mip.py
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

# Sets
I_list = list(data["i"])
KK_list = list(data["kk"])

model.I = pyo.Set(initialize=I_list, ordered=True, doc="index on integer variable")
model.KK = pyo.Set(initialize=KK_list, ordered=True, doc="cut identification set")

ord_i = {i: idx for idx, i in enumerate(I_list, start=1)}
card_i = len(I_list)

# Cut parameters (mutable, initially zero)
def _zero_init(*_):
    return 0.0

model.cutrhs = pyo.Param(model.KK, initialize=_zero_init, mutable=True, doc="cut RHS value")
model.cutlx = pyo.Param(model.KK, model.I, initialize=_zero_init, mutable=True, doc="cut lower bound")
model.cutux = pyo.Param(model.KK, model.I, initialize=_zero_init, mutable=True, doc="cut upper bound")
model.cuts = pyo.Param(model.KK, model.I, initialize=_zero_init, mutable=True, doc="cut solution value")

# Variables
model.x = pyo.Var(model.I, domain=pyo.Integers, bounds=(2, 4), doc="test variable")
model.z = pyo.Var(domain=pyo.Reals, doc="objective variable")

model.b = pyo.Var(model.KK, model.I, domain=pyo.Binary, doc="flip-flop for in-between solutions")
model.u = pyo.Var(model.KK, model.I, domain=pyo.NonNegativeReals, doc="changes up")
model.l = pyo.Var(model.KK, model.I, domain=pyo.NonNegativeReals, doc="changes down")

# Fix and bounds as in GAMS
if 2 in model.I:
    model.x[2].fix(3)
if 4 in model.I:
    model.x[4].setub(3)

# Objective: obj.. z =e= sum(i, 10^(card(i)-ord(i))*x(i));
def obj_def_rule(m):
    return m.z == sum(10 ** (card_i - ord_i[i]) * m.x[i] for i in m.I)

model.obj_def = pyo.Constraint(rule=obj_def_rule, doc="objective definition")
model.obj = pyo.Objective(expr=model.z, sense=pyo.minimize)

# Cuts – placeholder structure, skipped when params are zero

def cut_rule(m, k):
    if abs(pyo.value(m.cutrhs[k])) < 1e-12:
        return pyo.Constraint.Skip
    return -sum(m.x[i] for i in m.I) + sum(m.l[k, i] + m.u[k, i] for i in m.I) >= m.cutrhs[k]

model.cut = pyo.Constraint(model.KK, rule=cut_rule, doc="main cut equations (placeholder)")

def cutu_rule(m, k, i):
    if abs(pyo.value(m.cutux[k, i])) < 1e-12:
        return pyo.Constraint.Skip
    return m.u[k, i] <= m.cutux[k, i] * m.b[k, i]

model.cutu = pyo.Constraint(model.KK, model.I, rule=cutu_rule, doc="upper bound limit")

def cutl_rule(m, k, i):
    if abs(pyo.value(m.cutlx[k, i])) < 1e-12:
        return pyo.Constraint.Skip
    return m.l[k, i] <= m.cutlx[k, i] * (1 - m.b[k, i])

model.cutl = pyo.Constraint(model.KK, model.I, rule=cutl_rule, doc="lower bound limit")

def cutul_rule(m, k, i):

    if (
        abs(pyo.value(m.cuts[k, i])) < 1e-12
        and abs(pyo.value(m.cutux[k, i])) < 1e-12
        and abs(pyo.value(m.cutlx[k, i])) < 1e-12
    ):
        return pyo.Constraint.Skip
    return m.x[i] == m.cuts[k, i] + m.u[k, i] - m.l[k, i]

model.cutul = pyo.Constraint(model.KK, model.I, rule=cutul_rule, doc="x = cuts + u - l")
