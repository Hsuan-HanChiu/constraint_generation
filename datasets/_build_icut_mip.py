#!/usr/bin/env python
"""Builder for the icut_mip constraint-generation dataset.

icut_mip is a small integer-cut test model. With the shipped data all cut
parameters (cutrhs, cutux, cutlx, cuts) are zero, so the entire cut family
(cut, cutu, cutl, cutul) is Constraint.Skip-ped and produces no active
constraint instances. The only active, gradeable LINEAR constraint is the
objective-definition constraint obj_def. The cut constraints are excluded
(empty under the shipped data; nothing to grade).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "icut_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "I", "members": [1, 2, 3, 4],
         "doc": "the set of digit positions of the integer decision, given in order from the most significant position to the least significant position; the first member is the highest-order position and the last member is the lowest-order position"},
        {"name": "KK", "members": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
         "doc": "an identification set used to label successive generated cuts; under the shipped data no cut is active so this set indexes no active constraint"},
    ],
    "params": [
        {"name": "cutrhs", "index": "KK", "kind": "rhs",
         "doc": "the right-hand-side value of each generated cut; zero for every cut under the shipped data, which deactivates the entire cut family"},
        {"name": "cutlx", "index": "KK,I", "kind": "bound",
         "doc": "the allowed downward change at each position for each cut; zero everywhere under the shipped data"},
        {"name": "cutux", "index": "KK,I", "kind": "bound",
         "doc": "the allowed upward change at each position for each cut; zero everywhere under the shipped data"},
        {"name": "cuts", "index": "KK,I", "kind": "reference",
         "doc": "the reference solution value at each position for each cut; zero everywhere under the shipped data"},
    ],
    "vars": [
        {"name": "x", "index": "I", "domain": "Integers",
         "doc": "the digit chosen at each position; integer valued, bounded between 2 and 4, with the second position fixed at 3 and the fourth position capped at 3"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the scalar value of the assembled number, which is the quantity reported by the objective"},
        {"name": "b", "index": "KK,I", "domain": "Binary",
         "doc": "a flip-flop selector used inside the cut family to choose between an upward and a downward change at a position; inactive under the shipped data"},
        {"name": "u", "index": "KK,I", "domain": "NonNegativeReals",
         "doc": "the upward change at a position used inside the cut family; inactive under the shipped data"},
        {"name": "l", "index": "KK,I", "domain": "NonNegativeReals",
         "doc": "the downward change at a position used inside the cut family; inactive under the shipped data"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We assemble a single number from four ordered digit positions, choosing an integer "
    "digit at each position. The positions run from the most significant down to the least "
    "significant, so a digit chosen at a higher-order position contributes far more to the "
    "assembled value than one chosen at a lower-order position, scaled by powers of ten. "
    "The objective is to minimize the assembled value of the number."
)

OBJ_DEF = (
    "def obj_def_rule(model):\n"
    "    I_list = list(model.I)\n"
    "    n = len(I_list)\n"
    "    place = {i: idx for idx, i in enumerate(I_list, start=1)}\n"
    "    return model.z == sum(10 ** (n - place[i]) * model.x[i] for i in model.I)\n"
    "model.obj_def = Constraint(rule=obj_def_rule)"
)

WHOLESET = OBJ_DEF

records = [
    {"description": (
        "The reported value of the number must equal what the chosen digits assemble to. "
        "Reading the positions from the most significant down to the least significant, each "
        "position's digit carries a place value that is ten times larger than the position "
        "immediately after it, and the least significant position carries a place value of one. "
        "Set the reported value equal to the sum across all positions of each digit weighted by "
        "its place value."),
     "expected_pyomo": OBJ_DEF},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "icut_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
