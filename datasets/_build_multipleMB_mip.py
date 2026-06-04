#!/usr/bin/env python
"""Builder for the multipleMB_mip (multi-machine scheduling) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "multipleMB_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "J", "members": ["A", "B", "C", "D", "E", "F", "G"],
         "doc": "the jobs that must be scheduled"},
        {"name": "M", "members": ["A", "B"],
         "doc": "the machines available to process the jobs"},
        {"name": "PAIRS", "members": "all ordered pairs (j, k) of distinct jobs with j before k in the job ordering",
         "doc": "the unordered pairs of distinct jobs, each listed once as (j, k) with j ahead of k in the job ordering; used to reason about the relative sequence of two jobs that might share a machine"},
    ],
    "params": [
        {"name": "release", "index": "J", "kind": "time",
         "doc": "the release time of each job, the earliest time at which that job is allowed to start, in time units"},
        {"name": "duration", "index": "J", "kind": "time",
         "doc": "the processing duration of each job, the number of time units the job occupies a machine once started"},
        {"name": "due", "index": "J", "kind": "time",
         "doc": "the due date of each job, the time by which it is ideally completed, in time units"},
    ],
    "vars": [
        {"name": "start", "index": "J", "domain": "Reals",
         "doc": "the start time chosen for each job, bounded below by 0 and above by a large allowable horizon"},
        {"name": "makespan", "index": "", "domain": "NonNegativeReals",
         "doc": "the makespan of the schedule, meaning the latest completion time over all jobs"},
        {"name": "early", "index": "J", "domain": "NonNegativeReals",
         "doc": "the earliness of each job, the amount of time by which the job completes ahead of its due date"},
        {"name": "z", "index": "J, M", "domain": "Binary",
         "doc": "the machine assignment indicator, equal to 1 when the job is assigned to that machine and 0 otherwise"},
        {"name": "y", "index": "PAIRS", "domain": "Binary",
         "doc": "the sequencing indicator for a pair of jobs, equal to 1 when the first job of the pair is scheduled before the second job of the pair, and 0 when the order is reversed"},
    ],
    "objective": {"sense": "minimize", "expr_var": "makespan"},
}

NARRATIVE = (
    "We schedule a set of jobs on a small number of parallel machines. For each job we choose "
    "a start time and we choose which machine processes it, and for each pair of jobs that could "
    "land on the same machine we decide which one goes first. Each job occupies its machine for a "
    "fixed duration once it starts. The goal is to finish everything as quickly as possible, so we "
    "minimize the makespan, the time at which the last job completes."
)

# BigM = max release + total duration, recomputed from the params so it is instance-independent.
BIGM_SETUP = (
    "    BigM = max(value(model.release[jj]) for jj in model.J) "
    "+ sum(value(model.duration[jj]) for jj in model.J)\n"
)

C1 = (
    "def c1_rule(model, j):\n"
    "    return model.start[j] >= model.release[j]\n"
    "model.c1 = Constraint(model.J, rule=c1_rule)"
)
C2 = (
    "def c2_rule(model, j):\n"
    "    return model.start[j] + model.duration[j] + model.early[j] == model.due[j]\n"
    "model.c2 = Constraint(model.J, rule=c2_rule)"
)
C3 = (
    "def c3_rule(model, j):\n"
    "    return sum(model.z[j, mach] for mach in model.M) == 1\n"
    "model.c3 = Constraint(model.J, rule=c3_rule)"
)
C4 = (
    "def c4_rule(model, j):\n"
    "    return model.start[j] + model.duration[j] <= model.makespan\n"
    "model.c4 = Constraint(model.J, rule=c4_rule)"
)
D1 = (
    "def d1_rule(model, mach, j, k):\n"
    + BIGM_SETUP +
    "    return model.start[j] + model.duration[j] <= model.start[k] + BigM * (model.y[j, k] + (1 - model.z[j, mach]) + (1 - model.z[k, mach]))\n"
    "model.d1 = Constraint(model.M, model.PAIRS, rule=d1_rule)"
)
D2 = (
    "def d2_rule(model, mach, j, k):\n"
    + BIGM_SETUP +
    "    return model.start[k] + model.duration[k] <= model.start[j] + BigM * ((1 - model.y[j, k]) + (1 - model.z[j, mach]) + (1 - model.z[k, mach]))\n"
    "model.d2 = Constraint(model.M, model.PAIRS, rule=d2_rule)"
)

WHOLESET = "\n".join([C1, C2, C3, C4, D1, D2])

records = [
    {"description": (
        "Each job cannot begin before it becomes available. For every job, its chosen start time "
        "must be no earlier than the time at which that job is released."),
     "expected_pyomo": C1},
    {"description": (
        "Track how far ahead of schedule each job finishes. For every job, the time it starts plus "
        "the time it takes to process plus the amount by which it beats its deadline must equal that "
        "job's due date."),
     "expected_pyomo": C2},
    {"description": (
        "Every job has to run on a machine, and only one. For each job, the number of machines it is "
        "assigned to must be exactly one."),
     "expected_pyomo": C3},
    {"description": (
        "The makespan represents when the very last job is done. For every job, the makespan must be "
        "at least the time at which that job finishes, meaning its start time plus its processing "
        "duration."),
     "expected_pyomo": C4},
    {"description": (
        "When two jobs share the same machine and the first of the pair is sequenced ahead of the "
        "second, the second cannot start until the first has finished. For each machine and each pair "
        "of jobs, enforce that the first job's completion time is no later than the second job's start "
        "time, but allow this requirement to switch off whenever the two jobs are not both on that "
        "machine or the first is not the one running earlier. Use a large enough slack so that any one "
        "of those off conditions fully relaxes the requirement."),
     "expected_pyomo": D1},
    {"description": (
        "This is the mirror image of the previous sequencing requirement, covering the case where the "
        "second job of the pair runs before the first. When two jobs share the same machine and the "
        "second of the pair is sequenced ahead of the first, the first cannot start until the second "
        "has finished. For each machine and each pair of jobs, enforce that the second job's completion "
        "time is no later than the first job's start time, but allow this requirement to switch off "
        "whenever the two jobs are not both on that machine or the second is not the one running "
        "earlier. Use a large enough slack so that any one of those off conditions fully relaxes the "
        "requirement."),
     "expected_pyomo": D2},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "multipleMB_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
