#!/usr/bin/env python
"""Builder for the stockcc_mip (stock control / replenishment) constraint-generation dataset.

NOTE: the model's `defobj` constraint defines the objective variable as a sum of
terms of the form 1.5*Dv[nn]/x[nn] — a variable appears in the denominator, so the
expression is NONLINEAR (polynomial_degree() is None). It is NOT Z3-gradable for
logical equivalence and is therefore EXCLUDED. Only the three linear constraints
(capacity, defx, defsos) are emitted.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "stockcc_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "nn", "members": ["n1", "n2", "...", "n48"],
         "doc": "the inventory items being managed, one entry per stocked item"},
        {"name": "mm", "members": ["i1", "i2", "...", "i9"],
         "doc": "the discrete reorder-interval options; each option corresponds to one allowed number of replenishments per unit time, listed from the fewest orders to the most"},
    ],
    "params": [
        {"name": "N", "index": "", "kind": "limit",
         "doc": "the cap on the total number of replenishments per unit time, a single scalar count"},
        {"name": "Y", "index": "mm", "kind": "level",
         "doc": "the candidate number of orders per unit time associated with each reorder-interval option, in orders per unit time; the smallest option value is also the lower bound on an item's order rate and the largest is the upper bound"},
        {"name": "Dv", "index": "nn", "kind": "rate",
         "doc": "for each item, its demand rate multiplied by its unit cost, used only in the (excluded nonlinear) cost expression"},
    ],
    "vars": [
        {"name": "x", "index": "nn", "domain": "Reals",
         "doc": "the chosen number of orders per unit time for each item; bounded below by the smallest candidate order level and above by the largest"},
        {"name": "z", "index": "nn,mm", "domain": "Binary",
         "doc": "a one/zero selection that is 1 when an item is assigned a given reorder-interval option and 0 otherwise; exactly one option is chosen per item"},
        {"name": "obj", "index": "", "domain": "Reals",
         "doc": "the total cost value being minimized"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We manage replenishment for a collection of inventory items. For each item we choose how "
    "often to reorder by picking one option from a fixed menu of allowed order frequencies, which "
    "in turn sets that item's number of orders per unit time. The goal is to minimize the total "
    "ordering and inventory cost across all items."
)

CAPACITY = (
    "def capacity_rule(model):\n"
    "    return sum(model.x[nn] for nn in model.nn) <= 3*model.N\n"
    "model.capacity = Constraint(rule=capacity_rule)"
)
DEFX = (
    "def defx_rule(model, nn):\n"
    "    return sum(model.z[nn, mm]*model.Y[mm] for mm in model.mm) == model.x[nn]\n"
    "model.defx = Constraint(model.nn, rule=defx_rule)"
)
DEFSOS = (
    "def defsos_rule(model, nn):\n"
    "    return sum(model.z[nn, mm] for mm in model.mm) == 1\n"
    "model.defsos = Constraint(model.nn, rule=defsos_rule)"
)
WHOLESET = "\n".join([CAPACITY, DEFX, DEFSOS])

records = [
    {"description": (
        "There is a ceiling on how much ordering activity all items can have together. Adding up "
        "the chosen order rate across every item, the total cannot exceed three times the overall "
        "replenishment cap."),
     "expected_pyomo": CAPACITY},
    {"description": (
        "Each item's chosen order rate has to match the reorder option that was selected for it. "
        "For every item, the order rate equals the order level of whichever option is picked, found "
        "by summing each option's order level weighted by whether that option was chosen for the item."),
     "expected_pyomo": DEFX},
    {"description": (
        "Every item must be assigned exactly one reorder-interval option. For each item, the choices "
        "made across all the available options add up to one."),
     "expected_pyomo": DEFSOS},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "stockcc_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
