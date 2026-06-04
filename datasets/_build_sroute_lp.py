#!/usr/bin/env python
"""Builder for the sroute_lp (multi-commodity routing / node-balance) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "sroute_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["boston", "chicago", "dallas", "kansas-cty",
                                   "losangeles", "memphis", "portland", "salt-lake", "wash-dc"],
         "doc": "the cities in the network; this same set is also used as the alias ip and the alias ipp, so a triple over i, ip, ipp ranges over every ordered combination of three cities"},
    ],
    "params": [
        {"name": "uarc", "index": "i,ip", "kind": "network",
         "doc": "the undirected links of the network with their length, listed once per unordered pair of cities; a value is present only for pairs that are physically connected, in distance units"},
        {"name": "darc", "index": "i,ip", "kind": "network",
         "doc": "the directed-arc length between two cities, obtained by reading each undirected link in both directions; it is positive exactly when the two cities are directly connected and equals zero for every disconnected ordered pair, so a nonzero darc marks an available one-way arc and its value is the arc length in distance units"},
    ],
    "vars": [
        {"name": "x", "index": "i,ip,ipp", "domain": "NonNegativeReals",
         "doc": "the flow of the commodity destined for city given by the first index that travels along the directed arc from the second-index city to the third-index city; the first index labels the destination commodity and the last two indices identify the directed arc carrying it"},
        {"name": "cost", "index": "", "domain": "Reals",
         "doc": "the total routing cost over the whole network, in distance-weighted flow units"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We route flow across a network of cities connected by physical links. For each "
    "destination city we decide how much of that destination's flow to send along each "
    "available directed arc between two cities. Sending flow along an arc costs its length "
    "times the flow carried. The goal is to choose all the arc flows so that the total "
    "routing cost across the whole network is as small as possible."
)

NB = (
    "def nb_rule(model, i, ip):\n"
    "    if i != ip:\n"
    "        return sum(model.x[i, ipp, ip] for ipp in model.i if model.darc[ipp, ip] != 0) >= sum(model.x[i, ip, ipp] for ipp in model.i if model.darc[ip, ipp] != 0) + 1\n"
    "    else:\n"
    "        return Constraint.Skip\n"
    "model.nb = Constraint(model.i, model.i, rule=nb_rule)"
)
CD = (
    "def cd_rule(model):\n"
    "    return model.cost == sum(model.darc[ip, ipp] * model.x[i, ip, ipp] for i in model.i for ip in model.i for ipp in model.i)\n"
    "model.cd = Constraint(rule=cd_rule)"
)
WHOLESET = "\n".join([NB, CD])

records = [
    {"description": (
        "Every city other than a commodity's own destination must pass that destination's flow "
        "through with a little to spare. For each pairing of a destination with any city that is "
        "not that destination, the total of the destination's flow arriving at the city over the "
        "arcs that lead into it must be at least the total of the destination's flow leaving the "
        "city over the arcs that lead out of it, plus one more unit. Only arcs that actually exist "
        "between connected cities count on either side. When the city being balanced is the "
        "destination itself, no such requirement applies."),
     "expected_pyomo": NB},
    {"description": (
        "The total routing cost gathers the length-weighted flow over the entire network. For every "
        "destination commodity and every ordered pair of cities, multiply the flow of that commodity "
        "on the arc from the first city to the second by the length of that arc, and add it up across "
        "all commodities and all ordered city pairs. Set the total cost variable equal to this sum."),
     "expected_pyomo": CD},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "sroute_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
