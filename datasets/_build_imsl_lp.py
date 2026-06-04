#!/usr/bin/env python
"""Builder for the imsl_lp (piecewise-linear approximation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "imsl_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "n", "members": ["d-00", "d-01", "d-02", "...", "d-60"],
         "doc": "the data points where the target function is sampled"},
        {"name": "m", "members": ["a-00", "a-01", "a-02", "...", "a-10"],
         "doc": "the approximation points whose values are chosen to fit the data"},
    ],
    "params": [
        {"name": "y", "index": "n", "kind": "data",
         "doc": "the observed data value at each data point"},
        {"name": "t", "index": "n", "kind": "coordinate",
         "doc": "the x-coordinate of each data point"},
        {"name": "s", "index": "m", "kind": "coordinate",
         "doc": "the x-coordinate of each approximation point"},
        {"name": "k", "index": "", "kind": "count", "doc": "number of approximation intervals"},
        {"name": "deltn", "index": "", "kind": "spacing", "doc": "spacing between data points"},
        {"name": "deltm", "index": "", "kind": "spacing", "doc": "spacing between approximation points"},
        {"name": "w", "index": "m,n", "kind": "weight",
         "doc": "interpolation weight that maps the approximation value at approximation point m onto data point n; for each data point these weights combine the surrounding approximation values into the interpolated value at that data point"},
    ],
    "vars": [
        {"name": "ym", "index": "m", "domain": "Reals",
         "doc": "the approximation value chosen at each approximation point"},
        {"name": "dp", "index": "n", "domain": "NonNegativeReals",
         "doc": "the amount by which the interpolated value exceeds the data value at a data point, the positive deviation"},
        {"name": "dn", "index": "n", "domain": "NonNegativeReals",
         "doc": "the amount by which the interpolated value falls short of the data value at a data point, the negative deviation"},
        {"name": "tdev", "index": "", "domain": "Reals",
         "doc": "the total absolute deviation accumulated over all data points"},
    ],
    "objective": {"sense": "minimize", "expr_var": "tdev"},
}

NARRATIVE = (
    "We fit a piecewise linear approximation to a set of sampled data values. "
    "At each approximation point we choose a value, and these chosen values are "
    "interpolated onto every data point using fixed interpolation weights. For "
    "each data point we measure how far the interpolated value lies above or "
    "below the observed data value. We decide the approximation values and the "
    "resulting deviations. The objective is to make the total absolute deviation "
    "between the approximation and the data as small as possible."
)

DDEV = (
    "def ddev_rule(model, n):\n"
    "    return sum(model.w[m, n] * model.ym[m] for m in model.m) - model.y[n] == model.dp[n] - model.dn[n]\n"
    "model.ddev = Constraint(model.n, rule=ddev_rule)"
)
DTDEV = (
    "def dtdev_rule(model):\n"
    "    return model.tdev == sum(model.dp[n] + model.dn[n] for n in model.n)\n"
    "model.dtdev = Constraint(rule=dtdev_rule)"
)
WHOLESET = "\n".join([DDEV, DTDEV])

records = [
    {"description": (
        "At each data point, the interpolated approximation value is obtained by "
        "combining the chosen approximation values with that data point's interpolation "
        "weights. The signed gap between this interpolated value and the observed data "
        "value at the point equals the positive deviation minus the negative deviation "
        "there. Enforce this for every data point."),
     "expected_pyomo": DDEV},
    {"description": (
        "The total absolute deviation equals the sum over all data points of the "
        "positive deviation plus the negative deviation at each point. Set the total "
        "deviation variable equal to that sum."),
     "expected_pyomo": DTDEV},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "imsl_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
