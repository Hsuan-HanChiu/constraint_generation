#!/usr/bin/env python
"""Builder for the stockcc_easy_mip (discrete-replenishment stock control) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "stockcc_easy_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "nn", "members": ["n1", "n2", "n3", "..."],
         "doc": "the items to be stocked, each replenished independently"},
        {"name": "mm", "members": ["i1", "i2", "i3", "..."],
         "doc": "the candidate replenishment schedules; each member corresponds to one allowed value for how many orders an item is placed on per unit time"},
    ],
    "params": [
        {"name": "N", "index": "", "kind": "limit",
         "doc": "the cap on the total number of replenishments allowed across all items"},
        {"name": "Y", "index": "mm", "kind": "level",
         "doc": "the number of orders per unit time associated with each candidate schedule; choosing schedule mm for an item sets that item's order frequency to this value"},
        {"name": "Dv", "index": "nn", "kind": "value",
         "doc": "for each item, its demand rate multiplied by its unit cost"},
        {"name": "CostZ", "index": "nn,mm", "kind": "cost",
         "doc": "the cost incurred for item nn if it is assigned candidate schedule mm; precomputed as a fixed coefficient for each item-schedule pair"},
    ],
    "vars": [
        {"name": "x", "index": "nn", "domain": "Reals",
         "doc": "the chosen number of orders per unit time for each item; bounded below by the smallest candidate order frequency and above by the largest"},
        {"name": "z", "index": "nn,mm", "domain": "Binary",
         "doc": "equals 1 if item nn is assigned candidate schedule mm, and 0 otherwise"},
        {"name": "obj", "index": "", "domain": "Reals",
         "doc": "the total cost accumulated over all chosen item-schedule assignments"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We manage replenishment for a collection of items. Each item must be assigned exactly one "
    "replenishment schedule chosen from a fixed menu of candidate schedules, and that choice fixes "
    "how often the item is ordered per unit time. Every item-schedule pairing carries a known cost. "
    "We want to pick one schedule for each item so that the total cost across all items is as small "
    "as possible, while respecting an overall limit on how much ordering activity we can do."
)

DEFOBJMIP = (
    "def defobjmip_rule(model):\n"
    "    return model.obj == sum(model.CostZ[nn, mm] * model.z[nn, mm] for nn in model.nn for mm in model.mm)\n"
    "model.defobjmip = Constraint(rule=defobjmip_rule)"
)
CAPACITY = (
    "def capacity_rule(model):\n"
    "    return sum(model.x[nn] for nn in model.nn) <= 3 * model.N\n"
    "model.capacity = Constraint(rule=capacity_rule)"
)
DEFX = (
    "def defx_rule(model, nn):\n"
    "    return sum(model.z[nn, mm] * model.Y[mm] for mm in model.mm) == model.x[nn]\n"
    "model.defx = Constraint(model.nn, rule=defx_rule)"
)
DEFSOS = (
    "def defsos_rule(model, nn):\n"
    "    return sum(model.z[nn, mm] for mm in model.mm) == 1\n"
    "model.defsos = Constraint(model.nn, rule=defsos_rule)"
)
WHOLESET = "\n".join([DEFOBJMIP, CAPACITY, DEFX, DEFSOS])

records = [
    {"description": (
        "The total cost being minimized is built up from the chosen assignments. Add up, across every "
        "item and every candidate schedule, the cost of pairing that item with that schedule whenever "
        "the item is actually assigned to it, and set the total cost equal to that sum."),
     "expected_pyomo": DEFOBJMIP},
    {"description": (
        "There is an overall ceiling on ordering activity. Adding up the chosen order frequency across "
        "all items, the total must not exceed three times the allowed limit on replenishments."),
     "expected_pyomo": CAPACITY},
    {"description": (
        "Each item's order frequency follows from the schedule it is assigned. For every item, its chosen "
        "number of orders per unit time equals the order frequency of whichever candidate schedule it is "
        "assigned to."),
     "expected_pyomo": DEFX},
    {"description": (
        "Every item must be assigned exactly one replenishment schedule. For each item, exactly one of the "
        "candidate schedules is selected and the rest are not."),
     "expected_pyomo": DEFSOS},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "stockcc_easy_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
