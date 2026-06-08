# converted from gamslib cube (CUBE, SEQ=42)
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "low": value for scalar-indexed).
#
# Three-dimensional noughts and crosses: white (0) and black (1) balls are
# arranged in a 3x3x3 cube, one per cell, to minimize the number of lines whose
# balls are all of equal color. 49 lines exist: 27 axis lines, 18 in-plane
# diagonals, and 4 across-plane diagonals.

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Three-dimensional Noughts and Crosses (cube line balance)")

# Sets
model.s = pyo.Set(initialize=data["s"], doc="Domain for line identification")
model.x = pyo.Set(initialize=data["x"], doc="Coordinate labels")
model.d = pyo.Set(initialize=data["d"], doc="Directions (incr, decr)")
model.b = pyo.Set(initialize=data["b"], doc="Bounds (low, high)")

# ── derived index data reconstructed from the source sets ────────────────────
# Coordinate labels and their ordinals (GAMS ord over set x = {a, b, c}).
x_list = list(data["x"])
ord_x = {lab: i + 1 for i, lab in enumerate(x_list)}
card_x = len(x_list)

# df(x, s): line definition function (GAMS lines 43-44).
#   df(x, y)      = ord(y) - ord(x)        for y in coordinate labels
#   df(x, "incr") = 0                       (unassigned -> default)
#   df(x, "decr") = 1 + card(x) - 2*ord(x)
df = {}
for lab in x_list:
    for lab2 in x_list:                       # y in {a, b, c}
        df[(lab, lab2)] = ord_x[lab2] - ord_x[lab]
    df[(lab, "incr")] = 0
    df[(lab, "decr")] = 1 + card_x - 2 * ord_x[lab]

# ld(s, sp, spp): line definition set (GAMS lines 28-34).
ld = set()
for y in x_list:
    for z in x_list:
        ld.add(("incr", y, z))                # ld("incr", y, z)
        ld.add((y, "incr", z))                # ld(x, "incr", z)
        ld.add((y, z, "incr"))                # ld(x, y, "incr")
for dd in data["d"]:
    for z in x_list:
        ld.add(("incr", dd, z))               # ld("incr", d, z)
        ld.add((z, "incr", dd))               # ld(x, "incr", d)
        ld.add((dd, z, "incr"))               # ld(d, y, "incr")
    for dp in data["d"]:
        ld.add(("incr", dd, dp))              # ld("incr", d, dp)

ld_list = sorted(ld)


def _cell(lab, direction):
    """Map coordinate label `lab` shifted by df(lab, direction) to a label.

    GAMS set arithmetic: ord(lab) + df(lab, direction) indexes back into the
    coordinate set x = {a, b, c}. By construction the result is always in range.
    """
    pos = ord_x[lab] + df[(lab, direction)]
    return x_list[pos - 1]


# Parameters (genuine GAMS data parameters)
model.ls = pyo.Param(
    model.b,
    initialize=data["ls"],
    mutable=True,
    within=pyo.Reals,
    doc="Sign for line definitions (low 1, high -1)",
)

model.lr = pyo.Param(
    model.b,
    initialize=data["lr"],
    mutable=True,
    within=pyo.Reals,
    doc="RHS for line definitions (low 2, high -1)",
)

# Variables
model.core = pyo.Var(
    model.x, model.x, model.x,
    domain=pyo.Binary,
    doc="Placement of balls (white 0, black 1)",
)

model.line = pyo.Var(
    model.s, model.s, model.s,
    domain=pyo.NonNegativeReals,
    doc="Line identification",
)

model.num = pyo.Var(
    domain=pyo.Reals,
    doc="Number of lines of equal color",
)

# Constraints
# nbb.. sum((x,y,z), core(x,y,z)) =e= floor(card(x)**3 / 2)
def nbb_rule(model):
    rhs = (card_x ** 3) // 2
    return sum(model.core[ix, iy, iz]
               for ix in model.x for iy in model.x for iz in model.x) == rhs

model.nbb = pyo.Constraint(rule=nbb_rule, doc="Total number of balls definition")


# ldef(s,sp,spp,b)$ld(s,sp,spp)..
#   ls(b)*sum(x, core(x+df(x,s), x+df(x,sp), x+df(x,spp))) =l= line(s,sp,spp) + lr(b)
def ldef_rule(model, ss, sp, spp, bb):
    if (ss, sp, spp) not in ld:
        return pyo.Constraint.Skip
    lhs = model.ls[bb] * sum(
        model.core[_cell(lab, ss), _cell(lab, sp), _cell(lab, spp)]
        for lab in x_list
    )
    return lhs <= model.line[ss, sp, spp] + model.lr[bb]

model.ldef = pyo.Constraint(
    model.s, model.s, model.s, model.b,
    rule=ldef_rule,
    doc="Line definitions",
)


# ndef.. num =e= sum((s,sp,spp)$ld(s,sp,spp), line(s,sp,spp))
def ndef_rule(model):
    return model.num == sum(model.line[t] for t in ld_list)

model.ndef = pyo.Constraint(rule=ndef_rule, doc="Number of lines definition")

# Objective
model.obj = pyo.Objective(
    expr=model.num,
    sense=pyo.minimize,
    doc="Minimize number of lines of equal color",
)
