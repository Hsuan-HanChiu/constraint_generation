#!/usr/bin/env python
"""Builder for the badmip_mip constraint-generation dataset.

The model is FLAGGED nonlinear in the corpus, but every constraint is in fact
LINEAR: the only nonlinear-looking terms are products of the scalar PARAMETER s
with the decision variables x (e.g. (s+1)*x[i]), which are linear in x because s
is data. All four constraints (eq1, eq2, eq3, defobj) are polynomial degree 1 and
are kept. No constraints are excluded.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "badmip_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": list(range(1, 21)),
         "doc": "the full set of stage indices, the integers 1 through 20 in increasing order; consecutive members are neighbors and the ordering is meaningful"},
        {"name": "ii", "members": list(range(2, 20)),
         "doc": "the interior stage indices, the integers 2 through 19; these are exactly the stages that have both an immediately preceding stage and an immediately following stage in the full index set"},
    ],
    "params": [
        {"name": "s", "index": "", "kind": "coefficient",
         "doc": "a single fixed scalar coefficient, equal to 6, that scales the variables throughout the model; it is data, not a decision, so any product of s with a variable is linear in that variable"},
    ],
    "vars": [
        {"name": "x", "index": "i", "domain": "Integers",
         "doc": "the integer decision quantity at each stage; each value is a whole number with no lower bound, with an upper bound of 10 for stages 1 through 13 and a much larger upper bound for stages 14 through 20"},
        {"name": "obj", "index": "", "domain": "Reals",
         "doc": "a free real accounting variable that holds the objective value"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We choose an integer quantity at each of twenty ordered stages. A single fixed scalar "
    "coefficient scales these quantities throughout the model. One accounting variable records "
    "the objective value, and the goal is to minimize that objective value."
)

EQ1 = (
    "def eq1_rule(model):\n"
    "    return (model.s + 1) * model.x[1] >= model.s - 1\n"
    "model.eq1 = Constraint(rule=eq1_rule)"
)
EQ2 = (
    "def eq2_rule(model, i):\n"
    "    return -model.s * model.x[i-1] + (model.s + 1) * model.x[i] - model.x[i+1] >= (-1)**i * (model.s + 1)\n"
    "model.eq2 = Constraint(model.ii, rule=eq2_rule)"
)
EQ3 = (
    "def eq3_rule(model):\n"
    "    return -model.s * model.x[18] - (3*model.s - 1) * model.x[19] + 3 * model.x[20] >= -(5*model.s - 7)\n"
    "model.eq3 = Constraint(rule=eq3_rule)"
)
DEFOBJ = (
    "def defobj_rule(model):\n"
    "    return model.obj == -model.x[20]\n"
    "model.defobj = Constraint(rule=defobj_rule)"
)
WHOLESET = "\n".join([EQ1, EQ2, EQ3, DEFOBJ])

records = [
    {"description": (
        "There is a lower-bound requirement tying the very first stage's quantity to the model's "
        "fixed coefficient. Scale the first stage's quantity up by one more than that coefficient, "
        "and require the result to be at least one less than the coefficient."),
     "expected_pyomo": EQ1},
    {"description": (
        "Each interior stage must satisfy a lower-bound balance that links it to the stage just "
        "before it and the stage just after it. For every interior stage, take the stage's own "
        "quantity scaled by one more than the fixed coefficient, subtract the preceding stage's "
        "quantity scaled by the coefficient, and subtract the following stage's quantity, and "
        "require this combination to be at least a threshold whose size is one more than the "
        "coefficient and whose sign alternates from stage to stage, being negative at even-numbered "
        "stages and positive at odd-numbered stages."),
     "expected_pyomo": EQ2},
    {"description": (
        "There is a final lower-bound requirement linking the last three stages. Take the "
        "second-to-last stage's quantity scaled by the coefficient and the next-to-last stage's "
        "quantity scaled by one less than three times the coefficient, subtract both of those, then "
        "add three times the last stage's quantity, and require the result to be at least the "
        "negative of seven less than five times the coefficient."),
     "expected_pyomo": EQ3},
    {"description": (
        "The objective accounting variable is defined to equal the negative of the last stage's "
        "quantity."),
     "expected_pyomo": DEFOBJ},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "badmip_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
