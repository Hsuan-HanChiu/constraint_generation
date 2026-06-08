# converted from gamslib tablelayout (TABLELAYOUT, SEQ=402), "rows" formulation, MIP variant
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "0|1|10": value → (0, 1, 10): value).
#
# The GAMS source builds its data via an embedded-Python block that reads the
# tablelayout5x5.inc instance file and derives, for the "rows" formulation:
#   - rh(r,h)        : the (row, height) assignments that keep the layout feasible
#   - minRCHw(r,c,h) : the minimum width cell (r,c) needs when row r takes height h
#   - pw             : the page width
# Those derived quantities are baked into the JSON. The numerical height of a row
# equals the height UEL itself (nh(h) = h.val in GAMS), so the height index value
# is used directly as the height in the objective.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# rh set members arrive as pipe-strings "r|h"; parse into (row, height) int pairs.
rh_pairs = [tuple(int(p) for p in s.split("|")) for s in data["rh"]]
R_members = sorted({r for (r, h) in rh_pairs})
C_members = sorted({c for (r, c, h) in data["minRCHw"].keys()})
# heights available per row (for the one-height-per-row and accounting constraints)
heights_of_row = {r: [h for (rr, h) in rh_pairs if rr == r] for r in R_members}

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Automated Table Layout - minimize total table height (rows formulation, MIP)")

# Sets
model.R = pyo.Set(initialize=R_members, doc="Table rows")
model.C = pyo.Set(initialize=C_members, doc="Table columns")
model.rh = pyo.Set(dimen=2, initialize=rh_pairs, doc="Feasible (row, height) assignments")

# Parameters
model.pw = pyo.Param(
    initialize=data["pw"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Page width",
)

model.minRCHw = pyo.Param(
    model.rh, model.C,
    initialize={(r, h, c): data["minRCHw"][(r, c, h)] for (r, h) in rh_pairs for c in C_members},
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Minimum width of cell (r,c) when row r takes height h",
)

# Variables
model.bRH = pyo.Var(
    model.rh,
    domain=pyo.Binary,
    doc="Row r takes height h",
)

model.xRCw = pyo.Var(
    model.R, model.C,
    domain=pyo.Reals,
    doc="Width of cell (r,c)",
)

model.xCw = pyo.Var(
    model.C,
    domain=pyo.Reals,
    doc="Width of column c",
)

model.toth = pyo.Var(
    domain=pyo.Reals,
    doc="Total table height",
)

# Constraints
def defbRH_rule(model, r):
    return sum(model.bRH[r, h] for h in heights_of_row[r]) == 1

model.defbRH = pyo.Constraint(model.R, rule=defbRH_rule, doc="Each row takes exactly one height")

def defxRCw_rule(model, r, c):
    return model.xRCw[r, c] == sum(model.bRH[r, h] * model.minRCHw[r, h, c] for h in heights_of_row[r])

model.defxRCw = pyo.Constraint(model.R, model.C, rule=defxRCw_rule, doc="Define cell width")

def defxCwMIP_rule(model, r, c):
    return model.xCw[c] >= model.xRCw[r, c]

model.defxCwMIP = pyo.Constraint(model.R, model.C, rule=defxCwMIP_rule, doc="Column width is the max cell width")

def defpw_rule(model):
    return sum(model.xCw[c] for c in model.C) <= model.pw

model.defpw = pyo.Constraint(rule=defpw_rule, doc="Limit layout by page width")

def deftoth_rule(model):
    return model.toth == sum(model.bRH[r, h] * h for (r, h) in rh_pairs)

model.deftoth = pyo.Constraint(rule=deftoth_rule, doc="Accounting: total table height")

# Objective
model.obj = pyo.Objective(
    expr=model.toth,
    sense=pyo.minimize,
    doc="Minimize total table height",
)
