# converted from models/cubesoln.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel()

# Sets
model.I = RangeSet(1, 3)
model.S = Set(initialize=["a", "b", "c", "incr", "decr"])
model.B = Set(initialize=["low", "high"])
model.X = Set(within=model.S, initialize=["a", "b", "c"])
model.D = Set(within=model.S, initialize=["incr", "decr"])

def ld_init(model):
    elems = set()
    X = ["a", "b", "c"]
    D = ["incr", "decr"]

    for y in X:
        for z in X:
            elems.add(("incr", y, z))
    for x in X:
        for z in X:
            elems.add((x, "incr", z))
    for x in X:
        for y in X:
            elems.add((x, y, "incr"))
    for d in D:
        for z in X:
            elems.add(("incr", d, z))
    for x in X:
        for d in D:
            elems.add((x, "incr", d))
    for d in D:
        for y in X:
            elems.add((d, y, "incr"))
    for d in D:
        for dp in D:
            elems.add(("incr", d, dp))

    return list(elems)

model.LD = Set(dimen=3, initialize=ld_init)

# Parameters
model.ls = Param(model.B, initialize={"low": 1.0, "high": -1.0}, mutable=True)
model.lr = Param(model.B, initialize={"low": 2.0, "high": -1.0}, mutable=True)

def df_init(model, i, s):
    coord_map = {"a": 1, "b": 2, "c": 3}
    if s in coord_map:
        return coord_map[s] - i
    if s == "decr":
        return 4 - 2 * i
    return 0

model.df = Param(model.I, model.S, initialize=df_init, mutable=True)

# Variables
model.core = Var(model.I, model.I, model.I, domain=Binary)
model.line = Var(model.LD, domain=NonNegativeReals)
model.num = Var(domain=NonNegativeReals)

# Constraints
def nbb_rule(model):
    return sum(
        model.core[i, j, k] for i in model.I for j in model.I for k in model.I
    ) == 13

model.nbb = Constraint(rule=nbb_rule)

def ldef_rule(model, s, sp, spp, b):
    terms = []
    for i in model.I:
        df1 = int(value(model.df[i, s]))
        df2 = int(value(model.df[i, sp]))
        df3 = int(value(model.df[i, spp]))

        i1 = i + df1
        i2 = i + df2
        i3 = i + df3

        if 1 <= i1 <= 3 and 1 <= i2 <= 3 and 1 <= i3 <= 3:
            terms.append(model.core[i1, i2, i3])

    if not terms:
        return Constraint.Skip

    return (
        model.ls[b] * sum(terms)
        <= model.line[s, sp, spp] + model.lr[b]
    )

model.ldef = Constraint(model.LD, model.B, rule=ldef_rule)

def ndef_rule(model):
    return model.num == sum(model.line[s, sp, spp] for (s, sp, spp) in model.LD)

model.ndef = Constraint(rule=ndef_rule)

# Objective
model.obj = Objective(expr=model.num, sense=minimize)
