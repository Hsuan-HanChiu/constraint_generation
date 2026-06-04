#!/usr/bin/env python
"""Builder for the landing_mip (aircraft landing) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "landing_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "N", "members": [1, 2, 3, 4, 5],
         "doc": "the set of aircraft currently in approach, indexed by integers; ordering of the indices reflects no priority"},
        {"name": "K", "members": [1, 2],
         "doc": "the set of available runways, indexed by integers"},
    ],
    "params": [
        {"name": "c_plus", "index": "N", "kind": "cost",
         "doc": "the penalty charged per unit of time that an aircraft lands after its scheduled time, in cost per time unit"},
        {"name": "S", "index": "N,N", "kind": "separation",
         "doc": "the minimum required separation time between two aircraft that use the same runway in sequence; only defined for ordered pairs where the first index is strictly smaller than the second, with value 5 time units for every such pair"},
        {"name": "E", "index": "N", "kind": "time",
         "doc": "the earliest time at which each aircraft is allowed to land, in time units; equal to 5 for every aircraft"},
        {"name": "L", "index": "N", "kind": "time",
         "doc": "the latest time by which each aircraft is allowed to land, in time units; equal to 1000 for every aircraft"},
        {"name": "T", "index": "N", "kind": "time",
         "doc": "the originally scheduled (target) landing time of each aircraft, in time units; equal to 5 for every aircraft"},
        {"name": "M", "index": "", "kind": "big-M",
         "doc": "a single large constant used to deactivate the separation inequalities when the relevant ordering or runway-assignment conditions do not hold; a scalar with value 20"},
    ],
    "vars": [
        {"name": "w", "index": "N,N", "domain": "Binary",
         "doc": "ordering indicator over a pair of aircraft; equals 1 if the first aircraft lands before the second and 0 otherwise"},
        {"name": "x", "index": "N,K", "domain": "Binary",
         "doc": "runway assignment indicator; equals 1 if the aircraft is allocated to the runway and 0 otherwise"},
        {"name": "t", "index": "N", "domain": "NonNegativeReals",
         "doc": "the landing time of each aircraft, in time units"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We schedule a set of aircraft that are approaching an airport with several runways. For "
    "each aircraft we decide its landing time, which runway it is assigned to, and the order in "
    "which aircraft sharing a runway land relative to one another. Each aircraft has a scheduled "
    "target landing time, and landing later than that target incurs a per-unit-time penalty that "
    "varies by aircraft. The objective is to minimize the total delay penalty summed over all "
    "aircraft."
)

ARRIVAL = (
    "def arrival_time_constr_rule(m, i):\n"
    "    return m.t[i] >= m.T[i]\n"
    "model.arrival_time_constr = Constraint(model.N, rule=arrival_time_constr_rule)"
)
UPPER = (
    "def upper_time_window_constr_rule(m, i):\n"
    "    return m.t[i] <= m.L[i]\n"
    "model.upper_time_window_constr = Constraint(model.N, rule=upper_time_window_constr_rule)"
)
LOWER = (
    "def lower_time_window_constr_rule(m, i):\n"
    "    return m.E[i] <= m.t[i]\n"
    "model.lower_time_window_constr = Constraint(model.N, rule=lower_time_window_constr_rule)"
)
ASSIGN = (
    "def assignment_constr_rule(m, i):\n"
    "    return sum(m.x[i, k] for k in m.K) == 1\n"
    "model.assignment_constr = Constraint(model.N, rule=assignment_constr_rule)"
)
SEQ1 = (
    "def sequencing_constr1_rule(m, i, j, k):\n"
    "    if i < j:\n"
    "        return m.t[i] + m.S[i, j] - m.t[j] <= m.M * (1 - m.w[i, j]) + m.M * (1 - m.x[i, k]) + m.M * (1 - m.x[j, k])\n"
    "    else:\n"
    "        return m.t[i] >= m.T[i]\n"
    "model.sequencing_constr1 = Constraint(model.N, model.N, model.K, rule=sequencing_constr1_rule)"
)
SEQ2 = (
    "def sequencing_constr2_rule(m, i, j, k):\n"
    "    if j > i:\n"
    "        return m.t[j] + m.S[i, j] - m.t[i] <= m.M * m.w[i, j] + m.M * (1 - m.x[i, k]) + m.M * (1 - m.x[j, k])\n"
    "    else:\n"
    "        return m.t[i] >= m.T[i]\n"
    "model.sequencing_constr2 = Constraint(model.N, model.N, model.K, rule=sequencing_constr2_rule)"
)
WHOLESET = "\n".join([ARRIVAL, UPPER, LOWER, ASSIGN, SEQ1, SEQ2])

records = [
    {"description": (
        "Every aircraft must land no earlier than its originally scheduled target time, so each "
        "aircraft either lands on time or later than planned but never ahead of schedule."),
     "expected_pyomo": ARRIVAL},
    {"description": (
        "Each aircraft must land by its latest permitted time. For every aircraft the chosen "
        "landing time cannot exceed the latest time it is allowed to land."),
     "expected_pyomo": UPPER},
    {"description": (
        "Each aircraft must land no earlier than its earliest permitted time. For every aircraft "
        "the chosen landing time must be at least the earliest time it is allowed to land."),
     "expected_pyomo": LOWER},
    {"description": (
        "Every aircraft must be assigned to exactly one runway. For each aircraft, the assignment "
        "across all runways must add up to a single runway."),
     "expected_pyomo": ASSIGN},
    {"description": (
        "When one aircraft is set to land before another and both are using the same runway, the "
        "later one cannot land until enough separation time has passed after the earlier one. For "
        "each pair of aircraft and each runway, whenever the first aircraft is ordered before the "
        "second and both are assigned to that runway, the first aircraft's landing time plus the "
        "required separation must not exceed the second aircraft's landing time. This requirement "
        "is enforced only under that ordering and that shared runway, and is otherwise relaxed so "
        "it does not bind. For pairs that are not in this forward order the requirement reduces to "
        "the plain rule that an aircraft lands no earlier than its scheduled target time."),
     "expected_pyomo": SEQ1},
    {"description": (
        "This is the companion separation requirement for the opposite landing order. When the "
        "second aircraft of a pair is set to land before the first and both share the same runway, "
        "the first one cannot land until enough separation time has passed after the second. For "
        "each pair of aircraft and each runway, whenever the ordering puts the second aircraft "
        "first and both are assigned to that runway, the second aircraft's landing time plus the "
        "required separation must not exceed the first aircraft's landing time. The requirement is "
        "enforced only under that ordering and that shared runway, and is otherwise relaxed so it "
        "does not bind. For pairs that are not in this configuration the requirement reduces to the "
        "plain rule that an aircraft lands no earlier than its scheduled target time."),
     "expected_pyomo": SEQ2},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "landing_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
