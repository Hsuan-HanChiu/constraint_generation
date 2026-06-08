#!/usr/bin/env python
"""Builder for the alum_mip (World Aluminum Model, MIP) constraint-gen dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "alum_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["usa", "w-europe", "guyana"],
         "doc": "mining regions where bauxite is extracted"},
        {"name": "r", "members": ["western-us", "eastern-us", "guyana"],
         "doc": "producing regions that host refineries and smelters; alumina and aluminum are made here"},
        {"name": "j", "members": ["wn-america", "c-amer+car"],
         "doc": "marketing areas where final aluminum is demanded"},
        {"name": "c", "members": ["highsi", "mono", "tri-201", "alumina", "aluminum", "electr"],
         "doc": "all commodities: the various bauxite grades, the alumina intermediate, final aluminum, and electricity"},
        {"name": "cm", "members": ["highsi", "mono", "tri-201"],
         "doc": "the bauxite grades, a subset of the commodities; these are the raw ores mined"},
        {"name": "ci", "members": ["alumina"],
         "doc": "the intermediate commodities, namely alumina, a subset of the commodities"},
        {"name": "cf", "members": ["aluminum"],
         "doc": "the final products, namely aluminum, a subset of the commodities"},
        {"name": "cl", "members": ["electr"],
         "doc": "the electricity commodity, a subset of the commodities consumed by smelting"},
        {"name": "p", "members": ["ref-hs", "ref-m", "ref-t201", "smelting"],
         "doc": "the refining and smelting processes; each refining process turns one bauxite grade into alumina, and the smelting process turns alumina plus electricity into aluminum"},
        {"name": "m", "members": ["refineryss", "refinerym", "refineryt", "smelter"],
         "doc": "the productive units (physical plants): refineries and smelters"},
        {"name": "mr", "members": ["refineryss", "refinerym", "refineryt"],
         "doc": "the refining units, a subset of the productive units"},
        {"name": "ms", "members": ["smelter"],
         "doc": "the smelting unit, a subset of the productive units"},
        {"name": "seg", "members": [1, 2],
         "doc": "the discrete investment size segments used to build out new capacity in fixed increments"},
        {"name": "l", "members": ["el-actual", "el-hicost"],
         "doc": "the electricity supply types (price tiers); el-hicost is an unlimited high-cost backstop, the others have finite availability"},
        {"name": "f", "members": ["oecd", "ldcs"],
         "doc": "trade blocs used to write inter-bloc trade restrictions"},
        {"name": "cpospi", "members": ["(usa, highsi)", "(w-europe, mono)", "(guyana, tri-201)"],
         "doc": "the set of feasible (mining region, bauxite grade) pairs; a mine can only produce the bauxite grades paired with it here, and any quantity for an unlisted pair is meaningless"},
        {"name": "fr", "members": ["(oecd, western-us)", "(oecd, eastern-us)", "(ldcs, guyana)"],
         "doc": "membership pairs assigning each producing region to its trade bloc"},
        {"name": "fi", "members": ["(oecd, usa)", "(oecd, w-europe)", "(ldcs, guyana)"],
         "doc": "membership pairs assigning each mining region to its trade bloc"},
        {"name": "fj", "members": ["(oecd, wn-america)", "(ldcs, c-amer+car)"],
         "doc": "membership pairs assigning each marketing area to its trade bloc"},
    ],
    "params": [
        {"name": "interval", "index": "", "kind": "scalar",
         "doc": "the number of years in the planning interval, used to convert an annual mine output rate into a cumulative extraction over the interval for the reserve check"},
        {"name": "utm", "index": "", "kind": "scalar",
         "doc": "the fraction of installed mine capacity that is actually usable (capacity utilization for mines)"},
        {"name": "sigma", "index": "", "kind": "scalar",
         "doc": "the capital recovery factor that annualizes lump-sum investment outlays"},
        {"name": "gamma", "index": "", "kind": "scalar",
         "doc": "the fraction of a region's trade flow that is exempt from the bloc self-sufficiency rule; the complement, one minus gamma, is the share that must be met internally"},
        {"name": "pl", "index": "", "kind": "scalar",
         "doc": "the world market price of aluminum"},
        {"name": "a", "index": "c,p", "kind": "io",
         "doc": "input-output coefficients per unit of process activity, in tons of commodity per unit of process; negative values denote inputs consumed and positive values denote outputs produced"},
        {"name": "b", "index": "m,p", "kind": "io",
         "doc": "the amount of a productive unit's capacity used per unit of process activity"},
        {"name": "d", "index": "j", "kind": "demand",
         "doc": "the aluminum demand in each marketing area"},
        {"name": "nmaa2000", "index": "r", "kind": "demand",
         "doc": "non-metallurgical alumina demand drawn off in each producing region"},
        {"name": "nmba2000", "index": "i", "kind": "demand",
         "doc": "non-metallurgical bauxite demand drawn off in each mining region"},
        {"name": "zmbar", "index": "i", "kind": "reserve",
         "doc": "the maximum cumulative bauxite output level available from each mining region over the planning interval (the reserve ceiling)"},
        {"name": "capm", "index": "i", "kind": "capacity",
         "doc": "the existing plus already-committed mine capacity in each mining region"},
        {"name": "capr", "index": "r,m", "kind": "capacity",
         "doc": "the existing plus already-committed refinery or smelter capacity for each productive unit in each producing region"},
        {"name": "utr", "index": "m", "kind": "scalar",
         "doc": "the fraction of installed refinery or smelter capacity that is actually usable for each productive unit"},
        {"name": "sbm", "index": "i,seg", "kind": "size",
         "doc": "the mine plant-size increment associated with each investment segment in each mining region"},
        {"name": "sbr", "index": "m,seg,r", "kind": "size",
         "doc": "the refinery or smelter plant-size increment associated with each investment segment, per unit and producing region"},
        {"name": "om", "index": "i", "kind": "cost",
         "doc": "the operating cost per unit of bauxite mined in each mining region"},
        {"name": "ors", "index": "r,p", "kind": "cost",
         "doc": "the operating cost per unit of process activity at refineries and smelters in each producing region"},
        {"name": "muf", "index": "r,j", "kind": "cost",
         "doc": "the unit transport cost for shipping final aluminum from a producing region to a marketing area"},
        {"name": "mui", "index": "r,r", "kind": "cost",
         "doc": "the unit transport cost for shipping alumina between producing regions (interplant)"},
        {"name": "mur", "index": "i,r", "kind": "cost",
         "doc": "the unit transport cost for shipping bauxite from a mining region to a producing region"},
        {"name": "omegam", "index": "i,seg", "kind": "cost",
         "doc": "the fixed lump-sum investment cost of a mine expansion at each segment in each mining region"},
        {"name": "omegar", "index": "m,seg,r", "kind": "cost",
         "doc": "the fixed lump-sum investment cost of a refinery or smelter expansion at each segment, per unit and producing region"},
        {"name": "prelec", "index": "r,l", "kind": "price",
         "doc": "the electricity price by supply type in each producing region; a zero entry marks a supply type that is unavailable in that region"},
        {"name": "ubar", "index": "r,l", "kind": "capacity",
         "doc": "the upper bound on electricity availability by supply type in each producing region"},
    ],
    "vars": [
        {"name": "xf", "index": "r,j", "domain": "NonNegativeReals",
         "doc": "the quantity of final aluminum shipped from a producing region to a marketing area"},
        {"name": "xi", "index": "r,r", "domain": "NonNegativeReals",
         "doc": "the quantity of alumina shipped between producing regions; the first index is the origin and the second the destination"},
        {"name": "xm", "index": "c,i,r", "domain": "NonNegativeReals",
         "doc": "the quantity of a bauxite grade shipped from a mining region to a producing region"},
        {"name": "z", "index": "p,r", "domain": "NonNegativeReals",
         "doc": "the activity level of each refining or smelting process run in each producing region"},
        {"name": "zm", "index": "cm,i", "domain": "NonNegativeReals",
         "doc": "the output level of each bauxite grade mined in each mining region"},
        {"name": "hm", "index": "i", "domain": "NonNegativeReals",
         "doc": "the continuous amount of new mine capacity added in each mining region"},
        {"name": "hr", "index": "r,m", "domain": "NonNegativeReals",
         "doc": "the continuous amount of new refinery or smelter capacity added for each unit in each producing region"},
        {"name": "sm", "index": "seg,i", "domain": "NonNegativeReals",
         "doc": "the selection weight on each mine investment segment in each mining region; a convex-combination weight that picks how much of a segment's size increment is taken"},
        {"name": "sr", "index": "m,seg,r", "domain": "NonNegativeReals",
         "doc": "the selection weight on each refinery or smelter investment segment, per unit and producing region"},
        {"name": "ym", "index": "i", "domain": "Binary",
         "doc": "the build indicator for a mine expansion in each mining region; one if any expansion is undertaken there and zero otherwise"},
        {"name": "yr", "index": "r,m", "domain": "Binary",
         "doc": "the build indicator for a refinery or smelter expansion for each unit in each producing region; one if any expansion is undertaken and zero otherwise"},
        {"name": "u", "index": "l,r", "domain": "NonNegativeReals",
         "doc": "the electricity supplied of each type in each producing region"},
        {"name": "phiom", "index": "", "domain": "Reals",
         "doc": "the total mine operating cost (an accounting variable)"},
        {"name": "phior", "index": "", "domain": "Reals",
         "doc": "the total refinery and smelter operating cost including electricity (an accounting variable)"},
        {"name": "phit", "index": "", "domain": "Reals",
         "doc": "the total transport cost (an accounting variable)"},
        {"name": "phikm", "index": "", "domain": "Reals",
         "doc": "the total annualized mine investment cost (an accounting variable)"},
        {"name": "phikr", "index": "", "domain": "Reals",
         "doc": "the total annualized refinery and smelter investment cost (an accounting variable)"},
        {"name": "phi4", "index": "", "domain": "Reals",
         "doc": "the grand-total cost (an accounting variable)"},
    ],
    "objective": {"sense": "minimize", "expr_var": "phi4"},
}

NARRATIVE = (
    "We plan the world aluminum industry over a single investment horizon. Bauxite is "
    "mined in a number of mining regions, shipped to producing regions where it is refined "
    "into alumina, and the alumina is then smelted with electricity into aluminum and "
    "shipped to marketing areas to meet demand. We decide how much of each bauxite grade to "
    "mine in each region, how much of each refining and smelting process to run in each "
    "producing region, how much electricity of each supply type to draw, and the full set of "
    "shipments of bauxite, alumina, and finished aluminum across regions and markets. We also "
    "decide how much new mine, refinery, and smelter capacity to build, choosing discrete "
    "investment segments whose selection is governed by build indicators. The objective is to "
    "minimize the total cost, which gathers mine and refinery operating costs, electricity, "
    "transport, and the annualized cost of all new capacity investments."
)

# ── per-constraint expected_pyomo (self-contained; gates rebuilt from live sets) ──
MBM = (
    "def mbm_rule(m, cm, i):\n"
    "    if (i, cm) not in set(m.cpospi):\n"
    "        return Constraint.Skip\n"
    "    return m.zm[cm, i] >= sum(m.xm[cm, i, r] for r in m.r) + m.nmba2000[i]\n"
    "model.mbm = Constraint(model.cm, model.i, rule=mbm_rule)"
)
MBR = (
    "def mbr_rule(m, c, r):\n"
    "    cpos = set(m.cpospi)\n"
    "    prelec_pos = {(rr, ll) for (rr, ll) in m.prelec if value(m.prelec[rr, ll]) != 0}\n"
    "    lhs = sum(m.a[c, p] * m.z[p, r] for p in m.p)\n"
    "    if c in m.cm:\n"
    "        lhs += sum(m.xm[c, i, r] for i in m.i if (i, c) in cpos)\n"
    "    if c in m.ci:\n"
    "        lhs += sum(m.xi[rp, r] for rp in m.r)\n"
    "    if c in m.cl:\n"
    "        lhs += sum(m.u[l, r] for l in m.l if (r, l) in prelec_pos)\n"
    "    rhs = 0\n"
    "    if c in m.cf:\n"
    "        rhs += sum(m.xf[r, j] for j in m.j)\n"
    "    if c in m.ci:\n"
    "        rhs += sum(m.xi[r, rp] for rp in m.r) + m.nmaa2000[r]\n"
    "    return lhs >= rhs\n"
    "model.mbr = Constraint(model.c, model.r, rule=mbr_rule)"
)
FDB = (
    "def fdb_rule(m, j):\n"
    "    return sum(m.xf[r, j] for r in m.r) >= m.d[j]\n"
    "model.fdb = Constraint(model.j, rule=fdb_rule)"
)
RES = (
    "def res_rule(m, cm, i):\n"
    "    if (i, cm) not in set(m.cpospi):\n"
    "        return Constraint.Skip\n"
    "    return m.interval * m.zm[cm, i] <= m.zmbar[i]\n"
    "model.res = Constraint(model.cm, model.i, rule=res_rule)"
)
CCM = (
    "def ccm_rule(m, i):\n"
    "    cpos = set(m.cpospi)\n"
    "    return sum(m.zm[cm, i] for cm in m.cm if (i, cm) in cpos) <= m.utm * (m.capm[i] + m.hm[i])\n"
    "model.ccm = Constraint(model.i, rule=ccm_rule)"
)
CCR = (
    "def ccr_rule(m, r, mm):\n"
    "    return sum(m.b[mm, p] * m.z[p, r] for p in m.p) <= m.utr[mm] * (m.capr[r, mm] + m.hr[r, mm])\n"
    "model.ccr = Constraint(model.r, model.m, rule=ccr_rule)"
)
I1M = (
    "def i1m_rule(m, i):\n"
    "    return m.hm[i] == sum(m.sbm[i, seg] * m.sm[seg, i] for seg in m.seg)\n"
    "model.i1m = Constraint(model.i, rule=i1m_rule)"
)
I1R = (
    "def i1r_rule(m, r, mm):\n"
    "    return m.hr[r, mm] == sum(m.sbr[mm, seg, r] * m.sr[mm, seg, r] for seg in m.seg)\n"
    "model.i1r = Constraint(model.r, model.m, rule=i1r_rule)"
)
I2M = (
    "def i2m_rule(m, i):\n"
    "    return m.ym[i] == sum(m.sm[seg, i] for seg in m.seg)\n"
    "model.i2m = Constraint(model.i, rule=i2m_rule)"
)
I2R = (
    "def i2r_rule(m, r, mm):\n"
    "    return m.yr[r, mm] == sum(m.sr[mm, seg, r] for seg in m.seg)\n"
    "model.i2r = Constraint(model.r, model.m, rule=i2r_rule)"
)
TBA = (
    "def tba_rule(m, f):\n"
    "    cpos = set(m.cpospi); fr = set(m.fr); fi = set(m.fi)\n"
    "    expr = 0\n"
    "    for cm in m.cm:\n"
    "        for i in m.i:\n"
    "            if (i, cm) not in cpos:\n"
    "                continue\n"
    "            for r in m.r:\n"
    "                if (f, r) not in fr:\n"
    "                    continue\n"
    "                term = -m.gamma * m.xm[cm, i, r]\n"
    "                if (f, i) in fi:\n"
    "                    term += m.xm[cm, i, r]\n"
    "                expr += term\n"
    "    return expr >= 0\n"
    "model.tba = Constraint(model.f, rule=tba_rule)"
)
TAA = (
    "def taa_rule(m, f):\n"
    "    fr = set(m.fr)\n"
    "    lhs = (1 - m.gamma) * sum(-m.a[ci, 'smelting'] * m.z['smelting', r]\n"
    "                              for ci in m.ci for r in m.r if (f, r) in fr)\n"
    "    rhs = sum(m.xi[r, rp] for r in m.r for rp in m.r if (f, rp) in fr and (f, r) not in fr)\n"
    "    return lhs >= rhs\n"
    "model.taa = Constraint(model.f, rule=taa_rule)"
)
TAL = (
    "def tal_rule(m, f):\n"
    "    fr = set(m.fr); fj = set(m.fj)\n"
    "    expr = 0\n"
    "    for r in m.r:\n"
    "        for j in m.j:\n"
    "            if (f, j) not in fj:\n"
    "                continue\n"
    "            term = -m.gamma * m.xf[r, j]\n"
    "            if (f, r) in fr:\n"
    "                term += m.xf[r, j]\n"
    "            expr += term\n"
    "    return expr >= 0\n"
    "model.tal = Constraint(model.f, rule=tal_rule)"
)
AOM = (
    "def aom_rule(m):\n"
    "    cpos = set(m.cpospi)\n"
    "    return m.phiom == sum(m.om[i] * m.zm[cm, i]\n"
    "                          for cm in m.cm for i in m.i if (i, cm) in cpos) / 1000\n"
    "model.aom = Constraint(rule=aom_rule)"
)
AOR = (
    "def aor_rule(m):\n"
    "    return m.phior == (sum(m.ors[r, p] * m.z[p, r] for r in m.r for p in m.p)\n"
    "                       + sum(m.prelec[r, l] * m.u[l, r] for r in m.r for l in m.l)) / 1000\n"
    "model.aor = Constraint(rule=aor_rule)"
)
AT = (
    "def at_rule(m):\n"
    "    cpos = set(m.cpospi)\n"
    "    return m.phit == sum(\n"
    "        sum(m.muf[r, j] * m.xf[r, j] for j in m.j)\n"
    "        + sum(m.mui[r, rp] * m.xi[r, rp] for rp in m.r)\n"
    "        + sum(m.mur[i, r] * m.xm[cm, i, r] for cm in m.cm for i in m.i if (i, cm) in cpos)\n"
    "        for r in m.r) / 1000\n"
    "model.at = Constraint(rule=at_rule)"
)
AKM = (
    "def akm_rule(m):\n"
    "    return m.phikm == m.sigma * sum(m.omegam[i, seg] * m.sm[seg, i]\n"
    "                                    for seg in m.seg for i in m.i)\n"
    "model.akm = Constraint(rule=akm_rule)"
)
AKR = (
    "def akr_rule(m):\n"
    "    return m.phikr == m.sigma * sum(m.omegar[mm, seg, r] * m.sr[mm, seg, r]\n"
    "                                    for seg in m.seg for r in m.r for mm in m.m)\n"
    "model.akr = Constraint(rule=akr_rule)"
)
A4 = (
    "def a4_rule(m):\n"
    "    return m.phi4 == m.phit + m.phiom + m.phior + m.phikm + m.phikr\n"
    "model.a4 = Constraint(rule=a4_rule)"
)

# ── per-constraint Tier-1 descriptions ──────────────────────────────────────
records = [
    {"name": "mbm", "intent": "the bauxite mined of each grade in a region covers everything shipped out of it plus local non-metallurgical use",
     "description": (
        "For each mining region and each bauxite grade it can actually produce, the amount of that "
        "grade mined there must be enough to cover everything shipped from that region to the "
        "producing regions plus the non-metallurgical bauxite demand drawn off locally. Grades a "
        "region cannot produce are not constrained."),
     "expected_pyomo": MBM},
    {"name": "mbr", "intent": "in every producing region each commodity is in balance, with what is made and brought in covering what is shipped out and consumed",
     "description": (
        "In every producing region each commodity must balance, with the supply at least covering "
        "the use. Supply comes from whatever the local processes produce of that commodity, plus, "
        "for a bauxite grade, the inflows of that grade shipped in from the mining regions that can "
        "make it; for alumina, the inflows shipped in from other producing regions; and for "
        "electricity, the electricity supplied locally by the available supply types. The "
        "requirements that must be met are, for final aluminum, everything shipped out to the "
        "marketing areas, and for alumina, everything shipped out to other producing regions plus "
        "the local non-metallurgical alumina demand. Processes consume their inputs, which already "
        "enters supply as a negative production amount."),
     "expected_pyomo": MBR},
    {"name": "fdb", "intent": "each marketing area receives at least its aluminum demand",
     "description": (
        "Each marketing area must receive at least its aluminum demand. For every marketing area the "
        "total final aluminum shipped in from all producing regions must be at least the demand "
        "there."),
     "expected_pyomo": FDB},
    {"name": "res", "intent": "cumulative mining of each grade over the horizon stays within the region's reserve",
     "description": (
        "Mining cannot exhaust a region's reserves over the planning horizon. For each mining region "
        "and each bauxite grade it can produce, the annual output level scaled up over the length of "
        "the planning interval must not exceed that region's available reserve. Grades a region "
        "cannot produce are not constrained."),
     "expected_pyomo": RES},
    {"name": "ccm", "intent": "total mining in a region fits within its usable mine capacity including any expansion",
     "description": (
        "Mining in a region is limited by its usable mine capacity. For each mining region, the total "
        "output summed over the bauxite grades it can produce must not exceed the usable fraction of "
        "its capacity, where capacity is the existing committed capacity plus any new capacity built "
        "there."),
     "expected_pyomo": CCM},
    {"name": "ccr", "intent": "each productive unit's process load in a region fits within its usable capacity including any expansion",
     "description": (
        "Each refinery or smelter unit in a producing region is limited by its usable capacity. For "
        "every unit and producing region, the capacity that the processes draw on that unit must not "
        "exceed the usable fraction of its capacity, where capacity is the existing committed "
        "capacity plus any new capacity built for that unit there."),
     "expected_pyomo": CCR},
    {"name": "i1m", "intent": "new mine capacity equals the size increments of the chosen investment segments",
     "description": (
        "The new mine capacity added in a region is defined by the discrete investment segments "
        "chosen. For each mining region, the amount of new mine capacity must equal the sum over the "
        "investment segments of each segment's size increment weighted by how much of that segment "
        "is selected."),
     "expected_pyomo": I1M},
    {"name": "i1r", "intent": "new refinery or smelter capacity equals the size increments of the chosen investment segments",
     "description": (
        "The new refinery or smelter capacity added is defined by the discrete investment segments "
        "chosen. For every unit and producing region, the amount of new capacity must equal the sum "
        "over the investment segments of each segment's size increment weighted by how much of that "
        "segment is selected."),
     "expected_pyomo": I1R},
    {"name": "i2m", "intent": "the mine build indicator equals the total selection weight across segments",
     "description": (
        "A mine expansion is marked as built only to the extent that investment segments are "
        "selected. For each mining region, the build indicator must equal the total selection weight "
        "summed over all investment segments, which ties undertaking any expansion to the indicator."),
     "expected_pyomo": I2M},
    {"name": "i2r", "intent": "the refinery or smelter build indicator equals the total selection weight across segments",
     "description": (
        "A refinery or smelter expansion is marked as built only to the extent that investment "
        "segments are selected. For every unit and producing region, the build indicator must equal "
        "the total selection weight summed over all investment segments."),
     "expected_pyomo": I2R},
    {"name": "tba", "intent": "each bloc supplies enough of its own bauxite shipments, net of the exempt share",
     "description": (
        "For each trade bloc, bauxite trade must be self-sufficient apart from an exempt share. "
        "Looking at all bauxite shipments into producing regions of the bloc, the shipments that "
        "originate from mining regions inside the same bloc must be at least the exempt fraction of "
        "all such shipments into the bloc. Only feasible mine-and-grade combinations enter this "
        "accounting."),
     "expected_pyomo": TBA},
    {"name": "taa", "intent": "each bloc covers its alumina needs internally except for the exempt share",
     "description": (
        "For each trade bloc, alumina supply must be largely internal. The bloc's own alumina "
        "production, reduced to the non-exempt share, must be at least the alumina shipped into the "
        "bloc's producing regions from regions outside the bloc. A region's alumina production is "
        "what its smelting activity consumes as input."),
     "expected_pyomo": TAA},
    {"name": "tal", "intent": "each bloc supplies enough of its own finished aluminum shipments, net of the exempt share",
     "description": (
        "For each trade bloc, finished aluminum trade must be self-sufficient apart from an exempt "
        "share. Looking at all aluminum shipments into the marketing areas of the bloc, the shipments "
        "that originate from producing regions inside the same bloc must be at least the exempt "
        "fraction of all such shipments into the bloc."),
     "expected_pyomo": TAL},
    {"name": "aom", "intent": "mine operating cost totals the per-unit mining cost over all output, in thousands",
     "description": (
        "Total mine operating cost accumulates the cost of everything mined. Set the mine operating "
        "cost accounting variable equal to, over every feasible mining region and bauxite grade, the "
        "per-unit mining cost times the amount mined, expressed in thousands."),
     "expected_pyomo": AOM},
    {"name": "aor", "intent": "refinery and smelter operating cost totals process costs plus electricity, in thousands",
     "description": (
        "Total refinery and smelter operating cost gathers process running costs and electricity. Set "
        "the refinery and smelter operating cost accounting variable equal to the sum over producing "
        "regions and processes of the per-unit process cost times its activity, plus the sum over "
        "producing regions and electricity supply types of the electricity price times the "
        "electricity supplied, expressed in thousands."),
     "expected_pyomo": AOR},
    {"name": "at", "intent": "transport cost totals the shipping of aluminum, alumina, and bauxite, in thousands",
     "description": (
        "Total transport cost gathers all shipping. Set the transport cost accounting variable equal "
        "to, summed over producing regions, the cost of final aluminum shipments to the marketing "
        "areas, plus the cost of alumina shipments to other producing regions, plus the cost of "
        "bauxite shipments from feasible mining regions, each valued at its unit transport cost, all "
        "expressed in thousands."),
     "expected_pyomo": AT},
    {"name": "akm", "intent": "annualized mine investment cost totals the fixed segment costs of the chosen mine expansions",
     "description": (
        "Total mine investment cost annualizes the fixed cost of the mine expansions chosen. Set the "
        "mine investment cost accounting variable equal to the capital recovery factor times the sum "
        "over investment segments and mining regions of each segment's fixed expansion cost weighted "
        "by how much of that segment is selected."),
     "expected_pyomo": AKM},
    {"name": "akr", "intent": "annualized refinery and smelter investment cost totals the fixed segment costs of the chosen expansions",
     "description": (
        "Total refinery and smelter investment cost annualizes the fixed cost of the expansions "
        "chosen. Set the refinery and smelter investment cost accounting variable equal to the "
        "capital recovery factor times the sum over investment segments, producing regions, and "
        "units of each segment's fixed expansion cost weighted by how much of that segment is "
        "selected."),
     "expected_pyomo": AKR},
    {"name": "a4", "intent": "grand-total cost is the sum of transport, operating, and investment cost components",
     "description": (
        "The grand-total cost adds up all the cost components. Set the total cost accounting variable "
        "equal to the sum of the transport cost, the mine operating cost, the refinery and smelter "
        "operating cost, the mine investment cost, and the refinery and smelter investment cost."),
     "expected_pyomo": A4},
]

# ── whole-set ordinal narrative ─────────────────────────────────────────────
ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
            "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth", "Thirteenth",
            "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth"]
parts = ["To build the complete model, enforce the following relationships in order."]
for k, rec in enumerate(records):
    lead = ORDINALS[k] if k < len(records) - 1 else "Finally"
    parts.append(f"{lead}, {rec['intent']}.")
WHOLESET_DESC = " ".join(parts)
WHOLESET_PYOMO = "\n".join(rec["expected_pyomo"] for rec in records)

all_records = [
    {"description": r["description"], "expected_pyomo": r["expected_pyomo"]} for r in records
] + [{"description": WHOLESET_DESC, "expected_pyomo": WHOLESET_PYOMO}]

with open(OUT, "w") as fh:
    for r in all_records:
        fh.write(json.dumps({
            "problem_id": "alum_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(all_records)} records)")
