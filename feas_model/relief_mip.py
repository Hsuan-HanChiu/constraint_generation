# converted from gamslib relief (RELIEF, SEQ=353)
# Primary model `m`: best two drop locations (numdrops = 2).
# Plant-location MIP: choose drop cells on a 10x10 grid that minimize the
# total distance villagers (huts) walk to their nearest drop zone.
# Rolling efficient-frontier solves (numdrops = 1..20) and the 3%-cut
# elimination loop in the source .gms are scenario/reporting re-solves and
# are intentionally NOT converted.
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation; integer column tokens are coerced to ints (e.g. "A|5|A|1" → ("A",5,"A",1)).
data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ─────────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel(doc="Relief Mission - best two drop locations (plant location MIP)")

# Sets
model.r = pyo.Set(initialize=data["r"], doc="Grid rows (A..J)")
model.c = pyo.Set(initialize=data["c"], doc="Grid columns (1..10)")

# Hut locations are exactly the distinct source (row, col) cells appearing
# in the distance table dis(hut_r, hut_c, r, c).
_hut_keys = sorted({(k[0], k[1]) for k in data["dis"].keys()})
model.hut = pyo.Set(initialize=_hut_keys, dimen=2, doc="Hut (village) locations")

# Parameters
model.dis = pyo.Param(
    model.hut, model.r, model.c,
    initialize=data["dis"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Euclidean distance from each hut to grid cell (r,c)",
)

model.maxdem = pyo.Param(
    initialize=data["maxdem"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Maximum drop demand (total hut demand = supply cap at an open drop)",
)

model.numdrops = pyo.Param(
    initialize=data["numdrops"],
    mutable=True,
    within=pyo.NonNegativeReals,
    doc="Number of drop locations to open",
)

# Variables
model.drop = pyo.Var(
    model.r, model.c,
    domain=pyo.Binary,
    doc="1 if a relief drop is opened at grid cell (r,c)",
)

model.walk = pyo.Var(
    model.hut, model.r, model.c,
    domain=pyo.NonNegativeReals,
    doc="Fraction of a hut's demand served by drop at cell (r,c)",
)

model.total = pyo.Var(
    domain=pyo.Reals,
    doc="Total distance walked",
)

# Constraints
def demand_rule(model, hr, hc):
    return sum(model.walk[hr, hc, r, c] for r in model.r for c in model.c) == 1

model.demand = pyo.Constraint(model.hut, rule=demand_rule, doc="Each hut's demand fully served")

def supply_rule(model, r, c):
    return sum(model.walk[hr, hc, r, c] for (hr, hc) in model.hut) <= model.drop[r, c] * model.maxdem

model.supply = pyo.Constraint(model.r, model.c, rule=supply_rule, doc="Only open drops can supply")

def deftotal_rule(model):
    return model.total == sum(
        model.dis[hr, hc, r, c] * model.walk[hr, hc, r, c]
        for (hr, hc) in model.hut for r in model.r for c in model.c
    )

model.deftotal = pyo.Constraint(rule=deftotal_rule, doc="Accounting: total distance walked")

def defnumdrop_rule(model):
    return sum(model.drop[r, c] for r in model.r for c in model.c) == model.numdrops

model.defnumdrop = pyo.Constraint(rule=defnumdrop_rule, doc="Open exactly numdrops drops")

# Objective
model.obj = pyo.Objective(
    expr=model.total,
    sense=pyo.minimize,
    doc="Minimize total distance walked by all huts",
)
