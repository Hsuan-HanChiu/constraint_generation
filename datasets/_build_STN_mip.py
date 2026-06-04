#!/usr/bin/env python
"""Builder for the STN_mip (State-Task-Network batch scheduling) constraint-generation dataset.

GRADABILITY NOTE
----------------
The corpus model exposes on the Pyomo scaffold only: vars W, B, S, Q, Value, Cost
and params rho, rho_, C, Bmax, Bmin, Pi (plus the named constraints valuec, costc,
sc and a bundled ConstraintList `cons`). Several coefficient tables used by the
native constraints live ONLY in module-level Python (raw data dicts) and are NEVER
attached to the model: state prices, per-arc task durations P, task completion
times p, cleaning times Tclean, initial inventories, and the per-task fixed/variable
cost rates Cost/vCost. The grading namespace is locked to `model.*` (plus Constraint,
sum, pyo), so the ground truth for the constraints that depend on those tables CANNOT
be reconstructed and is therefore NOT gradable here. Those four families are EXCLUDED
(documented below). The two families whose ground truth is fully reconstructable from
model.* — the state storage-capacity limit (native `sc`) and the batch-size linking
bounds (the min and max halves of the native `cons` batch-capacity block) — are built
and graded.

EXCLUDED (not reconstructable from the model scaffold -> not Z3-gradable here):
  - valuec : Value == sum_s price[s]*S[s,H]            (needs state prices, horizon end)
  - costc  : Cost == sum (Cost[j,i]*W + vCost[j,i]*B)  (needs per-task cost rates)
  - unit-assignment (cons): no-overlap window per unit (needs p[i], Tclean)
  - state mass balance (cons): inventory recursion      (needs P durations, initial, time-shift)
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "STN_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [],  # the corpus model carries no named Pyomo Sets; index sets are implicit in the vars/params
    "params": [
        {"name": "rho", "index": "task, state", "kind": "fraction",
         "doc": "input fraction: the share of a task's batch that is drawn from a feeding state when the task runs; the keys of this parameter are exactly the valid task-to-feeding-state input arcs"},
        {"name": "rho_", "index": "task, state", "kind": "fraction",
         "doc": "output fraction: the share of a task's batch that is delivered to a receiving state when the task completes; the keys of this parameter are exactly the valid task-to-receiving-state output arcs"},
        {"name": "C", "index": "state", "kind": "capacity",
         "doc": "maximum storage capacity of each state, in material units; the amount of that material that can be held at any time cannot exceed this"},
        {"name": "Bmax", "index": "task, unit", "kind": "capacity",
         "doc": "maximum batch size for a task when run in a given unit, in material units; the keys of this parameter are exactly the valid task-unit pairs, i.e. which units are capable of which tasks"},
        {"name": "Bmin", "index": "task, unit", "kind": "capacity",
         "doc": "minimum batch size for a task when run in a given unit, in material units; only meaningful when that task is actually started in that unit"},
        {"name": "Pi", "index": "state, time", "kind": "flow",
         "doc": "external material entering (positive) or leaving (negative) a state at a time period, in material units"},
    ],
    "vars": [
        {"name": "W", "index": "task, unit, time", "domain": "Binary",
         "doc": "binary start indicator: 1 if the task is started in the unit at the time period, 0 otherwise; defined only over valid task-unit pairs and all time periods"},
        {"name": "B", "index": "task, unit, time", "domain": "NonNegativeReals",
         "doc": "size of the batch assigned to the task in the unit at the time period, in material units; defined over the same task-unit-time index as the start indicator"},
        {"name": "S", "index": "state, time", "domain": "NonNegativeReals",
         "doc": "inventory level of each state at each time period, in material units"},
        {"name": "Q", "index": "unit, time", "domain": "NonNegativeReals",
         "doc": "inventory held in each unit at each time period, in material units"},
        {"name": "Value", "index": "", "domain": "NonNegativeReals",
         "doc": "total revenue from product inventories at the end of the planning horizon, in dollars"},
        {"name": "Cost", "index": "", "domain": "NonNegativeReals",
         "doc": "total production cost over the horizon, in dollars"},
    ],
    "objective": {"sense": "maximize", "expr_var": "Value - Cost"},
}

NARRATIVE = (
    "We schedule batch production over a discrete time horizon on a network of "
    "processing units that transform materials held in storage states. For every "
    "time period we decide which task to start in which unit and how big its batch "
    "should be, and we track how much material sits in each storage state and each "
    "unit over time. The aim is to maximize the value of the final product "
    "inventories net of the total production cost."
)

# ---- gradable family 1: state storage-capacity limit (native name: sc) ----
SC = (
    "def sc_rule(model, s, t):\n"
    "    return model.S[s,t] <= model.C[s]\n"
    "model.sc = Constraint(list(model.S.keys()), rule=sc_rule)"
)

# helper used by both batch-cap rules: all (task, unit, time) start slots
_WT = "[(i,j,t) for (i,j) in model.Bmin.keys() for t in sorted({tt for (a,b,tt) in model.W.keys()})]"

# ---- gradable family 2a: batch-size lower linking bound ----
BATCH_MIN = (
    "def batch_min_rule(model, i, j, t):\n"
    "    return model.Bmin[i,j]*model.W[i,j,t] <= model.B[i,j,t]\n"
    f"model.batch_min = Constraint({_WT}, rule=batch_min_rule)"
)

# ---- gradable family 2b: batch-size upper linking bound ----
BATCH_MAX = (
    "def batch_max_rule(model, i, j, t):\n"
    "    return model.B[i,j,t] <= model.Bmax[i,j]*model.W[i,j,t]\n"
    f"model.batch_max = Constraint({_WT.replace('Bmin','Bmax')}, rule=batch_max_rule)"
)

WHOLESET = "\n".join([SC, BATCH_MIN, BATCH_MAX])

records = [
    {"description": (
        "Each storage state has a fixed holding capacity. For every state and every time "
        "period, the amount of material held in that state cannot exceed the capacity of "
        "that state."),
     "expected_pyomo": SC},
    {"description": (
        "A batch may only be assigned to a task in a unit if that task is actually started "
        "in that unit at that time, and when it is started the batch cannot be too small. "
        "For every valid task and unit and every time period, the batch size must be at "
        "least the minimum batch size whenever the task is started in that unit, and must "
        "be zero when it is not started."),
     "expected_pyomo": BATCH_MIN},
    {"description": (
        "When a task is started in a unit at a time period, the batch assigned to it cannot "
        "exceed that unit's maximum batch size for the task, and if the task is not started "
        "in that unit then no batch may be assigned. For every valid task and unit and every "
        "time period, the batch size is bounded above by the maximum batch size when the task "
        "is started there and forced to zero otherwise."),
     "expected_pyomo": BATCH_MAX},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "STN_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
