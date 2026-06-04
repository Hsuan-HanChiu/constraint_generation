#!/usr/bin/env python
"""Builder for the aircraft_lp (aircraft assignment / passenger bumping) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "aircraft_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["a", "b", "c", "d"],
         "doc": "the available aircraft types, each a distinct fleet of planes that can be flown on routes"},
        {"name": "j", "members": ["route-1", "route-2", "route-3", "route-4", "route-5"],
         "doc": "the flight routes that the airline serves"},
        {"name": "h", "members": [1, 2, 3, 4, 5],
         "doc": "the discrete demand states, indexing the possible passenger demand scenarios that can occur on a route"},
    ],
    "params": [
        {"name": "dd", "index": "j,h", "kind": "demand",
         "doc": "the passenger demand on a route under each demand state, in number of passengers"},
        {"name": "lambda_", "index": "j,h", "kind": "probability",
         "doc": "the probability that a given demand state occurs on a route; for each route the probabilities over the demand states sum to one"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the cost of operating one aircraft of a given type on a given route, in thousands of dollars"},
        {"name": "p", "index": "i,j", "kind": "capacity",
         "doc": "the passenger seating capacity that one aircraft of a given type provides on a given route, in number of passengers"},
        {"name": "aa", "index": "i", "kind": "availability",
         "doc": "the number of aircraft of each type that are available to assign"},
        {"name": "k", "index": "j", "kind": "penalty",
         "doc": "the revenue lost per bumped passenger on a route, in thousands of dollars per one hundred passengers bumped"},
        {"name": "ed", "index": "j", "kind": "expected demand",
         "doc": "the expected passenger demand on a route, computed as the probability-weighted average of the demand across the demand states"},
        {"name": "deltb", "index": "j,h", "kind": "incremental load",
         "doc": "the incremental passenger load that becomes carryable when reaching a demand state on a route, that is the additional passengers between this demand state and the previous one"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the number of aircraft of each type assigned to each route"},
        {"name": "y", "index": "j,h", "domain": "NonNegativeReals",
         "doc": "the number of passengers actually carried on a route in each demand state"},
        {"name": "b", "index": "j,h", "domain": "NonNegativeReals",
         "doc": "the number of passengers bumped on a route in each demand state, meaning those who demanded travel but were not carried"},
        {"name": "oc", "index": "", "domain": "NonNegativeReals",
         "doc": "the total operating cost of the aircraft assignment, in thousands of dollars"},
        {"name": "bc", "index": "", "domain": "NonNegativeReals",
         "doc": "the total expected bumping cost from passengers who could not be carried, in thousands of dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "oc + bc"},
}

NARRATIVE = (
    "We run an airline that has several types of aircraft and a set of routes to serve. "
    "We decide how many aircraft of each type to assign to each route, and given those "
    "assignments we determine how many passengers are actually carried and how many end up "
    "bumped on each route under each possible demand scenario. Operating the aircraft costs "
    "money, and bumping passengers who wanted to travel costs us lost revenue. The goal is to "
    "choose the assignments and resulting passenger flows so that the total operating cost plus "
    "the total expected bumping cost is as small as possible."
)

AB = (
    "def ab_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.j) <= model.aa[i]\n"
    "model.ab = Constraint(model.i, rule=ab_rule)"
)
YD = (
    "def yd_rule(model, j, h):\n"
    "    return model.y[j, h] <= sum(model.p[i, j] * model.x[i, j] for i in model.i)\n"
    "model.yd = Constraint(model.j, model.h, rule=yd_rule)"
)
BD = (
    "def bd_rule(model, j, h):\n"
    "    return model.b[j, h] == model.dd[j, h] - model.y[j, h]\n"
    "model.bd = Constraint(model.j, model.h, rule=bd_rule)"
)
OCD = (
    "def ocd_rule(model):\n"
    "    return model.oc == sum(model.c[i, j] * model.x[i, j] for i in model.i for j in model.j)\n"
    "model.ocd = Constraint(rule=ocd_rule)"
)
BCD2 = (
    "def bcd2_rule(model):\n"
    "    return model.bc == sum(model.k[j] * model.lambda_[j, h] * model.b[j, h] for j in model.j for h in model.h)\n"
    "model.bcd2 = Constraint(rule=bcd2_rule)"
)
YUP = (
    "def yup_rule(model, j, h):\n"
    "    return model.y[j, h] <= model.deltb[j, h]\n"
    "model.yup = Constraint(model.j, model.h, rule=yup_rule)"
)
WHOLESET = "\n".join([AB, YD, BD, OCD, BCD2, YUP])

records = [
    {"description": (
        "The number of aircraft we put into service is limited by how many we own. For each "
        "aircraft type, the total number of that type assigned across all the routes cannot "
        "exceed the number of that type that we have available."),
     "expected_pyomo": AB},
    {"description": (
        "We can only carry as many passengers as the assigned planes have seats for. For each "
        "route and each demand scenario, the passengers actually carried on that route cannot "
        "exceed the total seating capacity provided by all the aircraft assigned to that route."),
     "expected_pyomo": YD},
    {"description": (
        "Anyone who wanted to travel but was not carried counts as bumped. For each route and "
        "each demand scenario, the bumped passengers equal that scenario's demand on the route "
        "minus the passengers actually carried."),
     "expected_pyomo": BD},
    {"description": (
        "The total operating cost comes from flying the assigned aircraft. Set the operating "
        "cost equal to the sum over every aircraft type and route of the per-aircraft operating "
        "cost times the number of aircraft of that type assigned to that route."),
     "expected_pyomo": OCD},
    {"description": (
        "The total expected bumping cost reflects the lost revenue from bumped passengers, "
        "weighted by how likely each scenario is. Set the bumping cost equal to the sum over "
        "every route and demand scenario of the route's per-passenger bumping penalty times the "
        "probability of that scenario times the passengers bumped on that route in that scenario."),
     "expected_pyomo": BCD2},
    {"description": (
        "The passengers carried on a route should not run ahead of the demand that has actually "
        "materialized. For each route and each demand scenario, the passengers carried cannot "
        "exceed the incremental passenger load associated with that demand state on that route."),
     "expected_pyomo": YUP},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "aircraft_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
