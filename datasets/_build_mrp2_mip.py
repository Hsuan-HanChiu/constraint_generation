#!/usr/bin/env python
"""Builder for the mrp2_mip (material requirements planning) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "mrp2_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "PP", "members": ["AJ8172", "LQ8811", "RN0098", "NN1100", "WN7342"],
         "doc": "the set of stock-keeping units (SKUs / items) that can be produced; some items are end products with external demand and others are components used to build other items"},
        {"name": "TT", "members": ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"],
         "doc": "the planning periods (time buckets) in chronological order; the first member is the earliest period and each later member follows the one before it"},
        {"name": "KK", "members": ["HR-101", "MT-402"],
         "doc": "the set of shared production resources whose capacity is consumed when items are produced"},
    ],
    "params": [
        {"name": "R", "index": "PP,PP", "kind": "bill-of-materials",
         "doc": "the number of units of the first item required to build one unit of the second item, defining the bill of materials; zero when the first item is not a component of the second"},
        {"name": "demand", "index": "PP,TT", "kind": "demand",
         "doc": "the external (independent) customer demand for an item in a period, in units; zero when there is no external demand"},
        {"name": "LT", "index": "PP", "kind": "lead-time",
         "doc": "the production lead time of an item, given as a whole number of periods; production started in a period only becomes available to satisfy requirements that many periods later"},
        {"name": "LS", "index": "PP", "kind": "lot-size",
         "doc": "the minimum lot size of an item, in units; whenever an item is produced in a period the quantity produced must be at least this amount"},
        {"name": "I", "index": "PP", "kind": "inventory",
         "doc": "the beginning on-hand inventory of an item available at the start of the horizon, in units"},
        {"name": "U", "index": "PP,KK", "kind": "resource-usage",
         "doc": "the fraction of a resource's available capacity consumed by producing one unit of an item; the resource capacity in each period is normalized to one"},
        {"name": "M", "index": "PP", "kind": "big-M",
         "doc": "a large per-item constant used to switch the production-quantity upper bound on or off depending on whether the item is produced in that period; large enough never to restrict a genuine production decision"},
    ],
    "vars": [
        {"name": "d", "index": "PP,TT", "domain": "Binary",
         "doc": "production indicator; equals 1 if the item is produced in the period and 0 otherwise"},
        {"name": "x", "index": "PP,TT", "domain": "NonNegativeReals",
         "doc": "the quantity of the item produced in the period, in units"},
        {"name": "objvar", "index": "", "domain": "Reals",
         "doc": "the accounting variable holding the objective value"},
    ],
    "objective": {"sense": "minimize", "expr_var": "objvar"},
}

NARRATIVE = (
    "We plan production of a set of items over a sequence of time periods on shared resources. "
    "Items are linked by a bill of materials, so producing one item creates internal demand for "
    "the components that go into it, on top of the external customer demand for finished items. "
    "In each period we decide which items to produce and how many units of each to make. The "
    "objective is to minimize a weighted total of production that pushes output toward later "
    "periods, with quantities produced earlier in the horizon penalized more heavily than the "
    "same quantities produced later."
)

DEFOBJ = (
    "def defobj_rule(model):\n"
    "    TT = list(model.TT)\n"
    "    card = len(TT)\n"
    "    pos = {t: i + 1 for i, t in enumerate(TT)}\n"
    "    return model.objvar == sum(\n"
    "        (card - pos[t] + 1) * model.x[p, t] for p in model.PP for t in model.TT\n"
    "    )\n"
    "model.defobj = Constraint(rule=defobj_rule)"
)

DEFREQ = (
    "def defreq_rule(model, p, t):\n"
    "    TT = list(model.TT)\n"
    "    pos = {tt: i + 1 for i, tt in enumerate(TT)}\n"
    "    lhs = sum(\n"
    "        model.x[p, tp] for tp in model.TT if pos[tp] <= pos[t] - value(model.LT[p])\n"
    "    ) + model.I[p]\n"
    "    rhs = sum(\n"
    "        model.demand[p, tp] + sum(model.R[p, pp] * model.x[pp, tp] for pp in model.PP)\n"
    "        for tp in model.TT if pos[tp] <= pos[t]\n"
    "    )\n"
    "    return lhs >= rhs\n"
    "model.defreq = Constraint(model.PP, model.TT, rule=defreq_rule)"
)

DEFLOT = (
    "def deflot_rule(model, p, t):\n"
    "    return model.x[p, t] >= model.d[p, t] * model.LS[p]\n"
    "model.deflot = Constraint(model.PP, model.TT, rule=deflot_rule)"
)

DEFPROD = (
    "def defprod_rule(model, p, t):\n"
    "    return model.x[p, t] <= model.d[p, t] * model.M[p]\n"
    "model.defprod = Constraint(model.PP, model.TT, rule=defprod_rule)"
)

DEFCAP = (
    "def defcap_rule(model, t, k):\n"
    "    return sum(model.U[p, k] * model.x[p, t] for p in model.PP) <= 1\n"
    "model.defcap = Constraint(model.TT, model.KK, rule=defcap_rule)"
)

WHOLESET = "\n".join([DEFOBJ, DEFREQ, DEFLOT, DEFPROD, DEFCAP])

records = [
    {"description": (
        "Set the objective accounting variable equal to a weighted total of everything produced "
        "across all items and all periods, where each unit of production is weighted by how early "
        "in the horizon it is made. Production in the earliest period carries the largest weight "
        "and the weight decreases by one for each later period, so that the last period carries a "
        "weight of one. The accounting variable must equal the sum of these weighted production "
        "quantities over every item and every period."),
     "expected_pyomo": DEFOBJ},
    {"description": (
        "For each item and each period, everything available to meet that item's needs through "
        "the end of that period must be at least everything required of it through that period. "
        "What is available is the beginning inventory of the item plus all of its production that "
        "has had time to become usable, meaning production started early enough that its lead time "
        "has already elapsed by this period. What is required is the cumulative external demand for "
        "the item together with the cumulative internal demand created by producing the items that "
        "use it as a component, both accumulated from the start of the horizon through this period."),
     "expected_pyomo": DEFREQ},
    {"description": (
        "For each item and each period, whenever the item is produced the quantity made must be at "
        "least its minimum lot size, and when the item is not produced no production quantity is "
        "forced. The amount produced must be at least the lot size scaled by whether the item is "
        "produced in that period."),
     "expected_pyomo": DEFLOT},
    {"description": (
        "For each item and each period, no production can take place unless the item is marked as "
        "produced in that period. The quantity produced must not exceed the item's large allowable "
        "ceiling scaled by whether the item is produced, so that the quantity is forced to zero "
        "whenever the item is not produced and is otherwise effectively unrestricted by this rule."),
     "expected_pyomo": DEFPROD},
    {"description": (
        "For each period and each resource, the total amount of that resource consumed by all "
        "production scheduled in that period must not exceed the resource's available capacity, "
        "where each unit produced of an item consumes its share of the resource and the available "
        "capacity in a period is one."),
     "expected_pyomo": DEFCAP},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, set the "
        "objective accounting variable equal to the total production weighted so that earlier "
        "production counts for more than later production. Second, ensure that for every item and "
        "period the beginning inventory plus the production that has become usable given its lead "
        "time covers the cumulative external and component-driven demand through that period. "
        "Third, require that whenever an item is produced in a period the quantity made reaches at "
        "least its minimum lot size. Fourth, forbid any production of an item in a period unless it "
        "is marked as produced there, holding the quantity below its large ceiling otherwise. "
        "Finally, keep the total resource consumption of all production in each period within each "
        "resource's available capacity."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "mrp2_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
