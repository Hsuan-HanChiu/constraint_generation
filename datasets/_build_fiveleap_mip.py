#!/usr/bin/env python
"""Builder for the fiveleap_mip (five-leap board tour / MTZ) constraint-generation dataset.
Run with plain python (no special deps) to (re)generate the JSONL."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fiveleap_mip_constraint_gen.jsonl"

# ---- shared model vocabulary (same components block in every record) ----
COMPONENTS = {
    "sets": [
        {"name": "r", "members": ["1", "2", "3", "4", "5", "6", "7", "8"],
         "doc": "the rows of the board, labelled by number"},
        {"name": "c", "members": ["1", "2", "3", "4", "5", "6", "7", "8"],
         "doc": "the columns of the board, labelled by number. A square on the board is a row-column pair"},
        {"name": "m", "members": ["(row, col, row2, col2) quadruples"],
         "doc": "the set of legal leaps. It holds every ordered pair of squares such that a single leap of the piece can carry it from the first square directly to the second square. A leap is legal exactly when the squared change in row plus the squared change in column equals twenty-five, which is the fixed reach of this piece"},
        {"name": "ss", "members": [["1", "1"]],
         "doc": "the single starting square of the tour. The tour begins on this square and its tour position is fixed to one"},
    ],
    "params": [],
    "vars": [
        {"name": "xm", "index": "r,c,r,c", "domain": "Binary",
         "doc": "1 if the tour leaps directly from the first square to the second square, 0 otherwise. Only legal leaps can be used, so every pair of squares that is not a legal leap is fixed to 0"},
        {"name": "nm", "index": "r,c", "domain": "NonNegativeReals",
         "doc": "the position of a square in the visiting order along the tour. The starting square is fixed at position one"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the dummy objective value, equal to the count of leaps used"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "A single piece must make a closed tour of every square on a board. The piece "
    "moves only by a fixed leap, and from any square only certain other squares are "
    "reachable in one such leap. We decide which leaps to take so that the piece "
    "visits every square. We also track the position of each square in the visiting "
    "order. The objective is a dummy value that simply counts the leaps taken."
)

# ---- ground-truth Pyomo for each constraint (self-contained over model.* only) ----
# Re-derive in-rule: the start square is the one whose nm is fixed; the board size
# is the number of squares; legal leaps are exactly the members of model.m.

OBJ_DEF = (
    "def obj_def_rule(model):\n"
    "    return model.z == sum(model.xm[r, c, rp, cp] for (r, c, rp, cp) in model.m)\n"
    "model.obj_def = Constraint(rule=obj_def_rule)"
)

DEFFROM = (
    "def deffrom_rule(model, r, c):\n"
    "    return sum(model.xm[r, c, rp, cp] for (r1, c1, rp, cp) in model.m if r1 == r and c1 == c) == 1\n"
    "model.deffrom = Constraint(model.r, model.c, rule=deffrom_rule)"
)

DEFTO = (
    "def defto_rule(model, rp, cp):\n"
    "    return sum(model.xm[r, c, rp, cp] for (r, c, r2, c2) in model.m if r2 == rp and c2 == cp) == 1\n"
    "model.defto = Constraint(model.r, model.c, rule=defto_rule)"
)

DEFORDER = (
    "n_squares = len(model.r) * len(model.c)\n"
    "start_r, start_c = next((r, c) for r in model.r for c in model.c if model.nm[r, c].fixed)\n"
    "def deforder_rule(model, r, c, rp, cp):\n"
    "    if (r, c, rp, cp) not in model.m:\n"
    "        return Constraint.Skip\n"
    "    if rp == start_r and cp == start_c:\n"
    "        return Constraint.Skip\n"
    "    return model.nm[r, c] - model.nm[rp, cp] <= n_squares * (1 - model.xm[r, c, rp, cp]) - 1\n"
    "model.deforder = Constraint(model.r, model.c, model.r, model.c, rule=deforder_rule)"
)

WHOLESET = "\n".join([OBJ_DEF, DEFFROM, DEFTO, DEFORDER])

records = [
    {
        "description": (
            "Define the dummy objective value as the total number of leaps used in the "
            "tour, counting every leap that is taken, and set the objective variable "
            "equal to that count."
        ),
        "expected_pyomo": OBJ_DEF,
    },
    {
        "description": (
            "Each square must be left exactly once. For every square, exactly one legal "
            "leap departs from it to some reachable square."
        ),
        "expected_pyomo": DEFFROM,
    },
    {
        "description": (
            "Each square must be entered exactly once. For every square, exactly one "
            "legal leap arrives at it from some square that can reach it."
        ),
        "expected_pyomo": DEFTO,
    },
    {
        "description": (
            "The chosen leaps must form one single closed tour through all the squares "
            "rather than several smaller disconnected loops. Use the tour-position "
            "values to order the squares so that whenever a leap from one square to "
            "another is taken, the destination square comes later in the order than the "
            "origin square, except for leaps that return to the starting square, which "
            "are allowed to close the tour. This rules out any sub-loop that does not "
            "pass through the starting square."
        ),
        "expected_pyomo": DEFORDER,
    },
    {
        "description": "Generate the complete constraint set for this model.",
        "expected_pyomo": WHOLESET,
    },
]

with open(OUT, "w") as f:
    for r in records:
        rec = {
            "problem_id": "fiveleap_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {OUT} ({len(records)} records)")
