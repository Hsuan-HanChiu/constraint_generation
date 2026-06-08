#!/usr/bin/env python
"""Builder for the mexss_lp (Mexico Steel) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "mexss_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["ahmsa", "fundidora", "sicartsa", "hylsa", "hylsap"],
         "doc": "the steel plants where production takes place"},
        {"name": "j", "members": ["mexico-df", "monterrey", "guadalaja"],
         "doc": "the market locations where steel demand must be met"},
        {"name": "c", "members": ["pellets", "coke", "nat-gas", "electric", "scrap",
                                  "pig-iron", "sponge", "steel"],
         "doc": "all commodities handled by the model, spanning raw materials, intermediate products, and final products"},
        {"name": "cf", "members": ["steel"],
         "doc": "the final products, a subset of the commodities; these are the goods that are shipped to markets, exported, or imported"},
        {"name": "ci", "members": ["pig-iron", "sponge"],
         "doc": "the intermediate products, a subset of the commodities; these are produced and consumed internally and are neither purchased nor traded"},
        {"name": "cr", "members": ["pellets", "coke", "nat-gas", "electric", "scrap"],
         "doc": "the raw materials, a subset of the commodities; these can be purchased domestically to feed the processes"},
        {"name": "p", "members": ["pig-iron", "sponge", "steel-oh", "steel-el", "steel-bof"],
         "doc": "the production processes that can be run at each plant"},
        {"name": "m", "members": ["blast-furn", "openhearth", "bof", "direct-red", "elec-arc"],
         "doc": "the productive units (equipment types) at the plants whose capacity limits production"},
    ],
    "params": [
        {"name": "a", "index": "c,p", "kind": "io-coefficient",
         "doc": "the input-output coefficient of each commodity in each process, in units of commodity per unit of process level; positive entries are outputs produced by the process and negative entries are inputs consumed by it"},
        {"name": "b", "index": "m,p", "kind": "utilization",
         "doc": "the amount of a productive unit's capacity consumed per unit of process level when running that process"},
        {"name": "k", "index": "m,i", "kind": "capacity",
         "doc": "the available capacity of each productive unit at each plant, in million tons per year"},
        {"name": "d", "index": "c,j", "kind": "demand",
         "doc": "the demand for each commodity at each market, in million tons per year; only final products carry positive demand"},
        {"name": "muf", "index": "i,j", "kind": "transport-rate",
         "doc": "the unit transport cost for shipping final products from a plant to a market, in US dollars per ton"},
        {"name": "muv", "index": "j", "kind": "transport-rate",
         "doc": "the unit transport cost associated with imports arriving at a market, in US dollars per ton"},
        {"name": "mue", "index": "i", "kind": "transport-rate",
         "doc": "the unit transport cost associated with exports leaving a plant, in US dollars per ton"},
        {"name": "pd", "index": "c", "kind": "price",
         "doc": "the domestic purchase price of each commodity, in US dollars per unit"},
        {"name": "pv", "index": "c", "kind": "price",
         "doc": "the import price of each commodity, in US dollars per unit"},
        {"name": "pe", "index": "c", "kind": "price",
         "doc": "the export price of each commodity, in US dollars per unit"},
        {"name": "eb", "index": "", "kind": "bound",
         "doc": "the overall upper bound on exports of a final product, in million tons per year"},
    ],
    "vars": [
        {"name": "z", "index": "p,i", "domain": "NonNegativeReals",
         "doc": "the level at which each process is run at each plant, in million tons per year"},
        {"name": "x", "index": "c,i,j", "domain": "NonNegativeReals",
         "doc": "the quantity of a commodity shipped from a plant to a market, in million tons per year"},
        {"name": "u", "index": "c,i", "domain": "NonNegativeReals",
         "doc": "the quantity of a commodity purchased domestically at a plant, in million units per year"},
        {"name": "v", "index": "c,j", "domain": "NonNegativeReals",
         "doc": "the quantity of a commodity imported at a market, in million tons per year"},
        {"name": "e", "index": "c,i", "domain": "NonNegativeReals",
         "doc": "the quantity of a commodity exported from a plant, in million tons per year"},
        {"name": "phi", "index": "", "domain": "Reals",
         "doc": "the total cost over the whole system, in million US dollars"},
        {"name": "phipsi", "index": "", "domain": "Reals",
         "doc": "the total raw material purchase cost, in million US dollars"},
        {"name": "philam", "index": "", "domain": "Reals",
         "doc": "the total transport cost, in million US dollars"},
        {"name": "phipi", "index": "", "domain": "Reals",
         "doc": "the total import cost, in million US dollars"},
        {"name": "phieps", "index": "", "domain": "Reals",
         "doc": "the total export revenue, in million US dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "phi"},
}

NARRATIVE = (
    "We plan production and distribution for a set of steel plants that serve several markets. "
    "At each plant we decide how intensively to run each production process, how much raw material "
    "to purchase domestically, and how much of each commodity to ship to markets, to export, or to "
    "import into a market. Running processes turns raw materials and intermediate products into "
    "final products, and the plants are limited by the capacity of their productive units. "
    "Costs accumulate from buying raw materials, transporting goods, and importing, while exporting "
    "earns revenue. The objective is to minimize the total cost across the whole system."
)

# Per-constraint expected_pyomo (model. prefix, native names, self-contained)
MBF = (
    "def mbf_rule(model, cf, i):\n"
    "    return sum(model.a[cf, p] * model.z[p, i] for p in model.p) >= sum(model.x[cf, i, j] for j in model.j) + model.e[cf, i]\n"
    "model.mbf = Constraint(model.cf, model.i, rule=mbf_rule)"
)
MBI = (
    "def mbi_rule(model, ci, i):\n"
    "    return sum(model.a[ci, p] * model.z[p, i] for p in model.p) >= 0\n"
    "model.mbi = Constraint(model.ci, model.i, rule=mbi_rule)"
)
MBR = (
    "def mbr_rule(model, cr, i):\n"
    "    return sum(model.a[cr, p] * model.z[p, i] for p in model.p) + model.u[cr, i] >= 0\n"
    "model.mbr = Constraint(model.cr, model.i, rule=mbr_rule)"
)
CC = (
    "def cc_rule(model, m, i):\n"
    "    return sum(model.b[m, p] * model.z[p, i] for p in model.p) <= model.k[m, i]\n"
    "model.cc = Constraint(model.m, model.i, rule=cc_rule)"
)
MR = (
    "def mr_rule(model, cf, j):\n"
    "    return sum(model.x[cf, i, j] for i in model.i) + model.v[cf, j] >= model.d[cf, j]\n"
    "model.mr = Constraint(model.cf, model.j, rule=mr_rule)"
)
ME = (
    "def me_rule(model, cf):\n"
    "    return sum(model.e[cf, i] for i in model.i) <= model.eb\n"
    "model.me = Constraint(model.cf, rule=me_rule)"
)
APSI = (
    "def apsi_rule(model):\n"
    "    return model.phipsi == sum(model.pd[cr] * model.u[cr, i] for cr in model.cr for i in model.i)\n"
    "model.apsi = Constraint(rule=apsi_rule)"
)
ALAM = (
    "def alam_rule(model):\n"
    "    return model.philam == (\n"
    "        sum(model.muf[i, j] * model.x[cf, i, j] for cf in model.cf for i in model.i for j in model.j)\n"
    "        + sum(model.muv[j] * model.v[cf, j] for cf in model.cf for j in model.j)\n"
    "        + sum(model.mue[i] * model.e[cf, i] for cf in model.cf for i in model.i)\n"
    "    )\n"
    "model.alam = Constraint(rule=alam_rule)"
)
API = (
    "def api_rule(model):\n"
    "    return model.phipi == sum(model.pv[cf] * model.v[cf, j] for cf in model.cf for j in model.j)\n"
    "model.api = Constraint(rule=api_rule)"
)
AEPS = (
    "def aeps_rule(model):\n"
    "    return model.phieps == sum(model.pe[cf] * model.e[cf, i] for cf in model.cf for i in model.i)\n"
    "model.aeps = Constraint(rule=aeps_rule)"
)
OBJ_DEF = (
    "def obj_rule(model):\n"
    "    return model.phi == model.phipsi + model.philam + model.phipi - model.phieps\n"
    "model.obj_def = Constraint(rule=obj_rule)"
)

WHOLESET = "\n".join([MBF, MBI, MBR, CC, MR, ME, APSI, ALAM, API, AEPS, OBJ_DEF])

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, at each plant the total amount of each final product made by its processes must be enough "
    "to cover everything that final product is used for at that plant, namely what is shipped out to "
    "the markets plus what is exported. "
    "Second, at each plant each intermediate product must be produced in at least the amount the "
    "processes consume of it, since intermediates are neither bought nor traded. "
    "Third, at each plant each raw material consumed by the processes must be covered by what is "
    "purchased domestically. "
    "Fourth, at each plant the capacity of every productive unit used by the processes must not exceed "
    "the capacity available for that unit at that plant. "
    "Fifth, at each market the demand for each final product must be satisfied by what is shipped in "
    "from the plants together with what is imported. "
    "Sixth, the total amount of each final product exported across all plants must not exceed the "
    "overall export limit. "
    "Seventh, set the raw material cost equal to the cost of every domestic purchase valued at its "
    "domestic price. "
    "Eighth, set the transport cost equal to the cost of shipping final products from plants to markets, "
    "plus the transport cost tied to imports at the markets, plus the transport cost tied to exports "
    "leaving the plants. "
    "Ninth, set the import cost equal to every import valued at its import price. "
    "Tenth, set the export revenue equal to every export valued at its export price. "
    "Finally, define the total cost as the raw material cost plus the transport cost plus the import "
    "cost, less the export revenue."
)

records = [
    {"description": (
        "At each plant the total amount of each final product produced by running its processes must "
        "be at least as large as everything that final product is needed for at that plant, which is "
        "what gets shipped out to the markets plus what is exported."),
     "expected_pyomo": MBF},
    {"description": (
        "At each plant the net amount of each intermediate product made by the processes must be "
        "nonnegative, because intermediate products are neither purchased nor traded and so can only "
        "be supplied by production."),
     "expected_pyomo": MBI},
    {"description": (
        "At each plant the net amount of each raw material, counting what the processes consume "
        "together with what is purchased domestically, must be nonnegative, so that domestic purchases "
        "cover whatever the processes draw down."),
     "expected_pyomo": MBR},
    {"description": (
        "At each plant the capacity used on each productive unit by the running processes must not "
        "exceed the capacity available for that unit at that plant."),
     "expected_pyomo": CC},
    {"description": (
        "At each market the demand for each final product must be met by the total shipped in from all "
        "the plants together with what is imported at that market."),
     "expected_pyomo": MR},
    {"description": (
        "The total amount of each final product exported across all plants must not exceed the overall "
        "export limit."),
     "expected_pyomo": ME},
    {"description": (
        "Set the raw material cost equal to the total cost of all domestic purchases, valuing each "
        "purchased quantity of raw material at its domestic price and summing over all raw materials "
        "and plants."),
     "expected_pyomo": APSI},
    {"description": (
        "Set the transport cost equal to the cost of moving final products from the plants to the "
        "markets, plus the transport cost associated with imports arriving at the markets, plus the "
        "transport cost associated with exports leaving the plants."),
     "expected_pyomo": ALAM},
    {"description": (
        "Set the import cost equal to the total value of all imports, valuing each imported quantity of "
        "a final product at its import price and summing over all final products and markets."),
     "expected_pyomo": API},
    {"description": (
        "Set the export revenue equal to the total value of all exports, valuing each exported quantity "
        "of a final product at its export price and summing over all final products and plants."),
     "expected_pyomo": AEPS},
    {"description": (
        "Define the total cost as the raw material cost plus the transport cost plus the import cost, "
        "minus the export revenue."),
     "expected_pyomo": OBJ_DEF},
    {"description": WHOLESET_DESC,
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "mexss_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
