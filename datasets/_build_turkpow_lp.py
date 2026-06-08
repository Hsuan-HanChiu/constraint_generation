#!/usr/bin/env python
"""Builder for the turkpow_lp (Turkey power capacity-expansion) constraint-generation dataset.

All 11 constraints are linear and Z3-gradable. The grading harness execs each
expected_pyomo block in a bare namespace (only model/Constraint/sum/pyo/value),
so every rule RECONSTRUCTS its derived quantities (vintage/merit-order masks,
grown demand, durations, discount/recovery factors, escalated costs, vintaged
initial capacity) from the base sets and params alone. Nothing relies on module
globals.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "turkpow_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "time", "members": [1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005],
         "doc": "every calendar year of the full planning span from 1975 to 2005, in chronological order; used to count how many years separate two dates, where the count is the position of the year within this span measured from the very first year"},
        {"name": "te", "members": [1975, 1978, 1983, 1988, 1993, 1998, 2005],
         "doc": "the extended list of milestone years including the base year 1975, in chronological order"},
        {"name": "t", "members": [1978, 1983, 1988, 1993, 1998, 2005],
         "doc": "the milestone decision years excluding the base year, in chronological order; these are the years at which capacity may be added and at which the system must be checked; a year counts as on-or-after another when it is at the same position or later in this ordered list"},
        {"name": "b", "members": ["peak", "high", "medium", "low"],
         "doc": "the load blocks of the annual load-duration curve, listed from the highest-demand block to the lowest; 'peak' is the first block; a block is said to lie at-or-below another in this merit ordering when it appears at the same position or later in this list"},
        {"name": "mh", "members": ["hydro-1", "hydro-2", "hydro-3", "hydro-4", "hydro-5", "hydro-6", "hydro-7", "hydro-8", "hydro-9", "hydro-10", "hydro-11", "hydro-12", "hydro-13"],
         "doc": "the candidate hydro plants"},
        {"name": "mt", "members": ["gas-t", "oil", "lignite-1", "lignite-2", "lignite-3", "nuclear"],
         "doc": "the candidate thermal plant types"},
    ],
    "params": [
        {"name": "mdatah_initcap", "index": "mh", "kind": "capacity",
         "doc": "hydro plant capacity already in place at the start, in MW"},
        {"name": "mdatah_avail", "index": "mh", "kind": "availability",
         "doc": "hydro plant availability fraction, the share of installed capacity that can be counted on at any moment"},
        {"name": "mdatah_efact", "index": "mh", "kind": "factor",
         "doc": "hydro plant energy factor, the fraction of installed capacity that bounds the plant's average sustained output over the year"},
        {"name": "mdatah_opcost", "index": "mh", "kind": "cost",
         "doc": "hydro plant operating cost, in million TL per MW-year of energy delivered"},
        {"name": "mdatah_capcost", "index": "mh", "kind": "cost",
         "doc": "hydro plant capital cost, in million TL per MW of new capacity"},
        {"name": "mdatah_life", "index": "mh", "kind": "lifetime",
         "doc": "hydro plant economic life, in years"},
        {"name": "mdatah_maxcap", "index": "mh", "kind": "capacity",
         "doc": "the most new hydro capacity that may ever be built at a given hydro plant over the whole horizon, in MW"},
        {"name": "mdatat_initcap", "index": "mt", "kind": "capacity",
         "doc": "thermal capacity already in place at the start, in MW; this existing stock is treated as a vintage commissioned in the first decision year 1978"},
        {"name": "mdatat_avail", "index": "mt", "kind": "availability",
         "doc": "thermal plant availability fraction, the share of installed capacity that can be counted on at any moment"},
        {"name": "mdatat_opcost", "index": "mt", "kind": "cost",
         "doc": "thermal operating cost at base-year prices, in million TL per MW-year of energy delivered"},
        {"name": "mdatat_opcostg", "index": "mt", "kind": "rate",
         "doc": "the annual growth rate applied to thermal operating cost; the operating cost of a vintage is its base cost compounded by this rate over the number of years from the base year to the vintage's commissioning year"},
        {"name": "mdatat_capcost", "index": "mt", "kind": "cost",
         "doc": "thermal capital cost at base-year prices, in million TL per MW"},
        {"name": "mdatat_capcostg", "index": "mt", "kind": "rate",
         "doc": "the annual growth rate applied to thermal capital cost; the capital cost of a vintage is its base cost compounded by this rate over the number of years from the base year to the vintage's commissioning year"},
        {"name": "mdatat_life", "index": "mt", "kind": "lifetime",
         "doc": "thermal plant economic life, in years"},
        {"name": "mdatat_maxcap", "index": "mt", "kind": "capacity",
         "doc": "the most new thermal capacity that may be built for a given type, in MW; unbounded for types with no listed limit"},
        {"name": "dd_duration", "index": "b", "kind": "duration",
         "doc": "the number of hours per year that the system spends in each load block"},
        {"name": "dd_demand", "index": "b", "kind": "demand",
         "doc": "the power demand of each load block in the base year 1975, in MW; the demand of any later year is this base demand grown by the demand growth rate over the number of years from 1975, rounded to the nearest MW"},
        {"name": "rho", "index": "", "kind": "rate",
         "doc": "the discount (interest) rate per year"},
        {"name": "prr", "index": "", "kind": "fraction",
         "doc": "the planning reserve margin, the fraction of peak demand that available capacity must exceed"},
        {"name": "r", "index": "", "kind": "fraction",
         "doc": "the largest share of peak demand that aggregate hydro capacity is allowed to cover"},
        {"name": "g", "index": "", "kind": "rate",
         "doc": "the annual demand growth rate"},
    ],
    "vars": [
        {"name": "phi", "index": "", "domain": "Reals",
         "doc": "the total discounted system cost over the horizon, in million TL"},
        {"name": "phic", "index": "te", "domain": "Reals",
         "doc": "the capital charges incurred in each milestone year, in million TL"},
        {"name": "phio", "index": "te", "domain": "Reals",
         "doc": "the operating costs incurred in each milestone year, in million TL"},
        {"name": "hh", "index": "mh, te", "domain": "NonNegativeReals",
         "doc": "new hydro capacity added at a given hydro plant in a given milestone year, in MW"},
        {"name": "ht", "index": "mt, t", "domain": "NonNegativeReals",
         "doc": "new thermal capacity added for a given type in a given decision year, in MW; the year at which it is added is that vintage's commissioning year"},
        {"name": "htt", "index": "mt", "domain": "Reals",
         "doc": "total new thermal capacity built for a given type across the whole horizon, in MW"},
        {"name": "zh", "index": "mh, b, t", "domain": "NonNegativeReals",
         "doc": "hydro power output of a given plant in a given load block in a given year, in MW"},
        {"name": "zt", "index": "mt, t, b, t", "domain": "NonNegativeReals",
         "doc": "thermal power output indexed by type, then the vintage's commissioning year, then the load block, then the operating year, in MW; a vintage can only produce in years at or after its commissioning year"},
    ],
    "objective": {"sense": "minimize", "expr_var": "phi"},
}

NARRATIVE = (
    "We plan how Turkey's electricity system expands over a sequence of milestone years "
    "stretching to 2005. For each milestone year we decide how much new hydro and thermal "
    "generating capacity to build at each candidate plant, and for every load block of the "
    "year we decide how much power each existing and newly built plant should produce. "
    "Capacity once built stays available in all later years, and demand grows year over year. "
    "The objective is to make the total discounted cost of building and operating the system "
    "over the whole horizon as small as possible."
)

# ── Per-constraint expected Pyomo (self-contained: rebuilds all derived data) ──

DB = (
    "def db_rule(model, bb, tt):\n"
    "    time_list = list(model.time)\n"
    "    length = {yr: i for i, yr in enumerate(time_list)}\n"
    "    g = pyo.value(model.g)\n"
    "    B = list(model.b); T = list(model.t)\n"
    "    ordb = {x: i + 1 for i, x in enumerate(B)}\n"
    "    ordt = {x: i + 1 for i, x in enumerate(T)}\n"
    "    demand = round(pyo.value(model.dd_demand[bb]) * (1 + g) ** length[tt])\n"
    "    return (sum(model.zh[mhh, bbp, tt] for mhh in model.mh for bbp in B if ordb[bbp] >= ordb[bb])\n"
    "            + sum(model.zt[mtt, vv, bbp, tt] for mtt in model.mt for vv in T for bbp in B\n"
    "                  if ordb[bbp] >= ordb[bb] and ordt[tt] >= ordt[vv])) >= demand\n"
    "model.db = Constraint(model.b, model.t, rule=db_rule)"
)

PR = (
    "def pr_rule(model, tt):\n"
    "    time_list = list(model.time)\n"
    "    length = {yr: i for i, yr in enumerate(time_list)}\n"
    "    g = pyo.value(model.g); prr = pyo.value(model.prr)\n"
    "    T = list(model.t)\n"
    "    ordt = {x: i + 1 for i, x in enumerate(T)}\n"
    "    peak_demand = round(pyo.value(model.dd_demand['peak']) * (1 + g) ** length[tt])\n"
    "    kit = lambda mtt, vv: pyo.value(model.mdatat_initcap[mtt]) if vv == T[0] else 0.0\n"
    "    lhs = (sum(pyo.value(model.mdatah_avail[mhh]) * (pyo.value(model.mdatah_initcap[mhh])\n"
    "                + sum(model.hh[mhh, vv] for vv in T if ordt[tt] >= ordt[vv])) for mhh in model.mh)\n"
    "           + sum(pyo.value(model.mdatat_avail[mtt]) * sum(kit(mtt, vv) + model.ht[mtt, vv]\n"
    "                for vv in T if ordt[tt] >= ordt[vv]) for mtt in model.mt))\n"
    "    return lhs >= (1 + prr) * peak_demand\n"
    "model.pr = Constraint(model.t, rule=pr_rule)"
)

CCH = (
    "def cch_rule(model, mhh, tt):\n"
    "    T = list(model.t)\n"
    "    ordt = {x: i + 1 for i, x in enumerate(T)}\n"
    "    return (sum(model.zh[mhh, bb, tt] for bb in model.b)\n"
    "            <= pyo.value(model.mdatah_avail[mhh]) * (pyo.value(model.mdatah_initcap[mhh])\n"
    "               + sum(model.hh[mhh, vv] for vv in T if ordt[tt] >= ordt[vv])))\n"
    "model.cch = Constraint(model.mh, model.t, rule=cch_rule)"
)

CCT = (
    "def cct_rule(model, mtt, vv, tt):\n"
    "    T = list(model.t)\n"
    "    ordt = {x: i + 1 for i, x in enumerate(T)}\n"
    "    if ordt[tt] < ordt[vv]:\n"
    "        return Constraint.Skip\n"
    "    kit = pyo.value(model.mdatat_initcap[mtt]) if vv == T[0] else 0.0\n"
    "    return sum(model.zt[mtt, vv, bb, tt] for bb in model.b) <= pyo.value(model.mdatat_avail[mtt]) * (kit + model.ht[mtt, vv])\n"
    "model.cct = Constraint(model.mt, model.t, model.t, rule=cct_rule)"
)

ECH = (
    "def ech_rule(model, mhh, tt):\n"
    "    T = list(model.t); B = list(model.b)\n"
    "    ordb = {x: i + 1 for i, x in enumerate(B)}\n"
    "    ordt = {x: i + 1 for i, x in enumerate(T)}\n"
    "    totdur = sum(pyo.value(model.dd_duration[bbp]) for bbp in B)\n"
    "    dur = {bb: sum(pyo.value(model.dd_duration[bbp]) for bbp in B if ordb[bb] >= ordb[bbp]) / totdur for bb in B}\n"
    "    return (sum(dur[bb] * model.zh[mhh, bb, tt] for bb in B)\n"
    "            <= pyo.value(model.mdatah_efact[mhh]) * (pyo.value(model.mdatah_initcap[mhh])\n"
    "               + sum(model.hh[mhh, vv] for vv in T if ordt[tt] >= ordt[vv])))\n"
    "model.ech = Constraint(model.mh, model.t, rule=ech_rule)"
)

HCC = (
    "def hcc_rule(model, tt):\n"
    "    time_list = list(model.time)\n"
    "    length = {yr: i for i, yr in enumerate(time_list)}\n"
    "    g = pyo.value(model.g); r = pyo.value(model.r)\n"
    "    T = list(model.t)\n"
    "    ordt = {x: i + 1 for i, x in enumerate(T)}\n"
    "    peak_demand = round(pyo.value(model.dd_demand['peak']) * (1 + g) ** length[tt])\n"
    "    return (sum(pyo.value(model.mdatah_initcap[mhh]) + sum(model.hh[mhh, vv] for vv in T if ordt[tt] >= ordt[vv]) for mhh in model.mh)\n"
    "            <= r * peak_demand)\n"
    "model.hcc = Constraint(model.t, rule=hcc_rule)"
)

RCH = (
    "def rch_rule(model, mhh):\n"
    "    return sum(model.hh[mhh, tt] for tt in model.t) <= pyo.value(model.mdatah_maxcap[mhh])\n"
    "model.rch = Constraint(model.mh, rule=rch_rule)"
)

CAT = (
    "def cat_rule(model, mtt):\n"
    "    return model.htt[mtt] == sum(model.ht[mtt, vv] for vv in model.t)\n"
    "model.cat = Constraint(model.mt, rule=cat_rule)"
)

AK = (
    "def ak_rule(model, tt):\n"
    "    time_list = list(model.time)\n"
    "    length = {yr: i for i, yr in enumerate(time_list)}\n"
    "    rho = pyo.value(model.rho)\n"
    "    T = list(model.t)\n"
    "    ordt = {x: i + 1 for i, x in enumerate(T)}\n"
    "    sigma_h = {mhh: rho / (1 - (1 + rho) ** (-pyo.value(model.mdatah_life[mhh]))) for mhh in model.mh}\n"
    "    sigma_t = {mtt: rho / (1 - (1 + rho) ** (-pyo.value(model.mdatat_life[mtt]))) for mtt in model.mt}\n"
    "    def capcostt(mtt, vv):\n"
    "        cc = pyo.value(model.mdatat_capcost[mtt]); ccg = pyo.value(model.mdatat_capcostg[mtt])\n"
    "        return cc * (1 + ccg) ** length[vv] if ordt[tt] >= ordt[vv] else 0.0\n"
    "    return model.phic[tt] == (\n"
    "        sum(sigma_h[mhh] * pyo.value(model.mdatah_capcost[mhh]) * sum(model.hh[mhh, vv] for vv in T if ordt[tt] >= ordt[vv]) for mhh in model.mh)\n"
    "        + sum(sigma_t[mtt] * sum(capcostt(mtt, vv) * model.ht[mtt, vv] for vv in T) for mtt in model.mt))\n"
    "model.ak = Constraint(model.t, rule=ak_rule)"
)

AO = (
    "def ao_rule(model, tt):\n"
    "    time_list = list(model.time)\n"
    "    length = {yr: i for i, yr in enumerate(time_list)}\n"
    "    T = list(model.t); B = list(model.b)\n"
    "    ordb = {x: i + 1 for i, x in enumerate(B)}\n"
    "    ordt = {x: i + 1 for i, x in enumerate(T)}\n"
    "    totdur = sum(pyo.value(model.dd_duration[bbp]) for bbp in B)\n"
    "    dur = {bb: sum(pyo.value(model.dd_duration[bbp]) for bbp in B if ordb[bb] >= ordb[bbp]) / totdur for bb in B}\n"
    "    def opcostt(mtt, vv):\n"
    "        oc = pyo.value(model.mdatat_opcost[mtt]); ocg = pyo.value(model.mdatat_opcostg[mtt])\n"
    "        return oc * (1 + ocg) ** length[vv]\n"
    "    return model.phio[tt] == (\n"
    "        sum(pyo.value(model.mdatah_opcost[mhh]) * sum(dur[bb] * model.zh[mhh, bb, tt] for bb in B) for mhh in model.mh)\n"
    "        + sum(opcostt(mtt, vv) * sum(dur[bb] * model.zt[mtt, vv, bb, tt] for bb in B)\n"
    "              for mtt in model.mt for vv in T if ordt[tt] >= ordt[vv]))\n"
    "model.ao = Constraint(model.t, rule=ao_rule)"
)

OBJDEF = (
    "def objdef_rule(model):\n"
    "    time_list = list(model.time)\n"
    "    length = {yr: i for i, yr in enumerate(time_list)}\n"
    "    rho = pyo.value(model.rho)\n"
    "    T = list(model.t)\n"
    "    delta = {tt: (1 + rho) ** (-length[tt]) for tt in T}\n"
    "    return model.phi == sum(delta[tt] * (model.phic[tt] + model.phio[tt]) for tt in T)\n"
    "model.objdef = Constraint(rule=objdef_rule)"
)

WHOLESET = "\n".join([DB, PR, CCH, CCT, ECH, HCC, RCH, CAT, AK, AO, OBJDEF])

# ── Per-constraint Tier-1 descriptions (semantically complete, symbolically silent) ──

DESC_DB = (
    "For every load block in every decision year, the total power produced across all "
    "generators must be enough to meet that block's demand. Because the load blocks are "
    "stacked from the heaviest block down, the production that serves a given block is the "
    "output of every plant in that block together with the output it carries in all the "
    "lighter blocks beneath it, and only generating vintages that have already been "
    "commissioned by that year may contribute. Demand for the year is the base-year demand "
    "of the block grown forward at the demand growth rate."
)
DESC_PR = (
    "For every decision year, the system must hold enough firm capacity to cover peak demand "
    "with a reserve margin on top. Each plant's contribution is its availability fraction "
    "applied to the capacity it has in place that year, which is its starting capacity plus "
    "every addition commissioned up to and including that year, where the existing thermal "
    "stock counts as a first-year vintage. The sum of these firm contributions across all "
    "hydro and thermal plants must be at least the peak demand inflated by the reserve margin, "
    "with peak demand grown from the base year at the demand growth rate."
)
DESC_CCH = (
    "For every hydro plant in every decision year, the plant cannot generate more than the "
    "capacity it actually has available. Adding up the plant's output over all load blocks in "
    "that year, the total may not exceed its availability fraction times the capacity in place "
    "that year, namely its starting capacity plus all additions commissioned up to and "
    "including that year."
)
DESC_CCT = (
    "For every thermal vintage in every decision year at or after the year that vintage was "
    "commissioned, the vintage cannot generate more than the capacity it has available. Adding "
    "up that vintage's output over all load blocks in the year, the total may not exceed its "
    "availability fraction times its installed capacity, which is the amount built for that "
    "vintage plus, for the very first vintage only, the pre-existing thermal stock of that type."
)
DESC_ECH = (
    "For every hydro plant in every decision year, the energy the plant delivers over the year "
    "is limited by its energy factor, not just its instantaneous capacity. Weighting the plant's "
    "output in each load block by the share of the year that the block and all lighter blocks "
    "below it occupy, the weighted total may not exceed the plant's energy factor times the "
    "capacity it has in place that year, namely its starting capacity plus all additions "
    "commissioned up to and including that year."
)
DESC_HCC = (
    "For every decision year, hydro must not dominate the system. The combined capacity of all "
    "hydro plants in place that year, counting their starting capacity plus every addition "
    "commissioned up to and including that year, may not exceed an allowed share of that year's "
    "peak demand, with peak demand grown from the base year at the demand growth rate."
)
DESC_RCH = (
    "For every hydro plant, the total of all new capacity built at that plant across all "
    "decision years may not exceed the most new capacity that plant is ever allowed to add."
)
DESC_CAT = (
    "For every thermal type, the recorded total new capacity equals the sum of the capacity "
    "additions made for that type across all decision years."
)
DESC_AK = (
    "For every decision year, the capital charges of that year are defined as the annualized "
    "cost of all capacity standing that year. For each hydro plant, take its capital recovery "
    "factor times its capital cost applied to the capacity it has commissioned up to and "
    "including that year. For each thermal type, take its capital recovery factor applied to "
    "its additions, with each vintage's addition valued at that vintage's escalated capital "
    "cost, which is the base capital cost compounded at its capital cost growth rate over the "
    "years from the base year to the vintage's commissioning year, counting only vintages "
    "commissioned up to and including that year. The capital recovery factor spreads a plant's "
    "capital cost over its economic life at the discount rate. Set the year's capital charges "
    "equal to the sum of all these terms."
)
DESC_AO = (
    "For every decision year, the operating costs of that year are defined from the energy each "
    "plant delivers. For each hydro plant, value its duration-weighted output across the load "
    "blocks at its operating cost. For each thermal vintage commissioned up to and including the "
    "year, value its duration-weighted output across the load blocks at that vintage's escalated "
    "operating cost, which is the base operating cost compounded at its operating cost growth "
    "rate over the years from the base year to the vintage's commissioning year. The "
    "duration weight of a block is the share of the year occupied by that block together with "
    "all lighter blocks below it. Set the year's operating costs equal to the sum of all these "
    "terms."
)
DESC_OBJDEF = (
    "The total discounted cost is defined by bringing every year's costs back to present value. "
    "For each decision year, discount that year's capital charges and operating costs together "
    "by the discount factor for that year, which compounds the discount rate over the years from "
    "the base year. Set the total discounted cost equal to the sum of these discounted yearly "
    "costs over all decision years."
)

per = [
    (DESC_DB, DB), (DESC_PR, PR), (DESC_CCH, CCH), (DESC_CCT, CCT),
    (DESC_ECH, ECH), (DESC_HCC, HCC), (DESC_RCH, RCH), (DESC_CAT, CAT),
    (DESC_AK, AK), (DESC_AO, AO), (DESC_OBJDEF, OBJDEF),
]

# ── Whole-set ordinal narrative (composes per-constraint intents, in order) ──
WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for every load block in every decision year, require that the total power produced "
    "across all generators, accounting for the way load blocks stack from heaviest down and "
    "counting only already-commissioned vintages, meets that block's grown demand. "
    "Second, for every decision year, require that the firm capacity from every plant, each "
    "plant's availability applied to its in-place capacity that year, covers peak demand "
    "inflated by the reserve margin. "
    "Third, for every hydro plant in every decision year, cap the plant's total output across "
    "load blocks at its availability times the capacity it has in place that year. "
    "Fourth, for every thermal vintage in every year at or after its commissioning, cap that "
    "vintage's total output across load blocks at its availability times its installed capacity, "
    "where the first vintage also carries the pre-existing stock. "
    "Fifth, for every hydro plant in every decision year, cap the plant's duration-weighted "
    "energy across load blocks at its energy factor times its in-place capacity. "
    "Sixth, for every decision year, cap the combined in-place hydro capacity at an allowed "
    "share of that year's peak demand. "
    "Seventh, for every hydro plant, cap the total new capacity built across all years at that "
    "plant's maximum allowed new capacity. "
    "Eighth, for every thermal type, set its recorded total new capacity equal to the sum of its "
    "additions across all years. "
    "Ninth, for every decision year, define that year's capital charges as the annualized capital "
    "cost of all capacity standing that year, using each plant's capital recovery factor and each "
    "thermal vintage's escalated capital cost. "
    "Tenth, for every decision year, define that year's operating costs from each plant's "
    "duration-weighted energy valued at its operating cost, using each thermal vintage's escalated "
    "operating cost. "
    "Finally, define the total discounted cost as the sum over all decision years of that year's "
    "capital and operating costs discounted back to present value."
)

records = [{"description": d, "expected_pyomo": e} for d, e in per]
records.append({"description": WHOLESET_DESC, "expected_pyomo": WHOLESET})

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "turkpow_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
