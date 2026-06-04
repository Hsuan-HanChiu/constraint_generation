#!/usr/bin/env python
"""Builder for the thai_mip (Thai Navy evacuation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "thai_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["chumphon", "surat", "nakon", "songkhla"],
         "doc": "the ports where stranded men must be picked up and evacuated"},
        {"name": "j", "members": ["v-01", "v-02", "v-03", "v-04", "v-05", "v-06", "v-07", "v-08", "v-09", "v-10", "v-11", "v-12", "v-13", "v-14", "v-15"],
         "doc": "the candidate voyages; each voyage is a predefined route that calls at one or more ports"},
        {"name": "k", "members": ["small", "medium", "large"],
         "doc": "the ship classes, ordered from smallest to largest carrying capacity"},
        {"name": "a", "members": "list of (voyage, port) pairs",
         "doc": "the voyage-port assignments; a pair belongs to this set when that voyage actually calls at that port, so it tells you which ports each voyage can pick up men from"},
        {"name": "sc", "members": "list of (port, ship_class) pairs",
         "doc": "the port and ship-class pairs for which that class of ship is physically able to serve that port; a class missing for a port cannot dock or load there"},
        {"name": "vc", "members": "list of (voyage, ship_class) pairs",
         "doc": "the feasible voyage and ship-class combinations; a combination is feasible only when the ship class can serve every port that the voyage calls at, so only these voyage and class pairs may actually be operated"},
    ],
    "params": [
        {"name": "d", "index": "i", "kind": "demand",
         "doc": "the number of men that must be evacuated from each port, in men"},
        {"name": "shipcap", "index": "k", "kind": "capacity",
         "doc": "the carrying capacity of a single ship of each class, in men per ship"},
        {"name": "n", "index": "k", "kind": "availability",
         "doc": "the number of ships available in each class, a hard upper limit on how many sailings of that class can be operated in total"},
        {"name": "dist", "index": "j", "kind": "distance",
         "doc": "the distance associated with each voyage, used only in the objective"},
    ],
    "vars": [
        {"name": "z", "index": "j,k", "domain": "NonNegativeIntegers",
         "doc": "the number of times a given voyage is operated using a given ship class; a whole number since each sailing is one physical trip"},
        {"name": "y", "index": "j,k,i", "domain": "NonNegativeReals",
         "doc": "the number of men carried from a given port on a given voyage operated by a given ship class"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We are planning a naval evacuation. A fixed set of candidate voyages is available, each "
    "voyage being a route that calls at one or more coastal ports, and each voyage can be run "
    "with ships of different size classes. We decide how many times to run each voyage with each "
    "ship class and how many men to carry from each port on each of those sailings. The objective "
    "is to minimize a weighted combination of the total number of sailings, the total distance "
    "sailed, and the total man-distance moved, with the number of sailings weighted most heavily "
    "and the man-distance term weighted least."
)

DEMAND = (
    "def demand_rule(model, i):\n"
    "    return sum(model.y[j,k,i] for j, k in model.vc if (j,i) in model.a) >= model.d[i]\n"
    "model.demand = Constraint(model.i, rule=demand_rule)"
)
VOYCAP = (
    "def voycap_rule(model, j, k):\n"
    "    if (j, k) in model.vc:\n"
    "        return sum(model.y[j,k,i] for i in model.i if (j,i) in model.a) <= model.shipcap[k]*model.z[j,k]\n"
    "    else:\n"
    "        return Constraint.Skip\n"
    "model.voycap = Constraint(model.j, model.k, rule=voycap_rule)"
)
SHIPLIM = (
    "def shiplim_rule(model, k):\n"
    "    return sum(model.z[j,k] for j in model.j if (j, k) in model.vc) <= model.n[k]\n"
    "model.shiplim = Constraint(model.k, rule=shiplim_rule)"
)
WHOLESET = "\n".join([DEMAND, VOYCAP, SHIPLIM])

records = [
    {"description": (
        "Every port must have all of its stranded men picked up. For each port, the total number of "
        "men carried away from that port across all the sailings that actually call there must be at "
        "least the number of men that need to be evacuated from it."),
     "expected_pyomo": DEMAND},
    {"description": (
        "A sailing can only carry as many men as the ship operating it can hold. For each feasible "
        "combination of a voyage and a ship class, the total number of men carried out of all the "
        "ports that voyage calls at must not exceed the capacity of one ship of that class multiplied "
        "by the number of times that voyage is run with that class. Combinations that are not feasible "
        "are left out."),
     "expected_pyomo": VOYCAP},
    {"description": (
        "We cannot run more sailings of a ship class than we have ships in that class. For each ship "
        "class, the total number of sailings operated with that class, added up over all the voyages "
        "it can feasibly run, must not exceed the number of ships available in that class."),
     "expected_pyomo": SHIPLIM},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "thai_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
