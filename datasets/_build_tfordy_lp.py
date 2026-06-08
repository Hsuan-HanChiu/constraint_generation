#!/usr/bin/env python
"""Builder for the tfordy_lp (Antalya Forestry, dynamic) constraint-generation dataset.

12 families, all linear LP. The expected_pyomo for each constraint mirrors the
native rule from model_library/feas_model/tfordy_lp.py exactly (same helper
membership sets _wpos/_vpos, the te previous-period dict, and the Python-side
avl term selection), so the harness can strip the native constraint from the base
and re-add an equivalent.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tfordy_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "c", "members": ["pulplogs", "sawlogs", "pulp", "sawnwood", "..."],
         "doc": "all commodities in the wood economy, spanning both intermediate logs and final products"},
        {"name": "cf", "members": ["pulp", "sawnwood"],
         "doc": "the final products that are sold to market; a subset of the commodities"},
        {"name": "cl", "members": ["pulplogs", "sawlogs"],
         "doc": "the log types harvested from the forest and fed to industry; a subset of the commodities"},
        {"name": "s", "members": ["nigra", "brutia"],
         "doc": "the tree species grown"},
        {"name": "k", "members": ["good", "medium", "poor"],
         "doc": "site classes describing land quality"},
        {"name": "at", "members": ["a-10", "a-20", "...", "a-90"],
         "doc": "tree age classes of the existing forest, in years"},
        {"name": "u", "members": ["a-10", "a-20", "...", "a-90"],
         "doc": "the initial age class of an existing stand at the start of the horizon; ranges over the same age classes"},
        {"name": "p", "members": ["pulp-pl", "pulp-sl", "pulp-rs", "sawing"],
         "doc": "the wood-processing activities (processes) that convert log inputs into products"},
        {"name": "m", "members": ["pulp-mill", "saw-mill"],
         "doc": "the productive units (mills) whose capacity must be built and respected"},
        {"name": "te", "members": ["period-1", "period-2", "...", "period-9"],
         "doc": "the extended planning horizon of periods in chronological order; the first member is the opening period"},
        {"name": "t", "members": ["period-1", "period-2", "...", "period-9"],
         "doc": "the model decision horizon of periods, in chronological order; here it coincides with the extended horizon"},
        {"name": "wpos", "index": "(u, te)",
         "members": "sparse set of feasible (initial-age, period) pairs",
         "doc": "the set of feasible (initial age, period) pairs at which an existing stand of that starting age may be cut; only these combinations are admissible"},
        {"name": "vpos", "index": "(t, te)",
         "members": "sparse set of feasible (planting-period, period) pairs",
         "doc": "the set of feasible (planting period, later period) pairs; a stand planted in the first period of the pair can be managed or cut in the second; only these combinations are admissible"},
    ],
    "params": [
        {"name": "mup", "index": "", "kind": "cost",
         "doc": "the planting cost, in US dollars per hectare"},
        {"name": "muc", "index": "", "kind": "cost",
         "doc": "the cutting cost, in US dollars per cubic metre of logs"},
        {"name": "sgm", "index": "", "kind": "factor",
         "doc": "the capital recovery factor applied to convert built capacity into an annualized investment charge"},
        {"name": "scd", "index": "k", "kind": "distribution",
         "doc": "the fraction of land falling in each site class; a distribution over site classes"},
        {"name": "land", "index": "s", "kind": "endowment",
         "doc": "the land available for each species, in thousands of hectares"},
        {"name": "pc", "index": "p", "kind": "cost",
         "doc": "the unit process cost of each activity, in US dollars per cubic metre of input"},
        {"name": "pd", "index": "cf", "kind": "price",
         "doc": "the sales price of each final product, in US dollars per unit"},
        {"name": "nu", "index": "m", "kind": "cost",
         "doc": "the investment cost of building one unit of capacity at each mill, in US dollars per cubic metre of input"},
        {"name": "delt", "index": "t", "kind": "discount",
         "doc": "the discount factor applied to each period's net benefit"},
        {"name": "a", "index": "(c, p)", "kind": "io",
         "doc": "the input-output matrix: per unit of process activity, the amount of each commodity produced (positive) or consumed (negative)"},
        {"name": "b", "index": "(m, p)", "kind": "utilization",
         "doc": "the capacity utilization coefficient: input of mill capacity consumed per unit of each process activity"},
        {"name": "avl", "index": "(t, te)", "kind": "availability",
         "doc": "an availability mask over (period, period) pairs that is nonzero exactly when capacity built in the second period is live and usable in the first period; capacity once built stays available"},
        {"name": "iad", "index": "(at, s)", "kind": "distribution",
         "doc": "the initial age distribution: the proportion of each species' existing forest that starts in each age class"},
        {"name": "yw", "index": "(te, at, s, cl)", "kind": "yield",
         "doc": "the per-hectare yield of each log type from cutting existing forest of a given starting age and species in a given period, in cubic metres per hectare"},
        {"name": "yv", "index": "(t, te, s, cl, k)", "kind": "yield",
         "doc": "the per-hectare yield of each log type from managed (newly planted) forest, indexed by planting period, cutting period, species, log type, and site class, in cubic metres per hectare"},
    ],
    "vars": [
        {"name": "w", "index": "(s, k, wpos)", "domain": "NonNegativeReals",
         "doc": "the area of existing forest of a given species and site class, starting age and period, that is cut, in thousands of hectares per year; defined only over feasible (initial-age, period) pairs"},
        {"name": "v", "index": "(s, k, vpos)", "domain": "NonNegativeReals",
         "doc": "the area of managed new forest of a given species and site class, planted in one period and acted on in a later period, in thousands of hectares per year; defined only over feasible (planting-period, period) pairs"},
        {"name": "r", "index": "(cl, te)", "domain": "NonNegativeReals",
         "doc": "the supply of each log type delivered to industry in each period, in thousands of cubic metres per year"},
        {"name": "z", "index": "(p, t)", "domain": "NonNegativeReals",
         "doc": "the activity level of each process in each period, in thousands of cubic metres of input per year"},
        {"name": "h", "index": "(m, t)", "domain": "NonNegativeReals",
         "doc": "the capacity expansion built at each mill in each period, in thousands of cubic metres of input per year"},
        {"name": "x", "index": "(c, t)", "domain": "NonNegativeReals",
         "doc": "the final shipments of each commodity to market in each period, in thousands of units per year"},
        {"name": "phik", "index": "t", "domain": "Reals",
         "doc": "the investment cost incurred in each period, in thousands of US dollars per year"},
        {"name": "phir", "index": "t", "domain": "Reals",
         "doc": "the process cost incurred in each period, in thousands of US dollars per year"},
        {"name": "phix", "index": "t", "domain": "Reals",
         "doc": "the sales revenue earned in each period, in thousands of US dollars per year"},
        {"name": "phil", "index": "t", "domain": "Reals",
         "doc": "the cutting cost incurred in each period, in thousands of US dollars per year"},
        {"name": "phip", "index": "t", "domain": "Reals",
         "doc": "the planting cost incurred in each period, in thousands of US dollars per year"},
        {"name": "phi", "index": "", "domain": "Reals",
         "doc": "the total discounted net benefit over the whole horizon"},
    ],
    "objective": {"sense": "maximize", "expr_var": "phi"},
}

NARRATIVE = (
    "We plan the management of a regional forest economy over a sequence of periods. "
    "In each period we decide how much existing forest to cut and how much new forest to "
    "plant and later manage, by species and site class; how many logs of each type to deliver "
    "to industry; how intensely to run each wood-processing activity; how much new mill capacity "
    "to build; and how many units of each final product to ship to market. Each period also carries "
    "its own bookkeeping figures for investment, processing, cutting and planting costs and for sales "
    "revenue. The objective is to maximize the total discounted net benefit over the whole horizon."
)

# ── expected_pyomo strings (mirror the native rules) ──────────────────────────

EFS = (
    "def efs_rule(model, s, k, u):\n"
    "    _wpos = set(model.wpos)\n"
    "    return 10 * sum(model.w[s, k, u, t] for t in model.t if (u, t) in _wpos) \\\n"
    "        <= model.iad[u, s] * model.scd[k] * model.land[s]\n"
    "model.efs = Constraint(model.s, model.k, model.u, rule=efs_rule)"
)

PFS = (
    "def pfs_rule(model, s, k, t):\n"
    "    _wpos = set(model.wpos)\n"
    "    _vpos = set(model.vpos)\n"
    "    lhs = sum(model.v[s, k, t, te] for te in model.te if (t, te) in _vpos)\n"
    "    rhs = sum(model.w[s, k, u, t] for u in model.u if (u, t) in _wpos) \\\n"
    "        + sum(model.v[s, k, tp, t] for tp in model.t if (tp, t) in _vpos)\n"
    "    return lhs <= rhs\n"
    "model.pfs = Constraint(model.s, model.k, model.t, rule=pfs_rule)"
)

LBAL = (
    "def lbal_rule(model, cl, te):\n"
    "    _wpos = set(model.wpos)\n"
    "    _vpos = set(model.vpos)\n"
    "    managed = sum(model.yv[t, te, s, cl, k] * model.v[s, k, t, te]\n"
    "                  for k in model.k for s in model.s for t in model.t if (t, te) in _vpos)\n"
    "    existing = sum(model.yw[te, u, s, cl] * model.w[s, k, u, te]\n"
    "                   for k in model.k for s in model.s for u in model.u if (u, te) in _wpos)\n"
    "    return model.r[cl, te] == managed + existing\n"
    "model.lbal = Constraint(model.cl, model.te, rule=lbal_rule)"
)

SY2 = (
    "def sy2_rule(model, cl, te):\n"
    "    _te_list = list(model.te)\n"
    "    _te_prev = {_te_list[i]: _te_list[i - 1] for i in range(1, len(_te_list))}\n"
    "    if te not in _te_prev:\n"
    "        return Constraint.Skip\n"
    "    return model.r[cl, te] >= model.r[cl, _te_prev[te]]\n"
    "model.sy2 = Constraint(model.cl, model.te, rule=sy2_rule)"
)

BAL = (
    "def bal_rule(model, c, t):\n"
    "    expr = sum(model.a[c, p] * model.z[p, t] for p in model.p)\n"
    "    if c in model.cl:\n"
    "        expr = expr + model.r[c, t]\n"
    "    rhs = model.x[c, t] if c in model.cf else 0\n"
    "    return expr >= rhs\n"
    "model.bal = Constraint(model.c, model.t, rule=bal_rule)"
)

CAP = (
    "def cap_rule(model, m, t):\n"
    "    return sum(model.b[m, p] * model.z[p, t] for p in model.p) \\\n"
    "        <= sum(model.h[m, tp] for tp in model.t if (t, tp) in model.avl and value(model.avl[t, tp]) != 0)\n"
    "model.cap = Constraint(model.m, model.t, rule=cap_rule)"
)

AINVC = (
    "def ainvc_rule(model, t):\n"
    "    return model.phik[t] == model.sgm * sum(\n"
    "        model.nu[m] * model.h[m, tp]\n"
    "        for tp in model.t if value(model.avl[t, tp]) != 0 for m in model.m)\n"
    "model.ainvc = Constraint(model.t, rule=ainvc_rule)"
)

APROC = (
    "def aproc_rule(model, t):\n"
    "    return model.phir[t] == sum(model.pc[p] * model.z[p, t] for p in model.p)\n"
    "model.aproc = Constraint(model.t, rule=aproc_rule)"
)

ASALES = (
    "def asales_rule(model, t):\n"
    "    return model.phix[t] == sum(model.pd[cf] * model.x[cf, t] for cf in model.cf)\n"
    "model.asales = Constraint(model.t, rule=asales_rule)"
)

ACUTC = (
    "def acutc_rule(model, t):\n"
    "    return model.phil[t] == model.muc * sum(model.r[cl, t] for cl in model.cl)\n"
    "model.acutc = Constraint(model.t, rule=acutc_rule)"
)

APLNT = (
    "def aplnt_rule(model, t):\n"
    "    _vpos = set(model.vpos)\n"
    "    return model.phip[t] == model.mup * sum(\n"
    "        model.v[s, k, t, te] for s in model.s for k in model.k\n"
    "        for te in model.te if (t, te) in _vpos)\n"
    "model.aplnt = Constraint(model.t, rule=aplnt_rule)"
)

BENEFIT = (
    "def benefit_rule(model):\n"
    "    return model.phi == sum(\n"
    "        model.delt[t] * (model.phix[t] - model.phik[t] - model.phir[t]\n"
    "                         - model.phil[t] - model.phip[t]) for t in model.t)\n"
    "model.benefit = Constraint(rule=benefit_rule)"
)

WHOLESET = "\n".join([EFS, PFS, LBAL, SY2, BAL, CAP, AINVC, APROC, ASALES, ACUTC, APLNT, BENEFIT])

# ── per-constraint descriptions (Tier-1: complete intent, symbolically silent) ─

D_EFS = (
    "The amount of existing forest that gets cut over the whole horizon cannot exceed how much "
    "existing forest there is to begin with. For each species, site class, and starting age class, "
    "the total area of that existing stand cut across all the periods where cutting it is admissible "
    "must stay within the area of that stand initially present, which is the species' available land "
    "scaled by the share of land in that site class and the share of the forest that starts in that age class."
)

D_PFS = (
    "New forest cannot be managed before it exists. For each species, site class, and period, the area "
    "of newly planted forest that is acted on in that period cannot exceed the area that has been "
    "established by then, namely the existing forest cut in that period plus the new forest planted in "
    "earlier periods that becomes available in that period."
)

D_LBAL = (
    "The logs delivered to industry must come from what is actually harvested. For each log type and "
    "each period, the supply of that log type delivered equals the total yield obtained from cutting, "
    "summed over both the managed newly planted forest and the existing forest, across all species, "
    "site classes, and source stands feasible for that period, each area multiplied by its per-hectare yield."
)

D_SY2 = (
    "Log supply to industry should never fall over time, so harvests are sustained. For each log type, "
    "the supply delivered in a period must be at least the supply delivered in the immediately preceding "
    "period. The very first period has no predecessor and so carries no such requirement."
)

D_BAL = (
    "Each commodity must be in material balance in every period: production must cover use. For each "
    "commodity and period, the net amount produced by all the processing activities, together with any "
    "direct log supply when the commodity is a log type, must be at least the amount shipped out when "
    "the commodity is a final product."
)

D_CAP = (
    "Processing cannot exceed the mill capacity that has been built and is available. For each mill and "
    "each period, the total capacity used by all processing activities running that period must not exceed "
    "the cumulative capacity that has been built and is live in that period."
)

D_AINVC = (
    "Investment cost is charged on the capacity that is live in each period. For each period, the "
    "investment cost equals the capital recovery factor times the total cost of all mill capacity that "
    "has been built and is available in that period, valued at each mill's unit investment cost."
)

D_APROC = (
    "Process cost is the cost of running the processing activities. For each period, the process cost "
    "equals the sum over all activities of the activity level run that period valued at its unit process cost."
)

D_ASALES = (
    "Sales revenue comes from the final products shipped to market. For each period, the sales revenue "
    "equals the sum over all final products of the amount shipped that period valued at its sales price."
)

D_ACUTC = (
    "Cutting cost depends on how much wood is harvested. For each period, the cutting cost equals the "
    "unit cutting cost times the total of all log types delivered to industry in that period."
)

D_APLNT = (
    "Planting cost depends on how much new forest is established. For each period, the planting cost "
    "equals the unit planting cost times the total area of new forest planted in that period across all "
    "species and site classes."
)

D_BENEFIT = (
    "The overall measure of merit aggregates each period's net result, discounted to a common basis. "
    "The total discounted net benefit equals the sum over all periods of that period's discount factor "
    "times its net benefit, where the net benefit is sales revenue less investment, processing, cutting, "
    "and planting costs."
)

records = [
    {"description": D_EFS, "expected_pyomo": EFS},
    {"description": D_PFS, "expected_pyomo": PFS},
    {"description": D_LBAL, "expected_pyomo": LBAL},
    {"description": D_SY2, "expected_pyomo": SY2},
    {"description": D_BAL, "expected_pyomo": BAL},
    {"description": D_CAP, "expected_pyomo": CAP},
    {"description": D_AINVC, "expected_pyomo": AINVC},
    {"description": D_APROC, "expected_pyomo": APROC},
    {"description": D_ASALES, "expected_pyomo": ASALES},
    {"description": D_ACUTC, "expected_pyomo": ACUTC},
    {"description": D_APLNT, "expected_pyomo": APLNT},
    {"description": D_BENEFIT, "expected_pyomo": BENEFIT},
]

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, ensure the total existing forest cut across all admissible periods stays within the existing "
    "forest initially present for each species, site class, and starting age. "
    "Second, ensure new forest can only be managed once it has been established, so the area acted on in a "
    "period does not exceed what has been established by then. "
    "Third, set the supply of each log type delivered in each period equal to the total harvest yield from "
    "both managed and existing forest feasible for that period. "
    "Fourth, require log supply to industry for each log type to never fall from one period to the next. "
    "Fifth, keep every commodity in material balance in every period, with production covering shipments. "
    "Sixth, keep processing within the mill capacity built and available in each period. "
    "Seventh, set each period's investment cost to the capital recovery factor times the cost of capacity "
    "live in that period. "
    "Eighth, set each period's process cost to the activity levels valued at their unit process costs. "
    "Ninth, set each period's sales revenue to the final products shipped valued at their sales prices. "
    "Tenth, set each period's cutting cost to the unit cutting cost times the logs delivered that period. "
    "Eleventh, set each period's planting cost to the unit planting cost times the new forest planted that period. "
    "Finally, set the total discounted net benefit to the discounted sum over periods of sales revenue less "
    "investment, processing, cutting, and planting costs."
)

records.append({"description": WHOLESET_DESC, "expected_pyomo": WHOLESET})

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "tfordy_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
