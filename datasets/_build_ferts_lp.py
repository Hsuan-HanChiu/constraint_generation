#!/usr/bin/env python
"""Builder for the ferts_lp (EGYPT static fertilizer) constraint-generation dataset.

ferts_lp is a static production-and-distribution LP for the Egyptian fertilizer
sector (gamslib ferts). The model decides plant process levels, domestic shipments
of final products and intermediates, imports of final products and raw materials,
and domestic raw-material purchases, to minimize discounted total cost. The base
.py derives a family of "possibility sets" (which (commodity, plant) and
(process, plant) combinations are structurally allowed) and several transport-cost
parameters from the raw data; the graded constraints are expressed over those
derived sets. Because the grading namespace exposes only `model`, every
expected_pyomo rule reconstructs the derived sets/params it needs from the model's
own components (all params are mutable with default 0.0, so absent keys read as 0).
All constraints are LINEAR: the only division (psii/er) and the possibility-set
guards involve PARAMETERS only, so the resulting expressions are affine in the
decision variables.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "ferts_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["aswan", "helwan", "assiout", "kafr-el-zt", "abu-zaabal"],
         "doc": "the plant locations where production and processing can take place"},
        {"name": "j", "members": ["alexandria", "behera", "gharbia", "kafr-el-sh", "dakahlia", "damietta", "sharkia", "ismailia", "suez", "menoufia", "kalubia", "giza", "beni-suef", "fayoum", "minia", "assiout", "new-valley", "sohag", "quena", "aswan"],
         "doc": "the demand regions that consume final fertilizer products"},
        {"name": "m", "members": ["sulf-a-s", "sulf-a-p", "nitr-acid", "amm-elec", "amm-c-gas", "c-amm-nitr", "amm-sulf", "ssp"],
         "doc": "the productive units, the physical equipment whose installed capacity limits production"},
        {"name": "p", "members": ["sulf-a-s", "sulf-a-p", "nitr-acid", "amm-elec", "amm-c-gas", "can-310", "can-335", "amm-sulf", "ssp-155"],
         "doc": "the production processes that can be operated at a plant"},
        {"name": "cq", "members": ["n", "p2o5"],
         "doc": "the plant nutrients, nitrogen and phosphate"},
        {"name": "c", "members": ["urea", "can-260", "can-310", "can-335", "amm-sulf", "dap", "ssp-155", "c-250-55", "c-300-100", "ammonia", "nitr-acid", "sulf-acid", "el-aswan", "coke-gas", "phos-rock", "limestone", "el-sulfur", "pyrites", "electric", "bf-gas", "water", "steam", "bags"],
         "doc": "all commodities in the model: final products, intermediates, and raw/utility inputs"},
        {"name": "cf", "members": ["urea", "can-260", "can-310", "can-335", "dap", "ssp-155", "c-250-55", "c-300-100", "amm-sulf"],
         "doc": "the final products sold to demand regions; a subset of the commodities"},
        {"name": "ci", "members": ["ammonia", "nitr-acid", "sulf-acid"],
         "doc": "the intermediate products produced and consumed inside the sector; a subset of the commodities"},
        {"name": "cs", "members": ["ammonia", "sulf-acid"],
         "doc": "the intermediates that may be shipped between plants; a subset of the commodities"},
        {"name": "cr", "members": ["el-aswan", "coke-gas", "phos-rock", "limestone", "el-sulfur", "pyrites", "electric", "bf-gas", "water", "steam", "bags", "sulf-acid"],
         "doc": "the domestic raw materials and miscellaneous inputs; a subset of the commodities"},
    ],
    "params": [
        {"name": "cf75", "index": "j,c", "kind": "demand",
         "doc": "the 1974-75 fertilizer requirement of each demand region for each final product, in thousand tons per year; a region requires a product only where this is positive"},
        {"name": "a", "index": "c,p", "kind": "io_coefficient",
         "doc": "input-output coefficients per unit of process level: a positive value means the process produces that commodity, a negative value means it consumes that commodity, zero means no involvement"},
        {"name": "bcap", "index": "m,p", "kind": "io_coefficient",
         "doc": "capacity-utilization coefficients giving how much of a productive unit's capacity one unit of a process consumes"},
        {"name": "pv", "index": "c", "kind": "price",
         "doc": "import prices, cif US dollars per ton 1975; a commodity is importable only where this is positive"},
        {"name": "pd", "index": "i,c", "kind": "price",
         "doc": "domestic purchase prices of raw materials at each plant; a raw material can be purchased domestically at a plant only where this is positive"},
        {"name": "k", "index": "m,i", "kind": "capacity",
         "doc": "the installed capacity of each productive unit at each plant, in thousand tons per year; a unit exists at a plant only where this is positive"},
        {"name": "muf", "index": "i,j", "kind": "cost",
         "doc": "the per-ton transport cost of shipping final products from a plant to a demand region, in pounds per ton"},
        {"name": "mufv", "index": "j", "kind": "cost",
         "doc": "the per-ton transport cost of delivering imported final products from the import point to a demand region"},
        {"name": "mui", "index": "i,i", "kind": "cost",
         "doc": "the per-ton transport cost of shipping intermediates between two plants"},
        {"name": "mur", "index": "i", "kind": "cost",
         "doc": "the per-ton transport cost of moving imported raw materials inland to a plant"},
        {"name": "er", "index": "", "kind": "rate",
         "doc": "the exchange rate converting foreign-currency import value into local pounds"},
        {"name": "util", "index": "", "kind": "rate",
         "doc": "the maximum capacity utilization fraction allowed on any productive unit"},
    ],
    "vars": [
        {"name": "z", "index": "p,i", "domain": "Reals",
         "doc": "the operating level of each process at each plant, in thousand tons per year"},
        {"name": "xf", "index": "cf,i,j", "domain": "NonNegativeReals",
         "doc": "domestic shipment of each final product from each plant to each demand region, in thousand tons per year"},
        {"name": "xi", "index": "cs,i,i", "domain": "NonNegativeReals",
         "doc": "domestic shipment of each shippable intermediate from one plant to another; in this scenario interplant intermediate shipment is turned off so these are all fixed to zero"},
        {"name": "vf", "index": "cf,j", "domain": "NonNegativeReals",
         "doc": "imports of each final product delivered to each demand region, in thousand tons per year"},
        {"name": "vr", "index": "cr,i", "domain": "NonNegativeReals",
         "doc": "imports of each raw material received at each plant, in thousand tons per year"},
        {"name": "u", "index": "cr,i", "domain": "NonNegativeReals",
         "doc": "domestic purchases of each raw material at each plant, in thousand tons per year"},
        {"name": "psi", "index": "", "domain": "Reals",
         "doc": "the discounted total cost, the quantity minimized"},
        {"name": "psip", "index": "", "domain": "Reals",
         "doc": "the domestic recurrent cost component, in thousand pounds per year"},
        {"name": "psil", "index": "", "domain": "Reals",
         "doc": "the transport cost component, in thousand pounds per year"},
        {"name": "psii", "index": "", "domain": "Reals",
         "doc": "the import cost component, in thousand pounds per year"},
    ],
    "objective": {"sense": "minimize", "expr_var": "psi"},
}

NARRATIVE = (
    "This is a static planning model for a national fertilizer sector. We decide how "
    "intensely to run each production process at each plant, how much of each final "
    "product to ship from plants to demand regions, how much of each shippable "
    "intermediate to move between plants, how much of each final product and each raw "
    "material to import, and how much of each raw material to buy domestically at each "
    "plant. Several cost components are tracked separately: a domestic recurrent cost, "
    "a transport cost, and an import cost. The objective is to minimize the discounted "
    "total cost of meeting the country's fertilizer demand."
)

# ---------------------------------------------------------------------------
# Shared reconstruction of the model's derived possibility sets + transport
# params, expressed PURELY from model components (params default to 0.0, so a
# nonzero value flags presence). This header is prepended to every rule so each
# expected_pyomo is self-contained in the grading namespace (only `model`,
# `Constraint`, `sum`, `pyo` available). Mirrors the base .py preprocessing.
# ---------------------------------------------------------------------------
HEADER = (
    "i_set = list(model.i); j_set = list(model.j); m_set = list(model.m)\n"
    "p_set = list(model.p); c_set = list(model.c); cf_set = list(model.cf)\n"
    "cs_set = list(model.cs); cr_set = list(model.cr)\n"
    "av = lambda c,p: pyo.value(model.a[c,p])\n"
    "bv = lambda m,p: pyo.value(model.bcap[m,p])\n"
    "kv = lambda m,ii: pyo.value(model.k[m,ii])\n"
    "pdv = lambda ii,cr: pyo.value(model.pd[ii,cr])\n"
    "pvv = lambda c: pyo.value(model.pv[c])\n"
    "mufv_v = lambda jj: pyo.value(model.mufv[jj])\n"
    "muf_v = lambda ii,jj: pyo.value(model.muf[ii,jj])\n"
    "mui_v = lambda ii,ip: pyo.value(model.mui[ii,ip])\n"
    "mur_v = lambda ii: pyo.value(model.mur[ii])\n"
    "mpos = set((m,ii) for m in m_set for ii in i_set if kv(m,ii)!=0.0)\n"
    "ppos = set()\n"
    "for p in p_set:\n"
    "    for ii in i_set:\n"
    "        if not any((m,ii) not in mpos and bv(m,p)!=0.0 for m in m_set):\n"
    "            ppos.add((p,ii))\n"
    "ppos.discard(('can-310','helwan')); ppos.discard(('can-335','aswan'))\n"
    "cposp = set((c,ii) for c in c_set for ii in i_set if any((p,ii) in ppos and av(c,p)>0.0 for p in p_set))\n"
    "cposn = set((c,ii) for c in c_set for ii in i_set if any((p,ii) in ppos and av(c,p)<0.0 for p in p_set))\n"
    "cposi = set((cs,ii,ip) for cs in cs_set for ii in i_set for ip in i_set if (cs,ii) in cposp and (cs,ip) in cposn)\n"
    "cposd = set((cr,ii) for cr in cr_set for ii in i_set if (cr,ii) in cposn and pdv(ii,cr)!=0.0)\n"
    "cposr = set((cr,ii) for cr in cr_set for ii in i_set if (cr,ii) in cposn and pvv(cr)!=0.0)\n"
)


def with_header(body):
    return HEADER + body


# ── ap: domestic recurrent cost accounting ─────────────────────────────────
AP = with_header(
    "def ap_rule(model):\n"
    "    return model.psip == sum(model.pd[ii,cr]*model.u[cr,ii] for (cr,ii) in cposd)\n"
    "model.ap = Constraint(rule=ap_rule)"
)

# ── al: transport cost accounting ──────────────────────────────────────────
AL = with_header(
    "def al_rule(model):\n"
    "    e = 0.0\n"
    "    for cf in cf_set:\n"
    "        e += sum(muf_v(ii,jj)*model.xf[cf,ii,jj] for ii in i_set for jj in j_set if (cf,ii) in cposp and muf_v(ii,jj)!=0.0)\n"
    "        e += sum(mufv_v(jj)*model.vf[cf,jj] for jj in j_set if mufv_v(jj)!=0.0)\n"
    "    e += sum(mui_v(ii,ip)*model.xi[cs,ii,ip] for (cs,ii,ip) in cposi if mui_v(ii,ip)!=0.0)\n"
    "    e += sum(mur_v(ii)*model.vr[cr,ii] for (cr,ii) in cposr if mur_v(ii)!=0.0)\n"
    "    return model.psil == e\n"
    "model.al = Constraint(rule=al_rule)"
)

# ── ai: import cost accounting ─────────────────────────────────────────────
AI = with_header(
    "def ai_rule(model):\n"
    "    e = sum(model.pv[cf]*model.vf[cf,jj] for cf in cf_set for jj in j_set if pvv(cf)!=0.0)\n"
    "    e += sum(model.pv[cr]*model.vr[cr,ii] for (cr,ii) in cposr if pvv(cr)!=0.0)\n"
    "    return model.psii/model.er == e\n"
    "model.ai = Constraint(rule=ai_rule)"
)

# ── mbdb: material balance on demand ───────────────────────────────────────
MBDB = with_header(
    "mbdb_index = [(cf,jj) for cf in cf_set for jj in j_set if pyo.value(model.cf75[jj,cf])!=0.0]\n"
    "def mbdb_rule(model, cf, jj):\n"
    "    e = sum(model.xf[cf,ii,jj] for ii in i_set if (cf,ii) in cposp)\n"
    "    if pvv(cf)!=0.0:\n"
    "        e += model.vf[cf,jj]\n"
    "    return e >= model.cf75[jj,cf]\n"
    "model.mbdb = Constraint(mbdb_index, rule=mbdb_rule)"
)

# ── mb: commodity material balance at each plant ───────────────────────────
MB = with_header(
    "mb_index = [(c,ii) for c in c_set for ii in i_set]\n"
    "def mb_rule(model, c, ii):\n"
    "    e = sum(model.a[c,p]*model.z[p,ii] for p in p_set if (p,ii) in ppos and av(c,p)!=0.0)\n"
    "    if c in cs_set:\n"
    "        e += sum(model.xi[c,ip,ii] for ip in i_set if (c,ip,ii) in cposi)\n"
    "        e -= sum(model.xi[c,ii,ip] for ip in i_set if (c,ii,ip) in cposi)\n"
    "    if c in cr_set and (c,ii) in cposr:\n"
    "        e += model.vr[c,ii]\n"
    "    if c in cr_set and (c,ii) in cposd:\n"
    "        e += model.u[c,ii]\n"
    "    if c in cf_set and (c,ii) in cposp:\n"
    "        e -= sum(model.xf[c,ii,jj] for jj in j_set)\n"
    "    if not hasattr(e,'is_expression_type') and not hasattr(e,'is_variable_type'):\n"
    "        return Constraint.Skip\n"
    "    return e >= 0\n"
    "model.mb = Constraint(mb_index, rule=mb_rule)"
)

# ── cc: capacity limit on productive units ─────────────────────────────────
CC = with_header(
    "cc_index = [(m,ii) for (m,ii) in mpos]\n"
    "def cc_rule(model, m, ii):\n"
    "    return sum(model.bcap[m,p]*model.z[p,ii] for p in p_set if (p,ii) in ppos and bv(m,p)!=0.0) <= model.util*model.k[m,ii]\n"
    "model.cc = Constraint(cc_index, rule=cc_rule)"
)

# ── objdef: total cost identity ────────────────────────────────────────────
OBJDEF = (
    "def objdef_rule(model):\n"
    "    return model.psi == model.psip + model.psil + model.psii\n"
    "model.objdef = Constraint(rule=objdef_rule)"
)

WHOLESET = "\n".join([AP, AL, AI, MBDB, MB, CC, OBJDEF])

records = [
    {"description": (
        "Define the domestic recurrent cost. It equals the total amount spent buying raw "
        "materials domestically, summed over every plant and raw material that can be "
        "purchased domestically at that plant, valuing each purchase at that plant's local "
        "price for that material. Set the domestic recurrent cost equal to this total."),
     "expected_pyomo": AP},
    {"description": (
        "Define the transport cost. It collects four kinds of freight: shipping final "
        "products from the plants that make them out to the demand regions, delivering "
        "imported final products from the import point to the demand regions, moving "
        "shippable intermediates between plants, and hauling imported raw materials "
        "inland to the plants that receive them. Each movement is valued at its own "
        "per-ton transport rate. Set the transport cost equal to the sum of all these "
        "freight charges."),
     "expected_pyomo": AL},
    {"description": (
        "Define the import cost. The foreign value of imports is the total spent on "
        "imported final products delivered to the demand regions plus the total spent on "
        "imported raw materials received at the plants, each valued at its import price. "
        "Convert that foreign value into local currency through the exchange rate, and set "
        "the import cost equal to it."),
     "expected_pyomo": AI},
    {"description": (
        "Make sure every demand region's requirement for each final product it needs is "
        "met. For each region and each final product the region requires, the total of that "
        "product shipped in from the domestic plants that make it, plus any of it imported "
        "to the region when the product is importable, must be at least the region's "
        "requirement for that product."),
     "expected_pyomo": MBDB},
    {"description": (
        "Keep each commodity in balance at each plant, so that the plant never uses or ships "
        "out more of a commodity than it has available there. For each commodity and plant, "
        "net production by the plant's processes, plus shippable intermediates received from "
        "other plants minus those sent to other plants, plus imported and domestically "
        "purchased raw materials arriving at the plant, minus final product shipped out from "
        "the plant, must be nonnegative. Each term applies only where it is structurally "
        "possible for that commodity and plant."),
     "expected_pyomo": MB},
    {"description": (
        "Respect the installed capacity of every productive unit. For each productive unit "
        "that exists at a plant, the total capacity it consumes across all processes run at "
        "that plant must not exceed the allowed utilization fraction of that unit's installed "
        "capacity there."),
     "expected_pyomo": CC},
    {"description": (
        "Tie the total cost together. The discounted total cost equals the sum of the "
        "domestic recurrent cost, the transport cost, and the import cost."),
     "expected_pyomo": OBJDEF},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, "
        "define the domestic recurrent cost as total domestic raw-material spending across "
        "every plant and material purchasable there, each valued at its local price. Second, "
        "define the transport cost as the combined freight for shipping final products from "
        "plants to regions, delivering imported final products to regions, moving "
        "intermediates between plants, and hauling imported raw materials inland, each at its "
        "own per-ton rate. Third, define the import cost by converting, through the exchange "
        "rate, the foreign value of imported final products and imported raw materials valued "
        "at their import prices. Fourth, ensure every demand region's requirement for each "
        "final product it needs is met by domestic shipments plus any imports of that product. "
        "Fifth, keep every commodity in balance at every plant so net production plus "
        "intermediates received minus those sent plus raw materials arriving minus final "
        "product shipped out stays nonnegative, each term applying only where structurally "
        "possible. Sixth, respect each productive unit's installed capacity by keeping the "
        "capacity it consumes across processes within the allowed utilization fraction. "
        "Finally, set the discounted total cost equal to the sum of the domestic recurrent "
        "cost, the transport cost, and the import cost."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "ferts_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
