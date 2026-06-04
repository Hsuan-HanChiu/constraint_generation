#!/usr/bin/env python
"""Builder for the queens_mip (Maximum Queens, MIP) constraint-generation dataset.
Run with plain python (no special deps) to (re)generate the JSONL."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "queens_mip_constraint_gen.jsonl"

# ---- shared model vocabulary (same components block in every record) ----
COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["1", "2", "3", "4", "5", "6", "7", "8"],
         "doc": "the rows and columns of the square chess board, numbered from 1; the board is square so this same set indexes both the rank direction and the file direction, and a board square is a pair of one row and one column"},
        {"name": "s", "members": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
         "doc": "the diagonal bands of the board, one band per offset; for an n by n board there are 2n-1 diagonal bands running in each of the two diagonal directions"},
    ],
    "params": [
        {"name": "sh", "index": "s", "kind": "offset",
         "doc": "the column shift that selects which forward-sloping diagonal band a square lies on; for diagonal band s it equals the band number minus the board size plus one, so that band one is the longest corner-to-corner forward diagonal and the bands sweep across the board"},
        {"name": "rev", "index": "i",
         "kind": "offset",
         "doc": "a per-row reversal offset used to map a square onto its backward-sloping diagonal band; for row i it equals the board size plus one minus twice the row number"},
    ],
    "vars": [
        {"name": "x", "index": "i,i", "domain": "Binary",
         "doc": "1 if a queen is placed on the square at that row and column, 0 otherwise"},
        {"name": "tot", "index": "", "domain": "Reals",
         "doc": "the total number of queens placed on the board"},
    ],
    "objective": {"sense": "maximize", "expr_var": "tot"},
}

NARRATIVE = (
    "We place queens on a square chess board and decide, for each square, whether a "
    "queen sits on it. We want to put as many queens on the board as possible while "
    "keeping them in a non-attacking arrangement. The objective is to make the total "
    "number of placed queens as large as possible."
)

# ---- ground-truth Pyomo for each constraint (self-contained over model.* only) ----
# The diagonal rules re-derive the board geometry from model.i, model.sh and model.rev
# so that nothing outside model.* is referenced.

RANK = (
    "def a_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.i) == 1\n"
    "model.a = Constraint(model.i, rule=a_rule)"
)

FILE = (
    "def b_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.i) == 1\n"
    "model.b = Constraint(model.i, rule=b_rule)"
)

DIAG_FWD = (
    "def c_rule(model, s):\n"
    "    terms = []\n"
    "    for i in model.i:\n"
    "        j = str(int(i) + int(value(model.sh[s])))\n"
    "        if j in model.i:\n"
    "            terms.append(model.x[i, j])\n"
    "    if not terms:\n"
    "        return Constraint.Skip\n"
    "    return sum(terms) <= 1\n"
    "model.c = Constraint(model.s, rule=c_rule)"
)

DIAG_BWD = (
    "def d_rule(model, s):\n"
    "    terms = []\n"
    "    for i in model.i:\n"
    "        j = str(int(i) + int(value(model.rev[i])) + int(value(model.sh[s])))\n"
    "        if j in model.i:\n"
    "            terms.append(model.x[i, j])\n"
    "    if not terms:\n"
    "        return Constraint.Skip\n"
    "    return sum(terms) <= 1\n"
    "model.d = Constraint(model.s, rule=d_rule)"
)

TOTAL = (
    "def tot_rule(model):\n"
    "    return model.tot == sum(model.x[i, j] for i in model.i for j in model.i)\n"
    "model.tot_constraint = Constraint(rule=tot_rule)"
)

WHOLESET = "\n".join([RANK, FILE, DIAG_FWD, DIAG_BWD, TOTAL])

records = [
    {
        "description": (
            "Each row of the board must hold exactly one queen. For every row, the "
            "number of queens placed across that row's squares has to be exactly one."
        ),
        "expected_pyomo": RANK,
    },
    {
        "description": (
            "Each column of the board must hold exactly one queen. For every column, "
            "the number of queens placed down that column's squares has to be exactly "
            "one."
        ),
        "expected_pyomo": FILE,
    },
    {
        "description": (
            "No forward-sloping diagonal may hold more than one queen. For every "
            "forward diagonal band of the board, the queens placed on the squares that "
            "lie along that band can total at most one."
        ),
        "expected_pyomo": DIAG_FWD,
    },
    {
        "description": (
            "No backward-sloping diagonal may hold more than one queen. For every "
            "backward diagonal band of the board, the queens placed on the squares "
            "that lie along that band can total at most one."
        ),
        "expected_pyomo": DIAG_BWD,
    },
    {
        "description": (
            "Define the total count of placed queens as the number of squares that "
            "carry a queen, added up over the whole board, and set the total to equal "
            "that count."
        ),
        "expected_pyomo": TOTAL,
    },
    {
        "description": "Generate the complete constraint set for this model.",
        "expected_pyomo": WHOLESET,
    },
]

with open(OUT, "w") as f:
    for r in records:
        rec = {
            "problem_id": "queens_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {OUT} ({len(records)} records)")
