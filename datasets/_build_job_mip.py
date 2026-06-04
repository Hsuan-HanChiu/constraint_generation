#!/usr/bin/env python
"""Builder for the job_mip (job scheduling MIP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "job_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "J", "members": [1, 2, 3, 4, 5, 6, 7],
         "doc": "the jobs that make up the project, each of which must be scheduled"},
        {"name": "P", "members": [[1, 4], [2, 4], [2, 3], [3, 5], [3, 6], [4, 7]],
         "doc": "the precedence pairs of jobs; each member is an ordered pair in which the first job is a predecessor that must finish before the second job is allowed to begin"},
    ],
    "params": [
        {"name": "mincost", "index": "J", "kind": "cost",
         "doc": "the cost incurred for completing a job in its minimum allowed duration, in dollars per job"},
        {"name": "maxcost", "index": "J", "kind": "cost",
         "doc": "the cost incurred for completing a job in its maximum allowed duration, in dollars per job"},
        {"name": "mintime", "index": "J", "kind": "duration",
         "doc": "the minimum number of days a job is permitted to take"},
        {"name": "maxtime", "index": "J", "kind": "duration",
         "doc": "the maximum number of days a job is permitted to take"},
        {"name": "totaldays", "index": "", "kind": "horizon",
         "doc": "the total number of days available to complete the entire project"},
    ],
    "vars": [
        {"name": "s", "index": "J", "domain": "PositiveIntegers",
         "doc": "the start day chosen for each job, a positive integer"},
        {"name": "t", "index": "J", "domain": "PositiveIntegers",
         "doc": "the duration in days chosen for each job, a positive integer"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We are scheduling a project made up of several jobs. For each job we decide when it "
    "starts and how many days it takes to finish. A job can be completed faster or slower "
    "within an allowed range, and its cost depends on the duration we pick, running from a "
    "known cost at the fastest allowed duration to a known cost at the slowest allowed "
    "duration. The objective is to choose start days and durations so that the total cost "
    "of completing all the jobs is as small as possible."
)

MINTIME = (
    "def mintime_rule(model, j):\n"
    "    return model.t[j] >= model.mintime[j]\n"
    "model.mintimerule = Constraint(model.J, rule=mintime_rule)"
)
MAXTIME = (
    "def maxtime_rule(model, j):\n"
    "    return model.t[j] <= model.maxtime[j]\n"
    "model.maxtimerule = Constraint(model.J, rule=maxtime_rule)"
)
TOTALTIME = (
    "def totaltime_rule(model, j):\n"
    "    return model.s[j] + model.t[j] <= model.totaldays\n"
    "model.totaltimerule = Constraint(model.J, rule=totaltime_rule)"
)
PREDECESSORS = (
    "def predecessors_rule(model, i, j):\n"
    "    return model.s[i] + model.t[i] <= model.s[j]\n"
    "model.predecessorsrule = Constraint(model.P, rule=predecessors_rule)"
)
WHOLESET = "\n".join([MINTIME, MAXTIME, TOTALTIME, PREDECESSORS])

records = [
    {"description": (
        "Every job has a shortest duration it is allowed to take. For each job, the duration "
        "chosen must be at least that job's minimum allowed duration."),
     "expected_pyomo": MINTIME},
    {"description": (
        "Every job has a longest duration it is allowed to take. For each job, the duration "
        "chosen must not exceed that job's maximum allowed duration."),
     "expected_pyomo": MAXTIME},
    {"description": (
        "The whole project must fit inside the available time window. For each job, the day it "
        "starts plus the number of days it takes must not run past the total number of days "
        "available for the project."),
     "expected_pyomo": TOTALTIME},
    {"description": (
        "Some jobs cannot begin until other jobs are finished. For each precedence pair, the "
        "predecessor job must be completely finished before the dependent job is allowed to "
        "start, meaning the predecessor's start day plus its duration must come no later than "
        "the start day of the job that depends on it."),
     "expected_pyomo": PREDECESSORS},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "job_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
