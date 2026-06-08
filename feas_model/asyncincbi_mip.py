# converted from gamslib asyncincbi (ASYNCINCBI, SEQ=430)
# The GAMS file wraps the pk1 MIPLIB instance in async/CPLEX incumbent-reporting
# scaffolding (mutex, savesol.gms, monitorsol.gms). That machinery only re-solves
# the SAME deterministic MIP and stops it early once an incumbent is found; it does
# not change the model. We convert the underlying MIP and drop the async scaffolding.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "r1|b33": value → (r1, b33): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ─────────────────────────────────────────────────────────────────────
# Original pk1 structure:
#   x1 = x2 (e1), objective minimizes x1, so we minimize x2.
#   x2 >= x[i] for every continuous x[i] (e2..e31): x2 is the running max.
#   Each row r couples a "low"/"high" continuous pair with a weighted binary sum:
#     xlo[r] - xhi[r] + sum_j coef[r,j]*b[j] == rhs   (e32..e46)
model = pyo.ConcreteModel(doc="pk1 MIPLIB instance (asyncincbi underlying MIP)")

# Sets
model.rows = pyo.Set(initialize=data["rows"], ordered=True, doc="Coupling rows (e32..e46)")
model.bins = pyo.Set(initialize=data["bins"], ordered=True, doc="Binary variables b33..b87")

# Parameters
model.rhs = pyo.Param(
    initialize=data["rhs"],
    mutable=True,
    within=pyo.Reals,
    doc="Right-hand side of every coupling row",
)

model.coef = pyo.Param(
    model.rows, model.bins,
    initialize=data["coef"],
    mutable=True,
    within=pyo.Reals,
    doc="Binary coefficient of each bin in each coupling row",
)

# Variables
model.xmax = pyo.Var(
    domain=pyo.NonNegativeReals,
    doc="Objective variable: upper bound over all continuous x (x1 = x2)",
)

model.xlo = pyo.Var(
    model.rows,
    domain=pyo.NonNegativeReals,
    doc="First continuous var of each row (x3, x5, ...)",
)

model.xhi = pyo.Var(
    model.rows,
    domain=pyo.NonNegativeReals,
    doc="Second continuous var of each row (x4, x6, ...)",
)

model.b = pyo.Var(
    model.bins,
    domain=pyo.Binary,
    doc="Binary decision variables b33..b87",
)

# Constraints
def bound_lo_rule(model, r):
    return model.xmax >= model.xlo[r]

model.bound_lo = pyo.Constraint(model.rows, rule=bound_lo_rule, doc="xmax >= xlo[r] (subset of e2..e31)")

def bound_hi_rule(model, r):
    return model.xmax >= model.xhi[r]

model.bound_hi = pyo.Constraint(model.rows, rule=bound_hi_rule, doc="xmax >= xhi[r] (subset of e2..e31)")

def coupling_rule(model, r):
    return (
        model.xlo[r] - model.xhi[r]
        + sum(model.coef[r, j] * model.b[j] for j in model.bins)
        == model.rhs
    )

model.coupling = pyo.Constraint(model.rows, rule=coupling_rule, doc="Row coupling constraints (e32..e46)")

# Objective
model.obj = pyo.Objective(
    expr=model.xmax,
    sense=pyo.minimize,
    doc="Minimize x1 (= x2 = max over continuous x)",
)
