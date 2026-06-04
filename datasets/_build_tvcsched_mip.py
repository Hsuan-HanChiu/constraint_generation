#!/usr/bin/env python
"""Builder for the tvcsched_mip (color-spacing scheduling, network-flow MIP) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tvcsched_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "CACT", "members": ["R", "B", "W", "G"], "kind": "color",
         "doc": "the colors that actually have one or more items to place; colors with a count of zero are dropped and never appear here"},
        {"name": "S", "members": ["1", "...", "20"], "kind": "slot",
         "doc": "the ordered positions on the schedule, one per item to be placed, numbered consecutively from the first position onward"},
        {"name": "Arcs", "members": ["(color, from-node, to-node) triples"], "kind": "network arc",
         "doc": "the directed arcs of a per-color routing network whose nodes are a special source node labeled 0 together with the schedule positions; an arc carries flow of a single color from one node to a later node, and there are also return arcs from each position back to the source node 0; for a given color, an item placed at the from-node is followed next by an item of that color at the to-node, so traversing an arc moves from one occurrence of a color to its next occurrence"},
    ],
    "params": [
        {"name": "nc", "index": "C", "kind": "count",
         "doc": "the number of items of each color that must be placed somewhere on the schedule, as a whole number"},
        {"name": "dev", "index": "Arcs", "kind": "cost",
         "doc": "the spacing penalty charged for routing a color along an arc, equal to how far the gap between the two endpoints of the arc departs from that color's ideal even spacing; arcs touching the source node 0 carry no penalty"},
    ],
    "vars": [
        {"name": "f", "index": "Arcs", "domain": "NonNegativeReals",
         "doc": "the amount of flow sent along each arc for its color; one unit of flow traces the ordered sequence of positions used by a color"},
        {"name": "p", "index": "(C, S)", "domain": "Binary",
         "doc": "one when the given color is assigned to the given position, zero otherwise"},
        {"name": "obj", "index": "", "domain": "Reals",
         "doc": "the total spacing penalty accumulated over the whole schedule"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We arrange a collection of colored items into an ordered list of positions, one item per position. "
    "Each color comes with a fixed number of items that all have to be placed. We want items of the same "
    "color to be spread out as evenly as possible rather than bunched together, and we model the ordering "
    "of each color as a flow through a small routing network that visits that color's chosen positions in "
    "order. The objective is to minimize the total spacing penalty, which measures how far the gaps between "
    "consecutive same-color items stray from perfectly even spacing across the whole schedule."
)

# ── constraint sources (native names, model. prefix, self-contained) ──────────

BAL = (
    "def bal_rule(model, c, s):\n"
    "    incoming = sum(model.f[c, i, j] for (cc, i, j) in model.Arcs if cc == c and j == s)\n"
    "    outgoing = sum(model.f[c, i, j] for (cc, i, j) in model.Arcs if cc == c and i == s)\n"
    "    return incoming - outgoing == 0.0\n"
    "model.bal = Constraint(model.CACT, model.S, rule=bal_rule)"
)

BALINIT = (
    "def balinit_rule(model, c):\n"
    "    return sum(model.f[c, i, j] for (cc, i, j) in model.Arcs if cc == c and i == '0') == 1.0\n"
    "model.balinit = Constraint(model.CACT, rule=balinit_rule)"
)

DEFOPEN = (
    "def defopen_rule(model, c, s):\n"
    "    outflow = sum(model.f[c, i, j] for (cc, i, j) in model.Arcs if cc == c and i == s)\n"
    "    return outflow == model.p[c, s]\n"
    "model.defopen = Constraint(model.CACT, model.S, rule=defopen_rule)"
)

DEFSUMP = (
    "def defsump_rule(model, c):\n"
    "    return sum(model.p[c, s] for s in model.S) == model.nc[c]\n"
    "model.defsump = Constraint(model.CACT, rule=defsump_rule)"
)

COVSLOT = (
    "def covslot_rule(model, s):\n"
    "    return sum(model.p[c, s] for c in model.CACT) == 1.0\n"
    "model.covslot = Constraint(model.S, rule=covslot_rule)"
)

DEFOBJ = (
    "def defobj_rule(model):\n"
    "    return model.obj == sum(model.dev[c, i, j] * model.f[c, i, j] for (c, i, j) in model.Arcs)\n"
    "model.defobj = Constraint(rule=defobj_rule)"
)

WHOLESET = "\n".join([BAL, BALINIT, DEFOPEN, DEFSUMP, COVSLOT, DEFOBJ])

records = [
    {"description": (
        "For each color at each position, the routing of that color has to be conserved. The amount of that "
        "color's flow arriving at the position must equal the amount leaving it, so nothing accumulates or "
        "disappears at any position."),
     "expected_pyomo": BAL},
    {"description": (
        "Every color that has items to place starts its routing exactly once. For each such color, the total "
        "flow leaving the source node and entering the schedule must be exactly one unit."),
     "expected_pyomo": BALINIT},
    {"description": (
        "A position is used by a color exactly when that color's routing passes through it. For each color at "
        "each position, the total flow of that color leaving the position must equal whether that color is "
        "assigned to that position."),
     "expected_pyomo": DEFOPEN},
    {"description": (
        "Each color must end up placed the required number of times. For each color, the number of positions "
        "assigned to it across the whole schedule must equal that color's required item count."),
     "expected_pyomo": DEFSUMP},
    {"description": (
        "Every position holds exactly one item. For each position, exactly one color may be assigned to it."),
     "expected_pyomo": COVSLOT},
    {"description": (
        "The total spacing penalty accounts for every arc the routings traverse. Set the total penalty equal to "
        "the sum over all arcs of that arc's spacing penalty weighted by the amount of flow sent along it."),
     "expected_pyomo": DEFOBJ},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "tvcsched_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
