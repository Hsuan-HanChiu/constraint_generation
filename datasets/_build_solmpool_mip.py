#!/usr/bin/env python
"""Builder for the solmpool_mip (warehouse facility-location MIP) constraint-generation dataset.

All six constraints are linear (polynomial_degree == 1); none are bilinear or
otherwise nonlinear, so every constraint is included.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "solmpool_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["w1", "w2", "w3", "w4"],
         "doc": "the set of candidate warehouses that may be opened"},
        {"name": "j", "members": ["r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9"],
         "doc": "the set of demand regions that must each be served"},
    ],
    "params": [
        {"name": "f", "index": "i", "kind": "cost",
         "doc": "the fixed cost incurred to open each warehouse, in cost units"},
        {"name": "c", "index": "i", "kind": "capacity",
         "doc": "the capacity of each warehouse, expressed in the same units as region demand"},
        {"name": "d", "index": "j", "kind": "demand",
         "doc": "the demand of each region, expressed in the same units as warehouse capacity"},
        {"name": "t", "index": "j,i", "kind": "cost",
         "doc": "the transportation cost of serving a region from a warehouse, in cost units; indexed by region first and warehouse second"},
    ],
    "vars": [
        {"name": "totcost", "index": "", "domain": "Reals",
         "doc": "the total cost of the chosen plan, in cost units"},
        {"name": "fcost", "index": "", "domain": "Reals",
         "doc": "the total fixed cost of opening warehouses, in cost units"},
        {"name": "tcost", "index": "", "domain": "Reals",
         "doc": "the total transportation cost of serving regions, in cost units"},
        {"name": "ow", "index": "i", "domain": "Binary",
         "doc": "warehouse-open indicator; equals 1 if the warehouse is opened and 0 otherwise"},
        {"name": "oa", "index": "i,j", "domain": "Binary",
         "doc": "shipment-arc indicator; equals 1 if the region is served from the warehouse and 0 otherwise"},
    ],
    "objective": {"sense": "minimize", "expr_var": "totcost"},
}

NARRATIVE = (
    "We plan a network of warehouses that serve a number of demand regions. We decide which "
    "warehouses to open and, for each region, which open warehouse will serve it. Opening a "
    "warehouse incurs a fixed cost, and serving a region from a warehouse incurs a transportation "
    "cost. We also track the resulting total fixed cost, total transportation cost, and overall "
    "total cost. The objective is to minimize the overall total cost."
)

DEFTOTCOST = (
    "model.deftotcost = Constraint(expr=model.totcost == model.fcost + model.tcost)"
)
DEFFCOST = (
    "model.deffcost = Constraint(expr=model.fcost == sum(model.f[i] * model.ow[i] for i in model.i))"
)
DEFTCOST = (
    "model.deftcost = Constraint(expr=model.tcost == "
    "sum(model.t[j, i] * model.oa[i, j] for i in model.i for j in model.j))"
)
DEFWCAP = (
    "def defwcap_rule(m, i):\n"
    "    return sum(m.d[j] * m.oa[i, j] for j in m.j) <= m.c[i]\n"
    "model.defwcap = Constraint(model.i, rule=defwcap_rule)"
)
ONEW = (
    "def onew_rule(m, j):\n"
    "    return sum(m.oa[i, j] for i in m.i) == 1\n"
    "model.onew = Constraint(model.j, rule=onew_rule)"
)
DEFOW = (
    "def defow_rule(m, i, j):\n"
    "    return m.ow[i] >= m.oa[i, j]\n"
    "model.defow = Constraint(model.i, model.j, rule=defow_rule)"
)

D_TOTCOST = (
    "The total cost must equal the fixed cost of the warehouses opened plus the transportation cost "
    "of serving the regions.")
D_FCOST = (
    "The total fixed cost must equal the sum, over all warehouses, of each warehouse's fixed opening "
    "cost counted only when that warehouse is opened.")
D_TCOST = (
    "The total transportation cost must equal the sum, over every region and warehouse pairing, of "
    "the cost of serving that region from that warehouse counted only when the region is actually "
    "served from it.")
D_WCAP = (
    "For each warehouse, the combined demand of all regions it serves cannot exceed that warehouse's "
    "capacity.")
D_ONEW = (
    "Each region must be served by exactly one warehouse.")
D_OW = (
    "A region can be served from a warehouse only if that warehouse is open, so whenever a region is "
    "served from a warehouse that warehouse must be open.")

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, the total cost must equal the fixed cost of the warehouses opened plus the transportation "
    "cost of serving the regions. "
    "Second, the total fixed cost must equal the sum over all warehouses of each warehouse's fixed "
    "opening cost counted only when that warehouse is opened. "
    "Third, the total transportation cost must equal the sum over every region and warehouse pairing "
    "of the cost of serving that region from that warehouse counted only when the region is actually "
    "served from it. "
    "Fourth, for each warehouse the combined demand of all regions it serves cannot exceed that "
    "warehouse's capacity. "
    "Fifth, each region must be served by exactly one warehouse. "
    "Finally, a region can be served from a warehouse only if that warehouse is open."
)
WHOLESET = "\n".join([DEFTOTCOST, DEFFCOST, DEFTCOST, DEFWCAP, ONEW, DEFOW])

records = [
    {"description": D_TOTCOST, "expected_pyomo": DEFTOTCOST},
    {"description": D_FCOST, "expected_pyomo": DEFFCOST},
    {"description": D_TCOST, "expected_pyomo": DEFTCOST},
    {"description": D_WCAP, "expected_pyomo": DEFWCAP},
    {"description": D_ONEW, "expected_pyomo": ONEW},
    {"description": D_OW, "expected_pyomo": DEFOW},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as fh:
    for r in records:
        fh.write(json.dumps({
            "problem_id": "solmpool_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
