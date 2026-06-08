#!/usr/bin/env python
"""Builder for the dinam_lp (Dinamico: dynamic multi-sector, multi-skill planning
model of the Mexican economy) constraint-generation dataset.

Pure LP (all 16 constraints linear, verified maxdeg=1). The model decides sector
outputs, investments, labor moves, trade, and macro aggregates over a multi-year
horizon to maximize initial-year consumption.

NOTE on self-containment: the grader execs each expected_pyomo snippet in a bare
namespace (only model, Constraint, sum, pyo, value). So every rule below
reconstructs its own index helpers (year ordinals, the t-subhorizon, the lag
ordinals, the unskilled set, the interval, and the last/initial period cutoffs)
from model components alone -- it may NOT rely on the base module's globals.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "dinam_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "te", "members": ["y1968", "y1971", "y1974", "y1977", "y1980", "y1983", "y1986", "y1989"],
         "doc": "the full plan horizon of years in chronological order; the first member y1968 is the fixed base year and the last member y1989 is the post-terminal year; consecutive members are one period (three years) apart"},
        {"name": "t", "members": ["y1971", "y1974", "y1977", "y1980", "y1983", "y1986"],
         "doc": "the optimization sub-horizon, the years that are actually decided; it excludes the fixed base year and the post-terminal year"},
        {"name": "j", "members": ["agri", "mine", "petrol", "food", "text", "wood", "chem", "n-met", "b-met", "mach", "const", "elec", "comm", "trans", "serv"],
         "doc": "the producing input-output sectors of destination"},
        {"name": "i", "members": ["agri", "mine", "petrol", "food", "text", "wood", "chem", "n-met", "b-met", "mach", "const", "elec", "comm", "trans", "serv"],
         "doc": "the input-output commodities of origin, used to write commodity balances"},
        {"name": "idset", "members": ["agri", "mine", "petrol", "food", "text", "wood", "chem", "n-met", "b-met", "mach", "const", "elec", "comm", "trans", "serv", "imp"],
         "doc": "commodities of origin including the non-competitive imported commodity imp"},
        {"name": "im", "members": ["agri", "mine", "petrol", "food", "text", "wood", "chem", "n-met", "b-met", "mach"],
         "doc": "the merchandize commodities that can be exported"},
        {"name": "inc", "members": ["imp"],
         "doc": "the single non-competitive foreign commodity that must be imported and paid for in foreign exchange"},
        {"name": "s", "members": ["eng", "tech", "admin", "man", "unskill"],
         "doc": "the labor skill categories"},
        {"name": "sun", "members": ["unskill"],
         "doc": "the unskilled agricultural workers; the only skill category released when capital is added to agriculture"},
        {"name": "lset", "members": ["l0", "l1", "l2"],
         "doc": "the education lag structure in order; l0 is no lag, l1 is one period later, l2 is two periods later"},
        {"name": "eit", "members": ["change", "input"],
         "doc": "the two education input types; change describes graduates entering a skill and input describes resources consumed by the education process"},
    ],
    "params": [
        {"name": "a", "index": "idset,j,te", "kind": "io_coefficient",
         "doc": "the current-account input-output coefficients: units of commodity of origin needed per unit of sector output in a year"},
        {"name": "b", "index": "idset,j,te", "kind": "capital_coefficient",
         "doc": "the capital input-output coefficients: units of commodity of origin needed per unit of one-year capacity increase"},
        {"name": "k", "index": "j,te", "kind": "capital_coefficient",
         "doc": "the capital cost coefficient: value of investment goods needed per unit of one-year capacity increase in a sector"},
        {"name": "bk_agri", "index": "idset,te", "kind": "io_coefficient",
         "doc": "the commodity-of-origin requirement per unit of capital added to agriculture"},
        {"name": "apc", "index": "idset,te", "kind": "demand_coefficient",
         "doc": "the average propensity to consume: units of a commodity consumed per unit of aggregate consumption"},
        {"name": "apz", "index": "idset,te", "kind": "demand_coefficient",
         "doc": "the tourist consumption propensity: units of a commodity demanded per unit of tourism earnings"},
        {"name": "lreq", "index": "s,j,te", "kind": "labor_coefficient",
         "doc": "the labor requirement: workers of a skill needed per unit of sector output"},
        {"name": "alr", "index": "te", "kind": "labor_coefficient",
         "doc": "the agricultural labor released per unit of capital added to agriculture"},
        {"name": "es", "index": "idset", "kind": "trade_coefficient",
         "doc": "the share of the commodity-of-origin requirement attributable to high-cost manufacture exports"},
        {"name": "csm", "index": "idset", "kind": "trade_coefficient",
         "doc": "the commerce and service margin per unit of aggregate merchandize exports"},
        {"name": "ssr", "index": "idset,s", "kind": "io_coefficient",
         "doc": "the service requirement of a commodity to convert one rural worker of a skill into an urban worker"},
        {"name": "ldg", "index": "s,s", "kind": "labor_coefficient",
         "doc": "the labor downgrading coefficients: workers made available in the first skill per worker downgraded out of the second skill"},
        {"name": "lugt", "index": "s,s,te", "kind": "labor_coefficient",
         "doc": "the time-allowed labor upgrading coefficients: workers entering the first skill per worker upgraded out of the second skill in a year"},
        {"name": "sf", "index": "eit,s,lset,s", "kind": "education_coefficient",
         "doc": "the human-capital formation coefficients indexed by education input type, target skill, lag, and source skill; for the change type it gives graduates of the target skill produced, for the input type it gives source-skill labor consumed, both per unit of an education process started a number of periods earlier given by the lag"},
        {"name": "length", "index": "s", "kind": "education_coefficient",
         "doc": "the education lag length of a skill: an education process contributes only in periods whose ordinal position exceeds this length, so shorter trainings mature sooner"},
        {"name": "x0", "index": "j", "kind": "capacity",
         "doc": "the base-year output level of a sector that defines its initial installed capacity"},
        {"name": "zmi", "index": "t,t", "kind": "trade_coefficient",
         "doc": "the implicit protection factor relating high-cost manufacture exports of one year to commodity demand in another year"},
        {"name": "deltae", "index": "idset", "kind": "trade_coefficient",
         "doc": "the assumed post-terminal increment in merchandize exports of a commodity"},
        {"name": "deltaz", "index": "idset", "kind": "trade_coefficient",
         "doc": "the assumed post-terminal increment in tourism demand of a commodity"},
        {"name": "infc", "index": "t", "kind": "finance",
         "doc": "the interest due on concessional foreign capital in a year"},
        {"name": "pfc", "index": "t", "kind": "finance",
         "doc": "the fixed concessional foreign capital inflow in a year; the concessional inflow variable is fixed to this"},
        {"name": "fdpup", "index": "t", "kind": "bound",
         "doc": "the upper bound on direct private foreign capital inflows in a year"},
        {"name": "w1", "index": "te", "kind": "objective_weight",
         "doc": "the objective weight on consumption of each year; nonzero only for the initial optimized year so the maximand is initial-year consumption"},
        {"name": "elo", "index": "im,t", "kind": "bound",
         "doc": "the lower bound on exports of a merchandize commodity in a year"},
        {"name": "eup", "index": "im,t", "kind": "bound",
         "doc": "the upper bound on exports of a merchandize commodity in a year"},
        {"name": "zlo", "index": "t", "kind": "bound",
         "doc": "the lower bound on tourism earnings in a year"},
        {"name": "zup", "index": "t", "kind": "bound",
         "doc": "the upper bound on tourism earnings in a year"},
        {"name": "ls", "index": "te,s", "kind": "labor_supply",
         "doc": "the projected exogenous supply of labor of a skill in a year"},
        {"name": "interval", "index": "", "kind": "scalar",
         "doc": "the number of years in one period, equal to three; capacity increase variables are per-year so investments are multiplied by this to span a period"},
        {"name": "pvv", "index": "", "kind": "scalar",
         "doc": "the producers price scaling value applied to aggregate merchandize exports in the export definition"},
        {"name": "pci", "index": "", "kind": "scalar",
         "doc": "the income payment rate charged on the stock of prior direct foreign private capital"},
        {"name": "cfdp", "index": "", "kind": "scalar",
         "doc": "the cap on cumulative direct private foreign capital inflows over the optimized horizon"},
        {"name": "mps", "index": "", "kind": "scalar",
         "doc": "the marginal propensity to save: the most an increment of product may add to savings"},
        {"name": "gamma", "index": "", "kind": "scalar",
         "doc": "the consumption growth factor that links the next consumption increment to the current one on the gradualist path"},
        {"name": "gv3", "index": "", "kind": "scalar",
         "doc": "the three-year growth rate applied to the post-terminal capital requirement"},
        {"name": "infdpt", "index": "", "kind": "scalar",
         "doc": "the fixed level of interest and profit remittances on prior foreign capital; the remittance variable is fixed to this"},
    ],
    "vars": [
        {"name": "x", "index": "jd,te", "domain": "NonNegativeReals",
         "doc": "the gross output of a sector in a year"},
        {"name": "v", "index": "jd,te", "domain": "NonNegativeReals",
         "doc": "the one-year increase in a sector's productive capacity in a year, that is per-year investment"},
        {"name": "ld", "index": "s,te", "domain": "NonNegativeReals",
         "doc": "the labor downgraded out of a skill category in a year"},
        {"name": "ul", "index": "s,te", "domain": "NonNegativeReals",
         "doc": "the labor upgraded into a skill category in a year"},
        {"name": "ka", "index": "te", "domain": "NonNegativeReals",
         "doc": "the capital added to agriculture in a year, substituting for unskilled labor"},
        {"name": "ed", "index": "s,te", "domain": "NonNegativeReals",
         "doc": "the level of an education process for a target skill started in a year"},
        {"name": "rql", "index": "s,te", "domain": "NonNegativeReals",
         "doc": "the total requirement for labor of a skill in a year, the quantity defined by the labor-requirement equations"},
        {"name": "e", "index": "i,te", "domain": "NonNegativeReals",
         "doc": "the exports of a merchandize commodity in a year, bounded between its export lower and upper bounds"},
        {"name": "em", "index": "te", "domain": "NonNegativeReals",
         "doc": "the exports of high-cost subsidized manufactures in a year"},
        {"name": "ea", "index": "te", "domain": "NonNegativeReals",
         "doc": "the aggregate merchandize exports in a year"},
        {"name": "zt", "index": "te", "domain": "NonNegativeReals",
         "doc": "the earnings from tourism in a year, bounded between its tourism lower and upper bounds"},
        {"name": "fdp", "index": "te", "domain": "NonNegativeReals",
         "doc": "the direct private foreign capital inflow in a year, bounded above by its yearly upper bound"},
        {"name": "inv", "index": "te", "domain": "NonNegativeReals",
         "doc": "the gross domestic investment in a year; fixed at its base-year value in the base year"},
        {"name": "sav", "index": "te", "domain": "NonNegativeReals",
         "doc": "the gross domestic savings in a year; fixed at its base-year value in the base year"},
        {"name": "con", "index": "te", "domain": "NonNegativeReals",
         "doc": "the aggregate consumption in a year; fixed at its base-year value in the base year"},
        {"name": "gdp", "index": "te", "domain": "NonNegativeReals",
         "doc": "the gross domestic product in a year; fixed at its base-year value in the base year"},
        {"name": "fc", "index": "te", "domain": "Reals",
         "doc": "the concessional foreign capital inflow in a year; fixed to the given concessional inflow in each optimized year"},
        {"name": "rgap", "index": "te", "domain": "Reals",
         "doc": "the resource gap, the foreign-financed difference between investment and domestic savings in a year"},
        {"name": "infdp", "index": "", "domain": "Reals",
         "doc": "the interest and profit remittances on prior foreign capital; a single fixed quantity"},
        {"name": "max1", "index": "", "domain": "Reals",
         "doc": "the maximand, set equal to the weighted sum of consumption that equals initial-year consumption"},
    ],
    "objective": {"sense": "maximize", "expr_var": "max1"},
}

NARRATIVE = (
    "This is a dynamic multi-sector, multi-skill planning model of an economy over "
    "a horizon of years spaced three years apart, with a fixed base year, a span of "
    "optimized years, and a post-terminal year. For each optimized year we choose how "
    "much each sector produces, how much new productive capacity to build in each "
    "sector, how much capital to add to agriculture, how labor moves between skill "
    "categories through downgrading, upgrading, and education, how much of each "
    "commodity to export, how much tourism and high-cost manufacture export to earn, "
    "and how much foreign capital to bring in, together with the macroeconomic "
    "aggregates of consumption, savings, investment, the resource gap, and gross "
    "domestic product. The objective is to maximize consumption in the initial "
    "optimized year."
)

# ---------------------------------------------------------------------------
# Per-constraint ground-truth Pyomo. Each rule is SELF-CONTAINED: it rebuilds
# its own ordinals/helpers from `model` only (the grader gives no module globals).
# Data constants embedded directly: interval=3 (also model.interval), last=7,
# initial=1.
# ---------------------------------------------------------------------------

MB = (
    "def mb_rule(model, ii, y):\n"
    "    te = list(model.te); tt = list(model.t)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    expr = sum(model.a[ii, jj, y] * model.x[jj, y] + model.b[ii, jj, y] * model.v[jj, y] for jj in model.j)\n"
    "    expr += model.bk_agri[ii, y] * model.ka[y] + model.apc[ii, y] * model.con[y] + model.apz[ii, y] * model.zt[y]\n"
    "    expr += model.es[ii] * sum(model.zmi[y, yp] * model.em[yp] for yp in tt if ordte[y] >= ordte[yp])\n"
    "    if ii in model.im:\n"
    "        expr += model.e[ii, y]\n"
    "    expr += model.csm[ii] * model.ea[y] + sum(model.ssr[ii, ss] * model.ul[ss, y] for ss in model.s)\n"
    "    return expr <= 0\n"
    "model.mb = Constraint(model.i, model.t, rule=mb_rule)"
)

CAP = (
    "def cap_rule(model, jj, y):\n"
    "    te = list(model.te)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    interval = value(model.interval)\n"
    "    return model.x[jj, y] <= model.x0[jj] + interval * sum(model.v[jj, yy] for yy in model.te if ordte[y] > ordte[yy])\n"
    "model.cap = Constraint(model.j, model.t, rule=cap_rule)"
)

TIC = (
    "def tic_rule(model, ii, y):\n"
    "    te = list(model.te)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    LAST = 7; interval = value(model.interval)\n"
    "    if ordte[y] <= LAST:\n"
    "        return pyo.Constraint.Skip\n"
    "    ym1 = te[ordte[y] - 2]\n"
    "    lhs = model.apc[ii, ym1] * (model.con[y] - model.con[ym1])\n"
    "    lhs += model.gv3 * sum(model.b[ii, jj, ym1] * model.v[jj, ym1] for jj in model.j) + model.deltae[ii] + model.deltaz[ii]\n"
    "    rhs = interval * sum(-model.a[ii, jj, ym1] * model.v[jj, ym1] for jj in model.j)\n"
    "    return lhs <= rhs\n"
    "model.tic = Constraint(model.i, model.te, rule=tic_rule)"
)

DRQL = (
    "def drql_rule(model, ss, y):\n"
    "    te = list(model.te); sun = set(model.sun)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    interval = value(model.interval)\n"
    "    expr = sum(model.lreq[ss, jj, y] * model.x[jj, y] for jj in model.j)\n"
    "    if ss in sun:\n"
    "        expr -= model.alr[y] * (model.ka[y] + interval * sum(model.ka[yy] for yy in model.te if ordte[y] > ordte[yy]))\n"
    "    return expr == model.rql[ss, y]\n"
    "model.drql = Constraint(model.s, model.t, rule=drql_rule)"
)

TRQL = (
    "def trql_rule(model, ss, y):\n"
    "    te = list(model.te); sun = set(model.sun)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    LAST = 7; interval = value(model.interval)\n"
    "    if ordte[y] <= LAST:\n"
    "        return pyo.Constraint.Skip\n"
    "    ym1 = te[ordte[y] - 2]\n"
    "    expr = sum(model.lreq[ss, jj, y] * (model.x[jj, ym1] + interval * model.v[jj, ym1]) for jj in model.j)\n"
    "    if ss in sun:\n"
    "        expr -= interval * model.alr[y] * sum(model.ka[yp] for yp in model.te if ordte[y] > ordte[yp])\n"
    "    return expr == model.rql[ss, y]\n"
    "model.trql = Constraint(model.s, model.te, rule=trql_rule)"
)

LDSC = (
    "def ldsc_rule(model, ss, y):\n"
    "    te = list(model.te); lset = list(model.lset)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    ordl = {ll: kk + 1 for kk, ll in enumerate(lset)}\n"
    "    INITIAL = 1\n"
    "    if ordte[y] <= INITIAL:\n"
    "        return pyo.Constraint.Skip\n"
    "    rhs = model.ls[y, ss]\n"
    "    rhs += sum(model.ldg[ss, sp] * model.ld[sp, y] + model.lugt[ss, sp, y] * model.ul[sp, y] for sp in model.s)\n"
    "    for yp in model.te:\n"
    "        if not (ordte[y] >= ordte[yp]):\n"
    "            continue\n"
    "        for sp in model.s:\n"
    "            for ll in lset:\n"
    "                if (ordte[yp] + (ordl[ll] - 1)) > value(model.length[sp]):\n"
    "                    coeff = value(model.sf['change', ss, ll, sp])\n"
    "                    if coeff != 0:\n"
    "                        tgt = ordte[yp] + (ordl[ll] - 1)\n"
    "                        if 1 <= tgt <= len(te):\n"
    "                            rhs += model.sf['change', ss, ll, sp] * model.ed[sp, te[tgt - 1]]\n"
    "    for sp in model.s:\n"
    "        for ll in lset:\n"
    "            if (ordte[y] + (ordl[ll] - 1)) > value(model.length[sp]):\n"
    "                coeff = value(model.sf['input', ss, ll, sp])\n"
    "                if coeff != 0:\n"
    "                    tgt = ordte[y] + (ordl[ll] - 1)\n"
    "                    if 1 <= tgt <= len(te):\n"
    "                        rhs += model.sf['input', ss, ll, sp] * model.ed[sp, te[tgt - 1]]\n"
    "    return model.rql[ss, y] <= rhs\n"
    "model.ldsc = Constraint(model.s, model.te, rule=ldsc_rule)"
)

EXDEF = (
    "def exdef_rule(model, y):\n"
    "    te = list(model.te)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    return model.pvv * model.ea[y] == sum(model.e[r, y] for r in model.im) + sum(model.em[yp] for yp in model.t if ordte[y] >= ordte[yp])\n"
    "model.exdef = Constraint(model.t, rule=exdef_rule)"
)

FEXCH = (
    "def fexch_rule(model, y):\n"
    "    lhs = sum(model.apc[r, y] * model.con[y] + model.bk_agri[r, y] * model.ka[y]\n"
    "              + sum(model.a[r, jj, y] * model.x[jj, y] + model.b[r, jj, y] * model.v[jj, y] for jj in model.j)\n"
    "              for r in model.inc)\n"
    "    return lhs == model.ea[y] + model.zt[y] + model.rgap[y]\n"
    "model.fexch = Constraint(model.t, rule=fexch_rule)"
)

FGAP = (
    "def fgap_rule(model, y):\n"
    "    te = list(model.te)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    return (model.rgap[y] - model.fc[y] - model.fdp[y] + model.infdp\n"
    "            + model.pci * sum(model.fdp[yp] for yp in model.t if ordte[y] > ordte[yp]) == model.infc[y])\n"
    "model.fgap = Constraint(model.t, rule=fgap_rule)"
)

FFDP = (
    "model.ffdp = Constraint(expr=sum(model.fdp[y] for y in model.t) <= model.cfdp)"
)

GINV = (
    "def ginv_rule(model, y):\n"
    "    te = list(model.te)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    LAST = 7\n"
    "    if ordte[y] > LAST:\n"
    "        return pyo.Constraint.Skip\n"
    "    return sum(model.k[jj, y] * model.v[jj, y] for jj in model.j) + model.ka[y] == model.inv[y]\n"
    "model.ginv = Constraint(model.te, rule=ginv_rule)"
)

GSAV = (
    "def gsav_rule(model, y):\n"
    "    return model.inv[y] == model.sav[y] + model.rgap[y]\n"
    "model.gsav = Constraint(model.t, rule=gsav_rule)"
)

GGDP = (
    "def ggdp_rule(model, y):\n"
    "    return model.con[y] + model.sav[y] == model.gdp[y]\n"
    "model.ggdp = Constraint(model.t, rule=ggdp_rule)"
)

DSC = (
    "def dsc_rule(model, y):\n"
    "    te = list(model.te); tt = set(model.t)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    if y not in tt:\n"
    "        return pyo.Constraint.Skip\n"
    "    ym1 = te[ordte[y] - 2]\n"
    "    return model.sav[y] - model.sav[ym1] <= model.mps * (model.gdp[y] - model.gdp[ym1])\n"
    "model.dsc = Constraint(model.te, rule=dsc_rule)"
)

H = (
    "def h_rule(model, y):\n"
    "    te = list(model.te); tt = set(model.t)\n"
    "    ordte = {yy: kk + 1 for kk, yy in enumerate(te)}\n"
    "    if y not in tt:\n"
    "        return pyo.Constraint.Skip\n"
    "    yp1 = te[ordte[y]]\n"
    "    ym1 = te[ordte[y] - 2]\n"
    "    return model.con[yp1] - model.con[y] == model.gamma * (model.con[y] - model.con[ym1])\n"
    "model.h = Constraint(model.te, rule=h_rule)"
)

OBJ1 = (
    "model.obj1 = Constraint(expr=model.max1 == sum(model.w1[y] * model.con[y] for y in model.te))"
)

# Order matches the base model's constraint declaration order.
PER = [
    ("mb", MB,
     "For every commodity of origin and every optimized year, the total use of that "
     "commodity must not exceed what is available. Add up the commodity drawn by each "
     "sector for current production and for building new capacity, the commodity drawn "
     "by capital added to agriculture, by aggregate consumption, and by tourism demand, "
     "the commodity tied up by high-cost manufacture exports accumulated through that "
     "year, the direct exports of the commodity when it is an exportable merchandize, "
     "the commerce and service margin on aggregate merchandize exports, and the service "
     "needed to convert rural workers into urban workers across all skills. Require this "
     "total to be at most zero."),
    ("cap", CAP,
     "For every sector and every optimized year, output cannot exceed installed "
     "capacity. Capacity equals the base-year output plus the capacity built in all "
     "earlier years, where each year of capacity building is counted across the full "
     "length of a period. Require output to be at most this available capacity."),
    ("tic", TIC,
     "For the post-terminal year only, force enough investment in the immediately "
     "preceding year to sustain the economy beyond the horizon. For each commodity of "
     "origin, take the consumption increment into the post-terminal year valued at the "
     "preceding year's consumption propensity, plus the grown capital requirement of the "
     "preceding year's investment, plus the assumed post-terminal increments in exports "
     "and tourism, and require this to be covered by the commodity freed up across a "
     "period by that same preceding-year investment."),
    ("drql", DRQL,
     "For every skill and every optimized year, define the labor requirement. Sum the "
     "labor of that skill needed across all sectors at their output levels. For the "
     "unskilled agricultural workers only, subtract the labor released by capital added "
     "to agriculture in that year and in all earlier years, counting earlier additions "
     "across the full length of a period. Set the labor requirement equal to this total."),
    ("trql", TRQL,
     "For the post-terminal year only, define the labor requirement as it would stand "
     "after the horizon. For every skill, sum across all sectors the labor needed per "
     "unit at the preceding year's output grown by a period of that year's capacity "
     "building. For the unskilled agricultural workers only, subtract the labor released "
     "across a period by capital added to agriculture in all earlier years. Set the "
     "labor requirement equal to this total."),
    ("ldsc", LDSC,
     "For every skill and every optimized year after the first, the labor required must "
     "not exceed the labor available. Availability is the projected exogenous supply of "
     "that skill, plus the net effect of downgrading and upgrading labor between skill "
     "categories, plus the workers graduating into that skill from education processes "
     "that were started in earlier or current years and have matured by then, less the "
     "labor consumed as an input by education processes maturing in that year. Require "
     "the requirement to be at most this availability."),
    ("exdef", EXDEF,
     "For every optimized year, define aggregate merchandize exports. Scale aggregate "
     "merchandize exports by the producers price value and set the result equal to the "
     "sum of direct exports of every merchandize commodity in that year plus the "
     "high-cost manufacture exports accumulated through that year."),
    ("fexch", FEXCH,
     "For every optimized year, balance foreign exchange on the non-competitive imported "
     "commodity. Add up its demand from consumption, from capital added to agriculture, "
     "and from every sector's current production and capacity building, and set that "
     "total equal to aggregate merchandize exports plus tourism earnings plus the "
     "resource gap for that year."),
    ("fgap", FGAP,
     "For every optimized year, define the resource gap through the balance of foreign "
     "capital. Take the resource gap, subtract the concessional and direct private "
     "foreign capital inflows of that year, add the remittances on prior foreign "
     "capital, and add the income payments charged on the stock of direct private "
     "inflows from all earlier years. Set this equal to the interest due on concessional "
     "capital in that year."),
    ("ffdp", FFDP,
     "The direct private foreign capital brought in across all optimized years together "
     "must not exceed the cap on cumulative direct private capital inflows."),
    ("ginv", GINV,
     "For every year up to and including the last optimized year, define aggregate "
     "investment. Sum the capital cost of building new capacity across all sectors and "
     "add the capital put into agriculture, and set this equal to gross domestic "
     "investment in that year."),
    ("gsav", GSAV,
     "For every optimized year, gross domestic investment must equal gross domestic "
     "savings plus the resource gap for that year."),
    ("ggdp", GGDP,
     "For every optimized year, gross domestic product must equal aggregate consumption "
     "plus gross domestic savings."),
    ("dsc", DSC,
     "For every optimized year, the rise in savings from the previous year may not "
     "outpace saving out of growth. Take the increase in savings over the previous year "
     "and require it to be at most the marginal propensity to save applied to the "
     "increase in gross domestic product over the previous year."),
    ("h", H,
     "For every optimized year, consumption must follow a smooth gradual path. The "
     "increase in consumption into the next year must equal a fixed growth factor times "
     "the increase in consumption that occurred from the previous year into the current "
     "year."),
    ("obj1", OBJ1,
     "Define the maximand as the weighted sum of consumption over all years, with the "
     "weights chosen so that it equals consumption in the initial optimized year. Set "
     "the maximand variable equal to this weighted sum."),
]

WHOLESET_PY = "\n".join(p[1] for p in PER)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for every commodity and optimized year, require that total use of the "
    "commodity for production, capacity building, consumption, agricultural capital, "
    "tourism, accumulated high-cost exports, direct exports, trade margins, and "
    "rural-to-urban conversion stays within what is available. "
    "Second, require each sector's output to stay within its base capacity plus all "
    "capacity built in earlier years counted across full periods. "
    "Third, for the post-terminal year, force the preceding year's investment to cover "
    "the consumption increment, grown capital needs, and assumed post-terminal export "
    "and tourism increments. "
    "Fourth, define each skill's labor requirement as sector labor needs less the labor "
    "freed by capital added to agriculture for the unskilled. "
    "Fifth, define the post-terminal labor requirement from the preceding year's grown "
    "output, again netting out freed agricultural labor for the unskilled. "
    "Sixth, for every year after the first, require the labor required to stay within "
    "the supply plus net downgrading and upgrading plus matured education graduates less "
    "education labor inputs. "
    "Seventh, define aggregate merchandize exports as the priced sum of direct "
    "merchandize exports and accumulated high-cost manufacture exports. "
    "Eighth, balance foreign exchange on the imported commodity against exports, "
    "tourism, and the resource gap. "
    "Ninth, define the resource gap from the balance of concessional and private "
    "foreign capital, prior remittances, and income payments on past private inflows. "
    "Tenth, cap the cumulative direct private foreign capital over all years. "
    "Eleventh, define aggregate investment through the last optimized year as the "
    "capital cost of new capacity plus capital added to agriculture. "
    "Twelfth, require investment to equal savings plus the resource gap each year. "
    "Thirteenth, require gross domestic product to equal consumption plus savings each "
    "year. "
    "Fourteenth, hold the yearly rise in savings within the marginal propensity to save "
    "applied to the rise in product. "
    "Fifteenth, require consumption to follow a gradual path so each increment is a "
    "fixed factor of the previous increment. "
    "Finally, define the maximand as the weighted sum of consumption that equals "
    "initial-year consumption."
)

records = [{"description": d, "expected_pyomo": py} for (_, py, d) in PER]
records.append({"description": WHOLESET_DESC, "expected_pyomo": WHOLESET_PY})

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "dinam_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
