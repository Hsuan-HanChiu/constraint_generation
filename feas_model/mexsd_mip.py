# converted from models/mexsd_mip.py
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
    doc="MEXICO Steel - Small Dynamic"
)

# ----------------------------------------------------------------------
# SET_BLOCK
# ----------------------------------------------------------------------
model.i = Set(initialize=data["i"], doc="Steel plants")
model.im = Set(initialize=data["im"], doc="Mines")
model.j = Set(initialize=data["j"], doc="Markets")
model.c = Set(initialize=data["c"], doc="Commodities")
model.cf = Set(initialize=data["cf"], doc="Final products")
model.ce = Set(initialize=data["ce"], doc="Export product")
model.ci = Set(initialize=data["ci"], doc="Intermediate products")
model.cr = Set(initialize=data["cr"], doc="Raw materials")
model.cm = Set(initialize=data["cm"], doc="Mining products")
model.cv = Set(initialize=data["cv"], doc="Raw materials imported")
model.p = Set(initialize=data["p"], doc="Processes")
model.m = Set(initialize=data["m"], doc="Productive units")
model.me = Set(initialize=data["me"], doc="Expansion units")
model.t = Set(initialize=data["t"], doc="Time periods")
model.te = Set(initialize=data["te"], doc="Expansion periods")
model.energy = Set(initialize=data["energy"], doc="Energy commodities")
model.q = Set(initialize=data["q"], doc="Cost levels")
model.g = Set(initialize=data["g"], doc="Investment function segments")

# ----------------------------------------------------------------------
# PARAM_BLOCK - Extract and process parameters
# ----------------------------------------------------------------------
baseyear = data.get("baseyear", 1979)
theta = data.get("theta", 3)

# midyear and ts
midyear_dict = {}
for t in data["t"]:
    midyear_dict[t] = baseyear + theta * (data["t"].index(t) + 1)

model.midyear = Param(model.t, initialize=midyear_dict, doc="Period mid-years")

# ts(te,taue): time summation matrix
ts_dict = {}
for te in data["te"]:
    for taue in data["te"]:
        if data["te"].index(taue) <= data["te"].index(te):
            ts_dict[(te, taue)] = 1
        else:
            ts_dict[(te, taue)] = 0

model.ts = Param(model.te, model.te, initialize=ts_dict, default=0)

# Process data dictionaries
a_dict = {}
for key, val in data["a"].items():
    if isinstance(key, tuple):
        a_dict[key] = val
    else:
        a_dict[key] = val

b_dict = {}
for key, val in data["b"].items():
    if isinstance(key, tuple):
        b_dict[key] = val
    else:
        b_dict[key] = val

k_dict = {}
for key, val in data["k"].items():
    if isinstance(key, tuple):
        k_dict[key] = val
    else:
        k_dict[key] = val

# Convert string keys to tuple keys for multi-dimensional params
for key_name in ["a", "b", "k", "km", "rd", "ri", "rm", "inv", "dd", "site", "region", "pdb", "pv", "pe"]:
    if key_name in data:
        new_dict = {}
        for key, val in data[key_name].items():
            if isinstance(key, str) and "|" in key:
                # Already converted by run.py
                new_dict[key] = val
            elif isinstance(key, tuple):
                new_dict[key] = val
            else:
                new_dict[key] = val
        data[key_name] = new_dict

model.a = Param(model.c, model.p, initialize=data["a"], default=0, doc="Input-output coefficients")
model.b = Param(model.m, model.p, initialize=data["b"], default=0, doc="Capacity utilization")
model.k = Param(model.m, model.i, initialize=data["k"], default=0, doc="Capacities of productive units")

# Mining capacity data km
km_dict = {}
for key, val in data["km"].items():
    if isinstance(key, tuple):
        km_dict[key] = val

# Compute wbar and pw
wbar_dict = {}
pw_dict = {}
num_q = len(data["q"])

for cm in data["cm"]:
    for im in data["im"]:
        wmax_key = (cm, im, "wmax")
        if wmax_key in km_dict:
            wmax = km_dict[wmax_key]
            wbar_dict[(cm, im)] = wmax / num_q

            p_low = km_dict.get((cm, im, "p-low"), 0)
            p_high = km_dict.get((cm, im, "p-high"), 0)
            expo = km_dict.get((cm, im, "expo"), 1)

            for q in data["q"]:
                q_ord = int(q)
                pw_val = p_low + (p_high - p_low) * ((q_ord - 1) / (num_q - 1)) ** expo
                pw_dict[(cm, q, im)] = pw_val

model.wbar = Param(model.cm, model.im, initialize=wbar_dict, default=0)
model.pw = Param(model.cm, model.q, model.im, initialize=pw_dict, default=0)

# Demand computation
dt = data.get("dt", 5.2)
rse = data.get("rse", 40)
gd = data.get("gd", 10)

dd_dict = {}
for key, val in data["dd"].items():
    if isinstance(key, tuple) and len(key) == 1:
        dd_dict[key[0]] = val
    else:
        dd_dict[key] = val

d_dict = {}
for cf in data["cf"]:
    for j in data["j"]:
        for t in data["t"]:
            d_val = dt * (1 + rse/100) * dd_dict.get(j, 0) * (1 + gd/100) ** (midyear_dict[t] - baseyear)
            d_dict[(cf, j, t)] = d_val

model.d = Param(model.cf, model.j, model.t, initialize=d_dict, default=0)

# Export bound
eu_dict = {t: 0.2 for t in data["t"]}
model.eu = Param(model.t, initialize=eu_dict)

# Transport costs
rd_dict = {}
for key, val in data["rd"].items():
    if isinstance(key, tuple):
        rd_dict[key] = val

ri_dict = {}
for key, val in data["ri"].items():
    if isinstance(key, tuple):
        ri_dict[key] = val

# Make ri symmetric
ri_symmetric = {}
for key, val in ri_dict.items():
    if len(key) == 2:
        i1, i2 = key
        ri_symmetric[(i1, i2)] = max(val, ri_dict.get((i2, i1), 0))
        ri_symmetric[(i2, i1)] = ri_symmetric[(i1, i2)]
ri_dict.update(ri_symmetric)

rm_dict = {}
for key, val in data["rm"].items():
    if isinstance(key, tuple):
        rm_dict[key] = val

# Compute transport costs using formula: 2.48 + 0.0084*distance
muf_dict = {}
for i in data["i"]:
    for j in data["j"]:
        dist = rd_dict.get((i, j), 0)
        if dist > 0:
            muf_dict[(i, j)] = 2.48 + 0.0084 * dist

model.muf = Param(model.i, model.j, initialize=muf_dict, default=0)

mun_dict = {}
for i in data["i"]:
    for ip in data["i"]:
        dist = ri_dict.get((i, ip), 0)
        if dist > 0:
            mun_dict[(i, ip)] = 2.48 + 0.0084 * dist

model.mun = Param(model.i, model.i, initialize=mun_dict, default=0)

mum_dict = {}
for im in data["im"]:
    for i in data["i"]:
        dist = rm_dict.get((im, i), 0)
        if dist > 0:
            mum_dict[(im, i)] = 2.48 + 0.0084 * dist

model.mum = Param(model.im, model.i, initialize=mum_dict, default=0)

muv_dict = {}
for j in data["j"]:
    dist = rd_dict.get(("import", j), 0)
    if dist > 0:
        muv_dict[j] = 2.48 + 0.0084 * dist

model.muv = Param(model.j, initialize=muv_dict, default=0)

mue_dict = {}
for i in data["i"]:
    dist = rd_dict.get((i, "export"), 0)
    if dist > 0:
        mue_dict[i] = 2.48 + 0.0084 * dist

model.mue = Param(model.i, initialize=mue_dict, default=0)

# Investment data
inv_dict = {}
for key, val in data["inv"].items():
    if isinstance(key, tuple):
        inv_dict[key] = val

site_dict = {}
for key, val in data["site"].items():
    if isinstance(key, tuple) and len(key) == 1:
        site_dict[key[0]] = val
    else:
        site_dict[key] = val

# Compute investment parameters
# inv(me,"fixed") = inv(me,"phihat")*(.5**(inv(me,"beta")-1)-1)
inv_fixed = {}
omega_dict = {}
sb_dict = {}

for me in data["me"]:
    phihat = inv_dict.get((me, "phihat"), 0)
    beta = inv_dict.get((me, "beta"), 0.6)
    hhat = inv_dict.get((me, "hhat"), 1)

    fixed = phihat * (0.5 ** (beta - 1) - 1)
    inv_fixed[me] = fixed

    for i in data["i"]:
        site_val = site_dict.get(i, 1)
        omega_dict[(me, "1", i)] = fixed * site_val
        omega_dict[(me, "2", i)] = phihat * site_val
        omega_dict[(me, "3", i)] = phihat * site_val * 3
        omega_dict[(me, "4", i)] = phihat * site_val * 6 * 1.25

    sb_dict[(me, "1")] = 0
    sb_dict[(me, "2")] = hhat
    sb_dict[(me, "3")] = hhat * 3
    sb_dict[(me, "4")] = hhat * 6

model.omega = Param(model.me, model.g, model.i, initialize=omega_dict, default=0)
model.sb = Param(model.me, model.g, initialize=sb_dict, default=0)

# Financial parameters
zeta = data.get("zeta", 20)
rho = data.get("rho", 0.1)
sigma = rho / (1 - (1 + rho) ** (-zeta))

delta_dict = {}
for t in data["t"]:
    delta_dict[t] = (1 + rho) ** (baseyear - midyear_dict[t])

model.delta = Param(model.t, initialize=delta_dict)
model.sigma = Param(initialize=sigma)

# Resource and price parameters
model.rlev = Param(initialize=data.get("rlev", 1))
model.iron = Param(initialize=data.get("iron", 30))

# Domestic prices pd(cr,i,t)
pdb_dict = {}
for key, val in data["pdb"].items():
    if isinstance(key, tuple) and len(key) == 1:
        pdb_dict[key[0]] = val
    else:
        pdb_dict[key] = val

region_dict = {}
for key, val in data["region"].items():
    if isinstance(key, tuple) and len(key) == 1:
        region_dict[key[0]] = val
    else:
        region_dict[key] = val

pd_dict = {}
for cr in data["cr"]:
    for i in data["i"]:
        for t in data["t"]:
            t_ord = data["t"].index(t) + 1

            if cr == "nat-gas":
                price = min(128, pdb_dict.get("nat-gas", 14) + (128 - pdb_dict.get("nat-gas", 14)) / 4 * (t_ord - 1))
            else:
                price = pdb_dict.get(cr, 0)

            if cr in data["energy"]:
                price = price * (1 - region_dict.get(i, 0))

            pd_dict[(cr, i, t)] = price

model.pd = Param(model.cr, model.i, model.t, initialize=pd_dict, default=0)

# Import and export prices
pv_dict = {}
for key, val in data["pv"].items():
    if isinstance(key, tuple) and len(key) == 1:
        pv_dict[key[0]] = val
    else:
        pv_dict[key] = val

pe_dict = {}
for key, val in data["pe"].items():
    if isinstance(key, tuple) and len(key) == 1:
        pe_dict[key[0]] = val
    else:
        pe_dict[key] = val

model.pv = Param(model.c, initialize=pv_dict, default=0)
model.pe = Param(model.ce, initialize=pe_dict, default=0)

# ----------------------------------------------------------------------
# VAR_BLOCK
# ----------------------------------------------------------------------
model.z = Var(model.p, model.i, model.t, domain=NonNegativeReals)
model.w = Var(model.cm, model.q, model.im, model.t, domain=NonNegativeReals)
model.x = Var(model.c, model.i, model.j, model.t, domain=NonNegativeReals)
model.xn = Var(model.c, model.i, model.i, model.t, domain=NonNegativeReals)
model.xm = Var(model.c, model.im, model.i, model.t, domain=NonNegativeReals)
model.u = Var(model.c, model.i, model.t, domain=NonNegativeReals)
model.h = Var(model.m, model.i, model.t, domain=NonNegativeReals)
model.s = Var(model.me, model.g, model.i, model.t, domain=NonNegativeReals)
model.y = Var(model.me, model.i, model.te, domain=Binary)
model.v = Var(model.cf, model.j, model.t, domain=NonNegativeReals)
model.vr = Var(model.c, model.i, model.t, domain=NonNegativeReals)
model.e = Var(model.c, model.i, model.t, domain=NonNegativeReals)

model.phi = Var(doc="Total cost (discounted)")
model.phikap = Var(model.t, domain=NonNegativeReals)
model.phipsi = Var(model.t, domain=NonNegativeReals)
model.philam = Var(model.t, domain=NonNegativeReals)
model.phipi = Var(model.t, domain=NonNegativeReals)
model.phieps = Var(model.t, domain=NonNegativeReals)

# ----------------------------------------------------------------------
# OBJ_BLOCK
# ----------------------------------------------------------------------
def obj_rule(model):
    return model.phi

model.obj = Objective(rule=obj_rule, sense=minimize)

# ----------------------------------------------------------------------
# CONS_BLOCK
# ----------------------------------------------------------------------

# Material balance at steel plants
def mb_rule(model, c, i, t):
    lhs = sum(model.a[c, p] * model.z[p, i, t] for p in model.p)

    if c in data["cr"]:
        lhs += model.u[c, i, t]

    if c in data["cm"]:
        lhs += sum(model.xm[c, im, i, t] for im in model.im)

    if c in data["cv"]:
        lhs += model.vr[c, i, t]

    if c in data["ci"]:
        lhs += sum(model.xn[c, ip, i, t] for ip in model.i)

    rhs = 0
    if c in data["ci"]:
        rhs += sum(model.xn[c, i, ip, t] for ip in model.i)

    if c in data["cf"]:
        rhs += sum(model.x[c, i, j, t] for j in model.j)

    if c in data["ce"]:
        rhs += model.e[c, i, t]

    return lhs >= rhs

model.mb = Constraint(model.c, model.i, model.t, rule=mb_rule)

# Material balance at mines
def mbm_rule(model, cm, im, t):
    return sum(model.w[cm, q, im, t] for q in model.q) >= sum(model.xm[cm, im, i, t] for i in model.i)

model.mbm = Constraint(model.cm, model.im, model.t, rule=mbm_rule)

# Capacity constraints at steel plants
def cc_rule(model, m, i, t):
    lhs = sum(model.b[m, p] * model.z[p, i, t] for p in model.p)
    rhs = model.k[m, i]

    if m in data["me"]:
        for tau in data["t"]:
            if ts_dict.get((t, tau), 0) > 0 and tau in data["te"]:
                rhs += model.h[m, i, tau]

    return lhs <= rhs

model.cc = Constraint(model.m, model.i, model.t, rule=cc_rule)

# Capacity constraints at mines
def ccm_rule(model, cm, q, im):
    return sum(model.w[cm, q, im, t] for t in model.t) <= model.rlev * model.wbar[cm, im] / theta

model.ccm = Constraint(model.cm, model.q, model.im, rule=ccm_rule)

# Investment function segments
def ih_rule(model, me, i, te):
    return model.h[me, i, te] == sum(model.sb[me, g] * model.s[me, g, i, te] for g in model.g)

model.ih = Constraint(model.me, model.i, model.te, rule=ih_rule)

def ic_rule(model, me, i, te):
    return model.y[me, i, te] == sum(model.s[me, g, i, te] for g in model.g)

model.ic = Constraint(model.me, model.i, model.te, rule=ic_rule)

# Market requirements
def mr_rule(model, cf, j, t):
    return sum(model.x[cf, i, j, t] for i in model.i) + model.v[cf, j, t] >= model.d[cf, j, t]

model.mr = Constraint(model.cf, model.j, model.t, rule=mr_rule)

# Export bounds
def eb_rule(model, t):
    return sum(model.e[ce, i, t] for ce in model.ce for i in model.i) <= model.eu[t]

model.eb = Constraint(model.t, rule=eb_rule)

# Limit on steel production
def zb_rule(model, i, t):
    return model.z["pig-iron", i, t] + model.z["sponge", i, t] <= model.iron

model.zb = Constraint(model.i, model.t, rule=zb_rule)

# Accounting equations
def obj_account_rule(model):
    return model.phi == sum(
        model.delta[t] * theta * (
            model.phikap[t] + model.phipsi[t] + model.philam[t] +
            model.phipi[t] - model.phieps[t]
        ) for t in model.t
    )

model.obj_account = Constraint(rule=obj_account_rule)

def akap_rule(model, t):
    return model.phikap[t] == model.sigma * sum(
        model.omega[me, g, i] * model.s[me, g, i, tau]
        for me in model.me for g in model.g for i in model.i
        for tau in model.te if ts_dict.get((t, tau), 0) > 0
    )

model.akap = Constraint(model.t, rule=akap_rule)

def apsi_rule(model, t):
    return model.phipsi[t] == (
        sum(model.pd[cr, i, t] * model.u[cr, i, t] for cr in model.cr for i in model.i) +
        sum(model.pw[cm, q, im] * model.w[cm, q, im, t] for cm in model.cm for q in model.q for im in model.im)
    )

model.apsi = Constraint(model.t, rule=apsi_rule)

def alam_rule(model, t):
    return model.philam[t] == (
        sum(model.muf[i, j] * model.x[cf, i, j, t] for cf in model.cf for i in model.i for j in model.j if (i, j) in muf_dict) +
        sum(model.muv[j] * model.v[cf, j, t] for cf in model.cf for j in model.j if j in muv_dict) +
        sum(model.mum[im, i] * model.xm[cm, im, i, t] for cm in model.cm for im in model.im for i in model.i if (im, i) in mum_dict) +
        sum(model.mue[i] * model.e[ce, i, t] for ce in model.ce for i in model.i if i in mue_dict) +
        sum(model.mun[i, ip] * model.xn[ci, i, ip, t] for ci in model.ci for i in model.i for ip in model.i if (i, ip) in mun_dict) +
        sum(model.mue[i] * model.vr[cv, i, t] for cv in model.cv for i in model.i if i in mue_dict)
    )

model.alam = Constraint(model.t, rule=alam_rule)

def api_rule(model, t):
    return model.phipi[t] == (
        sum(model.pv[cf] * model.v[cf, j, t] for cf in model.cf for j in model.j if cf in pv_dict) +
        sum(model.pv[cv] * model.vr[cv, i, t] for cv in model.cv for i in model.i if cv in pv_dict)
    )

model.api = Constraint(model.t, rule=api_rule)

def aeps_rule(model, t):
    return model.phieps[t] == sum(
        model.pe[ce] * model.e[ce, i, t]
        for ce in model.ce for i in model.i if ce in pe_dict
    )

model.aeps = Constraint(model.t, rule=aeps_rule)
