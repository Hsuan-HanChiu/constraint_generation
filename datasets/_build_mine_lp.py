#!/usr/bin/env python
"""Builder for the mine_lp (open-pit block mining) constraint-generation dataset.
Run with plain python (no special deps) to (re)generate the JSONL."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "mine_lp_constraint_gen.jsonl"

# ---- shared model vocabulary (same components block in every record) ----
COMPONENTS = {
    "sets": [
        {"name": "L", "members": [1, 2, 3, 4],
         "doc": "the levels of the mine, listed from the surface downward; level 1 is the topmost layer and each later level sits directly beneath the previous one"},
        {"name": "I", "members": [1, 2, 3, 4],
         "doc": "the row position of a block within its level"},
        {"name": "J", "members": [1, 2, 3, 4],
         "doc": "the column position of a block within its level"},
        {"name": "K", "members": ["nw", "ne", "se", "sw"],
         "doc": "the four blocks on the level above that sit directly over and around a given block; each label is one of the four diagonal neighbor positions northwest, northeast, southeast, southwest"},
        {"name": "C", "index": "L,I,J", "members": "computed",
         "doc": "the set of blocks that have a full set of covering neighbors on the level above, so a downward precedence relationship can be stated for them; a block at level l, row i, column j belongs here when its level index plus its row index and its level index plus its column index each stay within the number of levels"},
        {"name": "D", "index": "L,I,J", "members": "computed",
         "doc": "the set of all blocks that can be extracted; a block at level l, row i, column j belongs here when its level index plus its row index and its level index plus its column index each stay within the number of levels plus one"},
    ],
    "params": [
        {"name": "conc", "index": "L,I,J", "kind": "concentration",
         "doc": "estimated ore concentration of a block, as a percentage of metal"},
        {"name": "cost", "index": "L", "kind": "cost",
         "doc": "the cost to extract a block on a given level"},
        {"name": "value", "index": "", "kind": "value",
         "doc": "the value of one fully extracted block if it were one hundred percent metal"},
        {"name": "li", "index": "K", "kind": "offset",
         "doc": "the row offset that locates each of the four covering neighbor positions; added to a block's row index it gives the row of that neighbor on the level above"},
        {"name": "lj", "index": "K", "kind": "offset",
         "doc": "the column offset that locates each of the four covering neighbor positions; added to a block's column index it gives the column of that neighbor on the level above"},
    ],
    "vars": [
        {"name": "x", "index": "L,I,J", "domain": "NonNegativeReals in [0, 1]",
         "doc": "the fraction of a block that is extracted, from zero for untouched up to one for fully removed"},
        {"name": "profit", "index": "", "domain": "Reals", "doc": "the total profit from extraction"},
    ],
    "objective": {"sense": "maximize", "expr_var": "profit"},
}

NARRATIVE = (
    "This is an open-pit mining problem. The deposit is divided into blocks arranged "
    "in a grid of levels stacked from the surface downward, and each block has an "
    "estimated ore concentration and a known extraction cost that depends on its "
    "level. The recovered metal from a block is worth more when its concentration is "
    "higher. We decide what fraction of each block to extract. The objective is to "
    "make the total profit as large as possible."
)

# ---- ground-truth Pyomo for each constraint (self-contained over model.* only) ----
PROFIT_DEF = (
    "def profit_def_rule(model):\n"
    "    return model.profit == sum((model.conc[l, i, j] * model.value / 100.0 - model.cost[l]) * model.x[l, i, j]\n"
    "                               for (l, i, j) in model.D)\n"
    "model.profit_def = Constraint(rule=profit_def_rule)"
)

PRECEDENCE = (
    "L_list = list(model.L); I_list = list(model.I); J_list = list(model.J)\n"
    "ordL = {L_list[idx]: idx + 1 for idx in range(len(L_list))}\n"
    "ordI = {I_list[idx]: idx + 1 for idx in range(len(I_list))}\n"
    "ordJ = {J_list[idx]: idx + 1 for idx in range(len(J_list))}\n"
    "succL = {L_list[idx]: (L_list[idx + 1] if idx + 1 < len(L_list) else None) for idx in range(len(L_list))}\n"
    "def precedence_rule(model, k, l, i, j):\n"
    "    lnext = succL[l]\n"
    "    if lnext is None:\n"
    "        return Constraint.Skip\n"
    "    off_i = int(value(model.li[k])); off_j = int(value(model.lj[k]))\n"
    "    ii_idx = ordI[i] - 1 + off_i\n"
    "    jj_idx = ordJ[j] - 1 + off_j\n"
    "    if ii_idx < 0 or jj_idx < 0 or ii_idx >= len(I_list) or jj_idx >= len(J_list):\n"
    "        return Constraint.Skip\n"
    "    ii = I_list[ii_idx]; jj = J_list[jj_idx]\n"
    "    return model.x[l, ii, jj] >= model.x[lnext, i, j]\n"
    "model.precedence = Constraint(model.K, model.C, rule=precedence_rule)"
)

WHOLESET = "\n".join([PROFIT_DEF, PRECEDENCE])

records = [
    {
        "description": (
            "Define the total profit earned across the whole mine. For every "
            "extractable block, the net worth of fully removing it is the value of "
            "its recovered metal at its concentration less the cost of extracting a "
            "block on its level, and the contribution of a block is that net worth "
            "scaled by the fraction of the block that is actually extracted. Set the "
            "profit equal to these contributions added up over all extractable blocks."
        ),
        "expected_pyomo": PROFIT_DEF,
    },
    {
        "description": (
            "A block cannot be dug out before the rock sitting on top of it has been "
            "cleared away first. For each block that has a full set of covering "
            "neighbors on the level above, and for each of those four diagonal "
            "covering neighbors, the fraction extracted from the covering neighbor "
            "must be at least the fraction extracted from the block directly below it. "
            "This ties every block to the four blocks above it so that a block can "
            "only be removed once the blocks covering it have been removed at least as "
            "much."
        ),
        "expected_pyomo": PRECEDENCE,
    },
    {
        "description": "Generate the complete constraint set for this model.",
        "expected_pyomo": WHOLESET,
    },
]

with open(OUT, "w") as f:
    for r in records:
        rec = {
            "problem_id": "mine_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {OUT} ({len(records)} records)")
