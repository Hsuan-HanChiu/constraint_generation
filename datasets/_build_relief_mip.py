#!/usr/bin/env python
"""Builder for the relief_mip (relief-drop plant-location) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "relief_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "r", "members": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
         "doc": "the grid rows, labelled A through J; together with the columns they index the cells of a square map"},
        {"name": "c", "members": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
         "doc": "the grid columns, numbered 1 through 10; together with the rows they index the cells of a square map"},
        {"name": "hut", "members": [["A", 5], ["B", 5], ["B", 9], ["B", 10], ["C", 1], ["C", 6], ["C", 8], ["C", 9], ["C", 10], ["D", 2], ["D", 7], ["D", 10], ["E", 2], ["E", 9], ["F", 8], ["G", 2], ["H", 2], ["H", 6], ["J", 8], ["J", 10]],
         "doc": "the village (hut) locations, each given as a (row, column) cell on the grid; these are the populations that must be served"},
    ],
    "params": [
        {"name": "dis", "index": "hut,r,c", "kind": "distance",
         "doc": "the Euclidean walking distance from each hut at its (row, column) cell to each candidate drop cell (row, column), in grid units"},
        {"name": "maxdem", "index": "", "kind": "capacity",
         "doc": "the maximum demand a single open drop can serve, expressed as a number of huts' worth of demand; a scalar large enough to act as the per-drop supply cap when a drop is open"},
        {"name": "numdrops", "index": "", "kind": "count",
         "doc": "the exact number of drop locations that must be opened across the whole grid; a scalar"},
    ],
    "vars": [
        {"name": "drop", "index": "r,c", "domain": "Binary",
         "doc": "the open-drop indicator for each grid cell; equals 1 if a relief drop is opened at that (row, column) cell and 0 otherwise"},
        {"name": "walk", "index": "hut,r,c", "domain": "NonNegativeReals",
         "doc": "the fraction of a hut's demand that is served by the drop at a given (row, column) cell; a number between 0 and 1 in any feasible solution"},
        {"name": "total", "index": "", "domain": "Reals",
         "doc": "the total distance walked, summed over all huts and the drops that serve them"},
    ],
    "objective": {"sense": "minimize", "expr_var": "total"},
}

NARRATIVE = (
    "We are planning a relief mission over a grid-shaped map dotted with villages. We must choose a "
    "fixed number of cells on the grid at which to open relief drops, and then decide what share of "
    "each village's demand is served from each open drop. Every village walks to the drops that serve "
    "it, and the distance from a village to a cell is known. The objective is to minimize the total "
    "distance walked by all villages to reach the drops that serve them."
)

DEMAND = (
    "def demand_rule(model, hr, hc):\n"
    "    return sum(model.walk[hr, hc, r, c] for r in model.r for c in model.c) == 1\n"
    "model.demand = Constraint(model.hut, rule=demand_rule)"
)
SUPPLY = (
    "def supply_rule(model, r, c):\n"
    "    return sum(model.walk[hr, hc, r, c] for (hr, hc) in model.hut) <= model.drop[r, c] * model.maxdem\n"
    "model.supply = Constraint(model.r, model.c, rule=supply_rule)"
)
DEFTOTAL = (
    "def deftotal_rule(model):\n"
    "    return model.total == sum(model.dis[hr, hc, r, c] * model.walk[hr, hc, r, c] for (hr, hc) in model.hut for r in model.r for c in model.c)\n"
    "model.deftotal = Constraint(rule=deftotal_rule)"
)
DEFNUMDROP = (
    "def defnumdrop_rule(model):\n"
    "    return sum(model.drop[r, c] for r in model.r for c in model.c) == model.numdrops\n"
    "model.defnumdrop = Constraint(rule=defnumdrop_rule)"
)
WHOLESET = "\n".join([DEMAND, SUPPLY, DEFTOTAL, DEFNUMDROP])

records = [
    {"description": (
        "Every village must have all of its demand met. For each village, the shares of its demand "
        "served from the drops across the whole grid must add up to its entire demand."),
     "expected_pyomo": DEMAND},
    {"description": (
        "A village can only be served from a cell where a drop has actually been opened, and no single "
        "drop may serve more than its capacity. For each grid cell, the total demand drawn from that "
        "cell across all villages must not exceed its serving capacity when a drop is open there, and "
        "must be zero when no drop is open there."),
     "expected_pyomo": SUPPLY},
    {"description": (
        "The total distance walked accounts for how far each village travels to every cell that serves "
        "it. Set the total distance equal to the sum, over all villages and all grid cells, of the "
        "distance from the village to the cell weighted by the share of that village's demand served "
        "from that cell."),
     "expected_pyomo": DEFTOTAL},
    {"description": (
        "Exactly the required number of drops must be opened. The count of opened drop cells across the "
        "whole grid must equal the prescribed number of drops."),
     "expected_pyomo": DEFNUMDROP},
    {"description": (
        "To build the complete model, enforce the following relationships in order. "
        "First, every village must have all of its demand met, so the shares serving each village across "
        "the whole grid add up to its full demand. "
        "Second, a village can only draw from a cell where a drop is open, and the total demand drawn "
        "from any cell must stay within its serving capacity when a drop is open there and be zero "
        "otherwise. "
        "Third, set the total distance walked equal to the sum over all villages and cells of the "
        "distance from a village to a cell weighted by the share of that village served from it. "
        "Finally, exactly the required number of drops must be opened across the whole grid."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for rec in records:
        f.write(json.dumps({
            "problem_id": "relief_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": rec["description"],
            "expected_pyomo": rec["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
