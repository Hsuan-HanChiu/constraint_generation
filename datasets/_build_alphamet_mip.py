#!/usr/bin/env python
"""Builder for the alphamet_mip (alphametics puzzle) constraint-generation dataset.

GEORGIA + OREGON + VERMONT = VIRGINIA, solved as a MIP: assign a distinct digit
to each letter (permutation), express each letter's value, and enforce
column-by-column addition with carries.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "alphamet_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "i", "members": ["g", "e", "o", "r", "i", "a", "n", "v", "m", "t"],
         "doc": "the set of distinct letters that appear in the puzzle; each letter must be assigned a digit"},
        {"name": "j", "members": ["g", "e", "o", "r", "i", "a", "n", "v", "m", "t"],
         "doc": "a second copy of the letter set used as the column index when assigning digits to letters; it is an alias of the letter set"},
        {"name": "k", "members": [1, 2, 3, 4, 5, 6, 7, 8],
         "doc": "the addition columns of the puzzle in order from the rightmost column to the leftmost; the first member is the units column and each later member is the next column to the left"},
        {"name": "lead", "members": ["g", "o", "v"],
         "doc": "the subset of letters that appear as the leading letter of a word; a leading letter is not allowed to take the digit zero"},
    ],
    "params": [
        {"name": "lhs", "index": "k,i", "kind": "count",
         "doc": "how many times each letter appears in a given column on the left-hand side of the addition, that is among the numbers being added together; zero when the letter does not appear in that column"},
        {"name": "rhs", "index": "i,k", "kind": "count",
         "doc": "how many times each letter appears in a given column on the right-hand side of the addition, that is in the result number; zero when the letter does not appear in that column"},
    ],
    "vars": [
        {"name": "x", "index": "i,j", "domain": "Binary",
         "doc": "the digit-assignment indicator, equal to 1 when a letter is assigned the digit corresponding to a given column position and 0 otherwise; the second index ranges over the same labels as the letters but its ordinal position from the start, counting from zero, is the digit value it stands for"},
        {"name": "y", "index": "i", "domain": "Reals",
         "doc": "the numeric digit value assigned to each letter, ranging from zero to nine"},
        {"name": "c", "index": "k", "domain": "NonNegativeIntegers",
         "doc": "the carry produced out of each column and passed into the next column to the left"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total of all the carries, which is the quantity being minimized"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We solve an addition puzzle in which several words are spelled out with letters and the "
    "letters stand for digits. We must assign a digit to every letter so that the digits spell out "
    "a correct addition, where two numbers added to a third give a fourth. Every letter takes a "
    "different digit, and a leading letter cannot be zero. Reading the addition column by column "
    "from right to left produces a carry out of each column into the next. We decide which digit "
    "each letter receives, the resulting numeric value of each letter, and the carry out of each "
    "column. The objective is to minimize the total of all the carries."
)

OBJDEF = (
    "def objdef_rule(model):\n"
    "    klist = list(model.k)\n"
    "    return model.z == sum(model.c[klist[klist.index(k) - 1]] for k in model.k if klist.index(k) > 0)\n"
    "model.objdef = Constraint(rule=objdef_rule)"
)
EQ = (
    "def eq_rule(model, k):\n"
    "    klist = list(model.k)\n"
    "    pos = klist.index(k)\n"
    "    carry_in = model.c[klist[pos - 1]] if pos > 0 else 0\n"
    "    lhs_expr = carry_in + sum(model.lhs[k, i] * model.y[i] for i in model.i)\n"
    "    rhs_expr = sum(model.rhs[i, k] * model.y[i] for i in model.i)\n"
    "    if k != klist[-1]:\n"
    "        rhs_expr = rhs_expr + 10 * model.c[k]\n"
    "    return lhs_expr == rhs_expr\n"
    "model.eq = Constraint(model.k, rule=eq_rule)"
)
YDEF = (
    "def ydef_rule(model, i):\n"
    "    return model.y[i] == sum(pos * model.x[i, j] for pos, j in enumerate(model.j))\n"
    "model.ydef = Constraint(model.i, rule=ydef_rule)"
)
X1 = (
    "def x1_rule(model, i):\n"
    "    return sum(model.x[i, j] for j in model.j) == 1\n"
    "model.x1 = Constraint(model.i, rule=x1_rule)"
)
X2 = (
    "def x2_rule(model, j):\n"
    "    return sum(model.x[i, j] for i in model.i) == 1\n"
    "model.x2 = Constraint(model.j, rule=x2_rule)"
)
LD = (
    "def ld_rule(model, lead):\n"
    "    return model.y[lead] >= 1\n"
    "model.ld = Constraint(model.lead, rule=ld_rule)"
)

OBJDEF_D = (
    "The quantity being minimized is the running total of carries. Set the total to the sum, taken "
    "over the columns, of the carry that comes into each column from the column to its right. The "
    "rightmost column has nothing coming into it, so it contributes nothing to this total."
)
EQ_D = (
    "Each column of the addition must balance once carries are taken into account. For every column, "
    "take the carry coming in from the column to its right and add to it the combined value of the "
    "letters being added together in that column, where each letter contributes its assigned value "
    "as many times as it appears there. This must equal the combined value of the letters that make "
    "up the result in that column, again counting each letter's value by how many times it appears, "
    "plus ten times the carry that this column sends out to the next column. The leftmost column "
    "sends out no carry, so for that column there is no carry-out term."
)
YDEF_D = (
    "Each letter's numeric value is determined by which digit it was assigned. For every letter, set "
    "its value equal to the digit it was given under the digit assignment."
)
X1_D = (
    "Every letter must receive exactly one digit. For each letter, its assignment across all the "
    "possible digits must add up to one."
)
X2_D = (
    "Every digit must be given to exactly one letter, so that no two letters share a digit. For each "
    "digit, its assignment across all the letters must add up to one."
)
LD_D = (
    "A leading letter is not allowed to stand for zero. For each leading letter, its assigned value "
    "must be at least one."
)

WHOLESET = "\n".join([OBJDEF, EQ, YDEF, X1, X2, LD])
WHOLESET_D = (
    "To build the complete model, enforce the following relationships in order. "
    "First, set the quantity being minimized equal to the running total of carries, summing over the "
    "columns the carry that comes into each column from the column to its right, with the rightmost "
    "column contributing nothing. "
    "Second, make each column of the addition balance: for every column, the carry coming in plus "
    "the combined value of the letters being added together in that column must equal the combined "
    "value of the letters making up the result in that column plus ten times the carry sent out to "
    "the next column, with the leftmost column sending out no carry. "
    "Third, determine each letter's numeric value from its digit assignment, setting each letter's "
    "value equal to the digit it was given. "
    "Fourth, require that every letter receives exactly one digit, so each letter's assignment across "
    "all digits adds up to one. "
    "Fifth, require that every digit goes to exactly one letter, so each digit's assignment across "
    "all letters adds up to one. "
    "Finally, forbid any leading letter from standing for zero, requiring each leading letter's "
    "assigned value to be at least one."
)

records = [
    {"description": OBJDEF_D, "expected_pyomo": OBJDEF},
    {"description": EQ_D, "expected_pyomo": EQ},
    {"description": YDEF_D, "expected_pyomo": YDEF},
    {"description": X1_D, "expected_pyomo": X1},
    {"description": X2_D, "expected_pyomo": X2},
    {"description": LD_D, "expected_pyomo": LD},
    {"description": WHOLESET_D, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "alphamet_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
