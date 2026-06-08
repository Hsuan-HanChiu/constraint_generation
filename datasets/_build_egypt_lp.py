#!/usr/bin/env python
"""Builder for the egypt_lp (Egypt agricultural / irrigation-water LP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "egypt_lp_constraint_gen.jsonl"

# ── fixed structural data baked into the expected_pyomo so the rules are
#    self-contained (the grader's exec namespace exposes only model/Constraint/sum/pyo) ──
_PREAMBLE = (
    "zone_of = {'u-egypt':'upper','m-egypt':'middle','e-delta':'delta','m-delta':'delta','w-delta':'delta'}\n"
    "sv = {('winter','w-veget'),('winter','w-tomato'),('winter','w-onion'),"
    "('summer','s-veget'),('summer','s-tomato'),('summer','s-potato'),"
    "('nili','n-veget'),('nili','n-tomato'),('nili','n-potato')}\n"
    "cfg = ['lo-berseem','sh-berseem','sugarcane','s-maize','n-maize','sorghum']\n"
    "cfd = ['wheat','barley','rice']\n"
    "tranc = [('m-egypt','m-egypt'),('m-egypt','e-delta'),('m-egypt','m-delta'),"
    "('e-delta','m-egypt'),('e-delta','e-delta'),('e-delta','m-delta'),"
    "('m-delta','m-egypt'),('m-delta','e-delta'),('m-delta','m-delta')]\n"
)

COMPONENTS = {
    "sets": [
        {"name": "c", "members": ["wheat", "barley", "...", "cotton", "rice", "veg-oil", "maize"],
         "doc": "the agricultural commodities (crops and processed products) the country can grow, trade and consume"},
        {"name": "r", "members": ["u-egypt", "m-egypt", "e-delta", "m-delta", "w-delta"],
         "doc": "the five farming regions of the country, defined by their barrages; every region belongs to exactly one agro-climatic zone (upper, middle, or delta)"},
        {"name": "tm", "members": ["oct", "nov", "...", "sep"],
         "doc": "the twelve months of the agricultural year"},
        {"name": "cn", "members": ["wheat", "barley", "...", "potato"],
         "doc": "the commodities that are sold on the national market and therefore have a domestic demand curve"},
        {"name": "cf", "members": ["lo-berseem", "sh-berseem", "wheat", "...", "sugarcane"],
         "doc": "the fodder crops, whose by-products feed livestock"},
        {"name": "ct", "members": ["wheat", "barley"],
         "doc": "the fodder crops whose straw can be physically transported between regions"},
        {"name": "nt", "members": ["protein", "starch"],
         "doc": "the two livestock nutrients tracked, protein and starch"},
        {"name": "s", "members": ["winter", "summer", "nili"],
         "doc": "the three growing seasons; each vegetable crop belongs to one season"},
        {"name": "g", "members": ["1", "2", "...", "10"],
         "doc": "the grid points of the piecewise demand curve; each commodity's domestic demand is split into ten consecutive quantity segments"},
    ],
    "params": [
        {"name": "yld", "index": "(c,c,r)", "kind": "yield",
         "doc": "the marketable yield matrix in tons per 1000 feddans, giving how much of an output commodity comes from growing one unit of a crop in a region; the diagonal carries each crop's own yield and the off-diagonal rows carry oil and aggregate-commodity conversions. An (output, crop, region) triple is absent when that crop is not grown in that region"},
        {"name": "land", "index": "(c,zone,tm)", "kind": "requirement",
         "doc": "the fraction of a feddan a crop occupies in a given zone and month; indexed by agro-climatic zone, not region. Absent when the crop is not in the field that month"},
        {"name": "laborm", "index": "(c,zone,tm)", "kind": "requirement",
         "doc": "the labor a crop needs in man-days per feddan in a given zone and month; indexed by zone, not region"},
        {"name": "water", "index": "(c,zone,tm)", "kind": "requirement",
         "doc": "the irrigation water a crop needs in a given zone and month, in the model's water units; indexed by zone, not region"},
        {"name": "feed", "index": "(cf,zone)", "kind": "yield",
         "doc": "the straw / by-product feed each fodder crop yields per unit grown in a zone, in 1000 tons per 1000 feddans; indexed by zone"},
        {"name": "cropdat", "index": "(c,attr)", "kind": "data",
         "doc": "per-crop technical coefficients; the protein and starch attributes give the nutrient content per ton of fodder as a percentage"},
        {"name": "agrreg", "index": "(r,attr)", "kind": "data",
         "doc": "regional figures; the area attribute is the cultivable land available in a region, and the protein and starch attributes are the region's livestock nutrient requirements. Absent attributes are zero"},
        {"name": "regwagm", "index": "(r,tm)", "kind": "price",
         "doc": "the average daily wage for a man in a region and month"},
        {"name": "netcs", "index": "(c,r)", "kind": "cost",
         "doc": "the per-unit non-labor input cost of growing a crop in a region (machinery, fertilizer, pesticide, seed, net of by-product credit)"},
        {"name": "qs", "index": "(cn,g)", "kind": "data",
         "doc": "the quantity at each demand-curve grid point: the domestic consumption level represented by segment g of a commodity's demand curve"},
        {"name": "ws", "index": "(cn,g)", "kind": "value",
         "doc": "the consumer-welfare value (area under the demand curve) accumulated up to grid point g of a commodity"},
        {"name": "pe", "index": "c", "kind": "price",
         "doc": "the export price of a commodity"},
        {"name": "pm", "index": "c", "kind": "price",
         "doc": "the import price of a commodity"},
        {"name": "los", "index": "cn", "kind": "fraction",
         "doc": "the post-harvest storage-loss fraction of a commodity; the share of gross production lost before it reaches the market. Absent means no loss"},
        {"name": "stran", "index": "(r,r)", "kind": "cost",
         "doc": "the cost of transferring one unit of straw from one region to another"},
        {"name": "veg", "index": "(r,s)", "kind": "limit",
         "doc": "the base vegetable-area figure for a region and season; the actual seasonal cap allows fifty percent above this base"},
        {"name": "grdf", "index": "", "kind": "ratio",
         "doc": "the minimum green-to-dry fodder ratio that regional fodder production must respect"},
        {"name": "day", "index": "", "kind": "data",
         "doc": "the number of working days in a month, used to convert a labor requirement expressed in man-days into man-months"},
        {"name": "prnut", "index": "", "kind": "cost",
         "doc": "the per-unit cost of supplying a livestock nutrient artificially instead of from fodder"},
        {"name": "totmd", "index": "", "kind": "value",
         "doc": "the fixed value of meat and milk output, a constant added to the welfare objective"},
        {"name": "waterlim", "index": "", "kind": "limit",
         "doc": "the total irrigation water available to the whole country over the year"},
    ],
    "vars": [
        {"name": "xcrop", "index": "(r,c)", "domain": "NonNegativeReals",
         "doc": "the area planted to each crop in each region, in 1000 feddans"},
        {"name": "sales", "index": "c", "domain": "NonNegativeReals",
         "doc": "the gross marketable production of each commodity, in 1000 tons"},
        {"name": "imports", "index": "c", "domain": "NonNegativeReals",
         "doc": "the quantity of each commodity imported, in 1000 tons"},
        {"name": "exports", "index": "c", "domain": "NonNegativeReals",
         "doc": "the quantity of each commodity exported, in 1000 tons"},
        {"name": "natq", "index": "(cn,g)", "domain": "NonNegativeReals",
         "doc": "the weight placed on each demand-curve grid point of a commodity; these weights pick where on the piecewise demand curve domestic consumption sits and must form a convex combination"},
        {"name": "fodder", "index": "(r,c)", "domain": "NonNegativeReals",
         "doc": "the straw / by-product fodder available in a region from each crop, in 1000 tons"},
        {"name": "trans", "index": "(ct,r,r)", "domain": "NonNegativeReals",
         "doc": "the straw of a transportable fodder crop moved from one region to another, in 1000 tons"},
        {"name": "anut", "index": "(nt,r)", "domain": "NonNegativeReals",
         "doc": "the amount of each livestock nutrient supplied artificially in a region"},
        {"name": "tlab", "index": "(r,tm)", "domain": "NonNegativeReals",
         "doc": "temporary hired labor used in a region and month, in 1000 man-months"},
        {"name": "flab", "index": "(r,tm)", "domain": "NonNegativeReals",
         "doc": "family labor used in a region and month, in 1000 man-months"},
        {"name": "cps", "index": "", "domain": "Reals",
         "doc": "the total consumer-and-producer surplus, the welfare quantity the model maximizes"},
    ],
    "objective": {"sense": "maximize", "expr_var": "cps"},
}

NARRATIVE = (
    "We plan the country's agriculture for one year across several farming regions. For each "
    "region we decide how many feddans to plant of each crop, how much temporary and family "
    "labor to use in each month, how much fodder to produce and move between regions, and how "
    "much of each nutrient to supply to livestock artificially. At the national level we decide "
    "the gross production of each commodity, how much to import and export, and where domestic "
    "consumption sits along each commodity's demand curve. The objective is to maximize the total "
    "consumer-and-producer surplus, which combines the welfare value of what people consume and "
    "the value of meat and milk, less the cost of crop inputs, hired and family labor, artificial "
    "nutrients, and moving straw between regions."
)

# ── per-constraint expected_pyomo (self-contained; model.-prefixed, native names) ────────

COMB = (
    "def comb_rule(model, cn):\n"
    "    return model.sales[cn] <= sum(model.xcrop[r, c] * model.yld[cn, c, r]\n"
    "        for r in model.r for c in model.c if (cn, c, r) in model.yld)\n"
    "model.comb = Constraint(model.cn, rule=comb_rule)"
)

DEMB = (
    "def demb_rule(model, cn):\n"
    "    loss = pyo.value(model.los[cn]) if cn in model.los else 0.0\n"
    "    return (model.sales[cn] * (1 - loss) + model.imports[cn]\n"
    "        == model.exports[cn] + sum(model.qs[cn, g] * model.natq[cn, g] for g in model.g))\n"
    "model.demb = Constraint(model.cn, rule=demb_rule)"
)

CONV = (
    "def conv_rule(model, cn):\n"
    "    return sum(model.natq[cn, g] for g in model.g) == 1\n"
    "model.conv = Constraint(model.cn, rule=conv_rule)"
)

LANDB = (
    _PREAMBLE +
    "def landb_rule(model, r, tm):\n"
    "    zz = zone_of[r]\n"
    "    lhs = sum(model.xcrop[r, c] * model.land[c, zz, tm]\n"
    "        for c in model.c if (c, zz, tm) in model.land)\n"
    "    area = pyo.value(model.agrreg[r, 'area']) if (r, 'area') in model.agrreg else 0.0\n"
    "    return lhs <= area\n"
    "model.landb = Constraint(model.r, model.tm, rule=landb_rule)"
)

LABBAL = (
    _PREAMBLE +
    "def labbal_rule(model, r, tm):\n"
    "    zz = zone_of[r]\n"
    "    lhs = sum(model.xcrop[r, c] * model.laborm[c, zz, tm]\n"
    "        for c in model.c if (c, zz, tm) in model.laborm) / pyo.value(model.day)\n"
    "    return lhs <= model.tlab[r, tm] + model.flab[r, tm]\n"
    "model.labbal = Constraint(model.r, model.tm, rule=labbal_rule)"
)

WATERB = (
    _PREAMBLE +
    "def waterb_rule(model):\n"
    "    return sum(model.xcrop[r, c] * model.water[c, zone_of[r], tm]\n"
    "        for r in model.r for c in model.c for tm in model.tm\n"
    "        if (c, zone_of[r], tm) in model.water) <= pyo.value(model.waterlim)\n"
    "model.waterb = Constraint(rule=waterb_rule)"
)

VEGETB = (
    _PREAMBLE +
    "def vegetb_rule(model, s, r):\n"
    "    cap = (pyo.value(model.veg[r, s]) if (r, s) in model.veg else 0.0) * 1.5\n"
    "    return sum(model.xcrop[r, c] for c in model.c if (s, c) in sv) <= cap\n"
    "model.vegetb = Constraint(model.s, model.r, rule=vegetb_rule)"
)

FODB = (
    _PREAMBLE +
    "def fodb_rule(model, r, cf):\n"
    "    zz = zone_of[r]\n"
    "    rhs = model.xcrop[r, cf] * (pyo.value(model.feed[cf, zz]) if (cf, zz) in model.feed else 0.0)\n"
    "    if cf in model.ct:\n"
    "        for (ri, rp) in tranc:\n"
    "            if ri == r and ri != rp:\n"
    "                if (cf, rp, r) in model.trans:\n"
    "                    rhs += model.trans[cf, rp, r]\n"
    "                if (cf, r, rp) in model.trans:\n"
    "                    rhs -= model.trans[cf, r, rp]\n"
    "    return model.fodder[r, cf] == rhs\n"
    "model.fodb = Constraint(model.r, model.cf, rule=fodb_rule)"
)

NUTB = (
    "def nutb_rule(model, nt, r):\n"
    "    req = pyo.value(model.agrreg[r, nt]) if (r, nt) in model.agrreg else 0.0\n"
    "    return (sum(model.fodder[r, cf]\n"
    "        * (pyo.value(model.cropdat[cf, nt]) if (cf, nt) in model.cropdat else 0.0) * 0.01\n"
    "        for cf in model.cf) + model.anut[nt, r] >= req)\n"
    "model.nutb = Constraint(model.nt, model.r, rule=nutb_rule)"
)

GFODB = (
    _PREAMBLE +
    "def gfodb_rule(model, r):\n"
    "    return (sum(model.fodder[r, c] for c in cfg) * pyo.value(model.grdf)\n"
    "        <= sum(model.fodder[r, c] for c in cfd))\n"
    "model.gfodb = Constraint(model.r, rule=gfodb_rule)"
)

OBJ_DEF = (
    _PREAMBLE +
    "def obj_def_rule(model):\n"
    "    welfare = sum(\n"
    "        sum(model.natq[cn, g] * model.ws[cn, g] for g in model.g)\n"
    "        + model.exports[cn] * (pyo.value(model.pe[cn]) if cn in model.pe else 0.0)\n"
    "        - model.imports[cn] * (pyo.value(model.pm[cn]) if cn in model.pm else 0.0)\n"
    "        for cn in model.cn)\n"
    "    transcost = sum(model.trans[c, r, rp]\n"
    "        * (pyo.value(model.stran[r, rp]) if (r, rp) in model.stran else 0.0)\n"
    "        for (c, r, rp) in model.trans)\n"
    "    cropcost = sum(model.xcrop[r, c] * model.netcs[c, r]\n"
    "        for r in model.r for c in model.c if (c, r) in model.netcs)\n"
    "    nutcost = sum(model.anut[nt, r] * pyo.value(model.prnut) for nt in model.nt for r in model.r)\n"
    "    labcost = sum((model.flab[r, tm] + 2 * model.tlab[r, tm])\n"
    "        * (pyo.value(model.regwagm[r, tm]) if (r, tm) in model.regwagm else 0.0) * pyo.value(model.day)\n"
    "        for r in model.r for tm in model.tm)\n"
    "    return model.cps == pyo.value(model.totmd) + welfare - transcost - cropcost - nutcost - labcost\n"
    "model.obj_def = Constraint(rule=obj_def_rule)"
)

WHOLESET = "\n".join([COMB, DEMB, CONV, LANDB, LABBAL, WATERB, VEGETB, FODB, NUTB, GFODB, OBJ_DEF])

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, cap each nationally marketed commodity's gross production at the total marketable "
    "output that the planted areas yield across all regions. "
    "Second, balance supply and demand for each marketed commodity, so that production net of "
    "storage loss plus imports equals exports plus the quantity consumed domestically along its "
    "demand curve. "
    "Third, require the domestic-consumption weights chosen along each commodity's demand curve to "
    "form a convex combination, summing to one. "
    "Fourth, keep the land planted in each region and month within the region's available "
    "cultivable area. "
    "Fifth, make sure the labor each region needs in every month, converted from man-days into "
    "man-months, is covered by the temporary and family labor used there. "
    "Sixth, hold total irrigation water used across all regions, crops and months within the "
    "national water supply. "
    "Seventh, limit the area of seasonal vegetables planted in each region and season to that "
    "season's allowed maximum. "
    "Eighth, account for the fodder available in each region from each crop as what its planted "
    "area yields, adjusted for transportable crops by the straw moved in from and out to other "
    "regions. "
    "Ninth, ensure each region's livestock nutrient needs are met by the nutrients in its fodder "
    "together with any artificially supplied nutrient. "
    "Tenth, require each region's green-fodder production, scaled by the minimum green-to-dry "
    "ratio, not to exceed its dry-fodder production. "
    "Finally, define the total surplus as the fixed meat-and-milk value plus consumer welfare and "
    "trade value, less the costs of straw transfer, crop inputs, artificial nutrients, and labor."
)

records = [
    {"description": (
        "For each commodity sold on the national market, its gross marketable production cannot "
        "exceed the total marketable output obtained from the areas planted to the relevant crops "
        "across all regions."),
     "expected_pyomo": COMB},
    {"description": (
        "For each commodity sold on the national market, the supply available to the market must "
        "balance the demand for it. The gross production that survives storage loss, together with "
        "what is imported, must equal what is exported plus the total quantity consumed "
        "domestically along that commodity's demand curve."),
     "expected_pyomo": DEMB},
    {"description": (
        "For each commodity sold on the national market, the weights chosen across the points of "
        "its demand curve must add up to one, so that domestic consumption is a proper combination "
        "of the curve's quantity levels."),
     "expected_pyomo": CONV},
    {"description": (
        "In each region and each month, the total land taken up by the crops growing there must "
        "not exceed the cultivable area available in that region."),
     "expected_pyomo": LANDB},
    {"description": (
        "In each region and each month, the labor required by the crops growing there, expressed "
        "in man-months, must be covered by the temporary labor and family labor used in that "
        "region that month."),
     "expected_pyomo": LABBAL},
    {"description": (
        "The total irrigation water used by all crops across every region and every month must "
        "not exceed the total water available to the country for the year."),
     "expected_pyomo": WATERB},
    {"description": (
        "In each region and each growing season, the area planted to that season's vegetable crops "
        "must not exceed the maximum vegetable area allowed for the region in that season."),
     "expected_pyomo": VEGETB},
    {"description": (
        "In each region, the fodder available from each crop is the fodder its planted area yields "
        "in that region. For the fodder crops whose straw can be moved between regions, this is "
        "adjusted by adding the straw brought in from other regions and subtracting the straw sent "
        "out to other regions."),
     "expected_pyomo": FODB},
    {"description": (
        "In each region, the livestock requirement for each nutrient must be met. The nutrient "
        "supplied by the region's fodder, plus any of that nutrient provided artificially, must be "
        "at least the region's requirement for it."),
     "expected_pyomo": NUTB},
    {"description": (
        "In each region, green fodder cannot dominate the fodder mix. The region's green-fodder "
        "production, scaled down by the minimum green-to-dry ratio, must not exceed its dry-fodder "
        "production."),
     "expected_pyomo": GFODB},
    {"description": (
        "Define the total consumer-and-producer surplus. It equals the fixed value of meat and "
        "milk, plus the welfare value of domestic consumption and the value of exports net of "
        "imports across the marketed commodities, minus the cost of moving straw between regions, "
        "minus the cost of crop inputs over all regions and crops, minus the cost of artificially "
        "supplied nutrients, minus the cost of family and temporary labor over all regions and "
        "months."),
     "expected_pyomo": OBJ_DEF},
    {"description": WHOLESET_DESC,
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "egypt_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
