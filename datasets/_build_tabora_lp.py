#!/usr/bin/env python
"""Builder for the tabora_lp (Tabora rural development fuelwood) constraint-generation dataset.

A 30-year dynamic LP for a Tanzanian village choosing between managing a planted
timber forest and harvesting the natural forest (whose travel time grows as it is
cut). All coefficients are derived parameters computed from the base scalar/indexed
params, so every rule below recomputes those derived quantities from `model` params
(only `model`, `Constraint`, `sum`, `value`, `pyo` are in the grading namespace).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tabora_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "t", "members": "y01..y30 as the integers 1..30",
         "doc": "the planning years in chronological order, indexed by the integers 1 through 30; the first year is 1 and each later year follows the one before it"},
        {"name": "a", "members": "1..24",
         "doc": "the age of planted timber in years, from 1 up to 24; timber planted in one year reaches age a exactly a years later"},
        {"name": "m", "members": ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
         "doc": "the twelve calendar months over which labor is supplied and used"},
        {"name": "mc", "members": ["jul", "aug", "sep", "oct"],
         "doc": "the cutting months, the subset of months during which wood is cut from the forest"},
        {"name": "i", "members": "1..9",
         "doc": "the nine concentric annuli (rings) of natural forest around the village; ring 1 is closest and ring 9 is farthest, so cutting a farther ring costs more travel time"},
        {"name": "c", "members": ["maize", "tobacco"],
         "doc": "the two annual crops the village can grow, maize and tobacco"},
    ],
    "params": [
        {"name": "yw", "index": "", "kind": "yield",
         "doc": "yield of the existing natural forest, in cubic metres of wood per hectare cut"},
        {"name": "yv", "index": "a", "kind": "yield",
         "doc": "yield of planted timber at each tree age a, in cubic metres per hectare; a hectare planted t-a years ago and managed now yields yv[a]"},
        {"name": "wrc", "index": "", "kind": "requirement",
         "doc": "wood needed to cure one hectare of tobacco, in cubic metres per hectare"},
        {"name": "dwr", "index": "", "kind": "requirement",
         "doc": "domestic wood requirement per family per year, in cubic metres per family"},
        {"name": "nfam", "index": "", "kind": "count",
         "doc": "number of families living in the village"},
        {"name": "sfam", "index": "", "kind": "size",
         "doc": "size of a family in adult-equivalent workers"},
        {"name": "wdm", "index": "", "kind": "rate",
         "doc": "working days available per worker per month"},
        {"name": "ld", "index": "(activity, m)", "kind": "requirement",
         "doc": "labor requirement table in man-days, by activity and month; activities include 'timber-1' and 'timber-2' (managing planted timber in its first and second year), the crop names, and 'other' (non-farm labor that reduces the labor pool); entries default to zero where not listed"},
        {"name": "labwc", "index": "", "kind": "rate",
         "doc": "labor to cut the natural forest, in man-days per cubic metre"},
        {"name": "labvc", "index": "", "kind": "rate",
         "doc": "labor to cut planted timber, in man-days per cubic metre"},
        {"name": "ws", "index": "", "kind": "rate",
         "doc": "walking speed when travelling to the forest, in kilometres per hour"},
        {"name": "whd", "index": "", "kind": "rate",
         "doc": "work hours available per day"},
        {"name": "sr", "index": "", "kind": "geometry",
         "doc": "starting radius of the innermost annulus, in kilometres"},
        {"name": "width", "index": "", "kind": "geometry",
         "doc": "radial width of each annulus, in kilometres; the average distance to ring i is sr - width/2 + width*i and its area is 100*pi*(that distance)*width hectares"},
        {"name": "tmd", "index": "(field, c)", "kind": "crop-data",
         "doc": "crop data table by crop, with fields 'input-cost' (tsh per hectare), 'yield' (kg per hectare), and 'price' (tsh per kg); crop revenue per hectare is yield times price, crop cost per hectare is the input-cost"},
        {"name": "fdmaize", "index": "", "kind": "demand",
         "doc": "domestic maize demand per family per year, in kilograms"},
        {"name": "matr", "index": "", "kind": "factor",
         "doc": "the fractional improvement in maize yield on land grown with maize in the year right after tobacco; such land yields matr times the normal maize output"},
        {"name": "tob", "index": "", "kind": "level",
         "doc": "steady-state tobacco area, in hectares; also the upper bound on maize-after-tobacco area available in the first year"},
        {"name": "tc", "index": "", "kind": "cost",
         "doc": "cost of planting timber, in tsh per hectare"},
        {"name": "resw", "index": "", "kind": "cost",
         "doc": "reservation wage, in tsh per hour, charged for labor spent cutting wood"},
        {"name": "tr", "index": "", "kind": "cost",
         "doc": "transport cost of wood, in tsh per cubic metre per kilometre"},
        {"name": "rho", "index": "", "kind": "rate",
         "doc": "annual discount rate; the discount factor applied to year t is (1+rho)**(-t)"},
    ],
    "vars": [
        {"name": "w", "index": "(t, i)", "domain": "NonNegativeReals",
         "doc": "hectares of natural forest cut in ring i during year t"},
        {"name": "v", "index": "t", "domain": "NonNegativeReals",
         "doc": "hectares of planted timber managed (planted) in year t; timber planted in year t-a is available at age a in year t"},
        {"name": "x", "index": "(t, c)", "domain": "NonNegativeReals",
         "doc": "hectares of crop c grown in year t"},
        {"name": "mat", "index": "t", "domain": "NonNegativeReals",
         "doc": "hectares of maize grown after tobacco in year t, which enjoys the improved post-tobacco yield"},
        {"name": "lc", "index": "(t, m)", "domain": "NonNegativeReals",
         "doc": "man-days of labor devoted to wood cutting in year t and month m; only meaningful in cutting months"},
        {"name": "rev", "index": "t", "domain": "Reals",
         "doc": "total crop revenue in year t, in thousands of tsh"},
        {"name": "cost", "index": "t", "domain": "Reals",
         "doc": "total cost in year t, in thousands of tsh"},
        {"name": "income", "index": "", "domain": "Reals",
         "doc": "total discounted net income over the whole 30-year horizon, in thousands of tsh"},
    ],
    "objective": {"sense": "maximize", "expr_var": "income"},
}

NARRATIVE = (
    "A village in the Tabora region must supply its own fuelwood and curing wood over a "
    "thirty-year horizon, choosing each year how much natural forest to cut from each of "
    "nine rings around the village, how much timber to plant and manage, and how many "
    "hectares of maize and tobacco to grow. Cutting the natural forest gets harder over "
    "time because the closer rings are exhausted and the village must travel farther, while "
    "planted timber takes years to mature but provides a sustainable supply. The village "
    "also tracks the labor it has available each month, the maize it needs to feed itself, "
    "and the extra maize yield it gets on land grown right after tobacco. Each year produces "
    "crop revenue and incurs planting, cutting, wage, and transport costs, and the goal is to "
    "maximize the total discounted net income over the whole horizon."
)

# Shared preamble: recompute every derived quantity the GAMS model precomputes,
# straight from `model` params, so each rule body is self-contained.
PRE = (
    "CARD_T = len(model.t)\n"
    "def P(p):\n"
    "    return value(getattr(model, p))\n"
    "nfam=P('nfam'); sfam=P('sfam'); resw=P('resw'); fdmaize=P('fdmaize'); tob=P('tob')\n"
    "sr=P('sr'); width=P('width'); ws=P('ws'); whd=P('whd'); wdm=P('wdm'); tr=P('tr')\n"
    "tc=P('tc'); wrc=P('wrc'); dwr=P('dwr'); labwc=P('labwc'); labvc=P('labvc')\n"
    "yw=P('yw'); rho=P('rho'); matr=P('matr')\n"
    "def _ld(r, mm):\n"
    "    return value(model.ld[r, mm]) if (r, mm) in model.ld else 0.0\n"
    "def _yv(aa):\n"
    "    return value(model.yv[aa])\n"
    "def _v(tt):\n"
    "    return 0.0 if (tt < 1 or tt > CARD_T) else model.v[tt]\n"
    "dmaize = fdmaize * nfam\n"
    "wr = tob * wrc + dwr * nfam\n"
    "delt = {tt: (1 + rho) ** (-tt) for tt in model.t}\n"
    "delta = {aa: (1 + rho) ** (-aa) for aa in model.a}\n"
    "vr = {tt: tr * sr * sum(_yv(aa) * delta[aa] for aa in model.a if tt + aa > CARD_T) for tt in model.t}\n"
    "dist = {ii: sr - width / 2 + width * ii for ii in model.i}\n"
    "fa = {ii: 100 * 3.1416 * dist[ii] * width for ii in model.i}\n"
    "labor = {mm: nfam * (sfam * wdm - _ld('other', mm)) for mm in model.m}\n"
    "labw = {ii: yw * labwc * whd / (whd - 2 * dist[ii] / ws) for ii in model.i}\n"
    "cc = {c: value(model.tmd['input-cost', c]) for c in model.c}\n"
    "yc = {c: value(model.tmd['yield', c]) for c in model.c}\n"
    "pc = {c: value(model.tmd['price', c]) for c in model.c}\n"
    "cr = {c: yc[c] * pc[c] for c in model.c}\n"
)

WB = PRE + (
    "def wb_rule(mo, t):\n"
    "    return yw * sum(mo.w[t, i] for i in mo.i) + sum(_yv(a) * _v(t - a) for a in mo.a) "
    ">= wrc * mo.x[t, 'tobacco'] + dwr * nfam\n"
    "model.wb = Constraint(model.t, rule=wb_rule)"
)
WA = PRE + (
    "def wa_rule(mo, i):\n"
    "    return sum(mo.w[t, i] for t in mo.t) <= fa[i]\n"
    "model.wa = Constraint(model.i, rule=wa_rule)"
)
LB = PRE + (
    "def lb_rule(mo, t, mm):\n"
    "    expr = _ld('timber-1', mm) * _v(t) + _ld('timber-2', mm) * _v(t - 1) "
    "+ sum(_ld(c, mm) * mo.x[t, c] for c in mo.c)\n"
    "    if mm in mo.mc:\n"
    "        expr = expr + mo.lc[t, mm]\n"
    "    return expr <= labor[mm]\n"
    "model.lb = Constraint(model.t, model.m, rule=lb_rule)"
)
LW = PRE + (
    "def lw_rule(mo, t):\n"
    "    return sum(mo.lc[t, mc] for mc in mo.mc) == "
    "sum(labw[i] * mo.w[t, i] for i in mo.i) + sum(labvc * _yv(a) * _v(t - a) for a in mo.a)\n"
    "model.lw = Constraint(model.t, rule=lw_rule)"
)
MM = PRE + (
    "def mm_rule(mo, t):\n"
    "    return yc['maize'] * (mo.x[t, 'maize'] + matr * mo.mat[t]) >= dmaize\n"
    "model.mm = Constraint(model.t, rule=mm_rule)"
)
TTB = PRE + (
    "def ttb_rule(mo, t):\n"
    "    expr = sum(_yv(a) * _v(t + (CARD_T - a)) for a in mo.a)\n"
    "    if not hasattr(expr, 'is_expression_type'):\n"
    "        return pyo.Constraint.Feasible\n"
    "    return expr <= wr\n"
    "model.ttb = Constraint(model.t, rule=ttb_rule)"
)
MATD1 = (
    "def matd1_rule(mo, t):\n"
    "    if t - 1 < 1:\n"
    "        return pyo.Constraint.Skip\n"
    "    return mo.mat[t] <= mo.x[t - 1, 'tobacco']\n"
    "model.matd1 = Constraint(model.t, rule=matd1_rule)"
)
MATD2 = (
    "def matd2_rule(mo, t):\n"
    "    return mo.mat[t] <= mo.x[t, 'maize']\n"
    "model.matd2 = Constraint(model.t, rule=matd2_rule)"
)
RD = PRE + (
    "def rd_rule(mo, t):\n"
    "    return mo.rev[t] == (sum(cr[c] * mo.x[t, c] for c in mo.c) + matr * cr['maize'] * mo.mat[t]) / 1000\n"
    "model.rd = Constraint(model.t, rule=rd_rule)"
)
CD = PRE + (
    "def cd_rule(mo, t):\n"
    "    return mo.cost[t] == (sum(cc[c] * mo.x[t, c] for c in mo.c) + tc * mo.v[t] "
    "+ resw * whd * sum(mo.lc[t, mc] for mc in mo.mc) "
    "+ sum(tr * yw * dist[i] * mo.w[t, i] for i in mo.i)) / 1000\n"
    "model.cd = Constraint(model.t, rule=cd_rule)"
)
OD = PRE + (
    "def od_rule(mo):\n"
    "    return mo.income == sum(delt[t] * (mo.rev[t] - mo.cost[t] + vr[t] * mo.v[t] / 1000) for t in mo.t)\n"
    "model.od = Constraint(rule=od_rule)"
)

per = [
    ("wb", "Each year the wood the village obtains must cover the wood it needs. For every year, the wood cut from the natural forest plus the wood yielded by the planted timber maturing that year must be at least the wood required to cure that year's tobacco plus the domestic wood the families need.", WB),
    ("wa", "The natural forest in each ring is finite. For every ring, the total area cut from that ring over all the years must not exceed the area of that ring.", WA),
    ("lb", "The village cannot use more labor in a month than it has. For every year and every month, the labor spent managing newly planted and second-year timber, the labor spent on the crops, and, in cutting months, the labor spent cutting wood together must not exceed the labor the village has available that month.", LB),
    ("lw", "Wood cutting requires labor in the cutting months. For every year, the labor devoted to wood cutting across the cutting months must equal the labor needed to cut the natural forest harvested that year plus the labor needed to cut the planted timber maturing that year.", LW),
    ("mm", "The village must feed itself. For every year, the maize produced, counting both ordinary maize land and the extra yield from maize grown right after tobacco, must be at least the village's domestic maize demand.", MM),
    ("ttb", "Timber planted too close to the end of the horizon would not mature in time to be useful, so it is limited. For every year, the timber that would only reach harvestable age after the horizon ends must yield no more than the village's total domestic and curing wood requirement.", TTB),
    ("matd1", "Maize can only get the post-tobacco boost on land that actually grew tobacco the year before. For every year after the first, the area of maize-after-tobacco must not exceed the tobacco area grown in the previous year.", MATD1),
    ("matd2", "Maize-after-tobacco is still maize land. For every year, the area of maize-after-tobacco must not exceed the maize area grown that year.", MATD2),
    ("rd", "Revenue must reflect what the crops earn. For every year, the revenue equals the revenue from each crop's area plus the extra revenue from the improved yield on maize grown after tobacco, expressed in thousands.", RD),
    ("cd", "Cost must reflect what the village spends. For every year, the cost equals crop input costs, timber planting cost, the wage paid for wood-cutting labor in the cutting months, and the transport cost of hauling cut natural-forest wood, all expressed in thousands.", CD),
    ("od", "Income must reflect discounted net returns. The total discounted income equals, summed over all years and discounted to the present, each year's revenue minus its cost plus the discounted residual value of the timber still standing.", OD),
]

names = [
    "First, in every year ensure the wood obtained from cutting the natural forest plus the planted timber maturing that year covers the wood needed for tobacco curing and domestic use.",
    "Second, for every ring of natural forest keep the total area cut across all years within the area of that ring.",
    "Third, for every year and month keep the labor used on timber management, crops, and wood cutting within the labor the village has that month.",
    "Fourth, in every year make the wood-cutting labor across the cutting months equal the labor required to cut the natural forest harvested and the planted timber matured that year.",
    "Fifth, in every year ensure the maize produced, including the post-tobacco yield boost, meets the village's domestic maize demand.",
    "Sixth, in every year limit the timber that would only mature after the horizon to no more than the total domestic and curing wood requirement.",
    "Seventh, in every year after the first keep the maize-after-tobacco area within the tobacco area grown the previous year.",
    "Eighth, in every year keep the maize-after-tobacco area within the maize area grown that year.",
    "Ninth, in every year set the revenue equal to the crop revenues plus the extra revenue from the improved post-tobacco maize yield.",
    "Tenth, in every year set the cost equal to crop input costs, timber planting cost, the wood-cutting wage, and the wood transport cost.",
    "Finally, set the total discounted income equal to the sum over all years of each year's revenue minus cost plus the discounted residual value of standing timber.",
]
WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. " + " ".join(names)
)
WHOLESET = "\n".join(c for _, _, c in per)

records = [{"description": d, "expected_pyomo": code} for _, d, code in per]
records.append({"description": WHOLESET_DESC, "expected_pyomo": WHOLESET})

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "tabora_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
