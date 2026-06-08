#!/usr/bin/env python
"""Builder for the absmip_mip (MIP formulation of y = min(x, 0)) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "absmip_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [],
    "params": [
        {"name": "xlo", "index": "", "kind": "bound",
         "doc": "the lower bound on the argument, a scalar equal to -5; its absolute value serves as the large constant that switches off the negative part when the indicator is on"},
        {"name": "xup", "index": "", "kind": "bound",
         "doc": "the upper bound on the argument, a scalar equal to 5; its absolute value serves as the large constant that switches off the positive part when the indicator is off"},
    ],
    "vars": [
        {"name": "x", "index": "", "domain": "Reals",
         "doc": "the argument to the function, a free real variable bounded between the lower and upper bounds"},
        {"name": "xp", "index": "", "domain": "NonNegativeReals",
         "doc": "the positive part of the argument, a nonnegative real that captures the argument when it is at or above zero"},
        {"name": "xn", "index": "", "domain": "NonNegativeReals",
         "doc": "the negative part of the argument, a nonnegative real that captures the magnitude of the argument when it is below zero"},
        {"name": "b", "index": "", "domain": "Binary",
         "doc": "a binary indicator that equals 1 when the argument is represented by its positive part and 0 when it is represented by its negative part"},
        {"name": "y", "index": "", "domain": "Reals",
         "doc": "the result of the function evaluation, a free real variable holding the minimum of the argument and zero"},
    ],
    "objective": {"sense": "minimize", "expr_var": "y"},
}

NARRATIVE = (
    "We evaluate the smaller of a single real argument and zero by writing it as a mixed-integer "
    "program. The argument is free to take any value within a fixed lower and upper bound. We split "
    "the argument into a nonnegative positive part and a nonnegative negative part, and we use a "
    "binary indicator to decide which of the two parts is active. The result variable records the "
    "value of the function. The objective is to minimize the result."
)

E1 = (
    "model.e1 = Constraint(expr=model.x == model.xp - model.xn)"
)
E2 = (
    "model.e2 = Constraint(expr=model.xp <= abs(value(model.xup)) * model.b)"
)
E3 = (
    "model.e3 = Constraint(expr=model.xn <= abs(value(model.xlo)) * (1 - model.b))"
)
DEFZMIN = (
    "model.defzmin = Constraint(expr=model.y == -model.xn)"
)
WHOLESET = "\n".join([E1, E2, E3, DEFZMIN])

records = [
    {"description": (
        "The argument must equal its positive part minus its negative part, so the two parts together "
        "reconstruct the original argument."),
     "expected_pyomo": E1},
    {"description": (
        "The positive part may only be nonzero when the indicator is on. When the indicator is on the "
        "positive part can range up to the magnitude of the upper bound, and when the indicator is off "
        "the positive part is forced to zero."),
     "expected_pyomo": E2},
    {"description": (
        "The negative part may only be nonzero when the indicator is off. When the indicator is off the "
        "negative part can range up to the magnitude of the lower bound, and when the indicator is on "
        "the negative part is forced to zero."),
     "expected_pyomo": E3},
    {"description": (
        "The result must equal the negation of the negative part, so the result is zero when the "
        "argument is nonnegative and equals the argument itself when the argument is below zero."),
     "expected_pyomo": DEFZMIN},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, the argument "
        "must equal its positive part minus its negative part so the two parts reconstruct the original "
        "argument. Second, the positive part may only be nonzero when the indicator is on, ranging up to "
        "the magnitude of the upper bound when the indicator is on and forced to zero otherwise. Third, "
        "the negative part may only be nonzero when the indicator is off, ranging up to the magnitude of "
        "the lower bound when the indicator is off and forced to zero otherwise. Finally, the result must "
        "equal the negation of the negative part, so the result is zero when the argument is nonnegative "
        "and equals the argument when the argument is below zero."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "absmip_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
