#!/usr/bin/env python
"""Builder for the coexx_mip (coexistence of two armies of queens) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "coexx_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["1", "2", "3", "4", "5"],
         "doc": "the row positions of the square board, given as integer-valued strings in increasing order; the board is square so this same set also indexes the columns"},
        {"name": "j", "members": ["1", "2", "3", "4", "5"],
         "doc": "the column positions of the square board; an alias of the row set with identical members, used when both a row and a column index appear together"},
        {"name": "s", "members": ["1", "2", "3", "4", "5", "6", "7"],
         "doc": "the set of diagonal lines of the board, given as integer-valued strings; there are as many diagonals as two less than twice the board side, and each diagonal collects the squares that share one diagonal direction. The board side equals the number of rows, and for a diagonal labelled s the column that meets row i on that diagonal is obtained by adding to the row index the offset (int(s) minus board side plus one); for the opposite diagonal direction the column that meets row i is obtained by adding to the row index the offset (board side plus one minus twice the row index plus that same first offset). Squares whose computed column falls outside the board are not on that diagonal"},
    ],
    "params": [],
    "vars": [
        {"name": "xw", "index": "i,j", "domain": "Binary",
         "doc": "placement indicator for a white queen; equals 1 if a white queen occupies the square at that row and column and 0 otherwise"},
        {"name": "xb", "index": "i,j", "domain": "Binary",
         "doc": "placement indicator for a black queen; equals 1 if a black queen occupies the square at that row and column and 0 otherwise"},
        {"name": "wa", "index": "i", "domain": "Binary",
         "doc": "row occupancy indicator for white; equals 1 if any white queen sits somewhere in that row and 0 otherwise"},
        {"name": "wb", "index": "i", "domain": "Binary",
         "doc": "column occupancy indicator for white; equals 1 if any white queen sits somewhere in that column and 0 otherwise"},
        {"name": "wc", "index": "s", "domain": "Binary",
         "doc": "diagonal occupancy indicator for white in one diagonal direction; equals 1 if any white queen sits on that diagonal and 0 otherwise"},
        {"name": "wd", "index": "s", "domain": "Binary",
         "doc": "diagonal occupancy indicator for white in the opposite diagonal direction; equals 1 if any white queen sits on that diagonal and 0 otherwise"},
        {"name": "tot", "index": "", "domain": "NonNegativeReals",
         "doc": "the common army size, that is the number of queens placed for each colour; both armies are required to be equally sized"},
    ],
    "objective": {"sense": "maximize", "expr_var": "tot"},
}

NARRATIVE = (
    "We place two equally sized armies of queens, one white and one black, on a square chessboard. "
    "For every square we decide whether it holds a white queen and whether it holds a black queen, "
    "and we track which rows, columns, and diagonals end up occupied by white queens. The two armies "
    "must be able to coexist on the board without any white queen and any black queen ever attacking "
    "one another. The objective is to make the common army size as large as possible."
)

AW = (
    "def aw_rule(model, i, j):\n"
    "    return model.wa[i] >= model.xw[i, j]\n"
    "model.aw = Constraint(model.i, model.j, rule=aw_rule)"
)
BW = (
    "def bw_rule(model, j, i):\n"
    "    return model.wb[j] >= model.xw[i, j]\n"
    "model.bw = Constraint(model.j, model.i, rule=bw_rule)"
)
CW = (
    "def cw_rule(model, s, i):\n"
    "    n = len(model.i)\n"
    "    sh = int(s) - n + 1\n"
    "    j_val = int(i) + sh\n"
    "    if j_val in range(1, n + 1):\n"
    "        return model.wc[s] >= model.xw[i, str(j_val)]\n"
    "    return Constraint.Skip\n"
    "model.cw = Constraint(model.s, model.i, rule=cw_rule)"
)
DW = (
    "def dw_rule(model, s, i):\n"
    "    n = len(model.i)\n"
    "    sh = int(s) - n + 1\n"
    "    rev = n + 1 - 2 * int(i) + sh\n"
    "    j_val = int(i) + rev\n"
    "    if j_val in range(1, n + 1):\n"
    "        return model.wd[s] >= model.xw[i, str(j_val)]\n"
    "    return Constraint.Skip\n"
    "model.dw = Constraint(model.s, model.i, rule=dw_rule)"
)
AB = (
    "def ab_rule(model, i, j):\n"
    "    return 1 - model.wa[i] >= model.xb[i, j]\n"
    "model.ab = Constraint(model.i, model.j, rule=ab_rule)"
)
BB = (
    "def bb_rule(model, j, i):\n"
    "    return 1 - model.wb[j] >= model.xb[i, j]\n"
    "model.bb = Constraint(model.j, model.i, rule=bb_rule)"
)
CB = (
    "def cb_rule(model, s, i):\n"
    "    n = len(model.i)\n"
    "    sh = int(s) - n + 1\n"
    "    j_val = int(i) + sh\n"
    "    if j_val in range(1, n + 1):\n"
    "        return 1 - model.wc[s] >= model.xb[i, str(j_val)]\n"
    "    return Constraint.Skip\n"
    "model.cb = Constraint(model.s, model.i, rule=cb_rule)"
)
DB = (
    "def db_rule(model, s, i):\n"
    "    n = len(model.i)\n"
    "    sh = int(s) - n + 1\n"
    "    rev = n + 1 - 2 * int(i) + sh\n"
    "    j_val = int(i) + rev\n"
    "    if j_val in range(1, n + 1):\n"
    "        return 1 - model.wd[s] >= model.xb[i, str(j_val)]\n"
    "    return Constraint.Skip\n"
    "model.db = Constraint(model.s, model.i, rule=db_rule)"
)
EB = (
    "def eb_rule(model):\n"
    "    return model.tot == sum(model.xb[i, j] for i in model.i for j in model.j)\n"
    "model.eb = Constraint(rule=eb_rule)"
)
EW = (
    "def ew_rule(model):\n"
    "    return model.tot == sum(model.xw[i, j] for i in model.i for j in model.j)\n"
    "model.ew = Constraint(rule=ew_rule)"
)
WHOLESET = "\n".join([AW, BW, CW, DW, AB, BB, CB, DB, EB, EW])

records = [
    {"description": (
        "Mark a row as occupied by white whenever it actually holds a white queen. For every square, "
        "if a white queen sits there then the indicator for white occupying that square's row must be "
        "turned on."),
     "expected_pyomo": AW},
    {"description": (
        "Mark a column as occupied by white whenever it actually holds a white queen. For every square, "
        "if a white queen sits there then the indicator for white occupying that square's column must "
        "be turned on."),
     "expected_pyomo": BW},
    {"description": (
        "Mark a diagonal as occupied by white whenever it actually holds a white queen, for the first "
        "diagonal direction. For each diagonal and each row, find the square where that diagonal crosses "
        "the row, and if a white queen sits on that square then the indicator for white occupying that "
        "diagonal must be turned on. Rows whose crossing square would fall outside the board are not "
        "considered for that diagonal."),
     "expected_pyomo": CW},
    {"description": (
        "Mark a diagonal as occupied by white whenever it actually holds a white queen, for the opposite "
        "diagonal direction. For each diagonal and each row, find the square where that diagonal crosses "
        "the row in this opposite direction, and if a white queen sits on that square then the indicator "
        "for white occupying that diagonal must be turned on. Rows whose crossing square would fall "
        "outside the board are not considered for that diagonal."),
     "expected_pyomo": DW},
    {"description": (
        "Keep black off any row that white already occupies. For every square, a black queen may sit "
        "there only when white does not occupy that square's row, so the two colours never share a row."),
     "expected_pyomo": AB},
    {"description": (
        "Keep black off any column that white already occupies. For every square, a black queen may sit "
        "there only when white does not occupy that square's column, so the two colours never share a "
        "column."),
     "expected_pyomo": BB},
    {"description": (
        "Keep black off any diagonal that white already occupies, for the first diagonal direction. For "
        "each diagonal and each row, find the square where that diagonal crosses the row, and a black "
        "queen may sit on that square only when white does not occupy that diagonal. Rows whose crossing "
        "square would fall outside the board are not considered for that diagonal."),
     "expected_pyomo": CB},
    {"description": (
        "Keep black off any diagonal that white already occupies, for the opposite diagonal direction. "
        "For each diagonal and each row, find the square where that diagonal crosses the row in this "
        "opposite direction, and a black queen may sit on that square only when white does not occupy "
        "that diagonal. Rows whose crossing square would fall outside the board are not considered for "
        "that diagonal."),
     "expected_pyomo": DB},
    {"description": (
        "Set the common army size equal to the number of black queens placed. Count every black queen "
        "on the board and require the army size to match that total."),
     "expected_pyomo": EB},
    {"description": (
        "Set the common army size equal to the number of white queens placed. Count every white queen "
        "on the board and require the army size to match that total, which together with the matching "
        "count for black forces both armies to be the same size."),
     "expected_pyomo": EW},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "coexx_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
