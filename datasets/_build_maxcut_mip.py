#!/usr/bin/env python
"""Builder for the maxcut_mip (linearized max-cut) constraint-generation dataset.

All constraints are LINEAR (polynomial_degree 1): the model is a linearized
max-cut, so the per-edge cut indicator is captured by four linear inequalities
rather than a quadratic x_i + x_j - 2 x_i x_j product. Every constraint is
included; none is nonlinear.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "maxcut_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "n", "members": ["1", "2", "3", "4", "5"],
         "doc": "the nodes (vertices) of the graph, indexed by name"},
        {"name": "e", "members": [["1", "2"], ["1", "3"], ["2", "3"], ["2", "4"], ["3", "5"], ["4", "5"]],
         "doc": "the edges of the graph, given as ordered node pairs (i, j) with i listed before j; each pair connects two distinct nodes"},
    ],
    "params": [
        {"name": "w", "index": "e", "kind": "weight",
         "doc": "the weight of each edge, which contributes to the cut value only when that edge has its two endpoints on opposite sides of the partition; weights may be positive or negative"},
    ],
    "vars": [
        {"name": "x", "index": "n", "domain": "Binary",
         "doc": "the side of the partition that each node is assigned to, taking value 0 for one side and 1 for the other"},
        {"name": "cut", "index": "e", "domain": "NonNegativeReals, bounded between 0 and 1",
         "doc": "the cut indicator of each edge, intended to be 1 when the edge's two endpoints lie on opposite sides and 0 otherwise; relaxed to the continuous interval from 0 to 1, since the surrounding inequalities and the maximizing objective drive it to the correct integral value"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total weight of all edges that cross the cut"},
    ],
    "objective": {"sense": "maximize", "expr_var": "obj"},
}

NARRATIVE = (
    "We are given a graph whose edges carry weights, and we must split its nodes into two sides. "
    "For each node we decide which of the two sides it goes on, and an edge is said to cross the "
    "cut when its two endpoints end up on opposite sides. We also track, for each edge, whether it "
    "crosses the cut, and we track the total weight collected from all crossing edges. The goal is "
    "to choose the partition so that the total weight of the edges crossing the cut is as large as "
    "possible."
)

OBJ_DEF = (
    "model.obj_def = Constraint(expr=model.z == sum(model.w[i, j] * model.cut[i, j] for (i, j) in model.e))"
)
XOR1 = (
    "def xor1_rule(model, i, j):\n"
    "    return model.cut[i, j] <= model.x[i] + model.x[j]\n"
    "model.xor1 = Constraint(model.e, rule=xor1_rule)"
)
XOR2 = (
    "def xor2_rule(model, i, j):\n"
    "    return model.cut[i, j] <= 2 - model.x[i] - model.x[j]\n"
    "model.xor2 = Constraint(model.e, rule=xor2_rule)"
)
XOR3 = (
    "def xor3_rule(model, i, j):\n"
    "    return model.cut[i, j] >= model.x[i] - model.x[j]\n"
    "model.xor3 = Constraint(model.e, rule=xor3_rule)"
)
XOR4 = (
    "def xor4_rule(model, i, j):\n"
    "    return model.cut[i, j] >= model.x[j] - model.x[i]\n"
    "model.xor4 = Constraint(model.e, rule=xor4_rule)"
)
WHOLESET = "\n".join([OBJ_DEF, XOR1, XOR2, XOR3, XOR4])

D_OBJ = (
    "The total cut weight must equal the combined weight of every edge that crosses the cut, where "
    "each edge contributes its own weight scaled by how much it crosses. Add up that contribution "
    "across all edges and set the tracked total equal to it."
)
D_XOR1 = (
    "An edge can only count as crossing the cut if at least one of its two endpoints sits on the "
    "side labelled one. For each edge, its crossing indicator must not exceed the combined side "
    "labels of its two endpoints, so when both endpoints are on side zero the edge cannot cross."
)
D_XOR2 = (
    "An edge can only count as crossing the cut if at least one of its two endpoints sits on the "
    "side labelled zero. For each edge, its crossing indicator must not exceed the amount by which "
    "the two endpoint side labels fall short of both being on side one, so when both endpoints are "
    "on side one the edge cannot cross."
)
D_XOR3 = (
    "Whenever the first endpoint of an edge is on side one and the second is on side zero, that "
    "edge must be counted as crossing the cut. For each edge, its crossing indicator must be at "
    "least the first endpoint's side label minus the second endpoint's side label."
)
D_XOR4 = (
    "Whenever the second endpoint of an edge is on side one and the first is on side zero, that "
    "edge must be counted as crossing the cut. For each edge, its crossing indicator must be at "
    "least the second endpoint's side label minus the first endpoint's side label."
)

WHOLE_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, " + D_OBJ[0].lower() + D_OBJ[1:] + " "
    "Second, an edge can only count as crossing the cut if at least one of its two endpoints sits "
    "on the side labelled one. "
    "Third, an edge can only count as crossing the cut if at least one of its two endpoints sits "
    "on the side labelled zero. "
    "Fourth, whenever the first endpoint of an edge is on side one and the second is on side zero, "
    "that edge must be counted as crossing the cut. "
    "Finally, whenever the second endpoint of an edge is on side one and the first is on side zero, "
    "that edge must be counted as crossing the cut."
)

records = [
    {"description": D_OBJ, "expected_pyomo": OBJ_DEF},
    {"description": D_XOR1, "expected_pyomo": XOR1},
    {"description": D_XOR2, "expected_pyomo": XOR2},
    {"description": D_XOR3, "expected_pyomo": XOR3},
    {"description": D_XOR4, "expected_pyomo": XOR4},
    {"description": WHOLE_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "maxcut_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
