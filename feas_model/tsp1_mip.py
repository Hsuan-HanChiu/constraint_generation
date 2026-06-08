# converted from models/tsp1_mip.py
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
    doc="Traveling Salesman Problem with Subtour Elimination"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.ii = Set(
    initialize=data["ii"],
    doc="All cities (i1-i17)"
)

model.i = Set(
    initialize=data["i"],
    within=model.ii,
    doc="Subset of cities to use (i1-i6)"
)

# Alias for i
model.j = Set(
    initialize=data["i"],
    doc="Alias for cities"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------
# c(ii,jj) - cost coefficients
c_dict = {}
for key, val in data["c"].items():
    if isinstance(key, tuple) and len(key) == 2:
        c_dict[key] = val

model.c = Param(
    model.ii, model.ii,
    initialize=c_dict,
    mutable=True,
    default=0,
    doc="Cost coefficients (br17 from TSPLIB)"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.x = Var(
    model.ii, model.ii,
    domain=Binary,
    doc="Decision variables - leg of trip"
)

model.z = Var(
    domain=Reals,
    doc="Objective variable"
)

# ----------------------------------------------------------------------
# Fix diagonal to 0 (no self-loops)
# ----------------------------------------------------------------------
for city in data["ii"]:
    model.x[city, city].fix(0)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.z

model.obj = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Minimize total cost"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# objective.. z =e= sum((i,j), c(i,j)*x(i,j))
def objective_rule(model):
    return model.z == sum(
        c_dict.get((i, j), 0) * model.x[i, j]
        for i in data["i"]
        for j in data["i"]
    )

model.objective = Constraint(
    rule=objective_rule,
    doc="Total cost"
)

# rowsum(i).. sum(j, x(i,j)) =e= 1
def rowsum_rule(model, i):
    return sum(model.x[i, j] for j in data["i"]) == 1

model.rowsum = Constraint(
    model.i,
    rule=rowsum_rule,
    doc="Leave each city only once"
)

# colsum(j).. sum(i, x(i,j)) =e= 1
def colsum_rule(model, j):
    return sum(model.x[i, j] for i in data["i"]) == 1

model.colsum = Constraint(
    model.j,
    rule=colsum_rule,
    doc="Arrive at each city only once"
)

# Add MTZ (Miller-Tucker-Zemlin) subtour elimination constraints
# This is a standard formulation that prevents subtours without
# needing iterative cut generation
# u[i] - u[j] + n*x[i,j] <= n-1 for i,j in cities (i != j, i != 1, j != 1)

n = len(data["i"])

# Add continuous variables u[i] for position in tour
model.u = Var(
    model.i,
    domain=Reals,
    bounds=(1, n),
    doc="Position in tour (MTZ variables)"
)

# Fix the first city's position
first_city = data["i"][0]
model.u[first_city].fix(1)

# MTZ constraints: u[i] - u[j] + n*x[i,j] <= n-1
def mtz_rule(model, i, j):
    if i == j or i == first_city or j == first_city:
        return Constraint.Skip
    return model.u[i] - model.u[j] + n * model.x[i, j] <= n - 1

model.mtz = Constraint(
    model.i, model.j,
    rule=mtz_rule,
    doc="MTZ subtour elimination constraints"
)
