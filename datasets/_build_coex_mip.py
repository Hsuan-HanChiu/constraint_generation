#!/usr/bin/env python
"""Builder for the coex_mip (peacefully coexisting armies of queens) constraint-gen dataset.

NOTE: distinct from coexx_mip. coex_mip uses an explicit attacking-pair set
M(i,j,ii,jj) listing every (black square, white square) pair that would attack
each other, with binary placement vars b and w and a single peace constraint.
coexx_mip instead tracks row/column/diagonal occupancy indicators. Different
formulation, different constraint set."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "coex_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": [1, 2, 3],
         "doc": "the positions along one side of the square chessboard, indexed by integers in increasing order; the board is square so this same set indexes both the rows and the columns, and a board square is identified by a (row, column) pair drawn from this set"},
        {"name": "M", "members": [[1, 1, 1, 1], [1, 1, 1, 2], [1, 1, 2, 2], [2, 2, 1, 1], [2, 2, 3, 3], [1, 1, 2, 1]],
         "doc": "the set of conflicting square pairs, given as 4-tuples (row, column, row2, column2); a tuple is present exactly when a black queen placed on the first square and a white queen placed on the second square would attack each other, that is they share the same row, the same column, or lie on a common diagonal. The first two indices refer to the black square and the last two to the white square"},
    ],
    "params": [],
    "vars": [
        {"name": "b", "index": "i,i", "domain": "Binary",
         "doc": "black queen placement indicator; equals 1 if a black queen occupies the square at that row and column and 0 otherwise"},
        {"name": "w", "index": "i,i", "domain": "Binary",
         "doc": "white queen placement indicator; equals 1 if a white queen occupies the square at that row and column and 0 otherwise"},
        {"name": "tot", "index": "", "domain": "Reals",
         "doc": "the common army size, that is the number of queens in each army; both armies are required to hold the same number of queens"},
    ],
    "objective": {"sense": "maximize", "expr_var": "tot"},
}

NARRATIVE = (
    "We place two equally sized armies of queens, one black and one white, on a square "
    "chessboard. For every square we decide whether it holds a black queen and whether it "
    "holds a white queen, and we track the common size shared by the two armies. The two "
    "armies must coexist peacefully, meaning no black queen and white queen may ever be "
    "positioned so that they attack each other. The objective is to make the common army "
    "size as large as possible."
)

EQ1 = (
    "def eq1_rule(model, i, j, ii, jj):\n"
    "    return model.b[i, j] + model.w[ii, jj] <= 1\n"
    "model.eq1 = Constraint(model.M, rule=eq1_rule)"
)
EQ2 = (
    "def eq2_rule(model):\n"
    "    return model.tot == sum(model.b[i, j] for i in model.i for j in model.i)\n"
    "model.eq2 = Constraint(rule=eq2_rule)"
)
EQ3 = (
    "def eq3_rule(model):\n"
    "    return model.tot == sum(model.w[i, j] for i in model.i for j in model.i)\n"
    "model.eq3 = Constraint(rule=eq3_rule)"
)

DESC_EQ1 = (
    "For every pair of squares that would let a black queen and a white queen attack each "
    "other, the two cannot both be occupied at once. At most one of those two squares may "
    "hold its queen, so the black queen and the white queen of any attacking pair are never "
    "placed together and the two armies stay at peace."
)
DESC_EQ2 = (
    "Set the common army size equal to the number of black queens placed. Count every black "
    "queen on the board and require the army size to match that total."
)
DESC_EQ3 = (
    "Set the common army size equal to the number of white queens placed. Count every white "
    "queen on the board and require the army size to match that total, which together with the "
    "matching count for black forces both armies to hold the same number of queens."
)

WHOLESET = "\n".join([EQ1, EQ2, EQ3])
WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, " + DESC_EQ1[0].lower() + DESC_EQ1[1:] + " "
    "Second, " + DESC_EQ2[0].lower() + DESC_EQ2[1:] + " "
    "Finally, " + DESC_EQ3[0].lower() + DESC_EQ3[1:]
)

records = [
    {"description": DESC_EQ1, "expected_pyomo": EQ1},
    {"description": DESC_EQ2, "expected_pyomo": EQ2},
    {"description": DESC_EQ3, "expected_pyomo": EQ3},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "coex_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
