# converted from gamslib indus89 (INDUS89, SEQ=181) - Indus Basin Model Revised (IBMR)
#
# This is the full agricultural-water-resource LP `wsisn` (IBMR with water
# network, linear objective), maximizing consumer-plus-producer surplus `cps`.
#
# The original GAMS model has heavy derived-data preprocessing (yields, water
# requirements `wnr`, demand-curve linearization `ws/qs`, canal/reservoir
# routing, etc.). A faithful *semantic* re-implementation was infeasible, so the
# model was extracted in fully-expanded coefficient-matrix form via GAMS CONVERT
# (the same scalar/Jacobian dump CONVERT emits), then transcribed here as a
# generic scalar LP:  variables x{i}, sparse coefficient matrix A[r, v],
# right-hand sides rhs[r], row senses csense[r] in {E, L, G}, plus per-variable
# bounds lb/ub and objective coefficients objc.
#
# NOTE ON FIDELITY: the demand-curve piecewise-linearization grid `p` was set to
# 6 points (original 20). The full-resolution model has 6,570 columns, which
# exceeds the GAMS community license cap (>5000 rows/cols), so CONVERT itself is
# blocked at model-generation time. p=6 (4,935 columns) is the highest grid
# resolution that fits under the cap and lets CONVERT run. This coarsens only the
# demand-curve approximation; the constraint structure and feasibility are
# preserved. Gurobi (which has no such cap) solves the extracted matrix to
# optimality.

import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "r1|x1": value → ("r1", "x1"): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(
    doc="Indus Basin Model Revised (IBMR) - irrigation/agriculture water LP, "
        "maximize consumer plus producer surplus (expanded coefficient-matrix form)"
)

# Sets
model.V = pyo.Set(initialize=data["V"], doc="Decision variable indices (x1..xN)")
model.R = pyo.Set(initialize=data["R"], doc="Constraint row indices (r1..rM)")

# Parameters
model.objc = pyo.Param(
    model.V,
    initialize=data["objc"],
    default=0.0,
    mutable=True,
    within=pyo.Reals,
    doc="Objective coefficient of each variable (surplus contribution)",
)

model.lb = pyo.Param(
    model.V,
    initialize=data["lb"],
    default=0.0,
    mutable=True,
    within=pyo.Reals,
    doc="Lower bound of each variable (0 unless overridden)",
)

model.ub = pyo.Param(
    model.V,
    initialize=data["ub"],
    default=float("inf"),
    mutable=True,
    within=pyo.Reals,
    doc="Upper bound of each variable (+inf unless overridden)",
)

model.A = pyo.Param(
    data["A"].keys(),
    initialize=data["A"],
    mutable=True,
    within=pyo.Reals,
    doc="Sparse constraint coefficient A[row, var]",
)

model.rhs = pyo.Param(
    model.R,
    initialize=data["rhs"],
    mutable=True,
    within=pyo.Reals,
    doc="Right-hand side of each constraint row",
)

model.csense = pyo.Param(
    model.R,
    initialize=data["csense"],
    within=pyo.Any,
    doc="Row sense: 'E' (==), 'L' (<=), or 'G' (>=)",
)

model.obj_const = pyo.Param(
    initialize=data["obj_const"],
    mutable=True,
    within=pyo.Reals,
    doc="Constant term added to the objective",
)

# Precompute the nonzeros incident to each row for efficient constraint build.
_rows_of = {r: [] for r in data["R"]}
for (r, v) in data["A"].keys():
    _rows_of[r].append(v)

# Variables
model.x = pyo.Var(model.V, domain=pyo.NonNegativeReals, doc="Generic decision variables")
for v in model.V:
    model.x[v].setlb(pyo.value(model.lb[v]))
    ubv = pyo.value(model.ub[v])
    model.x[v].setub(None if ubv == float("inf") else ubv)

# Constraints
def con_rule(model, r):
    lhs = sum(model.A[r, v] * model.x[v] for v in _rows_of[r])
    s = model.csense[r]
    b = model.rhs[r]
    if s == "E":
        return lhs == b
    elif s == "L":
        return lhs <= b
    else:  # "G"
        return lhs >= b

model.con = pyo.Constraint(model.R, rule=con_rule, doc="Expanded model rows")

# Objective
model.obj = pyo.Objective(
    expr=sum(model.objc[v] * model.x[v] for v in model.V) + model.obj_const,
    sense=pyo.maximize,
    doc="Maximize consumer plus producer surplus (million rupees)",
)
