#!/usr/bin/env python
"""Builder for the bidpwl_mip (piecewise-linear bid evaluation) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "bidpwl_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "v", "members": ["a", "b", "c", "d", "e"],
         "doc": "the set of vendors who have submitted bids"},
        {"name": "seg", "members": ["a|0", "a|1", "b|0", "b|1", "b|2", "b|3", "b|4", "c|0", "c|1", "d|0", "d|1", "e|0", "e|1", "e|2"],
         "doc": "the set of valid (vendor, segment) pairs; each vendor's cost is a piecewise-linear function of the units purchased, broken into consecutive segments, and this set lists exactly which segments exist for each vendor; segment 0 of every vendor is the 'no deal' segment with zero length representing buying nothing from that vendor"},
    ],
    "params": [
        {"name": "req", "index": "", "kind": "demand",
         "doc": "the total number of units that must be purchased across all vendors, a single scalar"},
        {"name": "px", "index": "seg", "kind": "breakpoint",
         "doc": "the start x-coordinate of each vendor-segment, that is the quantity at the beginning of the segment (its q-min), in units"},
        {"name": "py", "index": "seg", "kind": "breakpoint",
         "doc": "the start y-coordinate of each vendor-segment, that is the base cost already accumulated at the beginning of the segment, in dollars"},
        {"name": "pl", "index": "seg", "kind": "length",
         "doc": "the length of each vendor-segment, that is how many additional units can be bought while travelling within the segment (its q-max minus q-min), in units; the no-deal segment has length zero"},
        {"name": "pg", "index": "seg", "kind": "slope",
         "doc": "the slope of each vendor-segment, that is the marginal unit price charged for each additional unit bought while travelling within the segment, in dollars per unit"},
    ],
    "vars": [
        {"name": "cost", "index": "", "domain": "Reals",
         "doc": "the total purchase cost across all vendors, in dollars"},
        {"name": "x", "index": "v", "domain": "Reals",
         "doc": "the number of units purchased from each vendor"},
        {"name": "y", "index": "v", "domain": "Reals",
         "doc": "the cost of the units purchased from each vendor, in dollars"},
        {"name": "segx", "index": "seg", "domain": "NonNegativeReals",
         "doc": "the distance travelled into a vendor-segment measured from the segment's start point, in units; it is positive only for the segment chosen as active for that vendor"},
        {"name": "segb", "index": "seg", "domain": "Binary",
         "doc": "the segment-selection indicator; equals 1 if the segment is the active one chosen for its vendor and 0 otherwise"},
    ],
    "objective": {"sense": "minimize", "expr_var": "cost"},
}

NARRATIVE = (
    "We must purchase a required total number of units from a group of vendors, each of whom has "
    "submitted a bid in the form of a piecewise-linear cost function of the quantity bought, broken "
    "into consecutive segments. For each vendor we decide which single segment of its bid to operate "
    "on, how far into that chosen segment to travel, and from these the quantity bought and the cost "
    "incurred from that vendor. The objective is to minimize the total purchase cost across all "
    "vendors."
)

SEGCAP = (
    "def segcap_rule(model, v, s):\n"
    "    return model.segx[v, s] <= model.pl[v, s] * model.segb[v, s]\n"
    "model.segcap = Constraint(model.seg, rule=segcap_rule)"
)
ONESEG = (
    "def oneseg_rule(model, vv):\n"
    "    return sum(model.segb[v, s] for (v, s) in model.seg if v == vv) == 1\n"
    "model.oneseg = Constraint(model.v, rule=oneseg_rule)"
)
DEFX = (
    "def defx_rule(model, vv):\n"
    "    return model.x[vv] == sum(model.segb[v, s] * model.px[v, s] + model.segx[v, s]\n"
    "                              for (v, s) in model.seg if v == vv)\n"
    "model.defx = Constraint(model.v, rule=defx_rule)"
)
DEFY = (
    "def defy_rule(model, vv):\n"
    "    return model.y[vv] == sum(model.segb[v, s] * model.py[v, s] + model.segx[v, s] * model.pg[v, s]\n"
    "                              for (v, s) in model.seg if v == vv)\n"
    "model.defy = Constraint(model.v, rule=defy_rule)"
)
DEMAND = (
    "def demand_rule(model):\n"
    "    return model.req == sum(model.x[v] for v in model.v)\n"
    "model.demand = Constraint(rule=demand_rule)"
)
COSTDEF = (
    "def costdef_rule(model):\n"
    "    return model.cost == sum(model.y[v] for v in model.v)\n"
    "model.costdef = Constraint(rule=costdef_rule)"
)
WHOLESET = "\n".join([SEGCAP, ONESEG, DEFX, DEFY, DEMAND, COSTDEF])

DESC_SEGCAP = (
    "For every vendor-segment, the distance travelled into the segment cannot exceed the length of "
    "that segment, and it is allowed to be positive only when that segment is the one selected as "
    "active for its vendor. When a segment is not selected, no travel into it is permitted."
)
DESC_ONESEG = (
    "For each vendor, exactly one of that vendor's segments must be selected as the active one. "
    "Across all of a vendor's segments the selection indicators must add up to one."
)
DESC_DEFX = (
    "For each vendor, the number of units purchased is determined by which segment is active and "
    "how far into it we travel. It equals the start quantity of the selected segment plus the "
    "distance travelled into the active segment, summed over the vendor's segments."
)
DESC_DEFY = (
    "For each vendor, the cost of the units purchased is determined by which segment is active and "
    "how far into it we travel. It equals the base cost at the start of the selected segment plus "
    "the marginal unit price of the segment times the distance travelled into it, summed over the "
    "vendor's segments."
)
DESC_DEMAND = (
    "The total number of units purchased across all vendors must exactly meet the required amount."
)
DESC_COSTDEF = (
    "The total purchase cost is the sum of the costs of the units purchased from each vendor."
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for every vendor-segment the distance travelled into the segment cannot exceed its "
    "length and is allowed to be positive only when that segment is the one selected as active for "
    "its vendor. "
    "Second, for each vendor exactly one of that vendor's segments must be selected as the active one. "
    "Third, for each vendor the number of units purchased must equal the start quantity of the "
    "selected segment plus the distance travelled into the active segment. "
    "Fourth, for each vendor the cost of its units must equal the base cost at the start of the "
    "selected segment plus the marginal unit price of the segment times the distance travelled into it. "
    "Fifth, the total number of units purchased across all vendors must exactly meet the required amount. "
    "Finally, the total purchase cost must equal the sum of the costs of the units purchased from "
    "each vendor."
)

records = [
    {"description": DESC_SEGCAP, "expected_pyomo": SEGCAP},
    {"description": DESC_ONESEG, "expected_pyomo": ONESEG},
    {"description": DESC_DEFX, "expected_pyomo": DEFX},
    {"description": DESC_DEFY, "expected_pyomo": DEFY},
    {"description": DESC_DEMAND, "expected_pyomo": DEMAND},
    {"description": DESC_COSTDEF, "expected_pyomo": COSTDEF},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "bidpwl_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
