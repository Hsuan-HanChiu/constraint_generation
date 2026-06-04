#!/usr/bin/env python
"""Builder for the cross_mip (Alcuin's river-crossing) constraint-generation dataset.

All six constraints are linear (degree 1): the only product term, the direction
multiplier times the crossing variable, is param*var. The model is FLAGGED
nonlinear in the corpus but contains no genuinely nonlinear constraint, so all
six are included.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "cross_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["goose", "wolf", "corn"],
         "doc": "the items that must be ferried across the river; the goose, the wolf, and the corn"},
        {"name": "t", "members": ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10"],
         "doc": "the ordered sequence of time periods; the boat makes one trip per period, and the periods alternate between a trip leaving the near bank and a trip returning to the near bank"},
    ],
    "params": [
        {"name": "dir", "index": "t", "kind": "direction",
         "doc": "the travel direction of the boat in each period, equal to plus one in periods where the boat goes from the near bank to the far bank and minus one in periods where the boat returns from the far bank to the near bank; periods alternate starting with plus one in the first period"},
    ],
    "vars": [
        {"name": "y", "index": "i,t", "domain": "Binary",
         "doc": "bank-position indicator, equal to 1 when the item is on the far bank in that period and 0 when it is on the near bank; every item is fixed to the near bank in the first period"},
        {"name": "cross", "index": "i,t", "domain": "NonNegativeReals in [0,1]",
         "doc": "crossing indicator, equal to 1 when the item is carried across the river during that period and 0 otherwise; bounded between 0 and 1"},
        {"name": "done", "index": "t", "domain": "NonNegativeReals in [0,1]",
         "doc": "completion indicator for a period, which can be 1 only when every item is already on the far bank in that period; bounded between 0 and 1"},
        {"name": "nocross", "index": "", "domain": "Reals",
         "doc": "the count of periods in which the crossing is already complete, used as the quantity to be maximized"},
    ],
    "objective": {"sense": "maximize", "expr_var": "obj"},
}

NARRATIVE = (
    "We plan a sequence of boat trips that ferry a goose, a wolf, and a bag of corn from "
    "the near bank of a river to the far bank. For each period we decide which item, if any, "
    "is carried across, and we track which bank each item is on and whether the whole "
    "transfer has been completed by that period. The boat alternates direction period by "
    "period, starting with a trip away from the near bank. We want to keep everything on the "
    "far bank for as many periods as possible, so the objective is to maximize the number of "
    "periods in which the transfer is already complete."
)

DEFCROSS = (
    "def DefCross_rule(m, i, t):\n"
    "    if m.t.ord(t) == len(m.t):\n"
    "        return Constraint.Skip\n"
    "    tn = m.t.next(t)\n"
    "    return m.y[i, tn] == m.y[i, t] + m.dir[t] * m.cross[i, t]\n"
    "model.DefCross = Constraint(model.i, model.t, rule=DefCross_rule)"
)
DEFDONE = (
    "def DefDone_rule(m, i, t):\n"
    "    return m.done[t] <= m.y[i, t]\n"
    "model.DefDone = Constraint(model.i, model.t, rule=DefDone_rule)"
)
LIMCROSS = (
    "def limCross_rule(m, t):\n"
    "    if m.t.ord(t) == len(m.t):\n"
    "        return Constraint.Skip\n"
    "    return sum(m.cross[i, t] for i in m.i) <= 1\n"
    "model.limCross = Constraint(model.t, rule=limCross_rule)"
)
EATNONE1 = (
    "def EatNone1_rule(m, t):\n"
    "    return m.dir[t] * (m.y['goose', t] + m.y['wolf', t] - 1) <= m.done[t]\n"
    "model.EatNone1 = Constraint(model.t, rule=EatNone1_rule)"
)
EATNONE2 = (
    "def EatNone2_rule(m, t):\n"
    "    return m.dir[t] * (m.y['goose', t] + m.y['corn', t] - 1) <= m.done[t]\n"
    "model.EatNone2 = Constraint(model.t, rule=EatNone2_rule)"
)
OBJ = (
    "model.Obj = Constraint(expr=model.nocross == sum(model.done[t] for t in model.t))"
)

WHOLESET = "\n".join([DEFCROSS, DEFDONE, LIMCROSS, EATNONE1, EATNONE2, OBJ])

records = [
    {"description": (
        "Track how each item moves between the banks from one period to the next. In every "
        "period except the last, an item's position on the far bank in the following period "
        "equals its position in the current period adjusted by whether it is carried across "
        "during the current period, where the adjustment follows the boat's travel direction "
        "for that period so that a crossing toward the far bank moves it over and a crossing "
        "on a return trip moves it back."),
     "expected_pyomo": DEFCROSS},
    {"description": (
        "A period can only count as complete when every single item is already on the far bank. "
        "For each item and each period, the completion indicator for that period cannot exceed "
        "that item's far-bank position, so if any item is still on the near bank the period "
        "cannot be marked complete."),
     "expected_pyomo": DEFDONE},
    {"description": (
        "The boat can carry at most one item per trip. In every period except the last, the "
        "total amount of crossing across all items cannot exceed one."),
     "expected_pyomo": LIMCROSS},
    {"description": (
        "The goose and the wolf must never be left together on the bank away from the boat, "
        "since the wolf would eat the goose. For each period, taking account of which bank the "
        "boat is on that period, the situation in which both the goose and the wolf are on that "
        "unguarded bank is forbidden unless the whole transfer is already complete for that "
        "period."),
     "expected_pyomo": EATNONE1},
    {"description": (
        "The goose and the corn must never be left together on the bank away from the boat, "
        "since the goose would eat the corn. For each period, taking account of which bank the "
        "boat is on that period, the situation in which both the goose and the corn are on that "
        "unguarded bank is forbidden unless the whole transfer is already complete for that "
        "period."),
     "expected_pyomo": EATNONE2},
    {"description": (
        "Define the quantity being maximized as the total number of completed periods. It must "
        "equal the sum over all periods of the completion indicator."),
     "expected_pyomo": OBJ},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "cross_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
