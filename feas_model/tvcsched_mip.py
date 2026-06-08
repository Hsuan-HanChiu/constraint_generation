# converted from models/tvcsched_mip.py
import json
from pyomo.environ import *
import pyomo.environ as pyo

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = pyo.ConcreteModel()

# Base sets from JSON
sp_list = list(data["sp"])
c_list = list(data["c"])

model.SP = pyo.Set(initialize=sp_list, doc="slots plus zero")
model.C = pyo.Set(initialize=c_list, doc="colors")

# Order map like GAMS ord(sp): "0" first, then "1","2",...
sp_ord = {name: k for k, name in enumerate(sp_list)}

# Color counts from JSON
nc_data = data["nc"]
# Active colors: nc(c) > 0
active_colors = [c for c in c_list if nc_data.get(c, 0) > 0]

model.CACT = pyo.Set(initialize=active_colors, doc="colors with nc>0")

# Param nc(c)
def nc_init(model, c):
    return nc_data.get(c, 0)

model.nc = pyo.Param(model.C, initialize=nc_init, mutable=True, doc="balls per color")

# Scalars from JSON
isf = float(data.get("isf", 2.0))
msf = float(data.get("msf", 0.1))
sparse_flag = int(data.get("sparse", 0))
fix_pre_flag = int(data.get("fix_pre", 0))

# Total number of balls
n_val = sum(nc_data.get(c, 0) for c in c_list)

# Ideal distance dc(c) = n / nc(c)
dc = {}
for c in c_list:
    nc_val = nc_data.get(c, 0)
    dc[c] = float(n_val) / nc_val if nc_val > 0 else 0.0

# Slots 1..n (strings); "0" is special node
slots = [
    s for s in sp_list
    if s != "0" and sp_ord[s] <= n_val
]
slots = sorted(slots, key=lambda s: sp_ord[s])

model.S = pyo.Set(initialize=slots, doc="slots")

# Preplaced balls: keys like "1|W"
pre_raw = data.get("preplace", {})

def pre_init(model, c, s):
    key = f"{s}|{c}"
    return pre_raw.get(key, 0.0)

model.preplace = pyo.Param(
    model.C, model.S,
    initialize=pre_init,
    mutable=True,
    doc="preplaced balls"
)

# Build arcs (c,i,j) using pure Python, then create Set
arcs = []

nodes = ["0"] + slots  # nodes used in the network

if sparse_flag == 0:
    # Dense graph
    for c in active_colors:
        for i in nodes:
            if sp_ord[i] > n_val + 1:
                continue
            for j in nodes:
                if sp_ord[j] > sp_ord[i]:
                    arcs.append((c, i, j))
        # arcs back to source
        for s in slots:
            arcs.append((c, s, "0"))
else:
    # Sparse graph like GAMS
    for c in active_colors:
        # arcs from 0
        for j in nodes:
            if 1 < sp_ord[j] <= min(n_val + 1, 1 + isf * dc[c]):
                arcs.append((c, "0", j))

        sf = msf
        if sf * dc[c] < 5 and dc[c] > 0:
            sf = 5.0 / dc[c]

        for i in nodes:
            if not (1 < sp_ord[i] <= n_val + 1):
                continue
            low = max(sp_ord[i], sp_ord[i] + (1.0 - sf) * dc[c])
            high = min(n_val + 1, sp_ord[i] + (1.0 + sf) * dc[c])
            for j in nodes:
                if low < sp_ord[j] <= high:
                    arcs.append((c, i, j))

        # arcs back to source
        for s in slots:
            arcs.append((c, s, "0"))

# Remove duplicates
arcs = list(dict.fromkeys(arcs))

model.Arcs = pyo.Set(dimen=3, initialize=arcs, doc="network arcs (c,i,j)")

# Deviation dev(c,i,j)
def dev_init(model, c, i, j):
    if i != "0" and j != "0":
        return abs(sp_ord[j] - sp_ord[i] - dc[c])
    return 0.0

model.dev = pyo.Param(
    model.Arcs,
    initialize=dev_init,
    mutable=True,
    doc="distance deviation"
)

# Variables
model.f = pyo.Var(
    model.Arcs,
    domain=pyo.NonNegativeReals,
    doc="flow"
)

model.p = pyo.Var(
    model.C, model.S,
    domain=pyo.Binary,
    doc="placement"
)

model.obj = pyo.Var(domain=pyo.Reals, doc="objective")

# Flow balance at slots
def bal_rule(model, c, s):
    incoming = sum(
        model.f[c, i, s]
        for (cc, i, j) in model.Arcs
        if cc == c and j == s
    )
    outgoing = sum(
        model.f[c, s, j]
        for (cc, i, j) in model.Arcs
        if cc == c and i == s
    )
    return incoming - outgoing == 0.0

model.bal = pyo.Constraint(
    model.CACT, model.S,
    rule=bal_rule,
    doc="flow balance"
)

# Flow from source (node 0): 1 unit per active color
def balinit_rule(model, c):
    out0 = sum(
        model.f[c, "0", j]
        for (cc, i, j) in model.Arcs
        if cc == c and i == "0"
    )
    return out0 == 1.0

model.balinit = pyo.Constraint(
    model.CACT,
    rule=balinit_rule,
    doc="source balance"
)

# Open slot if flow leaves it
def defopen_rule(model, c, s):
    outflow = sum(
        model.f[c, s, j]
        for (cc, i, j) in model.Arcs
        if cc == c and i == s
    )
    return outflow == model.p[c, s]

model.defopen = pyo.Constraint(
    model.CACT, model.S,
    rule=defopen_rule,
    doc="open slots"
)

# Number of slots per color
def defsump_rule(model, c):
    return sum(model.p[c, s] for s in model.S) == model.nc[c]

model.defsump = pyo.Constraint(
    model.CACT,
    rule=defsump_rule,
    doc="slots per color"
)

# Slot cover: exactly one color per slot
def covslot_rule(model, s):
    return sum(model.p[c, s] for c in model.CACT) == 1.0

model.covslot = pyo.Constraint(
    model.S,
    rule=covslot_rule,
    doc="slot cover"
)

# Preplaced balls if enabled
'''''
if fix_pre_flag == 1:
    def pre_rule(model, c, s):
        if model.preplace[c, s] >= 0.5:
            return model.p[c, s] == 1.0
        return pyo.Constraint.Skip

    model.precon = pyo.Constraint(
        model.C, model.S,
        rule=pre_rule,
        doc="preplaced"
    )
'''''
# Objective definition
def defobj_rule(model):
    return model.obj == sum(
        model.dev[c, i, j] * model.f[c, i, j]
        for (c, i, j) in model.Arcs
    )

model.defobj = pyo.Constraint(rule=defobj_rule, doc="objective definition")

# Objective
model.OBJ = pyo.Objective(expr=model.obj, sense=pyo.minimize)
