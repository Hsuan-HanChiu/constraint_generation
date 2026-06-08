#!/usr/bin/env python
"""Builder for the netgen_lp (minimum-cost-flow) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "netgen_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "node", "members": ["1", "...", "50"],
         "doc": "the nodes of the transportation network, given as integer ids"},
        {"name": "arc", "members": ["(1,26)", "(1,27)", "..."],
         "doc": "the directed arcs of the network, each an ordered pair of nodes where flow may travel from the first node to the second node"},
    ],
    "params": [
        {"name": "cost", "index": "arc", "kind": "cost",
         "doc": "the unit shipping cost incurred for each unit of flow sent along an arc, in dollars per unit"},
        {"name": "capacity", "index": "arc", "kind": "capacity",
         "doc": "the maximum amount of flow that an arc can carry, in units"},
        {"name": "supply", "index": "node", "kind": "supply",
         "doc": "the amount of flow injected into the network from outside at a node, in units"},
        {"name": "demand", "index": "node", "kind": "demand",
         "doc": "the amount of flow withdrawn from the network to satisfy external requirements at a node, in units"},
    ],
    "vars": [
        {"name": "x", "index": "arc", "domain": "NonNegativeReals",
         "doc": "the amount of flow sent along each arc"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We route flow through a directed transportation network. Each node may inject "
    "some flow into the network from outside and may withdraw some flow to meet external "
    "requirements. Our decision is how much flow to send along each directed arc, where "
    "every unit shipped on an arc incurs a known per-unit cost. The objective is to make "
    "the total shipping cost over all arcs as small as possible."
)

CAP = (
    "def cap_rule(model, i, j):\n"
    "    return model.x[i, j] <= model.capacity[i, j]\n"
    "model.cap = Constraint(model.arc, rule=cap_rule)"
)
NET = (
    "def net_rule(model, nn):\n"
    "    inflow = sum(model.x[i, j] for (i, j) in model.arc if j == nn)\n"
    "    outflow = sum(model.x[i, j] for (i, j) in model.arc if i == nn)\n"
    "    return model.supply[nn] + inflow == outflow + model.demand[nn]\n"
    "model.net = Constraint(model.node, rule=net_rule)"
)
WHOLESET = "\n".join([CAP, NET])

CAP_DESC = (
    "Every arc can carry only so much flow. For each arc, the flow sent along that arc "
    "must not exceed the arc's carrying capacity."
)
NET_DESC = (
    "Flow must be conserved at every node. For each node, the flow injected into the network "
    "from outside at that node together with the total flow arriving on arcs that point into "
    "the node must equal the total flow leaving on arcs that point out of the node together "
    "with the flow withdrawn to meet external requirements at that node."
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for each arc, the flow sent along that arc must not exceed the arc's carrying "
    "capacity. "
    "Finally, for each node, the flow injected from outside together with the total flow "
    "arriving on arcs into the node must equal the total flow leaving on arcs out of the node "
    "together with the flow withdrawn to meet external requirements at that node."
)

records = [
    {"description": CAP_DESC, "expected_pyomo": CAP},
    {"description": NET_DESC, "expected_pyomo": NET},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "netgen_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
