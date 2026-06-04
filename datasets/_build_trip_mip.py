#!/usr/bin/env python
"""Builder for the trip_mip (platoon routing on a time-expanded traffic network)
constraint-generation dataset.

trip_mip is a MIP that is FLAGGED nonlinear: the per-link congestion-cost param
`c` is computed at build time with a `( ... )**0.25` power, but that power touches
only a PARAMETER (computed once, baked to a number), so every CONSTRAINT body is
linear (degree 1). All four structural constraints are kept.

EXCLUDED: `flow_conservation_const`. Its right-hand side is a random draw,
`np.random.normal(nu[x,d,tau_x], ...)`, evaluated to a concrete float at build
time. That value is not a clean algebraic function of the data (it depends on the
numpy call order and is not reproducible cell-by-cell from a description), so the
constraint is neither symbolically describable nor logically gradable for
equivalence. It is dropped and noted.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "trip_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "N", "members": [1, 2, 3, 4],
         "doc": "the nodes of the traffic network, indexed by integers"},
        {"name": "A", "members": [[1, 2], [1, 3], [2, 1], [2, 4], [3, 1], [3, 4], [4, 2], [4, 3]],
         "doc": "the directed physical links of the network, each an ordered pair of an origin node and a destination node"},
        {"name": "S", "members": [0, 1, 2, 3, 4, 5],
         "doc": "the discrete time periods of the planning horizon in chronological order; the last member is the final period (the horizon end)"},
        {"name": "cal_A", "members": "the time-expanded links",
         "doc": "the set of time-expanded links; each member is a four-tuple giving an origin node, a departure period, a destination node, and an arrival period, where the origin and destination form a physical link and the departure period is earlier than the arrival period; the gap between departure and arrival is the travel time chosen for that crossing"},
    ],
    "params": [
        {"name": "M", "index": "", "kind": "big-M",
         "doc": "a single large constant used to switch link inequalities on or off depending on whether a time-expanded link is selected; a scalar with value 5000"},
        {"name": "c", "index": "cal_A", "kind": "capacity",
         "doc": "the carrying capacity of each time-expanded link, in vehicles; a number computed for each origin, departure period, destination, and arrival period that reflects how much flow that particular crossing duration can hold"},
        {"name": "beta", "index": "N,N", "kind": "penalty",
         "doc": "the trip-completion penalty for each origin and destination node pair"},
        {"name": "nu", "index": "N,N,S", "kind": "demand",
         "doc": "the travel demand entering the network at an origin node for a given destination node in a given period, in vehicles"},
    ],
    "vars": [
        {"name": "delta", "index": "cal_A", "domain": "Binary",
         "doc": "selection indicator for a time-expanded link; equals 1 if that crossing (a given origin, departure period, destination, and arrival period) is used and 0 otherwise"},
        {"name": "f_d", "index": "cal_A,N", "domain": "NonNegativeReals",
         "doc": "the traffic volume routed on a time-expanded link that is bound for a particular final destination node; indexed by the origin, departure period, destination, and arrival period of the crossing together with the destination node the flow is headed to, in vehicles"},
    ],
    "objective": {"sense": "minimize", "expr_var": "total_cost"},
}

NARRATIVE = (
    "We route vehicle platoons across a city traffic network over a sequence of time "
    "periods. The network is expanded in time so that crossing a physical link means "
    "choosing both the link and how long the crossing takes, which fixes the departure "
    "period and the arrival period. For each such time-expanded crossing we decide "
    "whether to use it at all, and how much traffic headed to each final destination to "
    "send along it. The objective is to minimize the total travel effort across all "
    "crossings plus the trip-completion penalties incurred by flows that finish their "
    "journeys at the horizon end."
)

NO_DISP1 = (
    "def no_dispersion_const_1_rule(model, x, tau_x, y, tau_y):\n"
    "    M = 5000\n"
    "    return sum(model.f_d[x, tau_x, y, tau_y, d] for d in model.N) <= M * model.delta[x, tau_x, y, tau_y]\n"
    "model.no_dispersion_const_1 = Constraint(model.cal_A, rule=no_dispersion_const_1_rule)"
)

NO_DISP2 = (
    "def no_dispersion_const_2_rule(model, x, y, tau_x):\n"
    "    h = max(model.S)\n"
    "    if tau_x < h and (x, y) in model.A:\n"
    "        return sum(model.delta[x, tau_x, y, tau_x + s] for s in pyo.RangeSet(1, h - tau_x, 1)) <= 1\n"
    "    else:\n"
    "        return Constraint.Skip\n"
    "model.no_dispersion_const_2 = Constraint(model.N, model.N, model.S, rule=no_dispersion_const_2_rule)"
)

LINK_CONS = (
    "def link_consistency_const_rule(model, x, y, tau_x, tau_w):\n"
    "    M = 5000\n"
    "    h = max(model.S)\n"
    "    if tau_x < tau_w and tau_w < h and (x, y) in model.A:\n"
    "        expr_left = tau_x + sum(s * model.delta[x, tau_x, y, tau_x + s] for s in pyo.RangeSet(1, h - tau_x, 1))\n"
    "        expr_right = tau_w + sum(s * model.delta[x, tau_w, y, tau_w + s] for s in pyo.RangeSet(1, h - tau_w, 1)) \\\n"
    "            + M * (1 - sum(model.delta[x, tau_w, y, tau_w + s] for s in pyo.RangeSet(1, h - tau_w, 1)))\n"
    "        return expr_left <= expr_right\n"
    "    else:\n"
    "        return Constraint.Skip\n"
    "model.link_consistency_const = Constraint(model.N, model.N, model.S, model.S, rule=link_consistency_const_rule)"
)

CAPACITY = (
    "def capacity_const_rule(model, x, y, tau_x):\n"
    "    M = 5000\n"
    "    h = max(model.S)\n"
    "    if tau_x < h and (x, y) in model.A:\n"
    "        expr_left = sum(sum(sum(model.f_d[x, tau_x - s1, y, tau_x + s2, d] for d in model.N) for s2 in pyo.RangeSet(1, h - tau_x, 1)) for s1 in pyo.RangeSet(0, tau_x, 1))\n"
    "        expr_right = sum(model.delta[x, tau_x, y, tau_x + s] * model.c[x, tau_x, y, tau_x + s] for s in pyo.RangeSet(1, h - tau_x, 1)) \\\n"
    "            + M * (1 - sum(model.delta[x, tau_x, y, tau_x + s] for s in pyo.RangeSet(1, h - tau_x, 1)))\n"
    "        return expr_left <= expr_right\n"
    "    else:\n"
    "        return Constraint.Skip\n"
    "model.capacity_const = Constraint(model.N, model.N, model.S, rule=capacity_const_rule)"
)

WHOLESET = "\n".join([NO_DISP1, NO_DISP2, LINK_CONS, CAPACITY])

records = [
    {"description": (
        "Traffic can only travel on a crossing that has actually been selected, and a "
        "selected crossing can carry only a limited amount of traffic. For each "
        "time-expanded crossing, the total traffic sent along it across all final "
        "destinations must stay within a large allowance when the crossing is used, and "
        "must drop to nothing when the crossing is not used."),
     "expected_pyomo": NO_DISP1},
    {"description": (
        "Once vehicles leave a node along a physical link in a given period, they cannot "
        "spread out into more than one crossing of that link. For each origin node, each "
        "neighboring node it links to, and each period before the horizon end, at most "
        "one crossing of that link starting in that period may be selected across all "
        "possible arrival times."),
     "expected_pyomo": NO_DISP2},
    {"description": (
        "Vehicles that enter a link earlier must not arrive later than vehicles that "
        "enter the same link afterward, so crossings of one link keep their order in "
        "time. For each origin node, each neighboring node it links to, and each pair of "
        "departure periods where the first is earlier than the second and the second is "
        "before the horizon end, the arrival period of the earlier departure must be no "
        "later than the arrival period of the later departure. This ordering is enforced "
        "only when the later departure actually has a selected crossing, and is otherwise "
        "relaxed so it does not bind."),
     "expected_pyomo": LINK_CONS},
    {"description": (
        "The traffic occupying a link at a given moment cannot exceed the capacity of the "
        "crossing being used. For each origin node, each neighboring node it links to, and "
        "each period before the horizon end, add up all traffic that is in transit on that "
        "link at that period, counting flows that departed in that period or earlier and "
        "arrive in that period or later, across all final destinations. This total must not "
        "exceed the capacity of the selected crossing that starts in that period, with a "
        "large allowance added when no such crossing is selected so the limit does not bind."),
     "expected_pyomo": CAPACITY},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "trip_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
