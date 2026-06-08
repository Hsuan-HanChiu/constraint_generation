# converted from models/imsl_lp.py
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
    doc="Piecewise linear approximation: primal LP minimizing sum of absolute deviations"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.n = Set(
    initialize=data["n"],
    doc="x-coordinate labels for data"
)
model.m = Set(
    initialize=data["m"],
    doc="x-coordinate labels for approximation"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK  (all mutable = True)
# ----------------------------------------------------------------------
model.y = Param(
    model.n,
    initialize=data["y"],
    mutable=True,
    doc="data values at data points n"
)
model.t = Param(model.n, initialize=data["t"], mutable=True)
model.s = Param(model.m, initialize=data["s"], mutable=True)
model.k = Param(initialize=data["k"], mutable=True)
model.deltn = Param(initialize=data["deltn"], mutable=True)
model.deltm = Param(initialize=data["deltm"], mutable=True)
model.w = Param(
    model.m,
    model.n,
    initialize=data["w"],
    mutable=True,
    doc="interpolation weights that map approximation values ym(m) to data points n"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.ym = Var(
    model.m,
    domain=Reals,
    doc="approximation values at approximation points m"
)

# dp(n), dn(n): positive and negative deviations
model.dp = Var(
    model.n,
    domain=NonNegativeReals,
    doc="positive deviation at data point n"
)
model.dn = Var(
    model.n,
    domain=NonNegativeReals,
    doc="negative deviation at data point n"
)

# tdev: total deviation = sum_n (dp(n) + dn(n))
model.tdev = Var(
    domain=Reals,
    doc="total absolute deviation"
)
# ----------------------------------------------------------------------
# OBJ_BLOCK (primal: minimize total deviation)
# ----------------------------------------------------------------------
model.obj = Objective(
    expr=model.tdev,
    sense=minimize,
    doc="minimize sum of absolute deviations between approximation and data"
)    

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------
# ddev(n).. sum(m, w(m,n)*ym(m)) - y(n) =e= dp(n) - dn(n);
def ddev_rule(model, n):
    return (
        sum(model.w[m, n] * model.ym[m] for m in model.m)
        - model.y[n]
        == model.dp[n] - model.dn[n]
    )

model.ddev = Constraint(
    model.n,
    rule=ddev_rule,
    doc="deviation definition at each data point n"
)

# dtdev.. tdev =e= sum(n, dp(n) + dn(n));
def dtdev_rule(model):
    return model.tdev == sum(model.dp[n] + model.dn[n] for n in model.n)

model.dtdev = Constraint(
    rule=dtdev_rule,
    doc="total deviation definition"
)
