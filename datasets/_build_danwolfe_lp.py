#!/usr/bin/env python
"""Builder for the danwolfe_lp (multi-commodity network flow) constraint-generation dataset.

FLAGGED possibly-nonlinear: VERIFIED all three native constraints are LINEAR.
- defobj : z == sum_{k,e} cost[e]*x[k,e]            (param x var)  LINEAR
- defbal : outflow(k,i) - inflow(k,i) == bal[k,i]   (sums of vars) LINEAR
- defcap : sum_k x[k,e] <= cap[e]                   (sum of vars)  LINEAR
The random/math.log in the .py only generate PARAMETER VALUES (cost, cap, bal,
the edge set), never appear in constraint algebra. Nothing excluded.

The edge set `e` is generated inside the model build (seeded random), so the
expected_pyomo iterates over the LIVE components (model.e, model.k, model.i)
rather than re-deriving the edges, which is how the harness execs the code.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "danwolfe_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["n1", "n2", "n3", "...", "n20"],
         "doc": "the network nodes; flow originates, passes through, and terminates at these nodes"},
        {"name": "j", "members": ["n1", "n2", "n3", "...", "n20"],
         "doc": "an alias of the node set, used as the second endpoint when referring to a directed connection from one node to another"},
        {"name": "k", "members": ["k1", "k2", "k3", "k4", "k5"],
         "doc": "the commodities; each commodity is a separate good that flows through the same shared network with its own supply and demand pattern"},
        {"name": "e", "members": ["(n1, n3)", "(n1, n5)", "...directed node pairs..."],
         "doc": "the directed edges that actually exist in the network, given as ordered pairs of distinct nodes; an edge from one node to another permits flow in that direction only, and only node pairs present in this set may carry any flow"},
    ],
    "params": [
        {"name": "cost", "index": "e", "kind": "cost",
         "doc": "the per-unit cost of sending one unit of any commodity along an edge, in dollars per unit; the same edge cost applies to every commodity using that edge"},
        {"name": "cap", "index": "e", "kind": "capacity",
         "doc": "the bundle capacity of an edge, in units; this is the total amount of flow the edge can carry when the flows of all commodities sharing that edge are added together"},
        {"name": "bal", "index": "k, i", "kind": "balance",
         "doc": "the net supply of a commodity at a node, in units; a positive value means the node is a source that injects that much of the commodity, a negative value means the node is a sink that withdraws that much, and zero means the node is a pure transshipment point for that commodity"},
        {"name": "kdem", "index": "k", "kind": "demand",
         "doc": "the total demand of a commodity, in units, computed as the sum of all positive net supplies of that commodity across the nodes; provided for reference and not used in any constraint"},
    ],
    "vars": [
        {"name": "x", "index": "k, i, j", "domain": "NonNegativeReals",
         "doc": "the amount of a commodity routed from one node to another along the directed edge between them; defined per commodity and per ordered node pair, and only meaningful on pairs that are actual edges"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total routing cost accumulated over the whole network, in dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We route several distinct commodities through a shared directed network of nodes "
    "and edges. Each commodity has its own pattern of sources and sinks across the nodes, "
    "and we decide how much of each commodity to send along each available edge. Sending a "
    "unit of any commodity along an edge costs a known per-unit amount, and the edges are "
    "shared, so all commodities routed over the same edge draw on one common capacity. The "
    "objective is to minimize the total routing cost accumulated across the whole network."
)

DEFOBJ = (
    "def defobj_rule(model):\n"
    "    return model.z == sum(model.cost[i, j] * model.x[k, i, j] for k in model.k for (i, j) in model.e)\n"
    "model.defobj = Constraint(rule=defobj_rule)"
)

DEFBAL = (
    "def defbal_rule(model, k, i):\n"
    "    outflow = sum(model.x[k, i, j] for (a, j) in model.e if a == i)\n"
    "    inflow = sum(model.x[k, j, i] for (j, b) in model.e if b == i)\n"
    "    return outflow - inflow == model.bal[k, i]\n"
    "model.defbal = Constraint(model.k, model.i, rule=defbal_rule)"
)

DEFCAP = (
    "def defcap_rule(model, i, j):\n"
    "    return sum(model.x[k, i, j] for k in model.k) <= model.cap[i, j]\n"
    "model.defcap = Constraint(model.e, rule=defcap_rule)"
)

WHOLESET = "\n".join([DEFOBJ, DEFBAL, DEFCAP])

records = [
    {"description": (
        "The total routing cost must capture every unit of every commodity moving across the "
        "network. For each commodity and each existing edge, take the amount of that commodity "
        "sent along the edge and charge it at that edge's per-unit cost, then add all of these "
        "amounts together. Set the total cost variable equal to this grand total."),
     "expected_pyomo": DEFOBJ},
    {"description": (
        "Every commodity must be conserved at every node according to that node's role for it. "
        "For each commodity at each node, look at how much of that commodity leaves the node "
        "along its outgoing edges and how much arrives along its incoming edges. The amount "
        "leaving minus the amount arriving must equal the node's net supply of that commodity, "
        "so a source sends out its surplus, a sink absorbs its shortfall, and a transshipment "
        "node passes through exactly what it receives."),
     "expected_pyomo": DEFBAL},
    {"description": (
        "Each edge is shared by all the commodities that use it and cannot be overloaded. For "
        "each existing edge, add up the flow of every commodity sent along that edge, and keep "
        "that combined flow at or below the edge's capacity."),
     "expected_pyomo": DEFCAP},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "danwolfe_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
