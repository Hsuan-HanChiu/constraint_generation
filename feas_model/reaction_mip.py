# converted from models/reaction_mip.py
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
    doc="Logical Inference for Reaction Path Synthesis"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.v = Set(
    initialize=data["v"],
    doc="System variables (chemicals)"
)

model.rx = Set(
    initialize=data["rx"],
    doc="Logical conditions (reactions)"
)

model.yavail = Set(
    initialize=data["yavail"],
    within=model.v,
    doc="Available raw materials and catalysts"
)

model.ynotavail = Set(
    initialize=data["ynotavail"],
    within=model.v,
    doc="Raw materials and catalysts not available"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------

# logicc(rx,v,vv) - mathematical representation of chemical reactions
# After run.py processing, keys are tuples (rx, v, vv)
logicc_dict = {}
for key, val in data["logicc"].items():
    if isinstance(key, tuple) and len(key) == 3:
        logicc_dict[key] = val

model.logicc = Param(
    model.rx, model.v, model.v,
    initialize=logicc_dict,
    mutable=True,
    default=0,
    doc="Mathematical representation of chemical reactions"
)

# Build rxv(rx,v) set: rxv(rx,v) = sum(vv, logicc(rx,v,vv))
# This identifies which (rx,v) pairs have at least one vv such that logicc(rx,v,vv) > 0
rxv_set = set()
for (rx, v, vv), val in logicc_dict.items():
    if val > 0:
        rxv_set.add((rx, v))

model.rxv = Set(
    initialize=list(rxv_set),
    dimen=2,
    doc="rx to v mapping"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.y = Var(
    model.v,
    domain=Binary,
    doc="Binary variable for each chemical"
)

model.totsum = Var(
    domain=Reals,
    doc="Total sum (objective variable)"
)

# ----------------------------------------------------------------------
# Fix variables for available and not available chemicals
# ----------------------------------------------------------------------
# In GAMS: y.fx(yavail) = 1; y.fx(ynotavail) = 0
# We need to do this after variable creation but before constraints
for v in data["yavail"]:
    model.y[v].fix(1)

for v in data["ynotavail"]:
    model.y[v].fix(0)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    # obj.. totsum =e= y('y06')
    return model.totsum

model.obj = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Minimize y06 to determine if acetone can be produced"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# leq(rxv(rx,v)).. sum(logicc(rxv,vv), 1 - y(vv)) =g= 1 - y(v)
# This constraint says: if all reactants vv are present (y(vv)=1),
# then product v can be present (y(v)=1)
def leq_rule(model, rx, v):
    if (rx, v) not in rxv_set:
        return Constraint.Skip

    # Sum over vv where logicc(rx,v,vv) > 0
    lhs = sum(1 - model.y[vv]
              for vv in data["v"]
              if logicc_dict.get((rx, v, vv), 0) > 0)

    return lhs >= 1 - model.y[v]

model.leq = Constraint(
    model.rxv,
    rule=leq_rule,
    doc="Logic constraints"
)

# Define totsum constraint
def totsum_rule(model):
    target = data["target"]
    return model.totsum == model.y[target]

model.totsum_con = Constraint(
    rule=totsum_rule,
    doc="Define totsum as y(target)"
)
