#!/usr/bin/env python
"""Builder for the lrs_mip (linear recursive sequence fitting) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "lrs_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "t", "members": [1, 2, 3, 4, 5, 6],
         "doc": "the full time horizon, a sequence of integer time steps in chronological order; the first member is the earliest step and each later member follows the one before it"},
        {"name": "f", "members": [1, 2, 3],
         "doc": "the first stretch of time steps that act as the free seed of the sequence; these are the initial steps whose values are chosen directly, and the set has exactly as many members as the recurrence order"},
    ],
    "params": [
        {"name": "c", "index": "t", "kind": "observation",
         "doc": "the observed target sequence to be fitted, taking the value 0 or 1 at each time step"},
        {"name": "n", "index": "", "kind": "order",
         "doc": "the recurrence order, equal to the number of seed steps; the recurrence looks back this many steps, a scalar"},
        {"name": "r", "index": "", "kind": "shift",
         "doc": "the recurrence shift parameter, a scalar"},
        {"name": "n_minus_r", "index": "", "kind": "lag",
         "doc": "the second look-back distance of the recurrence, equal to the recurrence order minus the shift parameter, a scalar"},
    ],
    "vars": [
        {"name": "k", "index": "t", "domain": "Binary on the seed steps f, continuous in the unit interval [0,1] on the remaining steps",
         "doc": "the fitted recursive sequence value at each time step; on the seed steps it is a 0/1 decision, and on every later step it is determined in the unit interval and takes a 0/1 value automatically once the seed is fixed"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total number of disagreements between the fitted sequence and the observed target sequence over the whole horizon"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We are given an observed binary sequence over a horizon of time steps, and we want to "
    "reproduce it as closely as possible with a linear recursive sequence. We freely choose the "
    "0/1 values of the first few seed steps, and every later step is then generated from two "
    "earlier steps by a fixed recurrence. We also track how many time steps the generated "
    "sequence disagrees with the observed one. The objective is to minimize the total number of "
    "disagreements between the generated sequence and the observed sequence over the whole horizon."
)

OBJDEF = (
    "def objdef_rule(model):\n"
    "    return model.z == sum((model.k[tt] if pyo.value(model.c[tt]) == 0 else (1 - model.k[tt])) for tt in model.t)\n"
    "model.objdef = Constraint(rule=objdef_rule)"
)

# Recurrence index set: steps t for which both look-backs land inside the horizon.
# Built with set membership (no relational operator) so the harness's first-relop
# control perturbation targets the constraint body, not this guard.
REC_T = (
    "_lag = max(pyo.value(model.n), pyo.value(model.n_minus_r))\n"
    "_tset = set(model.t)\n"
    "rec_t = [tt for tt in model.t if (tt - _lag) in _tset]\n"
)

MODUP1 = (
    REC_T +
    "def modup1_rule(model, tt):\n"
    "    return model.k[tt] <= model.k[tt - pyo.value(model.n)] + model.k[tt - pyo.value(model.n_minus_r)]\n"
    "model.modup1 = Constraint(rec_t, rule=modup1_rule)"
)
MODUP2 = (
    REC_T +
    "def modup2_rule(model, tt):\n"
    "    return model.k[tt] <= 2 - model.k[tt - pyo.value(model.n)] - model.k[tt - pyo.value(model.n_minus_r)]\n"
    "model.modup2 = Constraint(rec_t, rule=modup2_rule)"
)
MODLO1 = (
    REC_T +
    "def modlo1_rule(model, tt):\n"
    "    return model.k[tt] >= -model.k[tt - pyo.value(model.n)] + model.k[tt - pyo.value(model.n_minus_r)]\n"
    "model.modlo1 = Constraint(rec_t, rule=modlo1_rule)"
)
MODLO2 = (
    REC_T +
    "def modlo2_rule(model, tt):\n"
    "    return model.k[tt] >= model.k[tt - pyo.value(model.n)] - model.k[tt - pyo.value(model.n_minus_r)]\n"
    "model.modlo2 = Constraint(rec_t, rule=modlo2_rule)"
)

WHOLESET = "\n".join([OBJDEF, MODUP1, MODUP2, MODLO1, MODLO2])

records = [
    {"description": (
        "Count the total number of time steps where the generated sequence and the observed "
        "sequence disagree, and set the disagreement total equal to that count. At a step where "
        "the observed value is zero, a disagreement happens when the generated value is one, and "
        "at a step where the observed value is one, a disagreement happens when the generated "
        "value is zero. Add up these mismatches over every step in the horizon."),
     "expected_pyomo": OBJDEF},
    {"description": (
        "For every step that the recurrence generates, the generated value cannot exceed the sum "
        "of the two earlier values it is built from, namely the value one recurrence order back "
        "and the value the second look-back distance back. This applies only to the steps reached "
        "by the recurrence, where both of those earlier steps fall inside the horizon."),
     "expected_pyomo": MODUP1},
    {"description": (
        "For every step that the recurrence generates, the generated value cannot exceed two "
        "minus the two earlier values it is built from, namely the value one recurrence order "
        "back and the value the second look-back distance back. This applies only to the steps "
        "reached by the recurrence, where both of those earlier steps fall inside the horizon."),
     "expected_pyomo": MODUP2},
    {"description": (
        "For every step that the recurrence generates, the generated value must be at least the "
        "value the second look-back distance back minus the value one recurrence order back. This "
        "applies only to the steps reached by the recurrence, where both of those earlier steps "
        "fall inside the horizon."),
     "expected_pyomo": MODLO1},
    {"description": (
        "For every step that the recurrence generates, the generated value must be at least the "
        "value one recurrence order back minus the value the second look-back distance back. This "
        "applies only to the steps reached by the recurrence, where both of those earlier steps "
        "fall inside the horizon."),
     "expected_pyomo": MODLO2},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, count "
        "the total number of steps where the generated sequence disagrees with the observed "
        "sequence and set the disagreement total equal to that count, where a disagreement is a "
        "generated one against an observed zero or a generated zero against an observed one, "
        "summed over the whole horizon. Second, for every step reached by the recurrence, keep "
        "the generated value no greater than the sum of the value one recurrence order back and "
        "the value the second look-back distance back. Third, for every step reached by the "
        "recurrence, keep the generated value no greater than two minus those same two earlier "
        "values. Fourth, for every step reached by the recurrence, keep the generated value at "
        "least the value the second look-back distance back minus the value one recurrence order "
        "back. Finally, for every step reached by the recurrence, keep the generated value at "
        "least the value one recurrence order back minus the value the second look-back distance "
        "back."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "lrs_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
