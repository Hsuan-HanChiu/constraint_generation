#!/usr/bin/env python
"""Builder for the cta_mip (Controlled Tabular Adjustment) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "cta_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["r1", "r2", "r3", "r4", "r5", "total"],
         "doc": "the row categories of the statistical table; the special member 'total' is the row that holds the marginal sum down each column rather than an ordinary data row"},
        {"name": "j", "members": ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "total"],
         "doc": "the column categories of the statistical table; the special member 'total' is the column that holds the marginal sum across each row rather than an ordinary data column"},
        {"name": "k", "members": ["p1", "p2", "p3", "total"],
         "doc": "the planes (sub-tables) of the statistical table; the special member 'total' is the plane that holds the marginal sum over the individual planes rather than an ordinary data plane"},
        {"name": "v", "members": "the (row, column, plane) triples whose original table value is non-zero",
         "doc": "the set of occupied cells of the table, given as (row, column, plane) triples; a cell belongs to this set exactly when its original published value is non-zero, and only these cells are tracked and adjusted"},
        {"name": "s", "members": "the (row, column, plane) triples that are confidential",
         "doc": "the set of sensitive cells, given as (row, column, plane) triples; these are the confidential cells that must be perturbed away from their original value by at least a required protection amount, and they are a subset of the occupied cells"},
    ],
    "params": [
        {"name": "dat", "index": "k,i,j", "kind": "value",
         "doc": "the original published value of each cell, indexed in plane-row-column order; note the index order is plane first, then row, then column"},
        {"name": "pro", "index": "k,i,j", "kind": "protection",
         "doc": "the required protection amount for each sensitive cell, indexed in plane-row-column order; this is the minimum distance by which a sensitive cell's value must be moved away from its original value, and it is positive only on sensitive cells"},
        {"name": "BigM", "index": "", "kind": "big-M",
         "doc": "a large multiplier constant used to switch off the upper bound on whichever adjustment direction is not selected for a sensitive cell; a scalar"},
    ],
    "vars": [
        {"name": "t", "index": "i,j,k", "domain": "Reals",
         "doc": "the adjusted value of each cell after perturbation, indexed in row-column-plane order"},
        {"name": "adjN", "index": "i,j,k", "domain": "NonNegativeReals",
         "doc": "the downward adjustment applied to each cell, that is the amount by which the adjusted value falls below the original value, indexed in row-column-plane order"},
        {"name": "adjP", "index": "i,j,k", "domain": "NonNegativeReals",
         "doc": "the upward adjustment applied to each cell, that is the amount by which the adjusted value rises above the original value, indexed in row-column-plane order"},
        {"name": "b", "index": "i,j,k", "domain": "Binary",
         "doc": "the direction indicator for a sensitive cell, equal to 1 when the cell is pushed upward and 0 when it is pushed downward, indexed in row-column-plane order"},
        {"name": "obj", "index": "", "domain": "Reals",
         "doc": "the total adjustment across all occupied cells, in the same units as the cell values"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We publish a multi-way statistical table whose cells include some confidential entries that "
    "cannot be released at their true values. For every occupied cell we decide an adjusted value to "
    "publish in place of the original, splitting the change into an upward part and a downward part, "
    "and for each confidential cell we decide which direction to move it. The published table must "
    "still read as a consistent table, and each confidential cell must be moved far enough to hide its "
    "true value. The objective is to make the total amount of adjustment across all occupied cells as "
    "small as possible."
)

DEFADJ = (
    "def defadj_rule(model, i, j, k):\n"
    "    return model.t[i, j, k] == model.dat[k, i, j] + model.adjP[i, j, k] - model.adjN[i, j, k]\n"
    "model.defadj = Constraint(model.v, rule=defadj_rule)"
)
ADDROW = (
    "def addrow_rule(model, i, k):\n"
    "    return sum(model.t[ip, j, kp] for (ip, j, kp) in model.v if ip == i and kp == k) == 2 * model.t[i, 'total', k]\n"
    "model.addrow = Constraint(model.i, model.k, rule=addrow_rule)"
)
ADDCOL = (
    "def addcol_rule(model, j, k):\n"
    "    return sum(model.t[i, jp, kp] for (i, jp, kp) in model.v if jp == j and kp == k) == 2 * model.t['total', j, k]\n"
    "model.addcol = Constraint(model.j, model.k, rule=addcol_rule)"
)
ADDPLA = (
    "def addpla_rule(model, i, j):\n"
    "    return sum(model.t[ip, jp, k] for (ip, jp, k) in model.v if ip == i and jp == j) == 2 * model.t[i, j, 'total']\n"
    "model.addpla = Constraint(model.i, model.j, rule=addpla_rule)"
)
PMIN = (
    "def pmin_rule(model, i, j, k):\n"
    "    return model.adjN[i, j, k] >= model.pro[k, i, j] * (1 - model.b[i, j, k])\n"
    "model.pmin = Constraint(model.s, rule=pmin_rule)"
)
PMAX = (
    "def pmax_rule(model, i, j, k):\n"
    "    return model.adjP[i, j, k] >= model.pro[k, i, j] * model.b[i, j, k]\n"
    "model.pmax = Constraint(model.s, rule=pmax_rule)"
)
PMINX = (
    "def pminx_rule(model, i, j, k):\n"
    "    return model.adjN[i, j, k] <= model.BigM * model.pro[k, i, j] * (1 - model.b[i, j, k])\n"
    "model.pminx = Constraint(model.s, rule=pminx_rule)"
)
PMAXX = (
    "def pmaxx_rule(model, i, j, k):\n"
    "    return model.adjP[i, j, k] <= model.BigM * model.pro[k, i, j] * model.b[i, j, k]\n"
    "model.pmaxx = Constraint(model.s, rule=pmaxx_rule)"
)
DEFOBJ = (
    "def defobj_rule(model):\n"
    "    return model.obj == sum(model.adjN[i, j, k] + model.adjP[i, j, k] for (i, j, k) in model.v)\n"
    "model.defobj = Constraint(rule=defobj_rule)"
)
WHOLESET = "\n".join([DEFADJ, ADDROW, ADDCOL, ADDPLA, PMIN, PMAX, PMINX, PMAXX, DEFOBJ])

records = [
    {"description": (
        "For each occupied cell, the value that gets published is its original value moved by the chosen "
        "adjustment. Set the adjusted value of the cell equal to its original value plus the upward "
        "adjustment and minus the downward adjustment."),
     "expected_pyomo": DEFADJ},
    {"description": (
        "The published table must stay internally consistent along its rows, so within each plane the row "
        "marginal must remain the true sum of the entries in that row. For each row and each plane, the "
        "adjusted values of the occupied cells lying in that row of that plane, including the row's own "
        "marginal entry, must add up to twice the adjusted marginal entry for that row and plane."),
     "expected_pyomo": ADDROW},
    {"description": (
        "The published table must stay internally consistent along its columns, so within each plane the "
        "column marginal must remain the true sum of the entries in that column. For each column and each "
        "plane, the adjusted values of the occupied cells lying in that column of that plane, including the "
        "column's own marginal entry, must add up to twice the adjusted marginal entry for that column and "
        "plane."),
     "expected_pyomo": ADDCOL},
    {"description": (
        "The published table must stay internally consistent across its planes, so for each cell position "
        "the marginal over the planes must remain the true sum over the individual planes. For each row and "
        "column position, the adjusted values of the occupied cells at that position across the planes, "
        "including the position's own marginal plane entry, must add up to twice the adjusted marginal "
        "entry for that position."),
     "expected_pyomo": ADDPLA},
    {"description": (
        "Every sensitive cell that is chosen to be pushed downward must be moved down by at least its "
        "required protection amount. For each sensitive cell, when the downward direction is selected the "
        "downward adjustment must be at least the protection amount, and when the upward direction is "
        "selected this lower bound falls away."),
     "expected_pyomo": PMIN},
    {"description": (
        "Every sensitive cell that is chosen to be pushed upward must be moved up by at least its required "
        "protection amount. For each sensitive cell, when the upward direction is selected the upward "
        "adjustment must be at least the protection amount, and when the downward direction is selected "
        "this lower bound falls away."),
     "expected_pyomo": PMAX},
    {"description": (
        "A sensitive cell may only be moved downward when the downward direction has actually been "
        "selected for it. For each sensitive cell, the downward adjustment is held at zero unless the "
        "downward direction is chosen, and when it is chosen the downward adjustment is allowed up to a "
        "large multiple of the protection amount."),
     "expected_pyomo": PMINX},
    {"description": (
        "A sensitive cell may only be moved upward when the upward direction has actually been selected "
        "for it. For each sensitive cell, the upward adjustment is held at zero unless the upward direction "
        "is chosen, and when it is chosen the upward adjustment is allowed up to a large multiple of the "
        "protection amount."),
     "expected_pyomo": PMAXX},
    {"description": (
        "The total adjustment that the objective tracks is the sum, over every occupied cell, of how much "
        "that cell was moved up together with how much it was moved down. Set the total adjustment equal to "
        "this sum over all occupied cells."),
     "expected_pyomo": DEFOBJ},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "cta_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
