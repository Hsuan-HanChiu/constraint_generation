#!/usr/bin/env python
"""Builder for the railcirc_mip (railway rolling-stock circulation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "railcirc_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "tu", "members": ["tu1", "tu2"],
         "doc": "the types of train unit available, each a self-contained set of cars that can be coupled together"},
        {"name": "c", "members": ["First", "Second"],
         "doc": "the passenger service classes, namely first class and second class"},
        {"name": "s", "members": ["A", "B"],
         "doc": "the stations in the network"},
        {"name": "g", "members": "all timetable graph arcs",
         "doc": "the arcs of the timetable graph, each a quadruple (origin station, origin time, destination station, destination time); this set unites the in-service arcs, the in-station waiting arcs that connect consecutive events at one station, and the overnight arcs that return from a day's last event back to its first event"},
        {"name": "is_", "members": "the in-service arcs",
         "doc": "the in-service arcs, the subset of graph arcs on which trains actually carry passengers between two stations; each is a quadruple (origin station, origin time, destination station, destination time)"},
        {"name": "on", "members": "the overnight arcs",
         "doc": "the overnight arcs, the subset of graph arcs that carry stock from the last event of the day at a station back to that station's first event of the day; each is a quadruple (origin station, origin time, destination station, destination time)"},
        {"name": "ste", "members": "the station timetable events",
         "doc": "the station timetable events, each a pair (station, time) marking a moment at a station where stock can arrive or depart"},
    ],
    "params": [
        {"name": "seats", "index": "tu,c", "kind": "capacity",
         "doc": "the number of seats of a given service class provided by one unit of a given train-unit type"},
        {"name": "numcars", "index": "tu", "kind": "size",
         "doc": "the number of cars in one unit of each train-unit type"},
        {"name": "cost", "index": "tu", "kind": "cost",
         "doc": "the cost of keeping one unit of each train-unit type stabled overnight"},
        {"name": "demand_param", "index": "is_,c", "kind": "demand",
         "doc": "the number of seats of a given service class demanded by passengers on each in-service arc"},
        {"name": "maxcars", "index": "", "kind": "capacity",
         "doc": "the maximum number of cars permitted on a single in-service train, a scalar"},
    ],
    "vars": [
        {"name": "f", "index": "tu,g", "domain": "NonNegativeIntegers",
         "doc": "the number of units of each train-unit type routed along each graph arc; integer because train units are indivisible"},
        {"name": "obj_var", "index": "", "domain": "Reals",
         "doc": "the total overnight stabling cost, an accounting variable"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj_var"},
}

NARRATIVE = (
    "We plan how a fleet of train units circulates through a daily timetable on a rail network. "
    "For every type of train unit and every arc of the timetable graph we decide how many units of "
    "that type travel along that arc, where the arcs include the scheduled passenger services, the "
    "waiting moves that hold stock at a station between events, and the overnight returns that carry "
    "stock from the end of one day to the start of the next. Train units come in different types that "
    "differ in their seating per class, their number of cars, and their overnight stabling cost. The "
    "objective is to minimize the total cost of the train units left stabled overnight."
)

CIRCULATION = (
    "def circulation_rule(model, tu, s, t):\n"
    "    inflow = sum(model.f[tu, a] for a in model.g if a[3] == t and a[2] == s)\n"
    "    outflow = sum(model.f[tu, a] for a in model.g if a[1] == t and a[0] == s)\n"
    "    return inflow == outflow\n"
    "model.circulation = Constraint(model.tu, model.ste, rule=circulation_rule)"
)
DEMAND = (
    "def demand_rule(model, s, t, ss, tt, c):\n"
    "    return model.demand_param[s, t, ss, tt, c] <= sum(model.f[tu, s, t, ss, tt] * model.seats[tu, c] for tu in model.tu)\n"
    "model.demand = Constraint(model.is_, model.c, rule=demand_rule)"
)
DEFMAXCARS = (
    "def maxcars_rule(model, s, t, ss, tt):\n"
    "    return sum(model.f[tu, s, t, ss, tt] * model.numcars[tu] for tu in model.tu) <= model.maxcars\n"
    "model.defmaxcars = Constraint(model.is_, rule=maxcars_rule)"
)
DEFOBJ = (
    "def defobj_rule(model):\n"
    "    return model.obj_var == sum(model.f[tu, a] * model.cost[tu] for tu in model.tu for a in model.on)\n"
    "model.defobj = Constraint(rule=defobj_rule)"
)
WHOLESET = "\n".join([CIRCULATION, DEMAND, DEFMAXCARS, DEFOBJ])

records = [
    {"description": (
        "Train stock can neither appear nor vanish at any point in the timetable. For each type of train "
        "unit and at each station timetable event, the total number of units of that type arriving on all "
        "arcs that end at that event must equal the total number of units of that type leaving on all arcs "
        "that begin at that event."),
     "expected_pyomo": CIRCULATION},
    {"description": (
        "Every scheduled service must seat the passengers who want to travel on it. For each in-service arc "
        "and each service class, the seats of that class provided by the train units assigned to the arc, "
        "summed over all train-unit types, must be at least the demand for that class on that arc."),
     "expected_pyomo": DEMAND},
    {"description": (
        "No scheduled service may run a train longer than the track allows. For each in-service arc, the "
        "total number of cars contributed by the train units assigned to that arc, summed over all "
        "train-unit types, must not exceed the maximum number of cars permitted on a single train."),
     "expected_pyomo": DEFMAXCARS},
    {"description": (
        "The total stabling cost accounts for every unit left out overnight. Set the total overnight cost "
        "equal to the sum over all train-unit types and all overnight arcs of the number of units of that "
        "type on that arc times the overnight stabling cost of that type."),
     "expected_pyomo": DEFOBJ},
    {"description": (
        "To build the complete model, enforce the following relationships in order. "
        "First, at each station timetable event and for each train-unit type, balance the units arriving "
        "against the units leaving so that stock is conserved. "
        "Second, for each in-service arc and each service class, require the seats provided by the assigned "
        "train units to cover the passenger demand for that class. "
        "Third, for each in-service arc, keep the total cars of the assigned train units within the limit "
        "allowed on a single train. "
        "Finally, set the total overnight stabling cost equal to the cost of all train units left stabled "
        "on the overnight arcs."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "railcirc_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
