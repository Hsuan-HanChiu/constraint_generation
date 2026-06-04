#!/usr/bin/env python
"""Builder for the airsp2_lp134 (aircraft-to-route assignment) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "airsp2_lp134_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["a", "b", "c", "d"],
         "doc": "the available aircraft types"},
        {"name": "j", "members": ["route-1", "route-2", "route-3", "route-4", "route-5"],
         "doc": "the routes that must be served"},
    ],
    "params": [
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the operating cost of flying one aircraft of a given type on a given route, in thousands of dollars per aircraft"},
        {"name": "pcap", "index": "i,j", "kind": "capacity",
         "doc": "the passenger capacity of one aircraft of a given type on a given route, in hundreds of passengers per aircraft"},
        {"name": "aircraft", "index": "i", "kind": "availability",
         "doc": "the number of aircraft of each type available to assign, as a count"},
        {"name": "fixeddemand", "index": "j", "kind": "demand",
         "doc": "the passenger demand that must be served on each route, in hundreds of passengers"},
        {"name": "costbumped", "index": "j", "kind": "cost",
         "doc": "the penalty cost per unit of passenger demand that is bumped on a route rather than served, in thousands of dollars per hundred passengers"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the number of aircraft of each type assigned to each route"},
        {"name": "bumped", "index": "j", "domain": "NonNegativeReals",
         "doc": "the amount of passenger demand bumped on each route, in hundreds of passengers"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total cost, in thousands of dollars, combining aircraft operating costs and bumping penalties"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "An airline has a fleet of different aircraft types and a set of routes that must be flown. "
    "For each route it decides how many aircraft of each type to assign, and how much passenger "
    "demand to leave unserved by bumping it. Operating an aircraft on a route costs a known amount "
    "that depends on both the aircraft type and the route, and bumping demand on a route incurs a "
    "per-unit penalty. The airline wants to make the combined total of operating costs and bumping "
    "penalties as small as possible."
)

COST = (
    "def cost_rule(model):\n"
    "    return model.z == (sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)\n"
    "                       + sum(model.costbumped[j] * model.bumped[j] for j in model.j))\n"
    "model.cost = Constraint(rule=cost_rule)"
)
AVAIL = (
    "def avail_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.j) <= model.aircraft[i]\n"
    "model.avail = Constraint(model.i, rule=avail_rule)"
)
DEMAND = (
    "def demand_rule(model, j):\n"
    "    return sum(model.pcap[i, j] * model.x[i, j] for i in model.i) + model.bumped[j] >= model.fixeddemand[j]\n"
    "model.demand = Constraint(model.j, rule=demand_rule)"
)
WHOLESET = "\n".join([COST, AVAIL, DEMAND])

records = [
    {"description": (
        "The total cost brings together everything the airline pays. For each aircraft type and "
        "route combination, value the aircraft assigned to that route at its operating cost, and "
        "add up these amounts over all combinations. Then add the bumping penalties, charging each "
        "route's per-unit penalty against the demand bumped on that route. Set the total cost equal "
        "to the sum of all the operating costs plus all the bumping penalties."),
     "expected_pyomo": COST},
    {"description": (
        "Each aircraft type is available only in limited quantity. For each aircraft type, the total "
        "number of that type assigned across all routes must not exceed the number of that type "
        "available."),
     "expected_pyomo": AVAIL},
    {"description": (
        "Every route's passenger demand has to be covered, either by flying enough seats or by "
        "bumping the shortfall. For each route, the seating capacity provided by all the aircraft "
        "assigned to it, together with the demand bumped on that route, must be at least the demand "
        "required on that route."),
     "expected_pyomo": DEMAND},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "airsp2_lp134",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
