#!/usr/bin/env python
"""Builder for the latin_mip (superimposed Latin squares) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "latin_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "S", "members": ["one", "two"],
         "doc": "the squares to be filled; there are two of them, laid one on top of the other on the same grid so that every cell of the grid holds an entry from each square"},
        {"name": "V", "members": ["val1", "val2", "val3", "val4"],
         "doc": "the symbols that may be placed in a cell; the same set of symbols is used for both squares"},
        {"name": "K", "members": ["row1", "row2", "row3", "row4"],
         "doc": "the rows of the grid"},
        {"name": "L", "members": ["col1", "col2", "col3", "col4"],
         "doc": "the columns of the grid; the grid is square so there are as many columns as rows and as many symbols as rows"},
    ],
    "params": [],
    "vars": [
        {"name": "y", "index": "S,V,K,L", "domain": "Binary",
         "doc": "a yes/no choice that is 1 when, in the given square, the given symbol is placed in the cell at the given row and column, and 0 otherwise"},
        {"name": "dev", "index": "V,K,L", "domain": "Reals",
         "doc": "an unused auxiliary quantity kept for historical reasons; it appears in no constraint"},
        {"name": "w", "index": "", "domain": "Reals",
         "doc": "the objective quantity, equal to the total number of symbol placements made across both squares"},
    ],
    "objective": {"sense": "minimize", "expr_var": "w"},
}

NARRATIVE = (
    "We are filling in two square grids of the same size, stacked on top of each other "
    "so they share one set of cells. For every square, every cell, every symbol, and "
    "every row and column we decide whether that symbol goes in that cell of that square. "
    "Each grid must end up as a proper Latin square, and the two squares must be arranged "
    "to relate to each other in the required way. The objective totals up how many symbol "
    "placements are made and seeks the smallest such total."
)

N2 = (
    "def n2_rule(model, s, k, l):\n"
    "    return sum(model.y[s, v, k, l] for v in model.V) == 1\n"
    "model.n2 = Constraint(model.S, model.K, model.L, rule=n2_rule)"
)
N3 = (
    "def n3_rule(model, s, v, l):\n"
    "    return sum(model.y[s, v, k, l] for k in model.K) == 1\n"
    "model.n3 = Constraint(model.S, model.V, model.L, rule=n3_rule)"
)
N5 = (
    "def n5_rule(model, s, v, k):\n"
    "    return sum(model.y[s, v, k, l] for l in model.L) == 1\n"
    "model.n5 = Constraint(model.S, model.V, model.K, rule=n5_rule)"
)
N6 = (
    "def n6_rule(model, v, k, l):\n"
    "    return sum(model.y[s, v, k, l] for s in model.S) <= 1\n"
    "model.n6 = Constraint(model.V, model.K, model.L, rule=n6_rule)"
)
NOBJ = (
    "def nobj_rule(model):\n"
    "    return model.w == sum(model.y[s, v, k, l] for s in model.S for v in model.V for k in model.K for l in model.L)\n"
    "model.nobj = Constraint(rule=nobj_rule)"
)
WHOLESET = "\n".join([N2, N3, N5, N6, NOBJ])

records = [
    {"description": (
        "Every cell of every square must be filled with exactly one symbol. For each "
        "square and each cell, the placements that put some symbol in that cell add up to "
        "exactly one, so the cell holds one symbol and no more."),
     "expected_pyomo": N2},
    {"description": (
        "Within each square, every symbol must appear exactly once in each column. For each "
        "square, each symbol, and each column, the placements that put that symbol somewhere "
        "in that column add up to exactly one."),
     "expected_pyomo": N3},
    {"description": (
        "Within each square, every symbol must appear exactly once in each row. For each "
        "square, each symbol, and each row, the placements that put that symbol somewhere in "
        "that row add up to exactly one."),
     "expected_pyomo": N5},
    {"description": (
        "Where the two squares overlap, they are not allowed to place the same symbol in the "
        "same cell. For each symbol and each cell, across both squares the placements of that "
        "symbol in that cell add up to at most one."),
     "expected_pyomo": N6},
    {"description": (
        "The objective quantity counts every symbol placement made. Set it equal to the total "
        "of all the placements summed over both squares, every symbol, and every cell."),
     "expected_pyomo": NOBJ},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "latin_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
