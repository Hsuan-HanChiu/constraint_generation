#!/usr/bin/env python
"""Builder for the marilyn_mip (eight-digit circle puzzle) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "marilyn_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "c", "members": ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"],
         "doc": "the circles in the figure, each of which must hold one digit; also serves as the set of available digit slots since there are exactly as many digits as circles"},
        {"name": "cc", "members": ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"],
         "doc": "an alias of the circle set, used as the second index when a relationship ranges over pairs of circles or over the eight candidate digit values; the position of a member in this ordering, counting from one, is the digit value it represents"},
        {"name": "net", "members": ["c1|c2", "c1|c3", "c1|c4", "c2|c1", "c2|c3", "c2|c5", "c2|c6", "c3|c1", "c3|c2", "c3|c4", "c3|c5", "c3|c6", "c3|c7", "c4|c1", "c4|c3", "c4|c6", "c4|c7", "c5|c2", "c5|c3", "c5|c6", "c5|c8", "c6|c2", "c6|c3", "c6|c4", "c6|c5", "c6|c7", "c6|c8", "c7|c3", "c7|c4", "c7|c6", "c7|c8", "c8|c5", "c8|c6", "c8|c7"],
         "doc": "the pairs of circles that are adjacent in the figure, listed as ordered pairs; the relation is symmetric so each unordered adjacency appears twice, once in each direction"},
    ],
    "params": [
        {"name": "bign", "index": "", "kind": "big-M",
         "doc": "a large constant used to deactivate an adjacency difference inequality when the relevant ordering indicator selects the other direction; a scalar with value 9"},
        {"name": "gap", "index": "", "kind": "separation",
         "doc": "the minimum required absolute difference between the digits placed in two adjacent circles; a scalar with value 2"},
        {"name": "lo", "index": "", "kind": "bound",
         "doc": "the smallest digit value that may be placed in a circle; a scalar with value 1"},
        {"name": "up", "index": "", "kind": "bound",
         "doc": "the largest digit value that may be placed in a circle; a scalar with value 8"},
    ],
    "vars": [
        {"name": "x", "index": "c", "domain": "Integers",
         "doc": "the digit value placed in each circle, an integer bounded between the smallest and largest allowed digit"},
        {"name": "ll", "index": "c,cc", "domain": "Binary",
         "doc": "an ordering indicator for an ordered pair of circles; it records which of the two adjacent circles holds the smaller digit, and only one direction of each adjacency can be active"},
        {"name": "y", "index": "c,cc", "domain": "Binary",
         "doc": "a digit assignment indicator that equals 1 when a circle is given the digit value corresponding to the second index and 0 otherwise"},
        {"name": "dummy", "index": "", "domain": "Reals",
         "doc": "an accounting variable holding the total of all placed digits"},
    ],
    "objective": {"sense": "minimize", "expr_var": "dummy"},
}

NARRATIVE = (
    "We place eight distinct digit values, one in each circle of a figure, choosing which digit goes "
    "in which circle. Alongside the digit placed in each circle we track, for every adjacent pair of "
    "circles, which of the two holds the smaller value, and we track the assignment of each digit value "
    "to a circle. The objective is to minimize an accounting variable that totals the digits placed "
    "across all circles."
)

LESS = (
    "def less_rule(model, c, cc):\n"
    "    return model.x[cc] <= model.x[c] - model.gap + model.bign * model.ll[c, cc]\n"
    "model.less = Constraint(model.net, rule=less_rule)"
)
MORE = (
    "def more_rule(model, c, cc):\n"
    "    return model.x[cc] >= model.x[c] + model.gap - model.bign * model.ll[cc, c]\n"
    "model.more = Constraint(model.net, rule=more_rule)"
)
CROSS = (
    "def cross_rule(model, c, cc):\n"
    "    return model.ll[c, cc] + model.ll[cc, c] == 1\n"
    "model.cross = Constraint(model.net, rule=cross_rule)"
)
DIGIT = (
    "def digit_rule(model, c):\n"
    "    return model.x[c] == sum((i + 1) * model.y[c, cc] for i, cc in enumerate(model.cc))\n"
    "model.digit = Constraint(model.c, rule=digit_rule)"
)
ROWSUM = (
    "def rowsum_rule(model, c):\n"
    "    return sum(model.y[c, cc] for cc in model.cc) == 1\n"
    "model.rowsum = Constraint(model.c, rule=rowsum_rule)"
)
COLSUM = (
    "def colsum_rule(model, c):\n"
    "    return sum(model.y[cc, c] for cc in model.cc) == 1\n"
    "model.colsum = Constraint(model.c, rule=colsum_rule)"
)
AP = (
    "def ap_rule(model):\n"
    "    return model.dummy == sum(model.x[c] for c in model.c)\n"
    "model.ap = Constraint(rule=ap_rule)"
)
WHOLESET = "\n".join([LESS, MORE, CROSS, DIGIT, ROWSUM, COLSUM, AP])

records = [
    {"description": (
        "For each adjacent pair of circles in a given direction, the digit in the second circle must stay "
        "below the digit in the first circle by at least the required difference, but only when the ordering "
        "indicator for that direction says the first circle holds the larger digit. When the indicator points "
        "the other way this requirement is loosened by the big constant so that it places no real limit."),
     "expected_pyomo": LESS},
    {"description": (
        "For each adjacent pair of circles in a given direction, the digit in the second circle must exceed "
        "the digit in the first circle by at least the required difference, but only when the ordering indicator "
        "for the reverse direction says the first circle holds the smaller digit. When that indicator points the "
        "other way this requirement is loosened by the big constant so that it places no real limit."),
     "expected_pyomo": MORE},
    {"description": (
        "For each adjacent pair of circles, exactly one of the two ordering directions is active, so between any "
        "two adjacent circles one is recognized as holding the smaller digit and the other the larger."),
     "expected_pyomo": CROSS},
    {"description": (
        "For each circle, the digit placed in it equals the digit value selected by its assignment, where each "
        "candidate value contributes its own magnitude weighted by whether that value was chosen for the circle."),
     "expected_pyomo": DIGIT},
    {"description": (
        "Each circle is assigned exactly one digit value, so across all candidate values the assignment for a "
        "circle sums to one."),
     "expected_pyomo": ROWSUM},
    {"description": (
        "Each digit value is used in exactly one circle, so across all circles the assignment of any given value "
        "sums to one."),
     "expected_pyomo": COLSUM},
    {"description": (
        "The accounting variable equals the total of all the digits placed across the circles."),
     "expected_pyomo": AP},
    {"description": (
        "To build the complete model, enforce the following relationships in order. "
        "First, for each adjacent pair of circles in a given direction, force the digit in the second circle to stay "
        "below the digit in the first by at least the required difference whenever the ordering indicator for that "
        "direction marks the first circle as the larger, and otherwise loosen it by the big constant so it does not bind. "
        "Second, for each adjacent pair in a given direction, force the digit in the second circle to exceed the digit in "
        "the first by at least the required difference whenever the reverse ordering indicator marks the first circle as the "
        "smaller, and otherwise loosen it by the big constant so it does not bind. "
        "Third, for each adjacent pair of circles let exactly one of the two ordering directions be active. "
        "Fourth, for each circle set the digit placed in it equal to the digit value selected by its assignment, with each "
        "candidate value contributing its own magnitude according to whether it was chosen. "
        "Fifth, give each circle exactly one assigned digit value. "
        "Sixth, use each digit value in exactly one circle. "
        "Finally, set the accounting variable equal to the total of all digits placed across the circles."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "marilyn_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
