#!/usr/bin/env python
"""Builder for the nebrazil_lp (North-East Brazil regional agricultural LP)
constraint-generation dataset.

This model is a scalar coefficient-matrix LP: a single constraint family `con`,
one row per equation index, where each row is a sparse weighted sum of decision
variables related to a per-row right-hand side by a per-row sense (<=, =, or >=).
There is exactly one constraint component, so the per-constraint record and the
whole-set record describe the same family.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "nebrazil_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "V", "members": "1..414",
         "doc": "the indices of the decision variables of the regional farm LP, one per production, processing, transport and accounting activity in the zone"},
        {"name": "E", "members": "1..185",
         "doc": "the indices of the equations of the regional farm LP, each one a single resource, balance or accounting relationship"},
        {"name": "Vfree", "members": "20 indices",
         "doc": "the subset of variable indices that are free variables ranging over all reals with no bounds, including the consumer-producer surplus accounting variable"},
        {"name": "Vbfree", "members": "36 indices",
         "doc": "the subset of variable indices that are bounded-free, ranging from zero up to a finite per-variable upper bound"},
    ],
    "params": [
        {"name": "A", "index": "(E, V)", "kind": "coefficient",
         "doc": "the sparse constraint coefficient on variable v in equation e; only the nonzero entries are stored, so an equation involves only the variables that actually appear in it"},
        {"name": "rhs", "index": "E", "kind": "bound",
         "doc": "the right-hand side constant of each equation, the resource limit, requirement or balance target it is compared against"},
        {"name": "sense", "index": "E", "kind": "relation",
         "doc": "the relational direction of each equation given as a code: -1 means the equation is a less-than-or-equal upper-limit constraint, 0 means it is an equality balance, and 1 means it is a greater-than-or-equal lower-requirement constraint"},
        {"name": "vub", "index": "Vbfree", "kind": "bound",
         "doc": "the finite upper bound for each bounded-free variable, in the variable's own activity units"},
    ],
    "vars": [
        {"name": "x", "index": "V", "domain": "Reals or NonNegativeReals",
         "doc": "the activity level of each decision variable; free variables in Vfree range over all reals, bounded-free variables in Vbfree range from zero to their upper bound, and every other variable is nonnegative"},
    ],
    "objective": {"sense": "maximize", "expr_var": "x[398]"},
}

NARRATIVE = (
    "This is a regional agricultural planning model for a farming zone in North-East "
    "Brazil. It chooses the activity level of every production, processing, transport "
    "and accounting variable in the zone. The plan is scored by a single accounting "
    "variable that measures the combined consumer and producer surplus, the overall "
    "farm income, and the goal is to make that surplus as large as possible."
)

# Mirror the base model's `_con_rule`: for each equation e, the weighted sum over
# its nonzero columns is related to rhs[e] by sense[e]. Self-contained (rebuilds
# the per-row nonzero column lists from A's keys).
CON = (
    "def con_rule(model, e):\n"
    "    cols = [v for (ee, v) in model.A.keys() if ee == e]\n"
    "    lhs = sum(model.A[e, v] * model.x[v] for v in cols)\n"
    "    s = pyo.value(model.sense[e])\n"
    "    if s < 0:\n"
    "        return lhs <= model.rhs[e]\n"
    "    if s > 0:\n"
    "        return lhs >= model.rhs[e]\n"
    "    return lhs == model.rhs[e]\n"
    "model.con = Constraint(model.E, rule=con_rule)"
)

CON_DESC = (
    "For each equation in the model, take the weighted sum of the decision variables "
    "that appear in that equation, each weighted by its coefficient in that equation, "
    "and relate that sum to the equation's right-hand side value. The direction of the "
    "relationship is set per equation by its sense: when the sense marks it as an upper "
    "limit the weighted sum must stay at or below the right-hand side, when the sense "
    "marks it as a lower requirement the weighted sum must stay at or above the "
    "right-hand side, and otherwise the weighted sum must equal the right-hand side "
    "exactly."
)

# Whole-set: ordinal narrative composing the per-constraint intents in order.
# This model has exactly one constraint family, so the ordinal narrative wraps
# that single intent.
WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for each equation in the model, take the weighted sum of the decision "
    "variables that appear in it, each weighted by its coefficient in that equation, "
    "and relate that sum to the equation's right-hand side according to the equation's "
    "sense: a sense marking an upper limit keeps the weighted sum at or below the "
    "right-hand side, a sense marking a lower requirement keeps it at or above the "
    "right-hand side, and otherwise the weighted sum must equal the right-hand side."
)
WHOLESET = CON

records = [
    {"description": CON_DESC, "expected_pyomo": CON},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "nebrazil_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
