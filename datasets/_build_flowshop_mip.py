#!/usr/bin/env python
"""Builder for the flowshop_mip (permutation flow-shop scheduling) constraint-generation dataset.
Run with plain python (no special deps) to (re)generate the JSONL."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "flowshop_mip_constraint_gen.jsonl"

# ---- shared model vocabulary (same components block in every record) ----
COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["i1", "i2", "i3"],
         "doc": "the jobs to be processed"},
        {"name": "m", "members": ["bending", "soldering", "assembly"],
         "doc": "the machines, listed in the fixed processing order; every job visits the machines in this same order, starting at the first machine listed and finishing at the last"},
        {"name": "k", "members": ["k1", "k2", "k3"],
         "doc": "the slots in the processing sequence, listed from first to last; the job placed in an earlier slot is processed before the job in a later slot, and all machines use this one common job ordering"},
    ],
    "params": [
        {"name": "proctime", "index": "m,i", "kind": "duration",
         "doc": "the time a machine needs to process a job, in time units, given for each machine and job pair"},
    ],
    "vars": [
        {"name": "rank", "index": "i,k", "domain": "Binary",
         "doc": "1 if the job is placed in the given sequence slot, 0 otherwise"},
        {"name": "start", "index": "m,k", "domain": "NonNegativeReals",
         "doc": "the time the machine begins working on whichever job occupies the given sequence slot"},
        {"name": "comp", "index": "m,k", "domain": "NonNegativeReals",
         "doc": "the time the machine finishes the job that occupies the given sequence slot"},
        {"name": "totwait", "index": "", "domain": "NonNegativeReals",
         "doc": "the makespan, meaning the moment the very last job leaves the very last machine"},
    ],
    "objective": {"sense": "minimize", "expr_var": "totwait"},
}

NARRATIVE = (
    "This is a permutation flow-shop scheduling problem. A set of jobs must each pass "
    "through every machine in one fixed machine order, and all machines process the "
    "jobs in the same single sequence. We decide the order in which the jobs are "
    "processed and the resulting start and finish times on each machine. The "
    "objective is to make the makespan as small as possible, meaning the time at "
    "which the last job clears the last machine."
)

# ---- ground-truth Pyomo for each constraint (self-contained over model.* only) ----
ONEINPOSITION = (
    "def oneInPosition_rule(model, k):\n"
    "    return sum(model.rank[i, k] for i in model.i) == 1\n"
    "model.oneInPosition = Constraint(model.k, rule=oneInPosition_rule)"
)

ONERANKPER = (
    "def oneRankPer_rule(model, i):\n"
    "    return sum(model.rank[i, k] for k in model.k) == 1\n"
    "model.oneRankPer = Constraint(model.i, rule=oneRankPer_rule)"
)

ONMACHREL = (
    "k_list = list(model.k)\n"
    "def onmachrel_rule(model, m, k):\n"
    "    k_idx = k_list.index(k)\n"
    "    if k_idx < len(k_list) - 1:\n"
    "        k_next = k_list[k_idx + 1]\n"
    "        return model.start[m, k_next] >= model.comp[m, k]\n"
    "    return Constraint.Skip\n"
    "model.onmachrel = Constraint(model.m, model.k, rule=onmachrel_rule)"
)

PERMACHREL = (
    "m_list = list(model.m)\n"
    "def permachrel_rule(model, m, k):\n"
    "    m_idx = m_list.index(m)\n"
    "    if m_idx < len(m_list) - 1:\n"
    "        m_next = m_list[m_idx + 1]\n"
    "        return model.start[m_next, k] >= model.comp[m, k]\n"
    "    return Constraint.Skip\n"
    "model.permachrel = Constraint(model.m, model.k, rule=permachrel_rule)"
)

DEFCOMP = (
    "def defcomp_rule(model, m, k):\n"
    "    return model.comp[m, k] == model.start[m, k] + sum(model.proctime[m, i] * model.rank[i, k] for i in model.i)\n"
    "model.defcomp = Constraint(model.m, model.k, rule=defcomp_rule)"
)

DEFOBJ = (
    "lastmachine = list(model.m)[-1]\n"
    "lastrank = list(model.k)[-1]\n"
    "def defobj_rule(model):\n"
    "    return model.totwait >= model.comp[lastmachine, lastrank]\n"
    "model.defobj = Constraint(rule=defobj_rule)"
)

WHOLESET = "\n".join([ONEINPOSITION, ONERANKPER, ONMACHREL, PERMACHREL, DEFCOMP, DEFOBJ])

records = [
    {
        "description": (
            "Each slot in the processing sequence must hold exactly one job. For every "
            "slot, exactly one job is assigned to occupy it."
        ),
        "expected_pyomo": ONEINPOSITION,
    },
    {
        "description": (
            "Each job must take exactly one place in the processing sequence. For every "
            "job, it is assigned to exactly one slot."
        ),
        "expected_pyomo": ONERANKPER,
    },
    {
        "description": (
            "On any one machine, work on consecutive slots cannot overlap. For each "
            "machine and each slot that has a following slot, the machine may not begin "
            "the job in the next slot until it has finished the job in the current slot."
        ),
        "expected_pyomo": ONMACHREL,
    },
    {
        "description": (
            "A job must clear one machine before the next machine in the processing "
            "order can begin working on it. For each slot and each machine that has a "
            "following machine, the start of that slot's job on the next machine cannot "
            "come before its finish on the current machine."
        ),
        "expected_pyomo": PERMACHREL,
    },
    {
        "description": (
            "On each machine, the finish time of the job in a slot equals its start "
            "time on that machine plus the time that machine needs to process whichever "
            "job occupies that slot."
        ),
        "expected_pyomo": DEFCOMP,
    },
    {
        "description": (
            "The makespan is no earlier than the finish time of the job in the last "
            "slot on the last machine in the processing order."
        ),
        "expected_pyomo": DEFOBJ,
    },
    {
        "description": "Generate the complete constraint set for this model.",
        "expected_pyomo": WHOLESET,
    },
]

with open(OUT, "w") as f:
    for r in records:
        rec = {
            "problem_id": "flowshop_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {OUT} ({len(records)} records)")
