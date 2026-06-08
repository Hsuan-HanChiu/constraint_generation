# converted from models/binpacking_mip.py
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
model.I = pyo.Set(initialize=list(data["i"]), doc="items")
model.J = pyo.Set(initialize=list(data["j"]), doc="bins")

# Parameters
model.B = pyo.Param(initialize=float(data["B"]), mutable=True, doc="bin capacity")
model.s = pyo.Param(
    model.I,
    initialize=lambda _m, i: float(data["s"][i]),
    mutable=True,
    doc="item sizes",
)

# Variables
model.y = pyo.Var(model.I, model.J, domain=pyo.Binary, doc="assignment of item to bin")
model.z = pyo.Var(model.J, domain=pyo.Binary, doc="bin open indicator")
model.open_bins = pyo.Var(
    domain=pyo.NonNegativeReals,
    doc="number of open bins",
)

# Constraints
def defopen_rule(model, j):
    return sum(model.s[i] * model.y[i, j] for i in model.I) <= model.B * model.z[j]

model.defopen = pyo.Constraint(model.J, rule=defopen_rule, doc="capacity in each bin")

def defone_rule(model, i):
    return sum(model.y[i, j] for j in model.J) == 1.0

model.defone = pyo.Constraint(model.I, rule=defone_rule, doc="each item in exactly one bin")

def defobj_rule(model):
    return model.open_bins == sum(model.z[j] for j in model.J)

model.defobj = pyo.Constraint(rule=defobj_rule, doc="definition of open_bins")

# Objective (name must be obj)
model.obj = pyo.Objective(expr=model.open_bins, sense=pyo.minimize)
