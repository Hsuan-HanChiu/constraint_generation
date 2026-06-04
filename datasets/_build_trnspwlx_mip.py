#!/usr/bin/env python
"""Builder for the trnspwlx_mip (transportation with piecewise-linear sqrt cost) constraint-generation dataset.

This is a MIP transportation model whose objective uses a concave square-root cost of
shipped volume. The square root is approximated by a piecewise-linear function over a
fixed breakpoint grid, encoded with per-segment continuous fill variables and per-segment
binary activation variables. Every constraint in the corpus model is LINEAR (degree 1):
the "sqrt" is realized entirely by the piecewise-linear segment encoding, not by a genuine
nonlinear term, so all constraints are Z3-gradable. No constraint is excluded.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "trnspwlx_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["seattle", "san-diego"],
         "doc": "the supply plants that ship goods"},
        {"name": "j", "members": ["new-york", "chicago", "topeka"],
         "doc": "the demand markets that receive goods"},
        {"name": "s", "members": ["s0", "s1", "s2", "s3", "s4", "s5", "s6"],
         "doc": "the segments of the piecewise-linear curve that approximates the square-root cost, listed from the lowest volume range to the highest; the first segment s0 is the unbounded anchor segment below the first breakpoint and the last segment s6 is the unbounded tail segment above the last breakpoint"},
        {"name": "sl", "members": ["x", "y", "l", "g"],
         "doc": "the four data fields stored for each piecewise-linear segment: x is the segment's starting volume breakpoint, y is the square-root curve value at that breakpoint, l is the horizontal length (width) of the segment, and g is the slope of the curve over the segment"},
        {"name": "ij", "members": [["seattle", "new-york"], ["seattle", "chicago"], ["seattle", "topeka"], ["san-diego", "new-york"], ["san-diego", "chicago"], ["san-diego", "topeka"]],
         "doc": "the set of valid plant-to-market shipping routes, one ordered pair per allowable route; here every plant can ship to every market so it is the full product of plants and markets"},
    ],
    "params": [
        {"name": "a", "index": "i", "kind": "capacity",
         "doc": "the supply capacity available at each plant, in cases; total shipments out of a plant may not exceed this"},
        {"name": "b", "index": "j", "kind": "demand",
         "doc": "the demand requirement at each market, in cases; total shipments into a market must meet at least this"},
        {"name": "d", "index": "i,j", "kind": "distance",
         "doc": "the distance from a plant to a market, in thousands of miles"},
        {"name": "f", "index": "", "kind": "freight",
         "doc": "the freight rate, in dollars per case per thousand miles; a single scalar"},
        {"name": "c", "index": "i,j", "kind": "cost",
         "doc": "the per-case transport cost on a route, in thousands of dollars per case, computed as the freight rate times the route distance divided by one thousand"},
        {"name": "sqrtp", "index": "s,sl", "kind": "curve-data",
         "doc": "the piecewise-linear curve data table indexed by segment and field; sqrtp[s,'x'] is the starting volume breakpoint of segment s, sqrtp[s,'y'] is the curve height at that breakpoint, sqrtp[s,'l'] is the width of segment s, and sqrtp[s,'g'] is the slope over segment s. The anchor segment s0 carries a sentinel width of -1 and the tail segment s6 a sentinel width of 1; only segments with a width strictly between 0 and 1000 are genuine bounded segments"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the quantity shipped on each route, in cases"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total transportation cost over all routes, in thousands of dollars"},
        {"name": "delta", "index": "i,j,s", "domain": "NonNegativeReals",
         "doc": "the amount of a route's shipped volume that falls within a given segment of the piecewise-linear curve, in cases; the fill of segment s for that route measured from the segment's starting breakpoint"},
        {"name": "y_seg", "index": "i,j,s", "domain": "Binary",
         "doc": "the segment-activation indicator for a route; equals 1 if that segment of the piecewise-linear curve is the active one for the route and 0 otherwise"},
        {"name": "sqrtx", "index": "i,j", "domain": "NonNegativeReals",
         "doc": "the piecewise-linear approximation of the square root of the route's shipped volume"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We ship a single commodity from a set of supply plants to a set of demand markets over "
    "a fixed set of allowable routes. For each route we decide how many cases to ship. The "
    "cost of a route grows with the square root of the volume shipped on it, a concave "
    "shipping economy that is approximated by a piecewise-linear curve built from continuous "
    "per-segment fill amounts and binary per-segment activation choices. The objective is to "
    "minimize the total transportation cost across all routes."
)

SUPPLY = (
    "def supply_rule(model, i):\n"
    "    return sum(model.x[i, j] for (ii, j) in model.ij if ii == i) <= model.a[i]\n"
    "model.supply = Constraint(model.i, rule=supply_rule)"
)
DEMAND = (
    "def demand_rule(model, j):\n"
    "    return sum(model.x[i, j] for (i, jj) in model.ij if jj == j) >= model.b[j]\n"
    "model.demand = Constraint(model.j, rule=demand_rule)"
)
DEFX = (
    "def defx_rule(model, i, j):\n"
    "    return model.x[i, j] == sum(\n"
    "        model.sqrtp[s, 'x'] * model.y_seg[i, j, s] + model.delta[i, j, s]\n"
    "        for s in model.s)\n"
    "model.defx = Constraint(model.ij, rule=defx_rule)"
)
DEFSQRTX = (
    "def defsqrtx_rule(model, i, j):\n"
    "    return model.sqrtx[i, j] == sum(\n"
    "        model.sqrtp[s, 'y'] * model.y_seg[i, j, s] + model.sqrtp[s, 'g'] * model.delta[i, j, s]\n"
    "        for s in model.s)\n"
    "model.defsqrtx = Constraint(model.ij, rule=defsqrtx_rule)"
)
LIMIT_DELTA = (
    "def limit_delta_rule(model, i, j, s):\n"
    "    L = value(model.sqrtp[s, 'l'])\n"
    "    if L < 0 or L > 1000:\n"
    "        return Constraint.Skip\n"
    "    return model.delta[i, j, s] <= model.sqrtp[s, 'l'] * model.y_seg[i, j, s]\n"
    "model.limit_delta = Constraint(model.ij, model.s, rule=limit_delta_rule)"
)
ONE_SEGMENT = (
    "def one_segment_rule(model, i, j):\n"
    "    return sum(model.y_seg[i, j, s] for s in model.s) <= 1\n"
    "model.one_segment = Constraint(model.ij, rule=one_segment_rule)"
)
DEFOBJDISC = (
    "def defobjdisc_rule(model):\n"
    "    return model.z == sum(model.c[i, j] * model.sqrtx[i, j] for (i, j) in model.ij)\n"
    "model.defobjdisc = Constraint(rule=defobjdisc_rule)"
)
WHOLESET = "\n".join([SUPPLY, DEMAND, DEFX, DEFSQRTX, LIMIT_DELTA, ONE_SEGMENT, DEFOBJDISC])

records = [
    {"description": (
        "Each plant can ship out only as much as it has available. For every plant, the total "
        "shipped to all markets it serves must not exceed that plant's supply capacity."),
     "expected_pyomo": SUPPLY},
    {"description": (
        "Every market's requirement must be covered. For each market, the total received from "
        "all plants that serve it must be at least that market's demand."),
     "expected_pyomo": DEMAND},
    {"description": (
        "The volume shipped on a route is reconstructed from the piecewise-linear segment "
        "encoding. For each route, the shipped volume equals the sum over all segments of the "
        "segment's starting breakpoint counted when that segment is the active one, plus the "
        "fill amount placed in each segment."),
     "expected_pyomo": DEFX},
    {"description": (
        "The approximate square root of a route's volume is read off the piecewise-linear curve. "
        "For each route, the approximated square root equals the sum over all segments of the "
        "curve height at the segment's starting breakpoint counted when that segment is active, "
        "plus the segment slope multiplied by the fill placed in that segment."),
     "expected_pyomo": DEFSQRTX},
    {"description": (
        "The fill placed in a segment cannot exceed the room that segment offers, and a segment "
        "can only be filled when it is the active one. For each route and each genuine bounded "
        "segment, the fill amount must not exceed the segment's width, and it is forced to zero "
        "unless that segment is activated. The unbounded anchor and tail segments are not "
        "restricted this way."),
     "expected_pyomo": LIMIT_DELTA},
    {"description": (
        "Each route may rest on at most one segment of the curve. For every route, the total "
        "number of activated segments must be at most one."),
     "expected_pyomo": ONE_SEGMENT},
    {"description": (
        "The total transportation cost ties together the per-route costs and the approximated "
        "square-root volumes. Set the total cost equal to the sum over all routes of the route's "
        "per-case transport cost multiplied by the approximated square root of its shipped volume."),
     "expected_pyomo": DEFOBJDISC},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "trnspwlx_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
