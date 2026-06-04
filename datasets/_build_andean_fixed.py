#!/usr/bin/env python
"""Builder for the andean_fixed (Andean fertilizer investment) constraint-generation dataset.

The corpus model is FLAGGED nonlinear, but every one of its 25 constraints has
polynomial degree 0 or 1 (verified): all are LINEAR. param**param and param/param
terms (sigma, delta, /1000) are constant coefficients. So all 25 constraints are
included; none are excluded for nonlinearity.

Reconstructions are self-contained: the grader execs expected_pyomo in a namespace
with only {model, Constraint, sum, pyo, value}, so every membership guard is rebuilt
from the model's own Pyomo Sets/Params (model.mc, model.cposp, model.ppos, ...).
Dense parameter dicts in the source (a, b, ndef, pd, pdlim) act as no-op guards over
their natural index and are dropped; sparse ones (hp, muf) map to the model Set/Param.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "andean_fixed_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "w", "members": ["bolivia", "colombia", "ecuador", "peru", "venezuela"],
         "doc": "the countries in the Andean group; cost accounting and package coordination are tracked per country"},
        {"name": "i", "members": ["palmasola", "cartagena", "barrancabr", "..."],
         "doc": "the plant locations where production units can operate and capacity can be expanded"},
        {"name": "j", "members": ["potosi", "bogota", "cali", "quito", "..."],
         "doc": "the demand regions that consume final fertilizer products"},
        {"name": "m", "members": ["amm-n-gas", "nitr-acid", "amm-nitr", "urea", "ssp", "..."],
         "doc": "the productive units (capacity-bearing equipment) that can exist at a plant"},
        {"name": "g", "members": ["old", "new"],
         "doc": "the vintage of a unit or process; old means pre-existing capacity, new means capacity added through investment"},
        {"name": "p", "members": ["amm-n-gas", "nitr-acid", "amm-nitr", "urea", "ssp", "..."],
         "doc": "the production processes; each process consumes and produces commodities according to fixed input-output coefficients"},
        {"name": "cq", "members": ["n", "p2o5", "k2o"],
         "doc": "the plant nutrients nitrogen, phosphate and potash that demand is expressed in"},
        {"name": "c", "members": ["nitr-acid", "amm-nitr", "urea", "ssp", "phos-acid", "sulf-acid", "..."],
         "doc": "all commodities in the model, covering intermediates, raw materials and final products"},
        {"name": "cf", "members": ["amm-nitr", "amm-sulf", "urea", "ssp", "tsp", "dap", "..."],
         "doc": "the final fertilizer products that satisfy regional demand"},
        {"name": "co", "members": ["c-20-18-10", "c-13-13-20", "..."],
         "doc": "the compound (blended) fertilizers, a subset of final products"},
        {"name": "cr", "members": ["sulf-acid", "electr", "nat-gas", "fuel-oil", "phos-rock", "el-sulfur", "brine"],
         "doc": "the raw materials that can be purchased locally at a plant"},
        {"name": "cis", "members": ["amm-nitr", "amm-sulf", "urea", "ssp", "phos-acid", "dap", "..."],
         "doc": "the commodities that can be shipped between plants (interplant shipments)"},
        {"name": "ce", "members": ["amm-nitr", "amm-sulf", "urea", "phos-acid", "dap", "..."],
         "doc": "the commodities that can be exported out of the region"},
        {"name": "cv", "members": ["amm-nitr", "amm-sulf", "urea", "phos-acid", "ammonia", "..."],
         "doc": "the commodities that can be imported from outside the region"},
        {"name": "t", "members": ["1981-83", "1984-86", "1987-89", "1990-92"],
         "doc": "the planning time periods over the horizon, in chronological order"},
        {"name": "te", "members": ["1984-86", "1987-89", "1990-92"],
         "doc": "the expansion periods in which new capacity can be installed; a subset of the time periods excluding the first"},
        {"name": "n", "members": ["bol-1", "col-1", "ecu-1", "per-1", "..."],
         "doc": "the investment packages; each package bundles a predefined set of unit expansions at specific plants"},
        {"name": "wi", "members": [["bolivia", "palmasola"], ["..."]],
         "doc": "the set of country-plant pairs that are valid, telling which plants belong to which country"},
        {"name": "wj", "members": [["bolivia", "potosi"], ["..."]],
         "doc": "the set of country-region pairs that are valid, telling which demand regions belong to which country"},
        {"name": "mc", "members": [["amm-nitr", "palmasola", "potosi"], ["..."]],
         "doc": "the set of allowed (final product, plant, region) shipment links; a final product may ship from a plant to a region only if the triple is in this set"},
        {"name": "ppos", "members": [["old", "amm-n-gas", "cartagena"], ["..."]],
         "doc": "the set of feasible (vintage, process, plant) combinations; a process may run at a plant with a given vintage only if the triple is in this set"},
        {"name": "mpos", "members": [["old", "amm-n-gas", "cartagena"], ["..."]],
         "doc": "the set of feasible (vintage, unit, plant) combinations; a capacity constraint applies for a unit at a plant only if the triple is in this set"},
        {"name": "cposm", "members": [["nitr-acid", "baranquill"], ["..."]],
         "doc": "the set of (commodity, plant) pairs where the commodity can be consumed or received at that plant"},
        {"name": "cposp", "members": [["nitr-acid", "baranquill"], ["..."]],
         "doc": "the set of (commodity, plant) pairs where the commodity can be produced or sent out from that plant"},
        {"name": "hpos", "members": [["amm-n-gas", "palmasola"], ["..."]],
         "doc": "the set of (unit, plant) pairs where new capacity expansion is possible"},
        {"name": "wn", "members": [["bolivia", "bol-1"], ["..."]],
         "doc": "the set of (country, package) pairs telling which investment packages belong to which country"},
        {"name": "cfv", "members": ["amm-nitr", "amm-sulf", "urea", "tsp", "dap", "pot-chlor"],
         "doc": "the final products that may be imported; a subset of final products excluding compounds"},
    ],
    "params": [
        {"name": "d", "index": "j,cq,t", "kind": "demand",
         "doc": "regional nutrient demand to be met, in thousand tons per year, by region, nutrient and period"},
        {"name": "db", "index": "j,t", "kind": "demand",
         "doc": "minimum ammonium sulfate requirement at a region in a period, in thousand tons per year"},
        {"name": "alpha", "index": "c,cq", "kind": "content",
         "doc": "nutrient content: tons of a nutrient delivered per ton of a commodity"},
        {"name": "a", "index": "c,p", "kind": "io-coeff",
         "doc": "input-output coefficient of a process: positive means the process produces the commodity, negative means it consumes it, per unit of process level"},
        {"name": "b", "index": "m,p", "kind": "io-coeff",
         "doc": "unit utilization: amount of a unit's capacity used per unit of process level"},
        {"name": "k", "index": "m,i,t", "kind": "capacity",
         "doc": "existing (old vintage) capacity of a unit at a plant in a period, in thousand tons per year"},
        {"name": "hp", "index": "n,i,m", "kind": "capacity",
         "doc": "the capacity each package adds for a given unit at a given plant, in thousand tons per year; defined only for the (package, plant, unit) triples a package actually covers"},
        {"name": "hb", "index": "m", "kind": "capacity",
         "doc": "the per-unit capacity ceiling used to bound variable expansion of a unit, in thousand tons per year"},
        {"name": "nu", "index": "m", "kind": "cost",
         "doc": "proportional investment cost of a unit, in thousand dollars per thousand-tons-per-year of capacity"},
        {"name": "nupf", "index": "n", "kind": "cost",
         "doc": "fixed cost of selecting a package, in thousand dollars"},
        {"name": "oz", "index": "g,p,i", "kind": "cost",
         "doc": "operating cost per unit of process level, by vintage, process and plant, in dollars per ton"},
        {"name": "ocap", "index": "m", "kind": "cost",
         "doc": "operating cost tied to installed expansion capacity of a unit, in dollars per ton per year"},
        {"name": "pv", "index": "c,t", "kind": "price",
         "doc": "import price of a commodity in a period, in dollars per ton"},
        {"name": "pe", "index": "c,t", "kind": "price",
         "doc": "export price of a commodity in a period, in dollars per ton"},
        {"name": "pd", "index": "i,c", "kind": "price",
         "doc": "local purchase price of a raw material at a plant, in dollars per ton"},
        {"name": "pdlim", "index": "i,c", "kind": "bound",
         "doc": "upper limit on local purchases of a raw material at a plant, in thousand tons per year"},
        {"name": "muf", "index": "i,j", "kind": "cost",
         "doc": "transport cost of moving final product from a plant to a region, in dollars per ton; defined only for connected plant-region pairs"},
        {"name": "mufv", "index": "j", "kind": "cost",
         "doc": "transport cost for imported final product delivered to a region, in dollars per ton"},
        {"name": "mur", "index": "i", "kind": "cost",
         "doc": "transport cost for imported raw material to a plant, in dollars per ton"},
        {"name": "mue", "index": "i", "kind": "cost",
         "doc": "transport cost for export from a plant, in dollars per ton"},
        {"name": "mui", "index": "i,i", "kind": "cost",
         "doc": "transport cost for interplant shipment between two plants, in dollars per ton"},
        {"name": "mux", "index": "c", "kind": "factor",
         "doc": "transport cost multiplier applied to a commodity (an acid surcharge factor)"},
        {"name": "lam", "index": "i", "kind": "bound",
         "doc": "the fraction of a plant's production of a commodity that is allowed to be exported"},
        {"name": "umin", "index": "t", "kind": "bound",
         "doc": "the minimum fraction of NPK capacity that must be utilized in a period"},
        {"name": "ts", "index": "t,te", "kind": "indicator",
         "doc": "a 0/1 indicator equal to 1 when the time period is at or after the expansion period, used to accumulate capacity installed in earlier expansion periods"},
        {"name": "ple", "index": "w,w", "kind": "indicator",
         "doc": "a 0/1 indicator equal to 1 for two distinct countries and 0 when the two country indices are the same, used to compare package phasing across countries"},
        {"name": "delta", "index": "t", "kind": "factor",
         "doc": "the discount factor applied to a period's cost when accumulating discounted total cost"},
        {"name": "sigma", "index": "", "kind": "factor",
         "doc": "the capital recovery factor that annualizes investment cost"},
        {"name": "unew", "index": "", "kind": "factor",
         "doc": "the utilization factor applied to newly installed capacity"},
        {"name": "gamma", "index": "", "kind": "factor",
         "doc": "a capacity multiplier used in the variable plant-size bound"},
        {"name": "npack", "index": "", "kind": "bound",
         "doc": "the minimum number of packages each country must select"},
        {"name": "nnum", "index": "", "kind": "bound",
         "doc": "the maximum number of expansion periods in which a single package may be selected"},
        {"name": "dpack", "index": "", "kind": "bound",
         "doc": "the maximum allowed difference in cumulative package count between two countries"},
        {"name": "tariffvi", "index": "", "kind": "rate",
         "doc": "the tariff rate applied to the value of imported intermediates"},
        {"name": "tariffvf", "index": "", "kind": "rate",
         "doc": "the tariff rate applied to the value of imported final products"},
    ],
    "vars": [
        {"name": "z", "index": "g,p,i,t", "domain": "NonNegativeReals",
         "doc": "the activity level of a process at a plant with a given vintage in a period, in thousand units per year"},
        {"name": "xf", "index": "c,i,j,t", "domain": "NonNegativeReals",
         "doc": "domestic shipment of a final product from a plant to a region in a period, in thousand tons per year"},
        {"name": "xi", "index": "c,i,i,t", "domain": "NonNegativeReals",
         "doc": "interplant shipment of a commodity from the first plant to the second plant in a period, in thousand tons per year"},
        {"name": "vf", "index": "cf,j,t", "domain": "NonNegativeReals",
         "doc": "imports of a final product delivered to a region in a period, in thousand tons per year"},
        {"name": "vi", "index": "c,i,t", "domain": "NonNegativeReals",
         "doc": "imports of an intermediate or raw material received at a plant in a period, in thousand tons per year"},
        {"name": "e", "index": "c,i,t", "domain": "NonNegativeReals",
         "doc": "exports of a commodity from a plant in a period, in thousand tons per year"},
        {"name": "u", "index": "c,i,t", "domain": "NonNegativeReals",
         "doc": "local purchases of a raw material at a plant in a period, in thousand tons per year"},
        {"name": "h", "index": "m,i,te", "domain": "NonNegativeReals",
         "doc": "capacity expansion of a unit at a plant installed in an expansion period, in thousand tons per year"},
        {"name": "yp", "index": "n,te", "domain": "Binary",
         "doc": "equals 1 if investment package is selected in the expansion period and 0 otherwise"},
        {"name": "yw", "index": "w,te", "domain": "NonNegativeReals",
         "doc": "the number of packages selected by a country in an expansion period"},
        {"name": "tvf", "index": "w,t", "domain": "Reals",
         "doc": "the value of final-product imports for a country in a period, in million dollars per year"},
        {"name": "tvi", "index": "w,t", "domain": "Reals",
         "doc": "the value of intermediate imports for a country in a period, in million dollars per year"},
        {"name": "phik", "index": "w,t", "domain": "Reals",
         "doc": "capital cost for a country in a period, in million dollars per year"},
        {"name": "phip", "index": "w,t", "domain": "Reals",
         "doc": "operating cost for a country in a period, in million dollars per year"},
        {"name": "phig", "index": "w,t", "domain": "Reals",
         "doc": "domestic materials cost for a country in a period, in million dollars per year"},
        {"name": "phiw", "index": "w,t", "domain": "Reals",
         "doc": "working capital cost for a country in a period, in million dollars per year"},
        {"name": "phim", "index": "w,t", "domain": "Reals",
         "doc": "import cost for a country in a period, in million dollars per year"},
        {"name": "phit", "index": "w,t", "domain": "Reals",
         "doc": "tariff cost for a country in a period, in million dollars per year"},
        {"name": "phil", "index": "w,t", "domain": "Reals",
         "doc": "transport cost for a country in a period, in million dollars per year"},
        {"name": "phie", "index": "w,t", "domain": "Reals",
         "doc": "export revenue for a country in a period, in million dollars per year"},
        {"name": "phi", "index": "w,t", "domain": "Reals",
         "doc": "total undiscounted annual cost for a country in a period, in million dollars per year"},
        {"name": "phitot", "index": "", "domain": "Reals",
         "doc": "the discounted total cost over the whole horizon, in million dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "phitot"},
}

NARRATIVE = (
    "We plan fertilizer production and investment across a group of Andean countries over "
    "several multi-year periods. Each country has plants that can run production processes, "
    "expand unit capacity by selecting bundled investment packages, and ship final products "
    "to demand regions. In each period we decide how much of each process to run at each "
    "plant, how much to ship domestically between plants and to regions, how much to import "
    "and export, how much raw material to buy locally, how much capacity to install, and "
    "which investment packages to select in each expansion period. A series of accounting "
    "quantities roll these activities up into capital, operating, materials, working capital, "
    "import, tariff, transport and export-revenue costs per country and period. The objective "
    "is to minimize the discounted total cost over the whole horizon."
)

# ---- reconstructed constraints (all validated native-equivalent) -------------
MBD = """def mbd_rule(model, cq, j, t):
    lhs = sum(model.alpha[cf, cq] * (
        sum(model.xf[cf, i, j, t] for i in model.i if (cf, i, j) in model.mc and (cf, i) in model.cposp)
        + (model.vf[cf, j, t] if cf in model.cfv else 0)
    ) for cf in model.cf)
    return lhs >= model.d[j, cq, t]
model.mbd = Constraint(model.cq, model.j, model.t, rule=mbd_rule)"""

MBA = """def mba_rule(model, j, t):
    lhs = sum(model.xf["amm-sulf", i, j, t] for i in model.i if ("amm-sulf", i) in model.cposp)
    lhs += model.vf["amm-sulf", j, t] if "amm-sulf" in model.cfv else 0
    return lhs >= model.db[j, t]
model.mba = Constraint(model.j, model.t, rule=mba_rule)"""

MB = """def mb_rule(model, c, i, t):
    has_production = any((g, p, i) in model.ppos for g in model.g for p in model.p)
    has_consumption = (c in model.cv and (c, i) in model.cposm) or ((c, i) in model.cposm) or (c in model.cis and (c, i) in model.cposm)
    has_usage = (c in model.cis and (c, i) in model.cposp) or (c in model.ce and (c, i) in model.cposp) or (c, i) in model.cposp
    if not (has_production or has_consumption or has_usage):
        return Constraint.Skip
    production = sum(model.a[c, p] * model.z[g, p, i, t] for g in model.g for p in model.p if (g, p, i) in model.ppos)
    consumption_terms = []
    if c in model.cv and (c, i) in model.cposm:
        consumption_terms.append(model.vi[c, i, t])
    if (c, i) in model.cposm:
        consumption_terms.append(model.u[c, i, t])
    if c in model.cis and (c, i) in model.cposm:
        for ip in model.i:
            if (c, ip) in model.cposp:
                consumption_terms.append(model.xi[c, ip, i, t])
    consumption = sum(consumption_terms) if consumption_terms else 0
    usage_terms = []
    if c in model.cis and (c, i) in model.cposp:
        for ip in model.i:
            if (c, ip) in model.cposm:
                usage_terms.append(model.xi[c, i, ip, t])
    if c in model.ce and (c, i) in model.cposp:
        usage_terms.append(model.e[c, i, t])
    if (c, i) in model.cposp:
        for j in model.j:
            if (c, i, j) in model.mc:
                usage_terms.append(model.xf[c, i, j, t])
    usage = sum(usage_terms) if usage_terms else 0
    return production + consumption >= usage
model.mb = Constraint(model.c, model.i, model.t, rule=mb_rule)"""

UBND = """def ubnd_rule(model, cr, i, t):
    if (cr, i) in model.cposm:
        return model.u[cr, i, t] <= model.pdlim[i, cr]
    return Constraint.Skip
model.ubnd = Constraint(model.cr, model.i, model.t, rule=ubnd_rule)"""

ELIM = """def elim_rule(model, ce, i, t):
    if (ce, i) not in model.cposp:
        return Constraint.Skip
    rhs_terms = [model.a[ce, p] * model.z[g, p, i, t] for g in model.g for p in model.p if (g, p, i) in model.ppos and model.a[ce, p] > 0]
    if not rhs_terms:
        return Constraint.Skip
    return model.e[ce, i, t] <= model.lam[i] * sum(rhs_terms)
model.elim = Constraint(model.ce, model.i, model.t, rule=elim_rule)"""

CC = """def cc_rule(model, g, m, i, t):
    if (g, m, i) not in model.mpos:
        return Constraint.Skip
    has_processes = any((g, p, i) in model.ppos for p in model.p)
    if not has_processes:
        return Constraint.Skip
    lhs = sum(model.b[m, p] * model.z[g, p, i, t] for p in model.p if (g, p, i) in model.ppos)
    if g == "old":
        rhs = model.k[m, i, t]
    else:
        rhs = sum(model.unew * model.h[m, i, te] for te in model.te if model.ts[t, te] == 1)
    return lhs <= rhs
model.cc = Constraint(model.g, model.m, model.i, model.t, rule=cc_rule)"""

CCMIN = """def ccmin_rule(model, i, t):
    has_npk = False
    for t_check in model.t:
        if model.k["npk", i, t_check] > 0:
            has_npk = True
            break
    if not has_npk:
        return Constraint.Skip
    lhs = sum(model.b["npk", p] * model.z["old", p, i, t] for p in model.p if ("old", p, i) in model.ppos)
    return lhs >= model.umin[t] * model.k["npk", i, t]
model.ccmin = Constraint(model.i, model.t, rule=ccmin_rule)"""

BINV = """def binv_rule(model, m, i, te):
    if (m, i) not in model.hpos:
        return Constraint.Skip
    rhs_terms = [model.hb[m] * model.yp[n, te] for n in model.n]
    if not rhs_terms:
        return Constraint.Skip
    return model.h[m, i, te] <= model.gamma * sum(rhs_terms)
model.binv = Constraint(model.m, model.i, model.te, rule=binv_rule)"""

BINF = """def binf_rule(model, m, i, te):
    if (m, i) not in model.hpos:
        return Constraint.Skip
    rhs_terms = [model.hp[n, i, m] * model.yp[n, te] for n in model.n if (n, i, m) in model.hp]
    if not rhs_terms:
        return Constraint.Skip
    return model.h[m, i, te] == sum(rhs_terms)
model.binf = Constraint(model.m, model.i, model.te, rule=binf_rule)"""

MINPACK = """def minpack_rule(model, w):
    lhs_terms = [model.yp[n, te] for n in model.n for te in model.te if (w, n) in model.wn]
    if not lhs_terms:
        return Constraint.Skip
    return sum(lhs_terms) >= model.npack
model.minpack = Constraint(model.w, rule=minpack_rule)"""

BW = """def bw_rule(model, w, te):
    return model.yw[w, te] == sum(model.yp[n, te] for n in model.n if (w, n) in model.wn)
model.bw = Constraint(model.w, model.te, rule=bw_rule)"""

GPLE = """def gple_rule(model, w, wp, te):
    if model.ple[w, wp] == 0:
        return Constraint.Skip
    return model.yw[w, te] - model.yw[wp, te] <= model.dpack
model.gple = Constraint(model.w, model.w, model.te, rule=gple_rule)"""

EX = """def ex_rule(model, n):
    return sum(model.yp[n, te] for te in model.te) <= model.nnum
model.ex = Constraint(model.n, rule=ex_rule)"""

ACC = """def acc_rule(model, w, t):
    term1 = sum(model.nu[m] * model.h[m, i, te] for te in model.te if model.ts[t, te] for i in model.i if (w, i) in model.wi for m in model.m if (m, i) in model.hpos)
    term2 = sum(model.nupf[n] * model.yp[n, te] for te in model.te if model.ts[t, te] for n in model.n if (w, n) in model.wn)
    return model.phik[w, t] == model.sigma * (term1 + term2) / 1000
model.acc = Constraint(model.w, model.t, rule=acc_rule)"""

ACP = """def acp_rule(model, w, t):
    term1 = sum(model.oz[g, p, i] * model.z[g, p, i, t] for i in model.i if (w, i) in model.wi for g in model.g for p in model.p if (g, p, i) in model.ppos)
    term2 = sum(model.ocap[m] * model.h[m, i, te] for i in model.i if (w, i) in model.wi for m in model.m for te in model.te if (m, i) in model.hpos and model.ts[t, te])
    return model.phip[w, t] == (term1 + term2) / 1000
model.acp = Constraint(model.w, model.t, rule=acp_rule)"""

ACG = """def acg_rule(model, w, t):
    terms = [model.pd[i, cr] * model.u[cr, i, t] for i in model.i if (w, i) in model.wi for cr in model.cr if (cr, i) in model.cposm]
    return model.phig[w, t] == sum(terms) / 1000
model.acg = Constraint(model.w, model.t, rule=acg_rule)"""

ACW = """def acw_rule(model, w, t):
    base = model.phip[w, t] + model.phig[w, t]
    import_terms = [((model.pv[cv, t] + model.mux[cv] * model.mur[i]) * model.vi[cv, i, t]) for i in model.i if (w, i) in model.wi for cv in model.cv if (cv, i) in model.cposm]
    import_sum = sum(import_terms) if import_terms else 0
    return model.phiw[w, t] == 0.025 * (base + import_sum) / 1000
model.acw = Constraint(model.w, model.t, rule=acw_rule)"""

ACM = """def acm_rule(model, w, t):
    return model.phim[w, t] == model.tvi[w, t] + model.tvf[w, t]
model.acm = Constraint(model.w, model.t, rule=acm_rule)"""

ACT = """def act_rule(model, w, t):
    return model.phit[w, t] == model.tariffvi * model.tvi[w, t] + model.tariffvf * model.tvf[w, t]
model.act = Constraint(model.w, model.t, rule=act_rule)"""

ATVF = """def atvf_rule(model, w, t):
    terms = [model.pv[cfv, t] * model.vf[cfv, j, t] for j in model.j if (w, j) in model.wj for cfv in model.cfv]
    return model.tvf[w, t] == sum(terms) / 1000
model.atvf = Constraint(model.w, model.t, rule=atvf_rule)"""

ATVI = """def atvi_rule(model, w, t):
    terms = [model.pv[cv, t] * model.vi[cv, i, t] for i in model.i if (w, i) in model.wi for cv in model.cv if (cv, i) in model.cposm]
    return model.tvi[w, t] == sum(terms) / 1000
model.atvi = Constraint(model.w, model.t, rule=atvi_rule)"""

ACL = """def acl_rule(model, w, t):
    term1 = sum(model.muf[i, j] * model.xf[cf, i, j, t] for j in model.j if (w, j) in model.wj for cf in model.cf for i in model.i if (cf, i, j) in model.mc and (cf, i) in model.cposp and (i, j) in model.muf)
    term2 = sum(model.mufv[j] * model.vf[cfv, j, t] for j in model.j if (w, j) in model.wj for cfv in model.cfv)
    term3 = sum(model.mux[ce] * model.mue[i] * model.e[ce, i, t] for i in model.i if (w, i) in model.wi for ce in model.ce if (ce, i) in model.cposp)
    term4 = sum(model.mux[cv] * model.mur[i] * model.vi[cv, i, t] for i in model.i if (w, i) in model.wi for cv in model.cv if (cv, i) in model.cposm)
    term5 = sum(model.mux[cis] * model.mui[i, ip] * model.xi[cis, i, ip, t] for i in model.i if (w, i) in model.wi for ip in model.i for cis in model.cis if (cis, ip) in model.cposm and (cis, i) in model.cposp)
    return model.phil[w, t] == (term1 + term2 + term3 + term4 + term5) / 1000
model.acl = Constraint(model.w, model.t, rule=acl_rule)"""

ACE = """def ace_rule(model, w, t):
    terms = [model.pe[ce, t] * model.e[ce, i, t] for i in model.i if (w, i) in model.wi for ce in model.ce if (ce, i) in model.cposp]
    return model.phie[w, t] == sum(terms) / 1000
model.ace = Constraint(model.w, model.t, rule=ace_rule)"""

AC = """def ac_rule(model, w, t):
    return model.phi[w, t] == (model.phik[w, t] + model.phip[w, t] + model.phig[w, t] + model.phiw[w, t] + model.phim[w, t] + model.phil[w, t] - model.phie[w, t])
model.ac = Constraint(model.w, model.t, rule=ac_rule)"""

PHITOT = """def phitot_def_rule(model):
    return model.phitot == sum(model.delta[t] * model.phi[w, t] for w in model.w for t in model.t)
model.phitot_def = Constraint(rule=phitot_def_rule)"""

ALL = [MBD, MBA, MB, UBND, ELIM, CC, CCMIN, BINV, BINF, MINPACK, BW, GPLE, EX,
       ACC, ACP, ACG, ACW, ACM, ACT, ATVF, ATVI, ACL, ACE, AC, PHITOT]
WHOLESET = "\n".join(ALL)

records = [
    {"description": (
        "For each nutrient, demand region and period, the nutrient delivered to that region must "
        "meet or exceed the required amount. Add up the nutrient content carried by every final "
        "product shipped into the region from the plants that can supply it, together with the "
        "nutrient content of any final product imported directly into the region, and require "
        "this total to be at least the demand for that nutrient in that region and period."),
     "expected_pyomo": MBD},
    {"description": (
        "For each demand region and period, the ammonium sulfate made available to that region "
        "must be at least the regions minimum ammonium sulfate requirement. Count both the "
        "ammonium sulfate shipped in from supplying plants and any ammonium sulfate imported "
        "directly into the region."),
     "expected_pyomo": MBA},
    {"description": (
        "For each commodity, plant and period, the plant cannot send out more of the commodity "
        "than it makes available. What is made available is what the plants processes produce of "
        "the commodity plus what arrives at the plant through imports, local purchases and "
        "interplant receipts. What is sent out is what the plant ships to other plants, exports, "
        "and ships as final product to demand regions. Production plus what comes in must cover "
        "what goes out. This balance applies only where the commodity can actually be produced, "
        "consumed or handled at that plant."),
     "expected_pyomo": MB},
    {"description": (
        "For each raw material, plant and period where the material can be purchased locally, the "
        "amount bought locally cannot exceed the local purchase limit for that material at that "
        "plant."),
     "expected_pyomo": UBND},
    {"description": (
        "For each exportable commodity, plant and period, exports of that commodity from the plant "
        "are capped at a fixed fraction of the plants own production of it. The cap is that "
        "fraction times the total amount the plants processes produce of the commodity. This "
        "applies only where the plant can produce the commodity."),
     "expected_pyomo": ELIM},
    {"description": (
        "For each vintage, unit, plant and period, the capacity of the unit used by the processes "
        "running at the plant cannot exceed the capacity available. For old vintage the available "
        "capacity is the existing capacity of that unit at the plant. For new vintage it is the "
        "utilized portion of the new capacity installed in expansion periods up to and including "
        "the current period. This applies only where the unit can exist at the plant with that "
        "vintage."),
     "expected_pyomo": CC},
    {"description": (
        "For each plant that has NPK capacity and each period, the NPK processing run at the plant "
        "must reach at least the required minimum utilization of its NPK capacity. The required "
        "level is the minimum utilization fraction for the period applied to the plants NPK "
        "capacity."),
     "expected_pyomo": CCMIN},
    {"description": (
        "For each unit, plant and expansion period where expansion is possible, the capacity added "
        "for that unit is bounded above by a multiple of the units capacity ceiling, scaled by "
        "whether the relevant packages are selected in that expansion period."),
     "expected_pyomo": BINV},
    {"description": (
        "For each unit, plant and expansion period where expansion is possible, the capacity added "
        "for that unit must exactly equal the capacity contributed by the selected packages. Each "
        "package that covers this unit at this plant contributes its defined capacity when it is "
        "selected in that expansion period."),
     "expected_pyomo": BINF},
    {"description": (
        "Each country must select at least the required minimum number of investment packages. "
        "For each country, count the packages belonging to that country that are selected across "
        "all expansion periods and require that count to be at least the minimum."),
     "expected_pyomo": MINPACK},
    {"description": (
        "For each country and expansion period, the countrys package count is defined as the "
        "number of its own packages selected in that expansion period."),
     "expected_pyomo": BW},
    {"description": (
        "For each pair of distinct countries and each expansion period, the two countries must "
        "keep their package counts close. The difference between the first countrys package count "
        "and the second countrys package count in that period cannot exceed the allowed phasing "
        "difference."),
     "expected_pyomo": GPLE},
    {"description": (
        "For each package, the number of expansion periods in which it is selected cannot exceed "
        "the maximum number of times a package is allowed to be chosen."),
     "expected_pyomo": EX},
    {"description": (
        "For each country and period, define the capital cost. It is the annualized investment "
        "cost, obtained by applying the capital recovery factor to the sum of two parts and "
        "expressing the result in million dollars. The first part is the proportional investment "
        "cost of each units capacity installed at the countrys plants in expansion periods up to "
        "and including the current period. The second part is the fixed cost of each of the "
        "countrys packages selected in those expansion periods."),
     "expected_pyomo": ACC},
    {"description": (
        "For each country and period, define the operating cost in million dollars. It combines "
        "the operating cost of running every process at the countrys plants in that period with "
        "the capacity-related operating cost of the expansion capacity installed at those plants "
        "in expansion periods up to and including the current period."),
     "expected_pyomo": ACP},
    {"description": (
        "For each country and period, define the domestic materials cost in million dollars as "
        "the total spent on locally purchased raw materials at the countrys plants, valuing each "
        "purchase at its local price."),
     "expected_pyomo": ACG},
    {"description": (
        "For each country and period, define the working capital cost as a fixed small fraction "
        "of the sum of the countrys operating cost, its domestic materials cost, and the delivered "
        "value of its intermediate imports, where each imported intermediate is valued at its "
        "import price plus its inbound transport cost. The result is expressed in million dollars."),
     "expected_pyomo": ACW},
    {"description": (
        "For each country and period, define the import cost as the value of the countrys "
        "intermediate imports plus the value of its final-product imports."),
     "expected_pyomo": ACM},
    {"description": (
        "For each country and period, define the tariff cost as the intermediate import tariff "
        "rate applied to the value of intermediate imports plus the final-product import tariff "
        "rate applied to the value of final-product imports."),
     "expected_pyomo": ACT},
    {"description": (
        "For each country and period, define the value of final-product imports in million dollars "
        "as the total cost of all final products imported into the countrys regions, valuing each "
        "at its import price."),
     "expected_pyomo": ATVF},
    {"description": (
        "For each country and period, define the value of intermediate imports in million dollars "
        "as the total cost of all intermediates imported into the countrys plants, valuing each at "
        "its import price."),
     "expected_pyomo": ATVI},
    {"description": (
        "For each country and period, define the transport cost in million dollars by summing the "
        "transport spending across all logistics flows for the country: shipping final products "
        "from plants to regions, delivering imported final products to regions, exporting from "
        "plants, bringing imported raw materials to plants, and moving commodities between plants. "
        "Each flow is valued at its own per-ton transport cost, with an acid surcharge factor "
        "applied where relevant."),
     "expected_pyomo": ACL},
    {"description": (
        "For each country and period, define the export revenue in million dollars as the total "
        "earned from exporting commodities out of the countrys plants, valuing each export at its "
        "export price."),
     "expected_pyomo": ACE},
    {"description": (
        "For each country and period, define the total annual undiscounted cost as the sum of "
        "capital, operating, domestic materials, working capital, import, and transport costs, "
        "minus export revenue."),
     "expected_pyomo": AC},
    {"description": (
        "Define the discounted total cost over the whole horizon as the sum across all countries "
        "and periods of each periods discount factor times that countrys total annual cost in the "
        "period."),
     "expected_pyomo": PHITOT},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "andean_fixed",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
