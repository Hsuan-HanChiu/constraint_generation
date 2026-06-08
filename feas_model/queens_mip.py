# converted from models/queens_mip.py
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
    doc="Maximum Queens Chess Problem"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.i = Set(
    initialize=data["i"],
    doc="Size of chess board"
)

model.s = Set(
    initialize=data["s"],
    doc="Diagonal offsets"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------
# Compute sh and rev parameters
iMax = data.get("iMax", 8)

sh_dict = {}
for s in data["s"]:
    sh_dict[s] = int(s) - iMax + 1

model.sh = Param(
    model.s,
    initialize=sh_dict,
    doc="Shift values for diagonals"
)

rev_dict = {}
for i in data["i"]:
    rev_dict[i] = iMax + 1 - 2*int(i)

model.rev = Param(
    model.i,
    initialize=rev_dict,
    doc="Reverse order"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.x = Var(
    model.i, model.i,
    domain=Binary,
    doc="Square occupied by queen"
)

model.tot = Var(
    doc="Total squares occupied by queens"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
# Create obj as the objective for compatibility with run.py
def obj_rule(model):
    return model.tot

model.obj = Objective(
    rule=obj_rule,
    sense=maximize,
    doc="Maximize total squares occupied by queens"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# a(i).. sum(j, x(i,j)) =e= 1
# No two queens may be in the same rank
def a_rule(model, i):
    return sum(model.x[i, j] for j in model.i) == 1

model.a = Constraint(
    model.i,
    rule=a_rule,
    doc="No two queens may be in the same rank"
)

# b(j).. sum(i, x(i,j)) =e= 1
# No two queens may be in the same file
def b_rule(model, j):
    return sum(model.x[i, j] for i in model.i) == 1

model.b = Constraint(
    model.i,
    rule=b_rule,
    doc="No two queens may be in the same file"
)

# c(s).. sum(i, x(i,i+sh(s))) =l= 1
# No two queens may be in the same diagonal (forward)
def c_rule(model, s):
    i_list = [i for i in data["i"]]
    terms = []
    for i in i_list:
        i_int = int(i)
        j_int = i_int + sh_dict[s]
        # Check if j is valid
        if 1 <= j_int <= iMax:
            j_str = str(j_int)
            terms.append(model.x[i, j_str])

    if len(terms) == 0:
        return Constraint.Skip
    return sum(terms) <= 1

model.c = Constraint(
    model.s,
    rule=c_rule,
    doc="No two queens may be in the same diagonal (forward)"
)

# d(s).. sum(i, x(i,i+(rev(i)+sh(s)))) =l= 1
# No two queens may be in the same diagonal (backward)
def d_rule(model, s):
    i_list = [i for i in data["i"]]
    terms = []
    for i in i_list:
        i_int = int(i)
        j_int = i_int + (rev_dict[i] + sh_dict[s])
        # Check if j is valid
        if 1 <= j_int <= iMax:
            j_str = str(j_int)
            terms.append(model.x[i, j_str])

    if len(terms) == 0:
        return Constraint.Skip
    return sum(terms) <= 1

model.d = Constraint(
    model.s,
    rule=d_rule,
    doc="No two queens may be in the same diagonal (backward)"
)

# obj.. tot =e= sum((i,j), x(i,j))
def tot_rule(model):
    return model.tot == sum(model.x[i, j] for i in model.i for j in model.i)

model.tot_constraint = Constraint(
    rule=tot_rule,
    doc="Objective definition"
)
