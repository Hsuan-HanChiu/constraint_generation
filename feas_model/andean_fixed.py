# converted from models/andean_fixed.py
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
    doc="Andean Fertilizer Model"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.w = Set(
    initialize=data["w"],
    doc="Countries"
)

model.i = Set(
    initialize=data["i"],
    doc="Plant locations"
)

model.j = Set(
    initialize=data["j"],
    doc="Demand regions"
)

model.m = Set(
    initialize=data["m"],
    doc="Productive units"
)

model.g = Set(
    initialize=data["g"],
    doc="Vintages (old/new)"
)

model.p = Set(
    initialize=data["p"],
    doc="Processes"
)

model.cq = Set(
    initialize=data["cq"],
    doc="Nutrients (n, p2o5, k2o)"
)

model.c = Set(
    initialize=data["c"],
    doc="Commodities"
)

model.cf = Set(
    initialize=data["cf"],
    doc="Final products"
)

model.co = Set(
    initialize=data["co"],
    doc="Compound fertilizers"
)

model.cr = Set(
    initialize=data["cr"],
    doc="Raw materials"
)

model.cis = Set(
    initialize=data["cis"],
    doc="Interplant shipment commodities"
)

model.ce = Set(
    initialize=data["ce"],
    doc="Export commodities"
)

model.cv = Set(
    initialize=data["cv"],
    doc="Import commodities"
)

model.t = Set(
    initialize=data["t"],
    doc="Time periods"
)

model.te = Set(
    initialize=data["te"],
    doc="Expansion periods"
)

model.n = Set(
    initialize=data["n"],
    doc="Expansion packages"
)

# Multi-dimensional sets
model.wi = Set(
    initialize=[tuple(x) for x in data["wi"]],
    within=model.w * model.i,
    doc="Country-plant mapping"
)

model.wj = Set(
    initialize=[tuple(x) for x in data["wj"]],
    within=model.w * model.j,
    doc="Country-demand region mapping"
)

model.wnpk = Set(
    initialize=[tuple(x) for x in data["wnpk"]],
    within=model.w * model.c,
    doc="Country-commodity mapping (all commodities, not just NPK)"
)

# Create old and new vintage indicator sets
model.old = Set(
    initialize=data["old"],
    doc="Old vintage indicator"
)

model.new = Set(
    initialize=data["new"],
    doc="New vintage indicator"
)

# ----------------------------------------------------------------------
# PARAM_BLOCK
# ----------------------------------------------------------------------

# Demand parameters
d_dict = {}
# Map time periods to demand table names
time_to_dem = {
    "1981-83": "dem82",
    "1984-86": "dem85",
    "1987-89": "dem88",
    "1990-92": "dem91"
}

for j in data["j"]:
    for cq in data["cq"]:
        for t in data["t"]:
            if t in time_to_dem:
                dem_key = time_to_dem[t]
                # After preprocessing, keys might be tuples or strings
                # Try tuple format first (j, cq)
                val = None
                if isinstance(list(data[dem_key].keys())[0], tuple):
                    val = data[dem_key].get((j, cq), 0)
                else:
                    # String format: "j|cq"
                    val = data[dem_key].get(f"{j}|{cq}", 0)

                if val and val > 0:
                    d_dict[(j, cq, t)] = val

model.d = Param(
    model.j, model.cq, model.t,
    initialize=d_dict,
    default=0.0,
    doc="Demand for nutrients (1000 tpy)"
)

# Minimum ammonium sulfate requirement
db_dict = {}
for j in data["j"]:
    for t in data["t"]:
        key_options = [
            f"{j}|ammonium",
            f"{j}|sulfate",
            f"{j}|requirement"
        ]
        for key_str in key_options:
            val = data["db"].get(key_str, 0)
            if val > 0:
                db_dict[(j, t)] = val
                break

model.db = Param(
    model.j, model.t,
    initialize=db_dict,
    default=0.0,
    doc="Minimum ammonium sulfate requirement (1000 tpy)"
)

# Nutrient content
alpha_dict = {}
for item, val in data["alpha"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            c, cq = item[0], item[1]
            if c in data["c"] and cq in data["cq"]:
                alpha_dict[(c, cq)] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            c, cq = parts[0], parts[1]
            if c in data["c"] and cq in data["cq"]:
                alpha_dict[(c, cq)] = val

model.alpha = Param(
    model.c, model.cq,
    initialize=alpha_dict,
    default=0.0,
    doc="Nutrient content"
)

# Input-output coefficients
a_dict = {}
for item, val in data["a"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            c, p = item[0], item[1]
            if c in data["c"] and p in data["p"]:
                a_dict[(c, p)] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            c, p = parts[0], parts[1]
            if c in data["c"] and p in data["p"]:
                a_dict[(c, p)] = val

model.a = Param(
    model.c, model.p,
    initialize=a_dict,
    default=0.0,
    doc="Input-output coefficients"
)

# Unit utilization matrix
b_dict = {}
for item, val in data["b"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            m, p = item[0], item[1]
            if m in data["m"] and p in data["p"]:
                b_dict[(m, p)] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            m, p = parts[0], parts[1]
            if m in data["m"] and p in data["p"]:
                b_dict[(m, p)] = val

model.b = Param(
    model.m, model.p,
    initialize=b_dict,
    default=0.0,
    doc="Unit utilization matrix"
)

# Capacity (simplified - would need to extract from am parameter)
# For now using dcap as existing capacity
k_dict = {}
for item, val in data["dcap"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            i_part, m_part = item[0], item[1]
            # Assign to all time periods (simplified)
            for t in data["t"]:
                if i_part in data["i"] and m_part in data["m"]:
                    k_dict[(m_part, i_part, t)] = val
    else:
        parts = item.split(".")
        if len(parts) == 2:
            i_part = parts[0]
            m_part = parts[1]
            # Assign to all time periods (simplified)
            for t in data["t"]:
                if i_part in data["i"] and m_part in data["m"]:
                    k_dict[(m_part, i_part, t)] = val

model.k = Param(
    model.m, model.i, model.t,
    initialize=k_dict,
    default=0.0,
    doc="Existing capacity (1000 tpy)"
)

# Package definition
ndef_dict = {}
for item, val in data["ndef"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 3:
            n, i, m = item[0], item[1], item[2]
            if n in data["n"] and i in data["i"] and m in data["m"]:
                ndef_dict[(n, i, m)] = val
    else:
        parts = item.split(".")
        if len(parts) == 3:
            n, i, m = parts[0], parts[1], parts[2]
            if n in data["n"] and i in data["i"] and m in data["m"]:
                ndef_dict[(n, i, m)] = val

model.ndef = Param(
    model.n, model.i, model.m,
    initialize=ndef_dict,
    default=0.0,
    doc="Package definition (1000 tpy)"
)

# Prices and costs
pv_dict = {}
for item, val in data["pv"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        c = item[0]
    else:
        c = item.split("|")[0]
    # Assign same price to all time periods (simplified)
    for t in data["t"]:
        if c in data["c"]:
            pv_dict[(c, t)] = val

model.pv = Param(
    model.c, model.t,
    initialize=pv_dict,
    default=0.0,
    doc="Import prices (us$ per ton)"
)

# Export prices (use same as import prices for simplification)
model.pe = Param(
    model.c, model.t,
    initialize=pv_dict,
    default=0.0,
    doc="Export prices (us$ per ton)"
)

# Local material prices
pd_dict = {}
for item, val in data["pd"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            i, c = item[0], item[1]
            if i in data["i"] and c in data["c"]:
                pd_dict[(i, c)] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            i, c = parts[0], parts[1].replace("pd(i,c)", "")
            # Try to extract commodity
            for comm in data["c"]:
                if comm in str(item):
                    if i in data["i"]:
                        pd_dict[(i, comm)] = val
                        break

model.pd = Param(
    model.i, model.c,
    initialize=pd_dict,
    default=0.0,
    doc="Local material prices (us$ per ton)"
)

# Operating costs
oz_dict = {}
for item, val in data["opcost"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            m, vintage = item[0], item[1]
            g_val = "old" if "operating" in str(vintage) else "new"
            if m in data["m"]:
                # Assign to all processes and plants (simplified)
                for p in data["p"]:
                    if p == m or m in p:
                        for i in data["i"]:
                            oz_dict[(g_val, p, i)] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            m, vintage = parts[0], parts[1]
            g_val = "old" if "operating" in vintage else "new"
            if m in data["m"]:
                # Assign to all processes and plants (simplified)
                for p in data["p"]:
                    if p == m or m in p:
                        for i in data["i"]:
                            oz_dict[(g_val, p, i)] = val

model.oz = Param(
    model.g, model.p, model.i,
    initialize=oz_dict,
    default=0.0,
    doc="Operating costs (us$ per ton)"
)

# Investment data
invdat_dict = {}
for item, val in data["invdat"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) >= 2:
            m = item[0]
            param_type = item[1]
            if m in data["m"]:
                type_key = "fixed" if "investment" in str(param_type) else "limit" if "data" in str(param_type) else "prop"
                invdat_dict[(m, type_key)] = val
    else:
        parts = item.split("|")
        if len(parts) >= 2:
            m = parts[0]
            param_type = parts[1]
            if m in data["m"]:
                type_key = "fixed" if "investment" in param_type else "limit" if "data" in param_type else "prop"
                invdat_dict[(m, type_key)] = val

# Extract nu (proportional investment cost)
nu_dict = {}
for m in data["m"]:
    val = invdat_dict.get((m, "prop"), 0)
    if val > 0:
        nu_dict[m] = val

model.nu = Param(
    model.m,
    initialize=nu_dict,
    default=0.0,
    doc="Proportional investment cost (1000 us$ per tpy)"
)

# Extract hb (capacity limit for packages)
hb_dict = {}
for m in data["m"]:
    val = invdat_dict.get((m, "limit"), 0)
    if val > 0:
        hb_dict[m] = val

model.hb = Param(
    model.m,
    initialize=hb_dict,
    default=0.0,
    doc="Capacity limit for packages (1000 tpy)"
)

# Compute hp (package capacity)
hp_dict = {}
for n in data["n"]:
    for i in data["i"]:
        for m in data["m"]:
            ndef_val = ndef_dict.get((n, i, m), 0)
            if ndef_val > 0:
                hp_dict[(n, i, m)] = 0.33 * ndef_val

model.hp = Param(
    model.n, model.i, model.m,
    initialize=hp_dict,
    default=0.0,
    doc="Package capacity (1000 tpy)"
)

# Compute nupf (fixed package cost)
nupf_dict = {}
for n in data["n"]:
    total = 0
    for i in data["i"]:
        for m in data["m"]:
            ndef_val = ndef_dict.get((n, i, m), 0)
            if ndef_val > 0:
                fixed_cost = invdat_dict.get((m, "fixed"), 0)
                total += 1000 * fixed_cost
    if total > 0:
        nupf_dict[n] = total

model.nupf = Param(
    model.n,
    initialize=nupf_dict,
    default=0.0,
    doc="Fixed package cost (1000 us$)"
)

# Compute ocap (operating cost per capacity)
ocap_dict = {}
for item, val in data["opcost"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            m, param_type = item[0], item[1]
            if "cost" in str(param_type) and m in data["m"]:
                ocap_dict[m] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            m, param_type = parts[0], parts[1]
            if "cost" in param_type and m in data["m"]:
                ocap_dict[m] = val

model.ocap = Param(
    model.m,
    initialize=ocap_dict,
    default=0.0,
    doc="Operating cost per capacity (us$ per tpy)"
)

# Scalar parameters
model.unew = Param(
    initialize=data["unew"],
    doc="Utilization factor for new capacity"
)

model.gamma = Param(
    initialize=data["gamma"],
    doc="Capacity multiplier"
)

model.npack = Param(
    initialize=data["npack"],
    doc="Minimum number of packages per country"
)

model.nnum = Param(
    initialize=data["nnum"],
    doc="Maximum number of times a package can be selected"
)

model.rho = Param(
    initialize=data["rho"],
    doc="Discount rate"
)

model.life = Param(
    initialize=data["life"],
    doc="Plant life (years)"
)

model.tariffvi = Param(
    initialize=data["tariffvi"],
    doc="Tariff on imported intermediate goods"
)

model.tariffvf = Param(
    initialize=data["tariffvf"],
    doc="Tariff on imported final goods"
)

# Compute sigma (capital recovery factor)
rho_val = data["rho"]
life_val = data["life"]
sigma_val = rho_val * (1 + rho_val)**life_val / ((1 + rho_val)**life_val - 1)

model.sigma = Param(
    initialize=sigma_val,
    doc="Capital recovery factor"
)

# Compute delta (discount factor for each period)
delta_dict = {}
for t in data["t"]:
    t_idx = data["t"].index(t)
    midyear = 1979 + 3 * (t_idx + 1)
    delta_val = (1 + rho_val)**(1981 - midyear) + (1 + rho_val)**(1982 - midyear) + (1 + rho_val)**(1983 - midyear)
    delta_dict[t] = delta_val

model.delta = Param(
    model.t,
    initialize=delta_dict,
    doc="Discount factor for each period"
)

# Time summation matrix
ts_dict = {}
for t in data["t"]:
    for tp in data["te"]:
        if data["t"].index(t) >= data["te"].index(tp):
            ts_dict[(t, tp)] = 1
        else:
            ts_dict[(t, tp)] = 0

model.ts = Param(
    model.t, model.te,
    initialize=ts_dict,
    default=0,
    doc="Time summation matrix"
)

# Transport costs (simplified - using subset of trsp table)
muf_dict = {}
for item, val in data["trsp"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            j, i = item[0], item[1]
            if j in data["j"] and i in data["i"]:
                muf_dict[(i, j)] = val
    else:
        parts = item.split("|")
        if len(parts) == 2:
            j, i = parts[0], parts[1]
            if j in data["j"] and i in data["i"]:
                muf_dict[(i, j)] = val

model.muf = Param(
    model.i, model.j,
    initialize=muf_dict,
    default=0.0,
    doc="Transport cost for final products (us$ per ton)"
)

# Marketing possibilities (simplified - allow all cf to ship to all regions)
mc_set = []
for cf in data["cf"]:
    for i in data["i"]:
        for j in data["j"]:
            mc_set.append((cf, i, j))

model.mc = Set(
    initialize=mc_set,
    within=model.c * model.i * model.j,
    doc="Marketing possibilities"
)

# Process possibilities (simplified - all processes possible at all plants with both vintages)
ppos_set = []
for g in data["g"]:
    for p in data["p"]:
        for i in data["i"]:
            # Check if process uses units that have capacity (old) or in investment packages (new)
            has_capacity = False
            for m in data["m"]:
                if b_dict.get((m, p), 0) != 0:
                    if g == "old":
                        # Old vintage: check for existing capacity
                        for t in data["t"]:
                            if k_dict.get((m, i, t), 0) > 0:
                                has_capacity = True
                                break
                    else:  # new vintage
                        # New vintage: check if in any investment package
                        for n in data["n"]:
                            if ndef_dict.get((n, i, m), 0) > 0:
                                has_capacity = True
                                break
                if has_capacity:
                    break
            if has_capacity:
                ppos_set.append((g, p, i))

model.ppos = Set(
    initialize=ppos_set,
    within=model.g * model.p * model.i,
    doc="Process possibility"
)

# Unit possibilities
mpos_set = []
for g in data["g"]:
    for m in data["m"]:
        for i in data["i"]:
            # Old vintage if existing capacity
            if g == "old":
                for t in data["t"]:
                    if k_dict.get((m, i, t), 0) > 0:
                        mpos_set.append((g, m, i))
                        break
            # New vintage if in package definition
            elif g == "new":
                for n in data["n"]:
                    if ndef_dict.get((n, i, m), 0) > 0:
                        mpos_set.append((g, m, i))
                        break

model.mpos = Set(
    initialize=mpos_set,
    within=model.g * model.m * model.i,
    doc="Unit possibility"
)

# Consumption possibilities (commodities that can be consumed at each plant)
cposm_set = []
for c in data["c"]:
    for i in data["i"]:
        # Check if any process at this plant consumes this commodity
        for g, p, i_check in ppos_set:
            if i_check == i and a_dict.get((c, p), 0) < 0:
                cposm_set.append((c, i))
                break

model.cposm = Set(
    initialize=cposm_set,
    within=model.c * model.i,
    doc="Consumption possibility"
)

# Production possibilities
cposp_set = []
for c in data["c"]:
    for i in data["i"]:
        # Check if any process at this plant produces this commodity
        for g, p, i_check in ppos_set:
            if i_check == i and a_dict.get((c, p), 0) > 0:
                cposp_set.append((c, i))
                break

model.cposp = Set(
    initialize=cposp_set,
    within=model.c * model.i,
    doc="Production possibility"
)

# Expansion possibilities
hpos_set = []
for m in data["m"]:
    for i in data["i"]:
        if ("new", m, i) in mpos_set:
            hpos_set.append((m, i))

model.hpos = Set(
    initialize=hpos_set,
    within=model.m * model.i,
    doc="Unit expansion possibility"
)

# Country-package mapping
wn_set = []
for w in data["w"]:
    for n in data["n"]:
        # Check if package n has facilities in country w
        for i in data["i"]:
            if (w, i) in [(w_,i_) for w_,i_ in data["wi"]]:
                for m in data["m"]:
                    if ndef_dict.get((n, i, m), 0) > 0:
                        wn_set.append((w, n))
                        break

model.wn = Set(
    initialize=wn_set,
    within=model.w * model.n,
    doc="Country-package mapping"
)

# Imported final products (subset of cf that can be imported)
cfv_list = [c for c in data["cf"] if c in data["cv"] and c not in data["co"]]

model.cfv = Set(
    initialize=cfv_list,
    within=model.cf,
    doc="Imported final products other than compounds"
)

# Export limits (lambda parameter)
lam_dict = {}
for i in data["i"]:
    if i == "tablazo" or i == "palmasola":
        lam_dict[i] = 0.7
    else:
        lam_dict[i] = 0.3

model.lam = Param(
    model.i,
    initialize=lam_dict,
    default=0.3,
    doc="Maximum export capability"
)

# Minimum NPK utilization (simplified)
umin_dict = {t: 0.0 for t in data["t"]}

model.umin = Param(
    model.t,
    initialize=umin_dict,
    default=0.0,
    doc="Minimum NPK utilization"
)

# Transport cost multiplier for acids
mux_dict = {c: 1.0 for c in data["c"]}

model.mux = Param(
    model.c,
    initialize=mux_dict,
    default=1.0,
    doc="Transport cost factor for acids"
)

# Other transport costs (simplified)
model.mur = Param(
    model.i,
    initialize={i: 0 for i in data["i"]},
    default=0.0,
    doc="Transport cost: imported raw material (us$ per ton)"
)

model.mue = Param(
    model.i,
    initialize={i: 0 for i in data["i"]},
    default=0.0,
    doc="Transport cost: export (us$ per ton)"
)

model.mui = Param(
    model.i, model.i,
    initialize={(i, ip): 0 for i in data["i"] for ip in data["i"]},
    default=0.0,
    doc="Transport cost: interplant shipments (us$ per ton)"
)

model.mufv = Param(
    model.j,
    initialize={j: 0 for j in data["j"]},
    default=0.0,
    doc="Transport cost: imported final products (us$ per ton)"
)

# Local material purchase limits
pdlim_dict = {}
for item, val in data["pd"].items():
    # Handle both string keys and tuple keys (after preprocessing)
    if isinstance(item, tuple):
        if len(item) == 2:
            i, c = item[0], item[1]
            if i in data["i"] and c in data["cr"]:
                pdlim_dict[(i, c)] = val * 1000  # Large limit
    else:
        parts = item.split("|")
        if len(parts) == 2:
            i, c_part = parts[0], parts[1]
            # Extract commodity from second part
            for c in data["cr"]:
                if c in c_part:
                    pdlim_dict[(i, c)] = val * 1000  # Large limit

model.pdlim = Param(
    model.i, model.c,
    initialize=pdlim_dict,
    default=0.0,
    doc="Local material purchase limits (1000 tpy)"
)

# Package constraint parameter
model.dpack = Param(
    initialize=1,
    doc="Maximum package phasing difference between countries"
)

# Country comparison matrix
ple_dict = {}
w_list = data["w"]
for w in w_list:
    for wp in w_list:
        if w_list.index(w) != w_list.index(wp):
            ple_dict[(w, wp)] = 1
        else:
            ple_dict[(w, wp)] = 0

model.ple = Param(
    model.w, model.w,
    initialize=ple_dict,
    default=0,
    doc="Matrix for comparing package phasing in countries"
)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.z = Var(
    model.g, model.p, model.i, model.t,
    domain=NonNegativeReals,
    doc="Process level (1000 units per year)"
)

model.xf = Var(
    model.c, model.i, model.j, model.t,
    domain=NonNegativeReals,
    doc="Domestic shipment activity: final products (1000 tpy)"
)

model.xi = Var(
    model.c, model.i, model.i, model.t,
    domain=NonNegativeReals,
    doc="Domestic shipment activity: interplant (1000 tpy)"
)

model.vf = Var(
    model.cf, model.j, model.t,
    domain=NonNegativeReals,
    doc="Imports: final products (1000 tpy)"
)

model.vi = Var(
    model.c, model.i, model.t,
    domain=NonNegativeReals,
    doc="Imports of: intermediates and raw materials (1000 tpy)"
)

model.e = Var(
    model.c, model.i, model.t,
    domain=NonNegativeReals,
    doc="Exports (1000 tpy)"
)

model.u = Var(
    model.c, model.i, model.t,
    domain=NonNegativeReals,
    doc="Domestic material purchases (1000 tpy)"
)

model.h = Var(
    model.m, model.i, model.te,
    domain=NonNegativeReals,
    doc="Capacity expansion (1000 tpy)"
)

model.yp = Var(
    model.n, model.te,
    domain=Binary,
    doc="Package decision variable (binary)"
)

model.yw = Var(
    model.w, model.te,
    domain=NonNegativeReals,
    doc="Package decision variable by country"
)

# Cost accounting variables
model.tvf = Var(
    model.w, model.t,
    domain=Reals,
    doc="Value of imports: final products (mill us$ per year)"
)

model.tvi = Var(
    model.w, model.t,
    domain=Reals,
    doc="Value of imports: intermediates (mill us$ per year)"
)

model.phik = Var(
    model.w, model.t,
    domain=Reals,
    doc="Capital cost (mill us$ per year)"
)

model.phip = Var(
    model.w, model.t,
    domain=Reals,
    doc="Operating cost (mill us$ per year)"
)

model.phig = Var(
    model.w, model.t,
    domain=Reals,
    doc="Domestic materials cost (mill us$ per year)"
)

model.phiw = Var(
    model.w, model.t,
    domain=Reals,
    doc="Working capital cost (mill us$ per year)"
)

model.phim = Var(
    model.w, model.t,
    domain=Reals,
    doc="Import cost (mill us$ per year)"
)

model.phit = Var(
    model.w, model.t,
    domain=Reals,
    doc="Tariffs (mill us$ per year)"
)

model.phil = Var(
    model.w, model.t,
    domain=Reals,
    doc="Transport cost (mill us$ per year)"
)

model.phie = Var(
    model.w, model.t,
    domain=Reals,
    doc="Export revenue (mill us$ per year)"
)

model.phi = Var(
    model.w, model.t,
    domain=Reals,
    doc="Cost per year (mill us$ per year)"
)

model.phitot = Var(
    doc="Discounted total cost (mill us$ discounted)"
)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# mbd(cq,j,t).. Material balance on demand
def mbd_rule(model, cq, j, t):
    lhs = sum(model.alpha[cf, cq] * (
        sum(model.xf[cf, i, j, t] for i in model.i
            if (cf, i, j) in mc_set and (cf, i) in cposp_set)
        + (model.vf[cf, j, t] if cf in cfv_list else 0)
    ) for cf in data["cf"])
    return lhs >= model.d[j, cq, t]

model.mbd = Constraint(
    model.cq, model.j, model.t,
    rule=mbd_rule,
    doc="Material balance on demand (1000 tpy)"
)

# mba(j,t).. Ammonium sulfate requirements
def mba_rule(model, j, t):
    lhs = sum(model.xf["amm-sulf", i, j, t] for i in model.i
              if ("amm-sulf", i) in cposp_set)
    lhs += model.vf["amm-sulf", j, t] if "amm-sulf" in cfv_list else 0
    return lhs >= model.db[j, t]

model.mba = Constraint(
    model.j, model.t,
    rule=mba_rule,
    doc="Ammonium sulfate requirements (1000 tpy)"
)

# mb(c,i,t).. Material balance at plants
def mb_rule(model, c, i, t):
    # Check if this commodity has any activity at this plant
    # Skip constraint if commodity is not produced, consumed, or used at this plant
    has_production = any((g, p, i) in ppos_set and (c, p) in a_dict
                       for g in model.g for p in model.p)
    has_consumption = (c in data["cv"] and (c, i) in cposm_set) or \
                     ((i, c) in pd_dict and (c, i) in cposm_set) or \
                     (c in data["cis"] and (c, i) in cposm_set)
    has_usage = (c in data["cis"] and (c, i) in cposp_set) or \
               (c in data["ce"] and (c, i) in cposp_set) or \
               (c, i) in cposp_set

    if not (has_production or has_consumption or has_usage):
        return Constraint.Skip

    # Production side
    production = sum(model.a[c, p] * model.z[g, p, i, t]
                    for g in model.g for p in model.p
                    if (g, p, i) in ppos_set and (c, p) in a_dict)

    # Consumption side
    consumption_terms = []

    # Imports of intermediates/raw materials
    if c in data["cv"] and (c, i) in cposm_set:
        consumption_terms.append(model.vi[c, i, t])

    # Local material purchases
    if (i, c) in pd_dict and (c, i) in cposm_set:
        consumption_terms.append(model.u[c, i, t])

    # Interplant receipts
    if c in data["cis"] and (c, i) in cposm_set:
        for ip in model.i:
            if (c, ip) in cposp_set:
                consumption_terms.append(model.xi[c, ip, i, t])

    consumption = sum(consumption_terms) if consumption_terms else 0

    # Usage side
    usage_terms = []

    # Interplant shipments
    if c in data["cis"] and (c, i) in cposp_set:
        for ip in model.i:
            if (c, ip) in cposm_set:
                usage_terms.append(model.xi[c, i, ip, t])

    # Exports
    if c in data["ce"] and (c, i) in cposp_set:
        usage_terms.append(model.e[c, i, t])

    # Final product shipments
    if (c, i) in cposp_set:
        for j in model.j:
            if (c, i, j) in mc_set:
                usage_terms.append(model.xf[c, i, j, t])

    usage = sum(usage_terms) if usage_terms else 0

    return production + consumption >= usage

model.mb = Constraint(
    model.c, model.i, model.t,
    rule=mb_rule,
    doc="Material balance at plants (1000 tpy)"
)

# ubnd(cr,i,t).. Bounds on local materials
def ubnd_rule(model, cr, i, t):
    if (cr, i) in cposm_set and (i, cr) in pdlim_dict:
        return model.u[cr, i, t] <= model.pdlim[i, cr]
    return Constraint.Skip

model.ubnd = Constraint(
    model.cr, model.i, model.t,
    rule=ubnd_rule,
    doc="Bounds on local materials (1000 tpy)"
)

# elim(ce,i,t).. Export limits
def elim_rule(model, ce, i, t):
    if (ce, i) not in cposp_set:
        return Constraint.Skip
    rhs_terms = [model.a[ce, p] * model.z[g, p, i, t]
                 for g in model.g for p in model.p
                 if (g, p, i) in ppos_set and (ce, p) in a_dict and model.a[ce, p] > 0]
    if not rhs_terms:
        return Constraint.Skip
    return model.e[ce, i, t] <= model.lam[i] * sum(rhs_terms)

model.elim = Constraint(
    model.ce, model.i, model.t,
    rule=elim_rule,
    doc="Export limits (1000 tpy)"
)

# cc(g,m,i,t).. Capacity constraints
def cc_rule(model, g, m, i, t):
    if (g, m, i) not in mpos_set:
        return Constraint.Skip

    # Check if any processes use this unit at this plant
    has_processes = any((g, p, i) in ppos_set and (m, p) in b_dict
                      for p in model.p)
    if not has_processes:
        return Constraint.Skip

    lhs = sum(model.b[m, p] * model.z[g, p, i, t]
              for p in model.p if (g, p, i) in ppos_set and (m, p) in b_dict)

    if g == "old":
        rhs = model.k[m, i, t]
    else:  # new
        rhs = sum(model.unew * model.h[m, i, te]
                 for te in model.te if model.ts[t, te] == 1)

    return lhs <= rhs

model.cc = Constraint(
    model.g, model.m, model.i, model.t,
    rule=cc_rule,
    doc="Capacity constraints (1000 tpy)"
)

# ccmin(i,t).. Minimum NPK utilization
def ccmin_rule(model, i, t):
    # Check if NPK capacity exists
    has_npk = False
    for t_check in model.t:
        if model.k["npk", i, t_check] > 0:
            has_npk = True
            break
    if not has_npk:
        return Constraint.Skip

    lhs = sum(model.b["npk", p] * model.z["old", p, i, t]
              for p in model.p if ("old", p, i) in ppos_set and ("npk", p) in b_dict)
    return lhs >= model.umin[t] * model.k["npk", i, t]

model.ccmin = Constraint(
    model.i, model.t,
    rule=ccmin_rule,
    doc="Minimum npk utilization (1000 tpy)"
)

# binv(m,i,te).. Binary constraint: variable plant size
def binv_rule(model, m, i, te):
    if (m, i) not in hpos_set:
        return Constraint.Skip
    rhs_terms = [model.hb[m] * model.yp[n, te]
                 for n in model.n if (n, i, m) in ndef_dict]
    if not rhs_terms:
        return Constraint.Skip
    return model.h[m, i, te] <= model.gamma * sum(rhs_terms)

model.binv = Constraint(
    model.m, model.i, model.te,
    rule=binv_rule,
    doc="Binary constraint: variable plant size (1000 tpy)"
)

# binf(m,i,te).. Binary constraint: fixed plant size
def binf_rule(model, m, i, te):
    # nfix same as hpos in this model
    if (m, i) not in hpos_set:
        return Constraint.Skip
    rhs_terms = [model.hp[n, i, m] * model.yp[n, te]
                 for n in model.n if (n, i, m) in hp_dict]
    if not rhs_terms:
        return Constraint.Skip
    return model.h[m, i, te] == sum(rhs_terms)

model.binf = Constraint(
    model.m, model.i, model.te,
    rule=binf_rule,
    doc="Binary constraint: fixed plant size (1000 tpy)"
)

# minpack(w).. Minimum number of packages per country
def minpack_rule(model, w):
    lhs_terms = [model.yp[n, te]
                 for n in model.n for te in model.te
                 if (w, n) in wn_set]
    if not lhs_terms:
        return Constraint.Skip
    return sum(lhs_terms) >= model.npack

model.minpack = Constraint(
    model.w,
    rule=minpack_rule,
    doc="Minimum number of packages per country"
)

# bw(w,te).. Aggregation of packages in country
def bw_rule(model, w, te):
    rhs_terms = [model.yp[n, te] for n in model.n if (w, n) in wn_set]
    if not rhs_terms:
        return model.yw[w, te] == 0
    return model.yw[w, te] == sum(rhs_terms)

model.bw = Constraint(
    model.w, model.te,
    rule=bw_rule,
    doc="Aggregation of packages in country"
)

# gple(w,wp,te).. Inter-country constraint on package - inequality
def gple_rule(model, w, wp, te):
    if model.ple[w, wp] == 0:
        return Constraint.Skip
    return model.yw[w, te] - model.yw[wp, te] <= model.dpack

model.gple = Constraint(
    model.w, model.w, model.te,
    rule=gple_rule,
    doc="Inter-country constraint on package - inequality"
)

# ex(n).. Package mutual exclusivity
def ex_rule(model, n):
    return sum(model.yp[n, te] for te in model.te) <= model.nnum

model.ex = Constraint(
    model.n,
    rule=ex_rule,
    doc="Package mutual exclusivity (units)"
)

# acc(w,t).. Accounting: capital cost
def acc_rule(model, w, t):
    term1 = sum(model.nu[m] * model.h[m, i, te]
               for te in model.te if model.ts[t, te] == 1
               for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
               for m in model.m if (m, i) in hpos_set)
    term2 = sum(model.nupf[n] * model.yp[n, te]
               for te in model.te if model.ts[t, te] == 1
               for n in model.n if (w, n) in wn_set)
    return model.phik[w, t] == model.sigma * (term1 + term2) / 1000

model.acc = Constraint(
    model.w, model.t,
    rule=acc_rule,
    doc="Accounting: capital cost (mill us$ per year)"
)

# acp(w,t).. Accounting: operating cost
def acp_rule(model, w, t):
    term1 = sum(model.oz[g, p, i] * model.z[g, p, i, t]
               for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
               for g in model.g for p in model.p if (g, p, i) in ppos_set)
    term2 = sum(model.ocap[m] * model.h[m, i, te]
               for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
               for m in model.m for te in model.te
               if (m, i) in hpos_set and model.ts[t, te] == 1)
    return model.phip[w, t] == (term1 + term2) / 1000

model.acp = Constraint(
    model.w, model.t,
    rule=acp_rule,
    doc="Accounting: operating cost (mill us$ per year)"
)

# acg(w,t).. Accounting: domestic materials
def acg_rule(model, w, t):
    terms = [model.pd[i, cr] * model.u[cr, i, t]
            for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
            for cr in model.cr if (cr, i) in cposm_set and (i, cr) in pd_dict]
    if not terms:
        return model.phig[w, t] == 0
    return model.phig[w, t] == sum(terms) / 1000

model.acg = Constraint(
    model.w, model.t,
    rule=acg_rule,
    doc="Accounting: domestic materials (mill us$ per year)"
)

# acw(w,t).. Accounting: working capital
def acw_rule(model, w, t):
    base = model.phip[w, t] + model.phig[w, t]
    import_terms = [((model.pv[cv, t] + model.mux[cv] * model.mur[i]) * model.vi[cv, i, t])
                   for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
                   for cv in data["cv"] if (cv, i) in cposm_set]
    import_sum = sum(import_terms) if import_terms else 0
    return model.phiw[w, t] == 0.025 * (base + import_sum) / 1000

model.acw = Constraint(
    model.w, model.t,
    rule=acw_rule,
    doc="Accounting: working capital (mill us$ per year)"
)

# acm(w,t).. Accounting: import cost
def acm_rule(model, w, t):
    return model.phim[w, t] == model.tvi[w, t] + model.tvf[w, t]

model.acm = Constraint(
    model.w, model.t,
    rule=acm_rule,
    doc="Accounting: import cost (mill us$ per year)"
)

# act(w,t).. Accounting: tariffs
def act_rule(model, w, t):
    return model.phit[w, t] == model.tariffvi * model.tvi[w, t] + model.tariffvf * model.tvf[w, t]

model.act = Constraint(
    model.w, model.t,
    rule=act_rule,
    doc="Accounting: tariffs (mill us$ per year)"
)

# atvf(w,t).. Definition of import value: finals products
def atvf_rule(model, w, t):
    terms = [model.pv[cfv, t] * model.vf[cfv, j, t]
            for j in model.j if (w, j) in [(w_, j_) for w_, j_ in data["wj"]]
            for cfv in cfv_list]
    if not terms:
        return model.tvf[w, t] == 0
    return model.tvf[w, t] == sum(terms) / 1000

model.atvf = Constraint(
    model.w, model.t,
    rule=atvf_rule,
    doc="Definition of import value: finals products (mill us$ per year)"
)

# atvi(w,t).. Definition of import value: intermediates
def atvi_rule(model, w, t):
    terms = [model.pv[cv, t] * model.vi[cv, i, t]
            for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
            for cv in data["cv"] if (cv, i) in cposm_set]
    if not terms:
        return model.tvi[w, t] == 0
    return model.tvi[w, t] == sum(terms) / 1000

model.atvi = Constraint(
    model.w, model.t,
    rule=atvi_rule,
    doc="Definition of import value: intermediates (mill us$ per year)"
)

# acl(w,t).. Accounting: transport cost
def acl_rule(model, w, t):
    # Final product transport
    term1 = sum(model.muf[i, j] * model.xf[cf, i, j, t]
               for j in model.j if (w, j) in [(w_, j_) for w_, j_ in data["wj"]]
               for cf in data["cf"]
               for i in model.i if (cf, i, j) in mc_set and (cf, i) in cposp_set and (i, j) in muf_dict)

    # Import transport
    term2 = sum(model.mufv[j] * model.vf[cfv, j, t]
               for j in model.j if (w, j) in [(w_, j_) for w_, j_ in data["wj"]]
               for cfv in cfv_list)

    # Export transport
    term3 = sum(model.mux[ce] * model.mue[i] * model.e[ce, i, t]
               for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
               for ce in data["ce"] if (ce, i) in cposp_set)

    # Import raw material transport
    term4 = sum(model.mux[cv] * model.mur[i] * model.vi[cv, i, t]
               for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
               for cv in data["cv"] if (cv, i) in cposm_set)

    # Interplant transport
    term5 = sum(model.mux[cis] * model.mui[i, ip] * model.xi[cis, i, ip, t]
               for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
               for ip in model.i
               for cis in data["cis"] if (cis, ip) in cposm_set and (cis, i) in cposp_set)

    return model.phil[w, t] == (term1 + term2 + term3 + term4 + term5) / 1000

model.acl = Constraint(
    model.w, model.t,
    rule=acl_rule,
    doc="Accounting: transport cost (mill us$ per year)"
)

# ace(w,t).. Accounting: export revenue
def ace_rule(model, w, t):
    terms = [model.pe[ce, t] * model.e[ce, i, t]
            for i in model.i if (w, i) in [(w_, i_) for w_, i_ in data["wi"]]
            for ce in data["ce"] if (ce, i) in cposp_set]
    if not terms:
        return model.phie[w, t] == 0
    return model.phie[w, t] == sum(terms) / 1000

model.ace = Constraint(
    model.w, model.t,
    rule=ace_rule,
    doc="Accounting: export revenue (mill us$ per year)"
)

# ac(w,t).. Accounting: total annual undiscounted cost
def ac_rule(model, w, t):
    return model.phi[w, t] == (model.phik[w, t] + model.phip[w, t] + model.phig[w, t] +
                               model.phiw[w, t] + model.phim[w, t] + model.phil[w, t] -
                               model.phie[w, t])

model.ac = Constraint(
    model.w, model.t,
    rule=ac_rule,
    doc="Accounting: total annual undiscounted cost (mill us$ per year)"
)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return sum(model.delta[t] * model.phi[w, t] for w in model.w for t in model.t)

model.obj = Objective(
    rule=obj_rule,
    sense=minimize,
    doc="Minimize discounted total cost (mill us$ discounted)"
)

# Link phitot to objective for compatibility
def phitot_def_rule(model):
    return model.phitot == sum(model.delta[t] * model.phi[w, t] for w in model.w for t in model.t)

model.phitot_def = Constraint(
    rule=phitot_def_rule,
    doc="Definition of total discounted cost"
)
