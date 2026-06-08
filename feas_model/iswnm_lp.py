# converted from models/iswnm_lp.py
import json
from pyomo.environ import *

# ── OptiChat data loading ─────────────────────────────────────────────────────
# Data is injected into module globals as 'data' by OptiChat's callback_tool.
# The JSON uses the {sets, scalar_params, indexed_params} format with pipe-key
# notation for multi-dimensional params (e.g. "row|col": value → (row, col): value).

data = globals().get("data", {})
# ─────────────────────────────────────────────────────────────────────────────

# ── model ───────────────────────────────────────────────────────────────────
model = ConcreteModel(name="ISWNM - Indus Surface Water Network")

# ======================================================================
# SETS
# ======================================================================

model.n = Set(initialize=data["n"], doc="Nodes of the Indus river system")
model.c = Set(initialize=data["c"], doc="Irrigation canals")
model.i = Set(initialize=data["i"], doc="System inflows (rim stations)")
model.m = Set(initialize=data["m"], doc="Months", ordered=True)
model.s = Set(initialize=data["s"], doc="Seasons")

# Subset: nodes excluding a-sea (for water balance)
nb_set = [n for n in data["n"] if n != "a-sea"]
model.nb = Set(initialize=nb_set, doc="Nodes with water balance")

# Set mappings (converted from pipe keys to tuples)
nc_set = []
for item in data["nc"]:
    if isinstance(item, tuple):
        nc_set.append(item)
    else:
        parts = item.split("|")
        if len(parts) == 2:
            nc_set.append((parts[0], parts[1]))

nn_set = []
for item in data["nn"]:
    if isinstance(item, tuple):
        nn_set.append(item)
    else:
        parts = item.split("|")
        if len(parts) == 2:
            nn_set.append((parts[0], parts[1]))

ni_set = []
for item in data["ni"]:
    if isinstance(item, tuple):
        ni_set.append(item)
    else:
        parts = item.split("|")
        if len(parts) == 2:
            ni_set.append((parts[0], parts[1]))

model.nc = Set(initialize=nc_set, dimen=2, doc="Node to canal mapping")
model.nn = Set(initialize=nn_set, dimen=2, doc="Node to node flow network")
model.ni = Set(initialize=ni_set, dimen=2, doc="Node to inflow mapping")

# ======================================================================
# PARAMETERS
# ======================================================================

# Canal capacity
ccap_dict = {}
for item, val in data["ccap"].items():
    if isinstance(item, tuple):
        ccap_dict[item[0]] = val
    else:
        ccap_dict[item] = val

model.ccap = Param(
    model.c,
    initialize=ccap_dict,
    default=0.0,
    mutable=True,
    doc="Canal capacity at canal head (MAF)"
)

# Node to node transfer capacity
ncap_dict = {}
for item, val in data["ncap"].items():
    if isinstance(item, tuple):
        ncap_dict[item] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            ncap_dict[(parts[0], parts[1])] = val

model.ncap = Param(
    model.n, model.n,
    initialize=ncap_dict,
    default=0.0,
    mutable=True,
    doc="Node to node transfer capacity (MAF)"
)

# Reservoir capacity
rcap_dict = {}
for item, val in data["rcap"].items():
    if isinstance(item, tuple):
        rcap_dict[item[0]] = val
    else:
        rcap_dict[item] = val

model.rcap = Param(
    model.n,
    initialize=rcap_dict,
    default=0.0,
    mutable=True,
    doc="Live capacity of reservoirs (MAF)"
)

# Initial reservoir contents
ircont_dict = {}
for item, val in data["ircont"].items():
    if isinstance(item, tuple):
        ircont_dict[item[0]] = val
    else:
        ircont_dict[item] = val

model.ircont = Param(
    model.n,
    initialize=ircont_dict,
    default=0.0,
    mutable=True,
    doc="Initial reservoir contents (MAF)"
)

# Inflow at rim stations
inflow_dict = {}
for item, val in data["inflow"].items():
    if isinstance(item, tuple):
        inflow_dict[item] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            inflow_dict[(parts[0], parts[1])] = val

model.inflow = Param(
    model.i, model.m,
    initialize=inflow_dict,
    default=0.0,
    mutable=True,
    doc="System inflows at rim stations (MAF)"
)

# Runoff to nodes
runoff_dict = {}
for item, val in data["runoff"].items():
    if isinstance(item, tuple):
        runoff_dict[item] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            runoff_dict[(parts[0], parts[1])] = val

model.runoff = Param(
    model.n, model.m,
    initialize=runoff_dict,
    default=0.0,
    mutable=True,
    doc="Rainfall runoff to nodes (000 AF)"
)

# Reservoir evaporation
revapl_dict = {}
for item, val in data["revapl"].items():
    if isinstance(item, tuple):
        revapl_dict[item] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            revapl_dict[(parts[0], parts[1])] = val

model.revapl = Param(
    model.n, model.m,
    initialize=revapl_dict,
    default=0.0,
    mutable=True,
    doc="Evaporation losses from reservoirs (000 AF)"
)

# Rule curves
rulelo_dict = {}
for item, val in data["rulelo"].items():
    if isinstance(item, tuple):
        rulelo_dict[item] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            rulelo_dict[(parts[0], parts[1])] = val

model.rulelo = Param(
    model.n, model.m,
    initialize=rulelo_dict,
    default=0.0,
    doc="Lower rule curve (% of capacity)"
)

ruleup_dict = {}
for item, val in data["ruleup"].items():
    if isinstance(item, tuple):
        ruleup_dict[item] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            ruleup_dict[(parts[0], parts[1])] = val

model.ruleup = Param(
    model.n, model.m,
    initialize=ruleup_dict,
    default=100.0,
    doc="Upper rule curve (% of capacity)"
)

# Tributary inflows (sparse - defaults to 0)
# Format: trib(n1, n, m) means flow from n1 to n
trib_dict = {}
for key, val in data["trib"].items():
    if isinstance(key, tuple) and len(key) == 3:
        trib_dict[key] = val
    else:
        parts = key.split("|")
        if len(parts) == 3:
            trib_dict[(parts[0], parts[1], parts[2])] = val

model.trib = Param(
    model.n, model.n, model.m,
    initialize=trib_dict,
    default=0.0,
    doc="Tributary inflows from n1 to n (MAF)"
)

# Seepage (sparse - defaults to 0)
model.seepage = Param(
    model.n, model.n, model.m,
    initialize={},  # Empty - most values are 0
    default=0.0,
    doc="Seepage from/to river reaches (000 AF)"
)

# Loss coefficients for link canals (simplified - assume 1.0 for now)
# In the full model, this is computed from evaporation and seepage data
model.coeffl = Param(
    model.n, model.n, model.m,
    initialize={},
    default=1.0,
    doc="Node to node transfer efficiency for link canals"
)

# ======================================================================
# VARIABLES
# ======================================================================

model.rcont = Var(
    model.n, model.m,
    within=NonNegativeReals,
    doc="End of month reservoir contents (MAF)"
)

model.canaldiv = Var(
    model.c, model.m,
    within=NonNegativeReals,
    doc="Monthly diversion to canal (MAF)"
)

model.f = Var(
    model.n, model.n, model.m,
    within=NonNegativeReals,
    doc="Flow from node n1 to node n (MAF)"
)

model.vol = Var(
    within=NonNegativeReals,
    doc="Total reservoir volume (MAF)"
)

# ======================================================================
# VARIABLE BOUNDS
# ======================================================================

# Canal diversion upper bounds
def canaldiv_bound_rule(model, c, m):
    return (0, model.ccap[c])

model.canaldiv_bounds = Constraint(
    model.c, model.m,
    rule=lambda model, c, m: model.canaldiv[c, m] <= model.ccap[c],
    doc="Canal diversion capacity limits"
)

# Flow capacity bounds
def f_bound_rule(model, n1, n, m):
    if (n1, n) in nn_set:
        cap_val = ncap_dict.get((n1, n), 0.0)
        if cap_val > 0:
            return model.f[n1, n, m] <= model.ncap[n1, n]
    return Constraint.Skip

model.f_bounds = Constraint(
    model.n, model.n, model.m,
    rule=f_bound_rule,
    doc="Node to node flow capacity limits"
)

# Reservoir content bounds (rule curves)
def rcont_lo_rule(model, n, m):
    if rcap_dict.get(n, 0.0) > 0:
        return model.rcont[n, m] >= model.rulelo[n, m] * model.rcap[n] / 100
    return Constraint.Skip

model.rcont_lo = Constraint(
    model.n, model.m,
    rule=rcont_lo_rule,
    doc="Reservoir lower rule curve"
)

def rcont_up_rule(model, n, m):
    if rcap_dict.get(n, 0.0) > 0:
        return model.rcont[n, m] <= model.ruleup[n, m] * model.rcap[n] / 100
    return Constraint.Skip

model.rcont_up = Constraint(
    model.n, model.m,
    rule=rcont_up_rule,
    doc="Reservoir upper rule curve"
)

# Fix September reservoir contents to initial values
def rcont_sep_rule(model, n):
    if rcap_dict.get(n, 0.0) > 0:
        return model.rcont[n, "sep"] == model.ircont[n]
    return Constraint.Skip

model.rcont_sep = Constraint(
    model.n,
    rule=rcont_sep_rule,
    doc="Fix September reservoir contents"
)

# ======================================================================
# CONSTRAINTS
# ======================================================================

# Water balance at each node
def nbal_rule(model, n, m):
    if n not in nb_set:
        return Constraint.Skip

    # Inflows from rim stations
    inflow_list = [model.inflow[i, m] for i in model.i if (n, i) in ni_set]
    inflow_term = sum(inflow_list) if inflow_list else 0

    # Runoff
    if (n, m) in runoff_dict:
        runoff_term = model.runoff[n, m] / 1000  # Convert from 000 AF to MAF
    else:
        runoff_term = 0

    # Tributary inflows (sparse parameter with default 0)
    # GAMS declares: trib(n1,n,m) meaning flow FROM n1 TO n
    # GAMS equation uses: sum(n1, trib(n,n1,m)) with swapped indices
    # But we want inflows TO node n, which means summing over source nodes n1
    # So we should sum: trib(n1, n, m) for all n1 (inflows to n)
    trib_term = sum(model.trib[n1, n, m] for n1 in model.n)

    # Inflows from upstream nodes (with losses for link canals)
    # GAMS: sum(n1$nn(n,n1), f(n,n1,m)*coeffl(n1,n,m)...)
    # nn(n,n1) means connection exists, f(n,n1,m) is flow on that arc
    upstream_list = [
        model.f[n, n1, m] * model.coeffl[n1, n, m]
        for n1 in model.n if (n, n1) in nn_set
    ]
    upstream_term = sum(upstream_list) if upstream_list else 0

    # Outflows to downstream nodes
    # GAMS: sum(n1$nn(n1,n), f(n1,n,m))
    downstream_list = [model.f[n1, n, m] for n1 in model.n if (n1, n) in nn_set]
    downstream_term = sum(downstream_list) if downstream_list else 0

    # Reservoir storage change
    # Get previous month's index
    m_list = list(model.m)
    m_idx = m_list.index(m)
    if m_idx > 0:
        prev_m = m_list[m_idx - 1]
    else:
        # January follows December (wrap around)
        prev_m = m_list[-1]

    if rcap_dict.get(n, 0.0) > 0:
        storage_term = (
            model.rcont[n, prev_m] - model.rcont[n, m]
            - model.revapl[n, m] / 1000  # Convert from 000 AF to MAF
        )
    else:
        storage_term = 0

    # Canal diversions
    canal_list = [model.canaldiv[c, m] for c in model.c if (n, c) in nc_set]
    canal_term = sum(canal_list) if canal_list else 0

    # Check if node has any variables involved (not just parameters)
    # Variables: f (upstream/downstream), rcont (storage), canaldiv (canals)
    has_variables = (
        len(upstream_list) > 0 or
        len(downstream_list) > 0 or
        rcap_dict.get(n, 0.0) > 0 or
        len(canal_list) > 0
    )

    # If no variables, this would be a constraint on constants only
    # which Pyomo doesn't allow. Return Constraint.Skip for such nodes.
    if not has_variables:
        return Constraint.Skip

    # Water balance equation
    return (
        inflow_term + runoff_term + trib_term + upstream_term
        + storage_term - downstream_term - canal_term
        == 0
    )

model.nbal = Constraint(
    model.nb, model.m,
    rule=nbal_rule,
    doc="Water balance at each node"
)

# Total reservoir volume definition
def defvol_rule(model):
    return model.vol == sum(
        model.rcont[n, m]
        for n in model.n if rcap_dict.get(n, 0.0) > 0
        for m in model.m
    )

model.defvol = Constraint(
    rule=defvol_rule,
    doc="Total reservoir volume definition"
)

# ======================================================================
# OBJECTIVE
# ======================================================================

model.obj = Objective(
    expr=model.vol,
    sense=maximize,
    doc="Maximize total reservoir volume (MAF)"
)
