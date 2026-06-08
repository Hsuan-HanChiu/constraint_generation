#!/usr/bin/env python
"""Builder for the gapmin_mip (generalized assignment problem) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "gapmin_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["r1", "r2", "r3", "r4", "r5"],
         "doc": "the set of resources (agents) available to carry out work"},
        {"name": "j", "members": ["i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "i9", "i10"],
         "doc": "the set of items (tasks) that each have to be carried out"},
    ],
    "params": [
        {"name": "a", "index": "i,j", "kind": "utilization",
         "doc": "the amount of a resource's capacity consumed when a given item is handled by that resource, in capacity units"},
        {"name": "f", "index": "i,j", "kind": "cost",
         "doc": "the cost incurred when a given item is assigned to a given resource, in cost units"},
        {"name": "b", "index": "i", "kind": "capacity",
         "doc": "the total capacity available at each resource, in capacity units"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "Binary",
         "doc": "assignment indicator; equals 1 if the item is assigned to the resource and 0 otherwise"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total cost of all assignments, in cost units"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We assign a collection of items to a set of resources. For each item we decide which single "
    "resource will handle it, and we also track the total cost that results from all the assignments "
    "we make. Every resource has a limited amount of capacity, and handling an item consumes some of "
    "the resource's capacity and incurs a cost that both depend on which resource is chosen. The "
    "objective is to minimize the total assignment cost."
)

CAPACITY = (
    "def capacity_rule(model, i):\n"
    "    return sum(model.a[i, j] * model.x[i, j] for j in model.j) <= model.b[i]\n"
    "model.capacity = Constraint(model.i, rule=capacity_rule)"
)
CHOICE = (
    "def choice_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.i) == 1\n"
    "model.choice = Constraint(model.j, rule=choice_rule)"
)
DEFZ = (
    "def defz_rule(model):\n"
    "    return model.z == sum(model.f[i, j] * model.x[i, j] for i in model.i for j in model.j)\n"
    "model.defz = Constraint(rule=defz_rule)"
)
WHOLESET = "\n".join([CAPACITY, CHOICE, DEFZ])

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, at each resource the total capacity consumed by the items assigned to it must stay "
    "within that resource's available capacity. "
    "Second, every item must be assigned to exactly one resource. "
    "Finally, the total assignment cost must equal the sum of the costs of all the assignments that "
    "are made."
)

records = [
    {"description": (
        "Each resource has a limited amount of capacity, and handling an item draws on that resource's "
        "capacity by an amount that depends on the item. For each resource, the total capacity consumed "
        "by the items assigned to it must not exceed the capacity available at that resource."),
     "expected_pyomo": CAPACITY},
    {"description": (
        "Every item has to be handled, and no item may be split across resources. For each item, it must "
        "be assigned to exactly one resource."),
     "expected_pyomo": CHOICE},
    {"description": (
        "The total assignment cost accounts for every assignment that is made. Set the total cost equal "
        "to the sum over all items and resources of the cost of assigning that item to that resource "
        "whenever the assignment is in effect."),
     "expected_pyomo": DEFZ},
    {"description": WHOLESET_DESC,
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "gapmin_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
