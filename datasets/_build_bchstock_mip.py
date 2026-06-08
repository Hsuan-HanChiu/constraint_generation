#!/usr/bin/env python
"""Builder for the bchstock_mip (cutting-stock) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "bchstock_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["w1", "w2", "w3", "w4"],
         "doc": "the set of finished products to be cut, each identified by its required width"},
        {"name": "p", "members": ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10"],
         "doc": "the set of available cutting patterns; each pattern is one way of slicing a single raw roll into finished widths, and some entries are unused empty slots that produce nothing"},
    ],
    "params": [
        {"name": "r", "index": "", "kind": "width",
         "doc": "the width of a raw paper roll, in width units; a single scalar equal to 100"},
        {"name": "w", "index": "i", "kind": "width",
         "doc": "the width of each finished product, in the same width units as the raw roll"},
        {"name": "d", "index": "i", "kind": "demand",
         "doc": "the number of finished pieces of each width that must be produced"},
        {"name": "aip", "index": "i,p", "kind": "yield",
         "doc": "the number of finished pieces of a given width that one application of a given cutting pattern yields; zero for combinations a pattern does not produce, including the unused empty patterns"},
    ],
    "vars": [
        {"name": "xp", "index": "p", "domain": "NonNegativeIntegers",
         "doc": "the number of times each cutting pattern is applied, i.e. how many raw rolls are cut according to that pattern; a whole number that cannot be negative"},
        {"name": "z", "index": "", "domain": "NonNegativeReals",
         "doc": "the total number of raw rolls used across all patterns"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We cut finished paper products of several widths out of raw paper rolls that all share a "
    "single standard width. Each finished width has a required quantity that must be met. A raw "
    "roll can be sliced according to any of a number of predefined cutting patterns, and for each "
    "pattern we decide how many raw rolls to cut that way. We also keep track of the total number "
    "of raw rolls consumed. The objective is to minimize the total number of raw rolls used."
)

NUMPAT = (
    "def numpat_rule(model):\n"
    "    return sum(model.xp[p] for p in model.p) == model.z\n"
    "model.numpat = Constraint(expr=numpat_rule(model))"
)
DEMAND = (
    "def demand_rule(model, i):\n"
    "    return sum(model.aip[i, p] * model.xp[p] for p in model.p) >= model.d[i]\n"
    "model.demand = Constraint(model.i, rule=demand_rule)"
)
WHOLESET = "\n".join([NUMPAT, DEMAND])

records = [
    {"description": (
        "The total number of raw rolls used is the number of rolls cut across every pattern added "
        "together. Set the total rolls used equal to the sum over all patterns of how many times "
        "each pattern is applied."),
     "expected_pyomo": NUMPAT},
    {"description": (
        "Every finished width must be produced in at least the quantity required. For each finished "
        "width, the total number of pieces of that width yielded across all patterns, counting how "
        "many times each pattern is applied and how many pieces of that width each application "
        "produces, must be at least the required quantity for that width."),
     "expected_pyomo": DEMAND},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, set the "
        "total number of raw rolls used equal to the sum across every pattern of how many times that "
        "pattern is applied. Finally, ensure that for each finished width the total number of pieces "
        "of that width produced across all patterns is at least the quantity required for that width."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "bchstock_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
