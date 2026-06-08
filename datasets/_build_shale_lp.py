#!/usr/bin/env python
"""Builder for the shale_lp (oil-shale investment planning) constraint-generation dataset.

LP, 22 constraint families. Many constraints reference GAMS presolve-derived
constant tables (drd, dgd, nu, sigma, ebm, ts, newcap, delf, bbr, bbg) and named
process/time subsets (PDU mine-dump, PMU mine-up, T1 first-two periods). The grading
exec namespace only exposes {model, Constraint, sum, pyo, value}, so each
expected_pyomo rule is made SELF-CONTAINED by embedding the derived literals inline.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "shale_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "c", "members": ["syncrude", "lpg", "ammonia", "coke", "sulfur", "shale-25", "shale-30", "shale-35", "sur-water", "mo-water", "grnd-water", "mined-25", "mined-30", "mined-35", "water", "shale-oil", "spentshale", "part", "so2", "misc-act-i", "can-space", "mine-fill", "spoil-dist", "part-red", "so2-red"],
         "doc": "all commodities tracked in the material balances, spanning final saleable products, the various raw materials, intermediate streams, and special accounting rows"},
        {"name": "cf", "members": ["syncrude", "lpg", "ammonia", "coke", "sulfur"],
         "doc": "the final saleable products, a subset of the commodities"},
        {"name": "crs", "members": ["shale-25", "shale-30", "shale-35"],
         "doc": "the raw shale grades that can be purchased, a subset of the commodities"},
        {"name": "crr", "members": ["sur-water", "mo-water"],
         "doc": "the renewable water sources that can be purchased each period, a subset of the commodities"},
        {"name": "crg", "members": ["grnd-water"],
         "doc": "the non-renewable groundwater source, purchased once over the whole horizon, a subset of the commodities"},
        {"name": "ci", "members": ["mined-25", "mined-30", "mined-35", "water", "shale-oil", "spentshale", "part", "so2", "misc-act-i"],
         "doc": "the intermediate commodities that are produced and consumed internally and must net to zero, a subset of the commodities"},
        {"name": "cc", "members": ["can-space"],
         "doc": "the canyon disposal-space commodity, a subset of the commodities"},
        {"name": "er", "members": ["part-red", "so2-red"],
         "doc": "the regulated air-pollution emissions, a subset of the commodities"},
        {"name": "p", "members": ["mining-25", "mining-30", "mining-35", "ret-25", "ret-30", "ret-35", "buy-h2o-s", "buy-h2o-g", "buy-h2o-m", "upgrading", "dispose-c", "dispose-u", "dispose-d", "miscell", "part-50", "so2-50", "part-90", "so2-90", "part-95", "so2-95", "part-99", "so2-99", "part-99pt5", "so2-99pt5"],
         "doc": "the production and disposal processes that can be operated; 'dispose-u' is the mine-backfill (dump) disposal process and the three 'mining-*' processes are the mine-up processes"},
        {"name": "m", "members": ["mine-25", "mine-30", "mine-35", "retort-25", "retort-30", "retort-35", "h2o-s-eq", "h2o-g-eq", "h2o-m-eq", "upgrader", "disp-c-eq", "disp-u-eq", "disp-d-eq", "misc-eq", "part-50-eq", "so2-50-eq", "part-90-eq", "so2-90-eq", "part-95-eq", "so2-95-eq", "part-99-eq", "so2-99-eq", "p-99pt5-eq", "s-99pt5-eq"],
         "doc": "the productive units (equipment) that must be installed to support process operation"},
        {"name": "i", "members": ["i1", "i2", "i3", "i4", "i5"],
         "doc": "the ordered break points of the piecewise water-purchase cost curve, from cheapest (i1) to most expensive (i5)"},
        {"name": "tf", "members": ["1985-89", "1990-94", "1995-99", "2000-04", "2005-09"],
         "doc": "the full ordered set of expansion (investment) time periods, including the initial 1985-89 build period"},
        {"name": "t", "members": ["1990-94", "1995-99", "2000-04", "2005-09"],
         "doc": "the operating time periods in chronological order; a subset of the expansion periods that excludes the initial 1985-89 build period"},
    ],
    "params": [
        {"name": "a", "index": "c,p", "kind": "io",
         "doc": "input-output coefficient: net amount of commodity c produced (positive) or consumed (negative) per unit of process p run; missing entries are zero"},
        {"name": "b", "index": "m,p", "kind": "io",
         "doc": "capacity-utilization coefficient: units of productive unit m required per unit of process p run; missing entries are zero"},
        {"name": "bd", "index": "cc", "kind": "capacity",
         "doc": "available canyon disposal space for the canyon-space commodity"},
        {"name": "bs", "index": "crs", "kind": "capacity",
         "doc": "total recoverable shale available for each shale grade over the whole horizon, in million tons"},
        {"name": "pf", "index": "cf,t", "kind": "price",
         "doc": "selling price of each final product in each operating period"},
        {"name": "newcap", "index": "t", "kind": "capacity",
         "doc": "additional syncrude output capacity that may be brought online in each operating period"},
        {"name": "bc", "index": "er", "kind": "background",
         "doc": "background ambient concentration of each regulated emission before any project emissions are added"},
        {"name": "esa", "index": "er", "kind": "standard",
         "doc": "the ambient air-quality standard (allowed concentration ceiling) for each regulated emission"},
        {"name": "ps", "index": "", "kind": "royalty",
         "doc": "the royalty rate charged per barrel of syncrude produced, in dollars per barrel"},
    ],
    "vars": [
        {"name": "z", "index": "p,tf", "domain": "NonNegativeReals",
         "doc": "operating level of each process in each expansion period"},
        {"name": "x", "index": "cf,tf", "domain": "NonNegativeReals",
         "doc": "output quantity of each final product in each expansion period"},
        {"name": "us", "index": "crs,tf", "domain": "NonNegativeReals",
         "doc": "purchased quantity of each shale grade in each expansion period"},
        {"name": "ur", "index": "crr,t", "domain": "NonNegativeReals",
         "doc": "purchased quantity of each renewable water source in each operating period"},
        {"name": "ug", "index": "crg", "domain": "NonNegativeReals",
         "doc": "total purchased quantity of groundwater over the whole horizon"},
        {"name": "h", "index": "m,tf", "domain": "NonNegativeReals",
         "doc": "investment (new capacity installed) in each productive unit in each expansion period"},
        {"name": "uur", "index": "crr,i,tf", "domain": "NonNegativeReals",
         "doc": "renewable water purchased on each break-point segment of the cost curve, by source and expansion period"},
        {"name": "uug", "index": "crg,i", "domain": "NonNegativeReals",
         "doc": "groundwater purchased on each break-point segment of the cost curve"},
        {"name": "pi", "index": "", "domain": "Reals",
         "doc": "total discounted profit over the whole horizon, in million dollars"},
        {"name": "r", "index": "t", "domain": "Reals",
         "doc": "sales revenue in each operating period"},
        {"name": "phiy", "index": "t", "domain": "Reals",
         "doc": "shale royalty cost in each operating period"},
        {"name": "phir", "index": "t", "domain": "Reals",
         "doc": "renewable water cost in each operating period"},
        {"name": "phig", "index": "", "domain": "Reals",
         "doc": "total groundwater cost over the whole horizon"},
        {"name": "phik", "index": "t", "domain": "Reals",
         "doc": "cost of capital (investment) charged in each operating period"},
        {"name": "phio", "index": "t", "domain": "Reals",
         "doc": "operating cost other than raw materials in each operating period"},
    ],
    "objective": {"sense": "maximize", "expr_var": "pi"},
}

NARRATIVE = (
    "This is an investment and operating plan for a Piceance-basin oil-shale syncrude "
    "complex over a multi-decade horizon. Across a sequence of expansion and operating "
    "periods we decide how hard to run each mining, retorting, upgrading, disposal, and "
    "pollution-control process, how much raw shale, renewable water, and groundwater to "
    "buy, how much of each final product to make, and how much to invest in each piece of "
    "productive equipment. Water is bought along a rising piecewise cost curve, so we also "
    "decide how much to take from each segment of that curve. The goal is to maximize the "
    "total discounted profit, which nets period sales revenue against the cost of raw "
    "materials, royalties, operating costs, and capital."
)

# ── per-constraint expected_pyomo (self-contained: derived tables embedded inline) ──

MSU = (
    "def msu_rule(model, cr, tt):\n"
    "    return sum(model.a[cr, pp] * model.z[pp, tt] for pp in model.p) == -model.us[cr, tt]\n"
    "model.msu = Constraint(model.crs, model.t, rule=msu_rule)"
)
MRW = (
    "def mrw_rule(model, cr, tt):\n"
    "    return sum(model.a[cr, pp] * model.z[pp, tt] for pp in model.p) == -model.ur[cr, tt]\n"
    "model.mrw = Constraint(model.crr, model.t, rule=mrw_rule)"
)
MGW = (
    "def mgw_rule(model, cr):\n"
    "    return sum(model.a[cr, pp] * model.z[pp, tt] for pp in model.p for tt in model.t) == -model.ug[cr]\n"
    "model.mgw = Constraint(model.crg, rule=mgw_rule)"
)
MI = (
    "def mi_rule(model, cc, tt):\n"
    "    return sum(model.a[cc, pp] * model.z[pp, tt] for pp in model.p) == 0\n"
    "model.mi = Constraint(model.ci, model.t, rule=mi_rule)"
)
MF = (
    "def mf_rule(model, cc, tt):\n"
    "    return sum(model.a[cc, pp] * model.z[pp, tt] for pp in model.p) == model.x[cc, tt]\n"
    "model.mf = Constraint(model.cf, model.t, rule=mf_rule)"
)
MNMR = (
    "def mnmr_rule(model):\n"
    "    PDU = ['dispose-u']; T1 = ['1990-94', '1995-99']\n"
    "    return 0 == sum(model.z[pp, tt] for pp in PDU for tt in T1)\n"
    "model.mnmr = Constraint(rule=mnmr_rule)"
)
MMR3 = (
    "def mmr3_rule(model):\n"
    "    PDU = ['dispose-u']; PMU = ['mining-25', 'mining-30', 'mining-35']\n"
    "    return sum(model.z[pp, '2000-04'] for pp in PDU) <= 0.413 * sum(model.z[pp, '1990-94'] for pp in PMU)\n"
    "model.mmr3 = Constraint(rule=mmr3_rule)"
)
MMR4 = (
    "def mmr4_rule(model):\n"
    "    PDU = ['dispose-u']; PMU = ['mining-25', 'mining-30', 'mining-35']\n"
    "    return (sum(model.z[pp, '2005-09'] for pp in PDU)\n"
    "            <= 0.413 * sum(model.z[pp, '1990-94'] + model.z[pp, '1995-99'] for pp in PMU)\n"
    "               - sum(model.z[pp, '2000-04'] for pp in PDU))\n"
    "model.mmr4 = Constraint(rule=mmr4_rule)"
)
CDC = (
    "def cdc_rule(model, cc):\n"
    "    theta = 5.0\n"
    "    return theta * sum(model.a[cc, pp] * model.z[pp, tt] for pp in model.p for tt in model.t) <= model.bd[cc]\n"
    "model.cdc = Constraint(model.cc, rule=cdc_rule)"
)
CS = (
    "def cs_rule(model, cr):\n"
    "    theta = 5.0\n"
    "    return theta * sum(model.us[cr, tt] for tt in model.t) <= model.bs[cr]\n"
    "model.cs = Constraint(model.crs, rule=cs_rule)"
)
MRWB = (
    "def mrwb_rule(model, cr, tt):\n"
    "    return model.ur[cr, tt] == sum(model.uur[cr, ix, tt] for ix in model.i)\n"
    "model.mrwb = Constraint(model.crr, model.t, rule=mrwb_rule)"
)
MGWB = (
    "def mgwb_rule(model, cr):\n"
    "    return model.ug[cr] == sum(model.uug[cr, ix] for ix in model.i)\n"
    "model.mgwb = Constraint(model.crg, rule=mgwb_rule)"
)
CAE = (
    "def cae_rule(model, e, tt):\n"
    "    ebm = 0.5480148709315376\n"
    "    return ebm * sum(model.a[e, pp] * model.z[pp, tt] for pp in model.p) + model.bc[e] <= model.esa[e]\n"
    "model.cae = Constraint(model.er, model.t, rule=cae_rule)"
)
CPU = (
    "def cpu_rule(model, mm, tt):\n"
    "    TF = ['1985-89', '1990-94', '1995-99', '2000-04', '2005-09']\n"
    "    ord_tf = {p: k + 1 for k, p in enumerate(TF)}\n"
    "    return (sum(model.b[mm, pp] * model.z[pp, tt] for pp in model.p)\n"
    "            <= sum(model.h[mm, tf] for tf in TF if ord_tf[tf] < ord_tf[tt]))\n"
    "model.cpu = Constraint(model.m, model.t, rule=cpu_rule)"
)
CIND = (
    "def cind_rule(model, tt):\n"
    "    newcap = {'1990-94': 66.0, '1995-99': 82.5, '2000-04': 99.0, '2005-09': 99.0}\n"
    "    T = ['1990-94', '1995-99', '2000-04', '2005-09']\n"
    "    k = T.index(tt)\n"
    "    rhs = newcap[tt]\n"
    "    if k >= 1:\n"
    "        rhs = rhs + model.x['syncrude', T[k - 1]]\n"
    "    return model.x['syncrude', tt] <= rhs\n"
    "model.cind = Constraint(model.t, rule=cind_rule)"
)
AREV = (
    "def arev_rule(model, tt):\n"
    "    return model.r[tt] == sum(model.pf[cc, tt] * model.x[cc, tt] for cc in model.cf)\n"
    "model.arev = Constraint(model.t, rule=arev_rule)"
)
AROY = (
    "def aroy_rule(model, tt):\n"
    "    return model.phiy[tt] == model.ps * sum(model.a['syncrude', pp] * model.z[pp, tt] for pp in model.p)\n"
    "model.aroy = Constraint(model.t, rule=aroy_rule)"
)
ARW = (
    "def arw_rule(model, tt):\n"
    "    bbr = {'sur-water': 1269.8632, 'mo-water': 1707.64}\n"
    "    drd = {('sur-water', 'i1', '1990-94'): 263.8222893313816, ('sur-water', 'i1', '1995-99'): 336.711523650183, ('sur-water', 'i1', '2000-04'): 429.7387095160112, ('sur-water', 'i1', '2005-09'): 548.4675916478286, ('sur-water', 'i2', '1990-94'): 631.5745714296711, ('sur-water', 'i2', '1995-99'): 806.0669808595292, ('sur-water', 'i2', '2000-04'): 1028.768425811057, ('sur-water', 'i2', '2005-09'): 1312.9981739448017, ('sur-water', 'i3', '1990-94'): 999.3268535279608, ('sur-water', 'i3', '1995-99'): 1275.4224380688752, ('sur-water', 'i3', '2000-04'): 1627.798142106103, ('sur-water', 'i3', '2005-09'): 2077.528756241775, ('sur-water', 'i4', '1990-94'): 1367.0791356262503, ('sur-water', 'i4', '1995-99'): 1744.777895278221, ('sur-water', 'i4', '2000-04'): 2226.82785840115, ('sur-water', 'i4', '2005-09'): 2842.0593385387483, ('sur-water', 'i5', '1990-94'): 1734.8314177245397, ('sur-water', 'i5', '1995-99'): 2214.1333524875654, ('sur-water', 'i5', '2000-04'): 2825.8575746961933, ('sur-water', 'i5', '2005-09'): 3606.5899208357196, ('mo-water', 'i1', '1990-94'): 2419999.7580000004, ('mo-water', 'i1', '1995-99'): 2419999.7580000004, ('mo-water', 'i1', '2000-04'): 2419999.7580000004, ('mo-water', 'i1', '2005-09'): 2419999.7580000004, ('mo-water', 'i2', '1990-94'): 2859999.7140000006, ('mo-water', 'i2', '1995-99'): 2859999.7140000006, ('mo-water', 'i2', '2000-04'): 2859999.7140000006, ('mo-water', 'i2', '2005-09'): 2859999.7140000006, ('mo-water', 'i3', '1990-94'): 3299999.669999998, ('mo-water', 'i3', '1995-99'): 3299999.669999998, ('mo-water', 'i3', '2000-04'): 3299999.669999998, ('mo-water', 'i3', '2005-09'): 3299999.669999998, ('mo-water', 'i4', '1990-94'): 3739999.626000002, ('mo-water', 'i4', '1995-99'): 3739999.626000002, ('mo-water', 'i4', '2000-04'): 3739999.626000002, ('mo-water', 'i4', '2005-09'): 3739999.626000002, ('mo-water', 'i5', '1990-94'): 4179999.5820000004, ('mo-water', 'i5', '1995-99'): 4179999.5820000004, ('mo-water', 'i5', '2000-04'): 4179999.5820000004, ('mo-water', 'i5', '2005-09'): 4179999.5820000004}\n"
    "    return model.phir[tt] == sum(\n"
    "        sum(drd[(cr, ix, tt)] * model.uur[cr, ix, tt] for ix in model.i) / bbr[cr]\n"
    "        for cr in model.crr)\n"
    "model.arw = Constraint(model.t, rule=arw_rule)"
)
AGW = (
    "def agw_rule(model):\n"
    "    bbg = {'grnd-water': 31048.0}\n"
    "    dgd = {('grnd-water', 'i1'): 1290.0, ('grnd-water', 'i2'): 3670.0, ('grnd-water', 'i3'): 6050.0, ('grnd-water', 'i4'): 8430.0, ('grnd-water', 'i5'): 10810.0}\n"
    "    return model.phig == sum(\n"
    "        sum(model.uug[cr, ix] * dgd[(cr, ix)] for ix in model.i) / bbg[cr]\n"
    "        for cr in model.crg)\n"
    "model.agw = Constraint(rule=agw_rule)"
)
ACAP = (
    "def acap_rule(model, tt):\n"
    "    sigma = 0.21128454461159624\n"
    "    nu = {'mine-25': 25.454036373817978, 'mine-30': 25.454036373817978, 'mine-35': 25.454036373817978, 'retort-25': 33.09024728596337, 'retort-30': 33.09024728596337, 'retort-35': 33.09024728596337, 'h2o-s-eq': 0.9053247580972247, 'h2o-g-eq': 1.8106495161944494, 'h2o-m-eq': 0.9053247580972247, 'upgrader': 39.70896384040662, 'disp-c-eq': 0.6060606060606061, 'disp-u-eq': 0.30303030303030304, 'disp-d-eq': 1.2121212121212122, 'misc-eq': 46.18181818181818, 'part-50-eq': 0.06073913452807211, 'so2-50-eq': 0.020607238653203613, 'part-90-eq': 0.20430436159442436, 'so2-90-eq': 0.06697352562291174, 'part-95-eq': 0.26504349612249645, 'so2-95-eq': 0.08758076427611536, 'part-99-eq': 0.4086087231888487, 'so2-99-eq': 0.13394705124582348, 'p-99pt5-eq': 0.46934785771692084, 's-99pt5-eq': 0.15455428989902711}\n"
    "    TF = ['1985-89', '1990-94', '1995-99', '2000-04', '2005-09']\n"
    "    ord_tf = {p: k + 1 for k, p in enumerate(TF)}\n"
    "    return model.phik[tt] == sigma * sum(\n"
    "        nu[mm] * model.h[mm, tf]\n"
    "        for mm in model.m for tf in TF if ord_tf[tf] < ord_tf[tt])\n"
    "model.acap = Constraint(model.t, rule=acap_rule)"
)
AOPC = (
    "def aopc_rule(model, tt):\n"
    "    opc = {'mining-25': 2.08, 'mining-30': 2.08, 'mining-35': 2.08, 'ret-25': 2.7, 'ret-30': 2.7, 'ret-35': 2.7, 'buy-h2o-s': 0.07, 'buy-h2o-m': 0.07, 'buy-h2o-g': 0.14, 'upgrading': 3.18, 'dispose-c': 0.4, 'dispose-u': 0.21, 'dispose-d': 1.86, 'miscell': 4.07, 'part-50': 0.01, 'so2-50': 0.01, 'part-90': 0.03, 'so2-90': 0.03, 'part-95': 0.04, 'so2-95': 0.04, 'part-99': 0.06, 'so2-99': 0.06, 'part-99pt5': 0.07, 'so2-99pt5': 0.07}\n"
    "    return model.phio[tt] == sum(opc.get(pp, 0.0) * model.z[pp, tt] for pp in model.p)\n"
    "model.aopc = Constraint(model.t, rule=aopc_rule)"
)
APROF = (
    "def aprof_rule(model):\n"
    "    theta = 5.0\n"
    "    delf = {'1985-89': 0.49717673529828993, '1990-94': 0.24718470612186585, '1995-99': 0.12289448520533648, '2000-04': 0.06110027894055318, '2005-09': 0.030377637209479086}\n"
    "    return model.pi == theta * sum(\n"
    "        delf[tt] * (model.r[tt] - model.phir[tt] - model.phio[tt] - model.phiy[tt] - model.phik[tt])\n"
    "        for tt in model.t) - model.phig\n"
    "model.aprof = Constraint(rule=aprof_rule)"
)

ALL = [MSU, MRW, MGW, MI, MF, MNMR, MMR3, MMR4, CDC, CS, MRWB, MGWB,
       CAE, CPU, CIND, AREV, AROY, ARW, AGW, ACAP, AOPC, APROF]
WHOLESET = "\n".join(ALL)

# ── per-constraint Tier-1 descriptions (plain, symbolically silent) ──
DESCRIPTIONS = [
    # msu
    "For each shale grade in each operating period, the net amount of that shale produced across all processes must exactly offset the amount of that shale purchased, so that everything consumed is accounted for by purchases.",
    # mrw
    "For each renewable water source in each operating period, the net amount of that water produced across all processes must exactly offset the amount of that water purchased that period.",
    # mgw
    "For groundwater, the net amount produced across all processes summed over every operating period must exactly offset the total groundwater purchased over the whole horizon.",
    # mi
    "For each intermediate commodity in each operating period, the net amount produced across all processes must balance to zero, since these streams are neither bought nor sold.",
    # mf
    "For each final product in each operating period, the net amount produced across all processes must equal the output quantity recorded for that product that period.",
    # mnmr
    "No mine backfilling is allowed during the first two operating periods, so the level of the backfill disposal process must be zero in each of those two periods.",
    # mmr3
    "In the third operating period, the amount of mine backfilling done cannot exceed a fixed fraction of the amount mined in the first operating period.",
    # mmr4
    "In the fourth operating period, the amount of mine backfilling done cannot exceed a fixed fraction of the total amount mined in the first two operating periods, after deducting whatever backfilling was already done in the third period.",
    # cdc
    "For canyon disposal space, the total spoils sent to the canyons across all processes and all operating periods, scaled by the length of a period, must not exceed the available canyon space.",
    # cs
    "For each shale grade, the total purchased over all operating periods, scaled by the length of a period, must not exceed the recoverable amount of that grade available over the whole horizon.",
    # mrwb
    "For each renewable water source in each operating period, the total purchased that period must equal the sum of the amounts taken from each segment of that source's piecewise cost curve.",
    # mgwb
    "For groundwater, the total purchased over the horizon must equal the sum of the amounts taken from each segment of its piecewise cost curve.",
    # cae
    "For each regulated emission in each operating period, the ambient concentration produced by the project's processes, added to the existing background concentration, must stay within that emission's air-quality standard.",
    # cpu
    "For each productive unit in each operating period, the capacity needed to run all the processes that period cannot exceed the total capacity that has been installed in that unit through investments made in all earlier expansion periods.",
    # cind
    "For syncrude output, the amount produced in each operating period cannot exceed the amount produced in the immediately preceding period plus the additional syncrude capacity allowed to come online that period. In the first operating period there is no preceding period to carry over.",
    # arev
    "For each operating period, sales revenue is defined as the sum over all final products of that product's selling price times its output quantity.",
    # aroy
    "For each operating period, the shale royalty cost is defined as the royalty rate per barrel times the net syncrude produced across all processes that period.",
    # arw
    "For each operating period, the renewable water cost is defined by charging each segment of each source's piecewise cost curve at its own incremental rate for the amount taken from that segment, normalized by the segment width, and summing over all segments and sources.",
    # agw
    "The total groundwater cost is defined by charging each segment of the groundwater piecewise cost curve at its own incremental rate for the amount taken from that segment, normalized by the segment width, and summing over all segments.",
    # acap
    "For each operating period, the cost of capital is defined as a discounting factor times the sum, over every productive unit and every earlier expansion period, of that unit's per-capacity capital charge times the investment made.",
    # aopc
    "For each operating period, the other operating cost is defined as the sum over all processes of that process's unit operating cost times its operating level that period.",
    # aprof
    "Total discounted profit is defined by taking, in each operating period, the sales revenue less the renewable water, operating, royalty, and capital costs, discounting each period to present value and scaling by the period length, summing over all operating periods, and then subtracting the total groundwater cost.",
]

# ── whole-set ordinal narrative ──
WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for each shale grade in each operating period, balance the net shale produced "
    "across all processes against the shale purchased that period. "
    "Second, do the same renewable-water balance for each water source in each operating period. "
    "Third, balance the net groundwater produced across all processes and all operating periods "
    "against the total groundwater purchased over the horizon. "
    "Fourth, require each intermediate commodity to net to zero in each operating period. "
    "Fifth, set each final product's net production equal to its recorded output in each operating period. "
    "Sixth, forbid any mine backfilling in the first two operating periods. "
    "Seventh, cap third-period backfilling at a fixed fraction of first-period mining. "
    "Eighth, cap fourth-period backfilling at a fixed fraction of the first two periods' mining, "
    "net of the backfilling already done in the third period. "
    "Ninth, keep total spoils sent to the canyons, scaled by period length, within available canyon space. "
    "Tenth, keep each shale grade's total purchases, scaled by period length, within its recoverable amount. "
    "Eleventh, make each renewable-water period purchase equal the sum of its piecewise-curve segment amounts. "
    "Twelfth, make total groundwater purchase equal the sum of its piecewise-curve segment amounts. "
    "Thirteenth, keep each emission's project concentration plus background within its air-quality standard "
    "in each operating period. "
    "Fourteenth, limit each productive unit's period capacity demand to the capacity installed by all earlier "
    "expansion periods. "
    "Fifteenth, cap syncrude output each period at the prior period's output plus the new capacity allowed that period. "
    "Sixteenth, define each period's sales revenue as price times output summed over final products. "
    "Seventeenth, define each period's royalty cost from the royalty rate and net syncrude produced. "
    "Eighteenth, define each period's renewable water cost from the segmented water-curve charges. "
    "Nineteenth, define the total groundwater cost from the segmented groundwater-curve charges. "
    "Twentieth, define each period's capital cost from the discounted per-unit capital charges on earlier investments. "
    "Twenty-first, define each period's other operating cost from unit operating costs times process levels. "
    "Finally, define total discounted profit as the period-by-period discounted net of revenue minus renewable water, "
    "operating, royalty, and capital costs, summed and then reduced by the total groundwater cost."
)

records = [{"description": d, "expected_pyomo": c} for d, c in zip(DESCRIPTIONS, ALL)]
records.append({"description": WHOLESET_DESC, "expected_pyomo": WHOLESET})

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "shale_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
