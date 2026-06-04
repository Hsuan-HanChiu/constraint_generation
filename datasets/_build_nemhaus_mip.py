#!/usr/bin/env python
"""Builder for the nemhaus_mip (quadratic assignment, linearized) constraint-generation dataset.
Run with plain python (no special deps) to (re)generate the JSONL."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "nemhaus_mip_constraint_gen.jsonl"

# ---- shared model vocabulary (same components block in every record) ----
COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["act-1", "act-2", "act-3", "act-4", "act-5"],
         "doc": "the activities that must each be placed at a facility"},
        {"name": "jj", "members": ["fac-1", "fac-2", "fac-3", "fac-4", "fac-5"],
         "doc": "all candidate facilities"},
        {"name": "j", "members": ["fac-1", "fac-2", "fac-3", "fac-4"],
         "doc": "the facilities that are open and available to host activities; only these may receive an assignment"},
        {"name": "k", "members": ["act-1", "act-2", "act-3", "act-4", "act-5"],
         "doc": "an alias of the activities i, used to index the second activity in a pair of activities"},
    ],
    "params": [
        {"name": "a", "index": "i,k", "kind": "cost",
         "doc": "interaction cost incurred when the first activity and the second activity of a pair are both placed at the same facility; many of these costs are zero, meaning that pair has no interaction"},
    ],
    "vars": [
        {"name": "xb", "index": "i,j", "domain": "Binary",
         "doc": "1 if the activity is assigned to the facility, 0 otherwise"},
        {"name": "y", "index": "i,j,k", "domain": "NonNegativeReals",
         "doc": "stands for the product of the first activity being assigned to the facility and the second activity being assigned to the same facility; it equals 1 only when both activities of the pair are assigned to that facility"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "total interaction cost"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We must place a set of activities into a set of open facilities. Whenever two "
    "activities end up at the same facility, a known interaction cost is incurred for "
    "that pair. We decide which facility each activity is assigned to. The objective "
    "is to make the total interaction cost as small as possible."
)

# ---- ground-truth Pyomo for each constraint (self-contained over model.* only) ----
BSCH = (
    "def bsch_rule(model, i):\n"
    "    return sum(model.xb[i, j] for j in model.j) == 1\n"
    "model.bsch = Constraint(model.i, rule=bsch_rule)"
)

BZDEF = (
    "def bzdef_rule(model):\n"
    "    return model.z == sum(\n"
    "        model.a[i, k] * model.y[i, j, k]\n"
    "        for i in model.i for k in model.k for j in model.j\n"
    "    )\n"
    "model.bzdef = Constraint(rule=bzdef_rule)"
)

YDEF = (
    "def ydef_rule(model, i, j, k):\n"
    "    if model.a[i, k] == 0:\n"
    "        return Constraint.Skip\n"
    "    return model.y[i, j, k] >= model.xb[i, j] + model.xb[k, j] - 1\n"
    "model.ydef = Constraint(model.i, model.j, model.k, rule=ydef_rule)"
)

WHOLESET = "\n".join([BSCH, BZDEF, YDEF])

records = [
    {
        "description": (
            "Every activity must be placed at exactly one of the open facilities. For "
            "each activity, the assignment over all open facilities adds up to exactly one."
        ),
        "expected_pyomo": BSCH,
    },
    {
        "description": (
            "Define the total interaction cost as the interaction cost of each pair of "
            "activities multiplied by whether both activities of the pair share a facility, "
            "added up over every pair of activities and every open facility, and set the "
            "total cost equal to that sum."
        ),
        "expected_pyomo": BZDEF,
    },
    {
        "description": (
            "Tie the shared-facility indicator for a pair of activities to their two "
            "assignments. For each pair of activities and each open facility, the indicator "
            "that both are placed at that facility must be at least one whenever both "
            "activities are assigned there, and otherwise it is free to stay at zero. Only "
            "consider pairs that actually have an interaction cost."
        ),
        "expected_pyomo": YDEF,
    },
    {
        "description": "Generate the complete constraint set for this model.",
        "expected_pyomo": WHOLESET,
    },
]

with open(OUT, "w") as f:
    for r in records:
        rec = {
            "problem_id": "nemhaus_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {OUT} ({len(records)} records)")
