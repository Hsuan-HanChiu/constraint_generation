#!/usr/bin/env python
"""Builder for the yemcem_mip (Yemen cement capacity-expansion) constraint-generation dataset.

All 17 constraints are linear in the decision variables and are INCLUDED. The
investment-cost account (akap) carries a parameter-only power/ratio term
(size/inv_size)**inv_scale; because every factor in that term is a parameter it
collapses to a constant coefficient, so the constraint is linear and Z3-gradable.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "yemcem_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": ["amran", "baijil", "mafrak"],
         "doc": "the candidate plant sites where production capacity can exist or be installed"},
        {"name": "J", "members": ["sanaa", "hodeideh", "taizz", "ibb", "dhamar"],
         "doc": "the market regions where finished product demand must be met"},
        {"name": "M", "members": ["dry-kiln", "wet-kiln", "mills"],
         "doc": "the productive units (kiln and milling technologies) that consume capacity"},
        {"name": "P", "members": ["dry", "wet", "grind"],
         "doc": "the production processes that can be operated at a plant"},
        {"name": "C", "members": ["cement", "clinker", "fuel"],
         "doc": "the commodities tracked in the material-balance accounting"},
        {"name": "CF", "members": ["cement"],
         "doc": "the subset of commodities that are saleable final products; here just cement"},
        {"name": "CI", "members": ["clinker", "fuel"],
         "doc": "the subset of commodities that are intermediates which may be imported"},
        {"name": "T", "members": ["1983-85", "1986-88", "1989-91", "1992-94"],
         "doc": "the planning time periods over the horizon, in chronological order"},
        {"name": "TE", "members": ["1986-88", "1989-91", "1992-94"],
         "doc": "the periods in which capacity expansion can be decided; the first period 1983-85 is excluded because existing capacity is already in place"},
        {"name": "S", "members": ["small", "medium", "large"],
         "doc": "the discrete kiln sizes that an investment can take"},
        {"name": "MS", "members": ["dry-kiln", "wet-kiln"],
         "doc": "the subset of productive units that exhibit economies of scale, so their capacity is added in discrete kiln sizes"},
        {"name": "MP", "members": ["mills"],
         "doc": "the subset of productive units without economies of scale, whose capacity is added continuously"},
    ],
    "params": [
        {"name": "a", "index": "C,P", "kind": "io-coefficient",
         "doc": "input-output coefficient: tons of a commodity produced (positive) or consumed (negative) per unit level of running a process"},
        {"name": "b", "index": "M,P", "kind": "capacity-use",
         "doc": "units of a productive unit's capacity consumed per unit level of running a process"},
        {"name": "k", "index": "M,I", "kind": "capacity",
         "doc": "the existing base capacity of a productive unit at a plant at the start of the horizon, in tons per year"},
        {"name": "ts", "index": "T,TE", "kind": "incidence",
         "doc": "a 0/1 time-summation incidence: 1 if an expansion period is on or before a given period and therefore already contributing capacity, 0 otherwise"},
        {"name": "klim", "index": "I", "kind": "capacity",
         "doc": "the maximum total capacity that may exist at a plant, in tons per year"},
        {"name": "rc", "index": "P", "kind": "cost",
         "doc": "the recurrent operating cost per unit level of a process"},
        {"name": "fc", "index": "M", "kind": "cost",
         "doc": "the fixed operating cost per ton of installed capacity of a productive unit"},
        {"name": "sigma", "index": "", "kind": "factor",
         "doc": "the capital recovery factor that annualizes investment outlays; a scalar"},
        {"name": "delta", "index": "T", "kind": "factor",
         "doc": "the discount factor applied to each period's cost when forming the present value"},
        {"name": "site", "index": "I", "kind": "factor",
         "doc": "a location cost multiplier applied to investment outlays at a plant"},
        {"name": "size", "index": "S", "kind": "capacity",
         "doc": "the capacity added by installing one kiln of a given discrete size, in tons per year"},
        {"name": "inv_cost", "index": "M", "kind": "cost",
         "doc": "the reference investment cost of a productive unit at its reference size"},
        {"name": "inv_size", "index": "M", "kind": "capacity",
         "doc": "the reference size of a productive unit used to scale its investment cost"},
        {"name": "inv_scale", "index": "M", "kind": "exponent",
         "doc": "the scale-economy exponent for a productive unit; together with the size and reference size it gives a constant unit investment cost for each discrete kiln size"},
        {"name": "muf", "index": "I,J", "kind": "cost",
         "doc": "the unit cost of shipping finished product from a plant to a market"},
        {"name": "muv", "index": "J", "kind": "cost",
         "doc": "the unit cost of delivering imported finished product to a market"},
        {"name": "mue", "index": "I", "kind": "cost",
         "doc": "the unit cost of moving finished product from a plant to the export point"},
        {"name": "mui", "index": "CI,I", "kind": "cost",
         "doc": "the unit cost of moving an imported intermediate to a plant"},
        {"name": "ebu", "index": "T", "kind": "bound",
         "doc": "the maximum total finished-product export allowed in a period"},
        {"name": "vbu", "index": "T", "kind": "bound",
         "doc": "the maximum total finished-product import allowed in a period"},
        {"name": "vibu", "index": "T", "kind": "bound",
         "doc": "the maximum total clinker import allowed in a period"},
        {"name": "pv", "index": "CF|CI", "kind": "price",
         "doc": "the import price of a final product or intermediate commodity"},
        {"name": "d", "index": "J,T,CF", "kind": "demand",
         "doc": "the required demand for a final product in a market and period, in tons"},
    ],
    "vars": [
        {"name": "z", "index": "P,I,T", "domain": "NonNegativeReals",
         "doc": "the operating level of a process at a plant in a period"},
        {"name": "x", "index": "CF,I,J,T", "domain": "NonNegativeReals",
         "doc": "the quantity of a final product shipped from a plant to a market in a period"},
        {"name": "v", "index": "CF,J,T", "domain": "NonNegativeReals",
         "doc": "the quantity of a final product imported and delivered to a market in a period"},
        {"name": "vi", "index": "CI,I,T", "domain": "NonNegativeReals",
         "doc": "the quantity of an intermediate commodity imported to a plant in a period"},
        {"name": "e", "index": "CF,I,T", "domain": "NonNegativeReals",
         "doc": "the quantity of a final product exported from a plant in a period"},
        {"name": "h", "index": "M,I,TE", "domain": "NonNegativeReals",
         "doc": "the amount of capacity of a productive unit added at a plant in an expansion period, in tons per year"},
        {"name": "y", "index": "MS,I,S,TE", "domain": "Binary",
         "doc": "equals 1 if a kiln of a given discrete size is installed for a scale-economy unit at a plant in an expansion period, and 0 otherwise"},
        {"name": "phi", "index": "", "domain": "Reals",
         "doc": "the total discounted cost over the horizon, which the model minimizes"},
        {"name": "phikap", "index": "T", "domain": "Reals",
         "doc": "the capital-investment cost charged in a period"},
        {"name": "phipsi", "index": "T", "domain": "Reals",
         "doc": "the recurrent operating cost charged in a period"},
        {"name": "philam", "index": "T", "domain": "Reals",
         "doc": "the transport cost charged in a period"},
        {"name": "phipi", "index": "T", "domain": "Reals",
         "doc": "the import cost charged in a period"},
        {"name": "phieps", "index": "T", "domain": "Reals",
         "doc": "the export revenue earned in a period"},
        {"name": "phiw", "index": "T", "domain": "Reals",
         "doc": "the working-capital cost charged in a period"},
    ],
    "objective": {"sense": "minimize", "expr_var": "phi"},
}

NARRATIVE = (
    "We plan cement production and capacity expansion for a country with several plant sites and "
    "several market regions over a multi-period horizon. For each period we decide how intensely to "
    "run each production process at each plant, how much capacity of each productive unit to add at "
    "each plant, and for the units with economies of scale which discrete kiln size to install. We "
    "also decide how much finished product to ship from each plant to each market, how much to "
    "import or export, and how much intermediate material to import. A set of accounting variables "
    "tracks the investment, operating, transport, import, export, and working-capital cost of each "
    "period, and these are combined into a single discounted total. The objective is to minimize "
    "that total discounted cost over the whole horizon."
)

# ── constraint ground-truth snippets (native names) ──────────────────────────
MB = (
    "def mb_rule(m, c, i, t):\n"
    "    lhs = sum(m.a[c, p] * m.z[p, i, t] for p in m.P)\n"
    "    if c in m.CI:\n"
    "        lhs += m.vi[c, i, t]\n"
    "    rhs = 0.0\n"
    "    if c in m.CF:\n"
    "        rhs = sum(m.x[c, i, j, t] for j in m.J) + m.e[c, i, t]\n"
    "    return lhs >= rhs\n"
    "model.mb = Constraint(model.C, model.I, model.T, rule=mb_rule)"
)
CC = (
    "def cc_rule(m, mm, i, t):\n"
    "    lhs = sum(m.b[mm, p] * m.z[p, i, t] for p in m.P)\n"
    "    rhs = m.k[mm, i] + sum(m.ts[t, tp] * m.h[mm, i, tp] for tp in m.TE)\n"
    "    return lhs <= rhs\n"
    "model.cc = Constraint(model.M, model.I, model.T, rule=cc_rule)"
)
ID = (
    "def id_rule(m, mm, i, te):\n"
    "    return m.h[mm, i, te] == sum(m.size[s] * m.y[mm, i, s, te] for s in m.S)\n"
    "model.id = Constraint(model.MS, model.I, model.TE, rule=id_rule)"
)
ICH = (
    "def ich_rule(m, mm, i, te):\n"
    "    return sum(m.y[mm, i, s, te] for s in m.S) <= 1.0\n"
    "model.ich = Constraint(model.MS, model.I, model.TE, rule=ich_rule)"
)
LIMIT = (
    "def limit_rule(m, i):\n"
    "    return sum(m.k[mm, i] + sum(m.h[mm, i, te] for te in m.TE) for mm in m.MS) <= m.klim[i]\n"
    "model.limit = Constraint(model.I, rule=limit_rule)"
)
MR = (
    "def mr_rule(m, cf, j, t):\n"
    "    return sum(m.x[cf, i, j, t] for i in m.I) + m.v[cf, j, t] >= m.d[j, t, cf]\n"
    "model.mr = Constraint(model.CF, model.J, model.T, rule=mr_rule)"
)
EB = (
    "def eb_rule(m, t):\n"
    "    return sum(m.e[cf, i, t] for cf in m.CF for i in m.I) <= m.ebu[t]\n"
    "model.eb = Constraint(model.T, rule=eb_rule)"
)
VB = (
    "def vb_rule(m, t):\n"
    "    return sum(m.v[cf, j, t] for cf in m.CF for j in m.J) <= m.vbu[t]\n"
    "model.vb = Constraint(model.T, rule=vb_rule)"
)
VIB = (
    "def vib_rule(m, t):\n"
    "    return sum(m.vi['clinker', i, t] for i in m.I) <= m.vibu[t]\n"
    "model.vib = Constraint(model.T, rule=vib_rule)"
)
OBJ_DEF = (
    "def obj_def_rule(m):\n"
    "    return m.phi == sum(m.delta[t] * (m.phikap[t] + m.phipsi[t] + m.philam[t] + m.phipi[t] + m.phiw[t] - m.phieps[t]) for t in m.T)\n"
    "model.obj_def = Constraint(rule=obj_def_rule)"
)
APSI = (
    "def apsi_rule(m, t):\n"
    "    proc_cost = sum(m.rc[p] * m.z[p, i, t] for p in m.P for i in m.I)\n"
    "    fixed_cost = sum(m.fc[mm] * (m.k[mm, i] + sum(m.ts[t, tp] * m.h[mm, i, tp] for tp in m.TE)) for mm in m.M for i in m.I)\n"
    "    return m.phipsi[t] == 0.001 * (proc_cost + fixed_cost)\n"
    "model.apsi = Constraint(model.T, rule=apsi_rule)"
)
AKAP = (
    "def akap_rule(m, t):\n"
    "    inv_ms = sum(m.site[i] * (m.inv_cost[mm] * (m.size[s] / m.inv_size[mm]) ** m.inv_scale[mm]) * m.y[mm, i, s, tp] * m.ts[t, tp] for mm in m.MS for i in m.I for s in m.S for tp in m.TE)\n"
    "    inv_mp = sum(m.site[i] * (m.inv_cost[mm] / m.inv_size[mm]) * m.h[mm, i, tp] * m.ts[t, tp] for mm in m.MP for i in m.I for tp in m.TE)\n"
    "    return m.phikap[t] == m.sigma * (inv_ms + inv_mp)\n"
    "model.akap = Constraint(model.T, rule=akap_rule)"
)
ALAM = (
    "def alam_rule(m, t):\n"
    "    cement_part = (sum(m.muf[i, j] * m.x[cf, i, j, t] for cf in m.CF for i in m.I for j in m.J)\n"
    "                   + sum(m.muv[j] * m.v[cf, j, t] for cf in m.CF for j in m.J)\n"
    "                   + sum(m.mue[i] * m.e[cf, i, t] for cf in m.CF for i in m.I))\n"
    "    interm_part = sum(m.mui[c, i] * m.vi[c, i, t] for c in m.CI for i in m.I)\n"
    "    return m.philam[t] == 0.001 * (cement_part + interm_part)\n"
    "model.alam = Constraint(model.T, rule=alam_rule)"
)
AEPS = (
    "def aeps_rule(m, t):\n"
    "    return m.phieps[t] == 0.001 * sum(m.e[cf, i, t] for cf in m.CF for i in m.I)\n"
    "model.aeps = Constraint(model.T, rule=aeps_rule)"
)
API = (
    "def api_rule(m, t):\n"
    "    cement_imports = sum(m.pv[cf] * m.v[cf, j, t] for cf in m.CF for j in m.J)\n"
    "    interm_imports = sum(m.pv[c] * m.vi[c, i, t] for c in m.CI for i in m.I)\n"
    "    return m.phipi[t] == 0.001 * (cement_imports + interm_imports)\n"
    "model.api = Constraint(model.T, rule=api_rule)"
)
AW = (
    "def aw_rule(m, t):\n"
    "    return m.phiw[t] == 0.25 * 0.1 * (m.phipsi[t] + m.phipi[t])\n"
    "model.aw = Constraint(model.T, rule=aw_rule)"
)

WHOLESET = "\n".join([MB, CC, ID, ICH, LIMIT, MR, EB, VB, VIB, OBJ_DEF,
                      APSI, AKAP, ALAM, AEPS, API, AW])

records = [
    {"description": (
        "For each commodity, plant, and period, production must be able to cover what leaves. The "
        "amount of the commodity produced by running the processes at the plant, together with any "
        "of that commodity imported when it is an intermediate, must be at least the amount of it "
        "that is shipped out to markets and exported when it is a final product."),
     "expected_pyomo": MB},
    {"description": (
        "For each productive unit, plant, and period, the capacity used cannot exceed the capacity "
        "available. The capacity consumed by running the processes at the plant must not be more "
        "than the existing base capacity of that unit plus all the capacity already added through "
        "expansions that are in effect by that period."),
     "expected_pyomo": CC},
    {"description": (
        "For each scale-economy unit, plant, and expansion period, the capacity added must match the "
        "kiln chosen. The amount of capacity installed equals the capacity contributed by whichever "
        "discrete kiln size is selected in that decision."),
     "expected_pyomo": ID},
    {"description": (
        "For each scale-economy unit, plant, and expansion period, at most one kiln size may be "
        "chosen. The selection across all available sizes can pick at most a single size."),
     "expected_pyomo": ICH},
    {"description": (
        "For each plant, the total capacity that ever exists across the scale-economy units cannot "
        "exceed the plant's capacity ceiling. Summing each such unit's existing base capacity and "
        "all the capacity it adds over the horizon must stay within the plant's limit."),
     "expected_pyomo": LIMIT},
    {"description": (
        "For each final product, market, and period, supply must meet demand. The total shipped to "
        "the market from all plants plus what is imported to that market must be at least the "
        "required demand there."),
     "expected_pyomo": MR},
    {"description": (
        "For each period, total exports of final products are capped. The sum of all final-product "
        "exports from every plant must not exceed the export limit for that period."),
     "expected_pyomo": EB},
    {"description": (
        "For each period, total imports of final products are capped. The sum of all final-product "
        "imports delivered to every market must not exceed the import limit for that period."),
     "expected_pyomo": VB},
    {"description": (
        "For each period, total clinker imports are capped. The sum of clinker imported to every "
        "plant must not exceed the clinker import limit for that period."),
     "expected_pyomo": VIB},
    {"description": (
        "The total discounted cost is defined by adding up, over all periods, the discounted sum of "
        "that period's investment, operating, transport, import, and working-capital costs less its "
        "export revenue."),
     "expected_pyomo": OBJ_DEF},
    {"description": (
        "For each period, the recurrent operating cost is defined. It is a small scaling of the "
        "combined process operating cost across all plants and the fixed cost of all installed "
        "capacity, where installed capacity means each unit's base capacity plus the expansions in "
        "effect by that period."),
     "expected_pyomo": APSI},
    {"description": (
        "For each period, the capital-investment cost is defined. It is the capital recovery factor "
        "applied to the location-adjusted investment outlays charged in that period: for the "
        "scale-economy units, the cost of each chosen kiln size, and for the units without scale "
        "economies, the cost proportional to the capacity added, counting only the expansions that "
        "are in effect by that period."),
     "expected_pyomo": AKAP},
    {"description": (
        "For each period, the transport cost is defined. It is a small scaling of the cost of "
        "shipping final products from plants to markets, delivering imported final products to "
        "markets, moving exported final products to the export point, and moving imported "
        "intermediates to plants."),
     "expected_pyomo": ALAM},
    {"description": (
        "For each period, the export revenue is defined as a small scaling of the total quantity of "
        "final products exported from all plants in that period."),
     "expected_pyomo": AEPS},
    {"description": (
        "For each period, the import cost is defined. It is a small scaling of the cost of imported "
        "final products delivered to markets plus the cost of imported intermediates delivered to "
        "plants, each valued at its import price."),
     "expected_pyomo": API},
    {"description": (
        "For each period, the working-capital cost is defined as a fixed fraction of the sum of that "
        "period's recurrent operating cost and its import cost."),
     "expected_pyomo": AW},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "yemcem_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
