#!/usr/bin/env python
"""Builder for the knights_mip (Maximum Knights Problem) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "knights_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["1", "2", "3", "4", "5", "6", "7", "8"],
         "doc": "the board coordinates along one side, given as string labels of the integers 1 through 8; a cell on the board is an ordered pair drawn from this set used for both the row index and the column index"},
        {"name": "n", "members": ["m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8"],
         "doc": "the eight possible knight moves, each one of the L-shaped relative jumps a knight can make from a given cell"},
        {"name": "axis", "members": ["h", "v"],
         "doc": "the two board axes along which a move is measured: h for the horizontal (row) direction and v for the vertical (column) direction"},
    ],
    "params": [
        {"name": "move", "index": "axis,n", "kind": "offset",
         "doc": "the signed displacement of each knight move along each axis, in cells; for a move, adding its horizontal displacement to a cell's row and its vertical displacement to that cell's column gives the cell that move lands on, which may fall off the board"},
    ],
    "vars": [
        {"name": "x", "index": "i,i", "domain": "Binary",
         "doc": "the placement indicator for a cell, equal to 1 if a knight is placed on that cell and 0 otherwise; the first index is the row and the second is the column"},
        {"name": "total", "index": "", "domain": "Reals",
         "doc": "the total number of knights placed anywhere on the board"},
    ],
    "objective": {"sense": "maximize", "expr_var": "obj"},
}

NARRATIVE = (
    "We place knights on a square chessboard. For every cell we decide whether or not a knight "
    "sits there, and we track the total count of knights on the board. The objective is to "
    "maximize the number of knights placed."
)

DEFTOTAL = (
    "model.deftotal = Constraint(expr=model.total == sum(model.x[i, j] for i in model.i for j in model.i))"
)

DEFMOVEX = (
    "def defmovex_rule(model, n, i, j):\n"
    "    ti = str(int(i) + int(value(model.move['h', n])))\n"
    "    tj = str(int(j) + int(value(model.move['v', n])))\n"
    "    if ti not in model.i or tj not in model.i:\n"
    "        return Constraint.Skip\n"
    "    return model.x[ti, tj] + model.x[i, j] <= 1\n"
    "model.defmovex = Constraint(model.n, model.i, model.i, rule=defmovex_rule)"
)

WHOLESET = "\n".join([DEFTOTAL, DEFMOVEX])

NARR_WHOLE = (
    "To build the complete model, enforce the following relationships in order. "
    "First, tie the running count of placed knights to the actual placements so that it equals the "
    "number of cells that hold a knight. "
    "Finally, forbid any two knights from threatening each other, so that whenever a cell and "
    "another cell a knight's move away from it are both on the board, at most one of those two "
    "cells may hold a knight."
)

records = [
    {"description": (
        "The total count of knights must match the placements actually made, so it equals the "
        "number of cells across the whole board that hold a knight."),
     "expected_pyomo": DEFTOTAL},
    {"description": (
        "No two knights may threaten one another. For every cell and every knight move, look at the "
        "cell reached by applying that move; if that target cell lies on the board, then at most one "
        "of the original cell and the target cell may hold a knight. When the target cell falls off "
        "the board the requirement does not apply."),
     "expected_pyomo": DEFMOVEX},
    {"description": NARR_WHOLE,
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "knights_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
