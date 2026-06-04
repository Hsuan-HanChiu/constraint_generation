#!/usr/bin/env python
"""Builder for the pdi_lp (production-distribution) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "pdi_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "p", "members": ["one", "two", "three"],
         "doc": "the production facilities"},
        {"name": "d", "members": ["east", "south", "west", "north"],
         "doc": "the distribution centers"},
        {"name": "c", "members": [1, 2, 3, 4, 5],
         "doc": "the customer zones, identified by number"},
        {"name": "m", "members": ["january", "february", "march", "april"],
         "doc": "the months of the planning horizon in chronological order; january is the first month and each later month follows the one before it; april is the final month"},
        {"name": "pf", "members": ["min-prod", "max-prod", "over-prod", "prod-cost", "over-cost"],
         "doc": "the names of the per-facility data fields"},
        {"name": "dcp", "members": ["max-invent", "hold-cost"],
         "doc": "the names of the per-distribution-center data fields"},
        {"name": "czp", "members": ["min-demand", "max-demand", "revenue"],
         "doc": "the names of the per-customer-zone data fields"},
    ],
    "params": [
        {"name": "pfd", "index": "p, pf", "kind": "facility data",
         "doc": "production facility data indexed by facility and field name; pfd[p,'min-prod'] and pfd[p,'max-prod'] are the lower and upper normal-shift production limits in units, pfd[p,'over-prod'] is the overtime production limit in units"},
        {"name": "fdec", "index": "p, d", "kind": "cost / arc mask",
         "doc": "first-echelon shipping cost in dollars per unit from a production facility to a distribution center; a value of zero means there is no shipping link between that facility and that center, so fdec[p,d] not equal to zero identifies the feasible facility-to-center shipping arcs"},
        {"name": "sdec", "index": "d, c", "kind": "cost / arc mask",
         "doc": "second-echelon shipping cost in dollars per unit from a distribution center to a customer zone; a value of zero means there is no shipping link between that center and that zone, so sdec[d,c] not equal to zero identifies the feasible center-to-zone shipping arcs"},
        {"name": "dcd", "index": "d, dcp", "kind": "center data",
         "doc": "distribution center data indexed by center and field name; dcd[d,'max-invent'] is the maximum amount that may be handled at the center in a month in units, dcd[d,'hold-cost'] is the storage cost in dollars per unit per month"},
        {"name": "czd", "index": "c, czp", "kind": "zone data",
         "doc": "customer zone data indexed by zone and field name; czd[c,'min-demand'] and czd[c,'max-demand'] are the lower and upper bounds on the served demand in units, czd[c,'revenue'] is the revenue in dollars per unit sold into that zone"},
        {"name": "pc", "index": "p, m", "kind": "cost",
         "doc": "normal-shift production cost in dollars per unit at each facility in each month"},
        {"name": "pco", "index": "p, m", "kind": "cost",
         "doc": "overtime production cost in dollars per unit at each facility in each month"},
        {"name": "revfac", "index": "m", "kind": "factor",
         "doc": "a dimensionless revenue multiplier applied to each month, scaling the per-unit revenue earned in that month"},
    ],
    "vars": [
        {"name": "x", "index": "p, d, m", "domain": "NonNegativeReals",
         "doc": "units shipped from a production facility to a distribution center in a month"},
        {"name": "y", "index": "d, c, m", "domain": "NonNegativeReals",
         "doc": "units shipped from a distribution center to a customer zone in a month"},
        {"name": "pn", "index": "p, m", "domain": "NonNegativeReals",
         "doc": "normal-shift production in units at each facility in each month"},
        {"name": "po", "index": "p, m", "domain": "NonNegativeReals",
         "doc": "overtime production in units at each facility in each month"},
        {"name": "s", "index": "d, m", "domain": "NonNegativeReals",
         "doc": "the storage level carried at a distribution center at the end of each month in units"},
        {"name": "dm", "index": "c", "domain": "Reals",
         "doc": "the demand level served to each customer zone, in units, taken to be the same in every month"},
        {"name": "h", "index": "d, m", "domain": "NonNegativeReals",
         "doc": "the amount handled at a distribution center in a month in units, that is the goods available there before shipping out to customers"},
        {"name": "profit", "index": "", "domain": "Reals", "doc": "total profit in dollars"},
        {"name": "revenue", "index": "", "domain": "Reals", "doc": "total revenue in dollars over the horizon"},
        {"name": "transport", "index": "", "domain": "Reals", "doc": "total transport cost in dollars over both echelons"},
        {"name": "production", "index": "", "domain": "Reals", "doc": "total production cost in dollars over the horizon"},
        {"name": "holding", "index": "", "domain": "Reals", "doc": "total inventory holding cost in dollars over the horizon"},
    ],
    "objective": {"sense": "maximize", "expr_var": "profit"},
}

NARRATIVE = (
    "We run a two-echelon production and distribution network over a sequence of months. "
    "Several production facilities make goods on normal and overtime shifts, ship them to "
    "distribution centers, which in turn ship to customer zones. Along the way we decide how "
    "much each facility produces on normal and overtime shifts, how much moves on each "
    "facility-to-center and each center-to-zone shipping link each month, how much each center "
    "handles and carries in storage, and how much demand to serve in each customer zone. The "
    "objective is to maximize total profit, which is revenue from sales net of transport, "
    "production, and inventory holding costs."
)

IB = (
    "def ib_rule(model, d, m):\n"
    "    key_list = list(model.m)\n"
    "    m_idx = next((idx for idx, key in enumerate(key_list) if key == m))\n"
    "    if m_idx == 0:\n"
    "        return model.h[d,m] == sum(model.x[p,d,m] for p in model.p if model.fdec[p,d] != 0)\n"
    "    else:\n"
    "        return model.h[d,m] == model.s[d,model.m.prev(m)] + sum(model.x[p,d,m] for p in model.p if model.fdec[p,d] != 0)\n"
    "model.ib = Constraint(model.d, model.m, rule=ib_rule)"
)
PB = (
    "def pb_rule(model, p, m):\n"
    "    return model.pn[p,m] + model.po[p,m] == sum(model.x[p,d,m] for d in model.d if model.fdec[p,d] != 0)\n"
    "model.pb = Constraint(model.p, model.m, rule=pb_rule)"
)
HB = (
    "def hb_rule(model, d, m):\n"
    "    return model.s[d,m] == model.h[d,m] - sum(model.y[d,c,m] for c in model.c if model.sdec[d,c] != 0)\n"
    "model.hb = Constraint(model.d, model.m, rule=hb_rule)"
)
DB = (
    "def db_rule(model, c, m):\n"
    "    return sum(model.y[d,c,m] for d in model.d if model.sdec[d,c] != 0) == model.dm[c]\n"
    "model.db = Constraint(model.c, model.m, rule=db_rule)"
)
AR = (
    "def ar_rule(model):\n"
    "    return model.revenue == sum(model.revfac[m]*model.czd[c,'revenue']*model.y[d,c,m] for d in model.d for c in model.c for m in model.m if model.sdec[d,c] != 0)\n"
    "model.ar = Constraint(rule=ar_rule)"
)
AT = (
    "def at_rule(model):\n"
    "    return model.transport == sum(sum(model.fdec[p,d]*model.x[p,d,m] for p in model.p) + sum(model.sdec[d,c]*model.y[d,c,m] for c in model.c) for d in model.d for m in model.m)\n"
    "model.at = Constraint(rule=at_rule)"
)
AP = (
    "def ap_rule(model):\n"
    "    return model.production == sum(model.pc[p,m]*model.pn[p,m] + model.pco[p,m]*model.po[p,m] for p in model.p for m in model.m)\n"
    "model.ap = Constraint(rule=ap_rule)"
)
AH = (
    "def ah_rule(model):\n"
    "    return model.holding == sum(model.dcd[d,'hold-cost']*model.s[d,m] for d in model.d for m in model.m)\n"
    "model.ah = Constraint(rule=ah_rule)"
)
APR = (
    "def apr_rule(model):\n"
    "    return model.profit == model.revenue - model.transport - model.production - model.holding + 10\n"
    "model.apr = Constraint(rule=apr_rule)"
)
SLO = (
    "def slo_rule(model, d):\n"
    "    return model.s[d,'april'] >= 200\n"
    "model.slo = Constraint(model.d, rule=slo_rule)"
)
HUP = (
    "def hup_rule(model, d, m):\n"
    "    return model.h[d,m] <= model.dcd[d,'max-invent']\n"
    "model.hup = Constraint(model.d, model.m, rule=hup_rule)"
)
PNLO = (
    "def pnlo_rule(model, p, m):\n"
    "    return model.pn[p,m] >= model.pfd[p,'min-prod']\n"
    "model.pnlo = Constraint(model.p, model.m, rule=pnlo_rule)"
)
PNUP = (
    "def pnup_rule(model, p, m):\n"
    "    return model.pn[p,m] <= model.pfd[p,'max-prod']\n"
    "model.pnup = Constraint(model.p, model.m, rule=pnup_rule)"
)
POUP = (
    "def poup_rule(model, p, m):\n"
    "    return model.po[p,m] <= model.pfd[p,'over-prod']\n"
    "model.poup = Constraint(model.p, model.m, rule=poup_rule)"
)
DMLO = (
    "def dmlo_rule(model, c):\n"
    "    return model.dm[c] >= model.czd[c,'min-demand']\n"
    "model.dmlo = Constraint(model.c, rule=dmlo_rule)"
)
DMUP = (
    "def dmup_rule(model, c):\n"
    "    return model.dm[c] <= model.czd[c,'max-demand']\n"
    "model.dmup = Constraint(model.c, rule=dmup_rule)"
)

WHOLESET = "\n".join([IB, PB, HB, DB, AR, AT, AP, AH, APR, SLO, HUP, PNLO, PNUP, POUP, DMLO, DMUP])

records = [
    {"description": (
        "The amount a distribution center has available to handle in a month must reflect what "
        "flows into it. For each center and each month, the handled amount equals the total units "
        "shipped into that center from the production facilities it is linked to, plus whatever was "
        "left in storage at that center at the end of the previous month. In the first month there is "
        "no previous month, so nothing carries over and the handled amount is just the incoming "
        "shipments."),
     "expected_pyomo": IB},
    {"description": (
        "Everything a facility produces in a month has to be shipped out. For each production facility "
        "and each month, the sum of its normal-shift production and its overtime production equals the "
        "total units it ships to the distribution centers it is linked to."),
     "expected_pyomo": PB},
    {"description": (
        "What a distribution center keeps in storage at the end of a month is what is left after it "
        "ships to customers. For each center and each month, the ending storage level equals the amount "
        "handled at the center that month minus the total units shipped out to the customer zones it is "
        "linked to."),
     "expected_pyomo": HB},
    {"description": (
        "Each customer zone must receive exactly the demand level chosen for it. For each customer zone "
        "and each month, the total units shipped into that zone from all the distribution centers linked "
        "to it equals the served demand level of that zone."),
     "expected_pyomo": DB},
    {"description": (
        "Total revenue is what is earned from selling to customers across the whole horizon. Set the "
        "revenue variable equal to the sum over every center-to-zone shipment in every month of the units "
        "shipped, valued at that zone's per-unit revenue and scaled by that month's revenue multiplier. "
        "Only shipments on links that actually exist contribute."),
     "expected_pyomo": AR},
    {"description": (
        "Total transport cost adds up the shipping cost on both echelons over the whole horizon. Set the "
        "transport variable equal to the sum over every month of the first-echelon cost, which charges "
        "each facility-to-center shipment at its per-unit rate, plus the second-echelon cost, which charges "
        "each center-to-zone shipment at its per-unit rate."),
     "expected_pyomo": AT},
    {"description": (
        "Total production cost adds up what it costs to run normal and overtime shifts at every facility "
        "in every month. Set the production variable equal to the sum over all facilities and months of "
        "the normal-shift production valued at its per-unit normal cost plus the overtime production valued "
        "at its per-unit overtime cost."),
     "expected_pyomo": AP},
    {"description": (
        "Total holding cost adds up the cost of carrying inventory at the distribution centers across the "
        "horizon. Set the holding variable equal to the sum over all centers and months of the ending "
        "storage level at each center valued at that center's per-unit storage cost."),
     "expected_pyomo": AH},
    {"description": (
        "Profit ties the financial pieces together. Set the profit variable equal to total revenue minus "
        "total transport cost minus total production cost minus total holding cost, then add a fixed "
        "constant of ten."),
     "expected_pyomo": APR},
    {"description": (
        "Each distribution center must finish the planning horizon with a minimum cushion of stock. For "
        "every center, the storage level carried at the end of the final month must be at least two hundred "
        "units."),
     "expected_pyomo": SLO},
    {"description": (
        "No distribution center may handle more than its capacity allows. For each center and each month, "
        "the amount handled must not exceed that center's maximum handling capacity."),
     "expected_pyomo": HUP},
    {"description": (
        "Every facility has a floor on its normal-shift output. For each facility and each month, the "
        "normal-shift production must be at least that facility's minimum production level."),
     "expected_pyomo": PNLO},
    {"description": (
        "Every facility has a ceiling on its normal-shift output. For each facility and each month, the "
        "normal-shift production must not exceed that facility's maximum production level."),
     "expected_pyomo": PNUP},
    {"description": (
        "Overtime output at a facility is capped. For each facility and each month, the overtime production "
        "must not exceed that facility's overtime production limit."),
     "expected_pyomo": POUP},
    {"description": (
        "The demand served in a customer zone cannot fall below its minimum. For each customer zone, the "
        "served demand level must be at least that zone's minimum demand."),
     "expected_pyomo": DMLO},
    {"description": (
        "The demand served in a customer zone cannot exceed its maximum. For each customer zone, the served "
        "demand level must not exceed that zone's maximum demand."),
     "expected_pyomo": DMUP},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "pdi_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
