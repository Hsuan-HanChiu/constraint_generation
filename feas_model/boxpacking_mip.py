# converted from gamslib boxpacking (boxpacking, SEQ=434)
# 3D container packing problem (Ocloo/Fuegenschuh/Pamen 2020 formulation).
# Maximize the total volume of boxes placed into a single container subject to
# container-dimension limits and non-overlap (relative-position) constraints.
# The GAMS source solves this MIP repeatedly under a batch heuristic; this is the
# single primary optimization model over all existing boxes (scenario/report
# re-solves dropped).
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "b1|o1|x": value → (b1, o1, x): value).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="3D box packing - maximize packed volume in container")

# Sets
model.b = pyo.Set(initialize=list(data["b"]), doc="boxes")
model.o = pyo.Set(initialize=list(data["o"]), doc="six possible orientations of a box")
model.d = pyo.Set(initialize=list(data["d"]), doc="spatial dimensions (x, y, z)")

# allowed (box, orientation) pairs: only those present in the bo parameter
_bo_keys = set(data["bo"].keys())
model.bo = pyo.Set(
    dimen=2,
    initialize=sorted(_bo_keys),
    doc="available orientations for each box",
)

# Parameters
model.dim_o = pyo.Param(
    model.b, model.o, model.d,
    initialize={k: float(v) for k, v in data["dim_o"].items()},
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="dimension of box b in orientation o along axis d",
)
model.box_vol = pyo.Param(
    model.b,
    initialize={k: float(v) for k, v in data["box_vol"].items()},
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="volume of each box (m3)",
)
model.dim_cont = pyo.Param(
    model.d,
    initialize={k: float(v) for k, v in data["dim_cont"].items()},
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="container dimensions along each axis",
)

# Variables
model.OMEGA = pyo.Var(model.b, domain=pyo.Binary, doc="box placed in container (1) or not (0)")
model.ALPHA = pyo.Var(model.bo, domain=pyo.Binary, doc="box placed with orientation o (1) or not (0)")
model.RELPOS = pyo.Var(
    model.b, model.b, model.d, domain=pyo.Binary,
    doc="relative position: 1 if first box location+dim <= second box location",
)
model.LOC = pyo.Var(
    model.b, model.d, domain=pyo.NonNegativeReals,
    doc="(x,y,z) location of bottom-left-back corner of box in container",
)
model.DIM = pyo.Var(
    model.b, model.d, domain=pyo.NonNegativeReals,
    doc="(x,y,z) dimension of box in container given its orientation",
)
model.VOL = pyo.Var(domain=pyo.Reals, doc="total volume of all boxes in container")

# Constraints
# (23/24/25) define realized dimension of a box from its selected orientation
def def_DIM_rule(model, b, d):
    return model.DIM[b, d] == sum(model.dim_o[b, o, d] * model.ALPHA[b, o]
                                  for o in model.o if (b, o) in model.bo)
model.eq_def_DIM = pyo.Constraint(model.b, model.d, rule=def_DIM_rule,
                                  doc="define box dimension from orientation")

# (26) select exactly one orientation iff the box is in the container
def couple_rule(model, b):
    return sum(model.ALPHA[b, o] for o in model.o if (b, o) in model.bo) == model.OMEGA[b]
model.eq_couple_ALPHA_OMEGA = pyo.Constraint(model.b, rule=couple_rule,
                                             doc="select orientation only for placed boxes")

# (27 a/b/c) box must fit inside the container if placed
def inside_rule(model, b, d):
    return model.LOC[b, d] + model.DIM[b, d] <= model.dim_cont[d] * model.OMEGA[b]
model.eq_inside_container = pyo.Constraint(model.b, model.d, rule=inside_rule,
                                           doc="respect container dimensions")

# (28 a/b/c) RELPOS only active for boxes actually in the container
def deactivate_rule(model, b1, b2, d):
    if model.b.ord(b1) >= model.b.ord(b2):
        return pyo.Constraint.Skip
    return model.RELPOS[b1, b2, d] + model.RELPOS[b2, b1, d] <= model.OMEGA[b1]
model.eq_deactivate_RELPOS = pyo.Constraint(model.b, model.b, model.d, rule=deactivate_rule,
                                            doc="RELPOS nonzero only if first box placed")

# (29) if both boxes placed, they must be separated along at least one axis
def def_RELPOS_rule(model, b1, b2):
    if model.b.ord(b1) >= model.b.ord(b2):
        return pyo.Constraint.Skip
    return sum(model.RELPOS[b1, b2, d] + model.RELPOS[b2, b1, d] for d in model.d) \
        >= model.OMEGA[b1] + model.OMEGA[b2] - 1
model.eq_def_RELPOS = pyo.Constraint(model.b, model.b, rule=def_RELPOS_rule,
                                     doc="define separation requirement for placed pairs")

# (30 a/b/c) non-overlap big-M: enforced along the axis where RELPOS=1
def no_overlap_rule(model, b1, b2, d):
    if b1 == b2:
        return pyo.Constraint.Skip
    return model.LOC[b1, d] + model.DIM[b1, d] <= model.LOC[b2, d] \
        + model.dim_cont[d] * (1 - model.RELPOS[b1, b2, d])
model.eq_no_overlap = pyo.Constraint(model.b, model.b, model.d, rule=no_overlap_rule,
                                     doc="boxes in container must not overlap")

# (31) objective accounting
def def_VOL_rule(model):
    return model.VOL == sum(model.box_vol[b] * model.OMEGA[b] for b in model.b)
model.eq_def_VOL = pyo.Constraint(rule=def_VOL_rule, doc="total packed volume")

# Objective (name must be obj)
model.obj = pyo.Objective(expr=model.VOL, sense=pyo.maximize,
                          doc="maximize the volume of boxes packed in the container")
