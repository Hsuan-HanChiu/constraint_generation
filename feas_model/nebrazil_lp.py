# converted from gamslib nebrazil (NEBRAZIL, SEQ=87)
#
# North-East Brazil Regional Agricultural Model.
# The original GAMS model solves the same farm-income LP five times, once per
# zone (west, sertao, southeast, east, agreste), with a different right-hand-side
# data instance each pass — these are five independent single-zone LPs, NOT
# iterations.  This OptiChat conversion bakes in the FIRST zone's data instance
# (zone = "west") and drops the zone loop and reporting, yielding ONE clean,
# deterministic regional LP.
#
# The single-zone LP is represented in scalar (coefficient-matrix) form:
#   maximize  x[obj]              (consumer-producer surplus, a free variable)
#   s.t.      sum_v A[e,v]*x[v]  {<=,=,>=}  rhs[e]   for every equation e
# with variable bounds inherited from the zone-west instance.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format; pipe-delimited
# keys (e.g. "4|94") are decoded to tuple keys (4, 94) and integer-looking
# tokens are coerced to ints by the normalizer.
data = globals().get("data", {})

# The normalizer coerces pipe-delimited multi-index keys (e.g. "4|94" -> (4, 94))
# to ints but leaves single-token set members and dict keys as strings. Coerce
# every index here so variable/equation indices line up with the coefficient
# matrix's integer tuple keys.
def _i(t):
    return int(t) if isinstance(t, str) else t


_V = [_i(v) for v in data["V"]]
_E = [_i(e) for e in data["E"]]
_Vfree = [_i(v) for v in data["Vfree"]]
_Vbfree = [_i(v) for v in data["Vbfree"]]
_A = {(_i(e), _i(v)): float(c) for (e, v), c in data["A"].items()}
_rhs = {_i(e): float(r) for e, r in data["rhs"].items()}
_sense = {_i(e): int(round(float(s))) for e, s in data["sense"].items()}
_vub = {_i(v): float(b) for v, b in data["vub"].items()}
# ─────────────────────────────────────────────────────────────────────────────

# Objective variable index (free var x398 = consumer-producer surplus "cps")
OBJ_VAR = 398

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(
    doc="North-East Brazil regional agricultural LP (zone=west) - maximize farm income"
)

# Sets
model.V = pyo.Set(initialize=_V, doc="Variable indices (1..414)")
model.E = pyo.Set(initialize=_E, doc="Equation indices (1..185)")
model.Vfree = pyo.Set(initialize=_Vfree, doc="Free variables (-inf, +inf)")
model.Vbfree = pyo.Set(initialize=_Vbfree, doc="Bounded-free variables [0, vub]")

# Parameters
model.A = pyo.Param(
    _A.keys(),
    initialize=_A,
    mutable=True,
    within=pyo.Reals,
    doc="Sparse constraint coefficient A[e, v]",
)
model.rhs = pyo.Param(
    model.E,
    initialize=_rhs,
    mutable=True,
    within=pyo.Reals,
    doc="Right-hand side of each equation",
)
model.sense = pyo.Param(
    model.E,
    initialize=_sense,
    mutable=True,
    within=pyo.Integers,
    doc="Constraint sense: -1 = <=, 0 = =, 1 = >=",
)
model.vub = pyo.Param(
    model.Vbfree,
    initialize=_vub,
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Finite upper bound for bounded-free variables",
)

# Variable domain / bounds:
#   - free vars (Vfree)   -> Reals, no bounds
#   - bounded-free (Vbfree) -> Reals, [0, vub]
#   - all others          -> NonNegativeReals, [0, +inf)
_vfree = set(_Vfree)
_vbfree = set(_Vbfree)


def _var_domain(model, v):
    return pyo.Reals if (v in _vfree or v in _vbfree) else pyo.NonNegativeReals


def _var_bounds(model, v):
    if v in _vbfree:
        return (0.0, pyo.value(model.vub[v]))
    return (None, None)


# Variables
model.x = pyo.Var(
    model.V,
    domain=_var_domain,
    bounds=_var_bounds,
    doc="Decision variables of the scalar single-zone LP",
)

# Precompute the nonzero columns of each row for fast constraint construction.
_rows = {e: [] for e in _E}
for (e, v) in _A.keys():
    _rows[e].append(v)


# Constraints
def _con_rule(model, e):
    lhs = sum(model.A[e, v] * model.x[v] for v in _rows[e])
    s = pyo.value(model.sense[e])
    if s < 0:
        return lhs <= model.rhs[e]
    if s > 0:
        return lhs >= model.rhs[e]
    return lhs == model.rhs[e]


model.con = pyo.Constraint(model.E, rule=_con_rule, doc="Single-zone LP equations")

# Objective
model.obj = pyo.Objective(
    expr=model.x[OBJ_VAR],
    sense=pyo.maximize,
    doc="Maximize consumer-producer surplus (farm income) for zone west",
)
