#!/usr/bin/env python
"""Builder for the dicex_mip (non-transitive dice design, extended) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "dicex_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "f", "members": ["face1", "face2", "face3", "face4", "face5", "face6"],
         "doc": "the faces of a single die, listed in a fixed positional order from the first face to the last; this ordering is used to talk about adjacent faces"},
        {"name": "d", "members": ["dice1", "dice2", "dice3"],
         "doc": "the dice being designed, arranged in a fixed cyclic order; the die that follows the last die in this order wraps back around to the first die, which encodes the cyclic beating relationship the design aims for"},
    ],
    "params": [
        {"name": "wn", "index": "", "kind": "target",
         "doc": "the minimum number of wins targeted in the design; a scalar reference value of 19"},
        {"name": "big", "index": "", "kind": "big-M",
         "doc": "a single large constant used to switch off a face-comparison inequality when the corresponding comparison is not asserted; its magnitude equals the number of dice multiplied by the number of faces"},
        {"name": "fnum", "index": "d,f", "domain": "NonNegativeReals", "kind": "value-pool",
         "doc": "the pool of candidate numeric values, one slot per die-and-face position, that the design draws from when it assigns an actual numeric value to each die face; in the full data these range from 1 up to the number of dice times the number of faces"},
    ],
    "vars": [
        {"name": "wnx", "index": "", "domain": "Reals",
         "doc": "the common number of face-versus-face wins each die scores against the next die in the cycle"},
        {"name": "fval", "index": "d,f", "domain": "Integers",
         "doc": "the integer value placed on each face of each die, bounded between 1 and the number of dice times the number of faces; the first face of the first die is fixed to the value 1 to break symmetry"},
        {"name": "comp", "index": "d,f,f", "domain": "Binary",
         "doc": "a face-comparison indicator that equals 1 when a given face of a die is asserted to beat a given face of the next die in the cycle, and 0 otherwise; the first face index refers to the current die and the second to the next die"},
        {"name": "fmap", "index": "d,f,d,f", "domain": "Binary",
         "doc": "an assignment indicator that equals 1 when a particular die-face position draws its number from a particular slot of the value pool; the first die-face pair is the position being filled and the second die-face pair is the pool slot supplying the value"},
    ],
    "objective": {"sense": "maximize", "expr_var": "obj"},
}

NARRATIVE = (
    "We design a set of dice with integer face values so that they beat each other in a cycle, "
    "where each die tends to beat the next die in the cyclic order. For each die we decide the "
    "numeric value placed on every one of its faces, drawing those values from a shared pool of "
    "candidate numbers, and we decide which faces of a die are counted as beating which faces of "
    "the next die. We also track the common number of face-versus-face wins a die achieves "
    "against the next die in the cycle. The objective is to maximize that number of wins."
)

EQ1 = (
    "def eq1_rule(m, d):\n"
    "    return sum(m.comp[d, f, fp] for f in m.f for fp in m.f) == m.wnx\n"
    "model.eq1 = Constraint(model.d, rule=eq1_rule)"
)
EQ2 = (
    "_d = list(model.d)\n"
    "def eq2_rule(m, d, f, fp):\n"
    "    d_next = _d[(_d.index(d) + 1) % len(_d)]\n"
    "    return m.fval[d, f] + m.big * (1 - m.comp[d, f, fp]) >= m.fval[d_next, fp] + 1\n"
    "model.eq2 = Constraint(model.d, model.f, model.f, rule=eq2_rule)"
)
EQ3 = (
    "_f = list(model.f)\n"
    "def eq3_rule(m, d, f):\n"
    "    fi = _f.index(f)\n"
    "    if fi == 0:\n"
    "        return Constraint.Skip\n"
    "    return m.fval[d, _f[fi - 1]] + 1 <= m.fval[d, f]\n"
    "model.eq3 = Constraint(model.d, model.f, rule=eq3_rule)"
)
EQ4 = (
    "def eq4_rule(m, d, f):\n"
    "    return sum(m.fnum[dp, fp] * m.fmap[d, f, dp, fp] for dp in m.d for fp in m.f) == m.fval[d, f]\n"
    "model.eq4 = Constraint(model.d, model.f, rule=eq4_rule)"
)
EQ5 = (
    "def eq5_rule(m, dp, fp):\n"
    "    return sum(m.fmap[d, f, dp, fp] for d in m.d for f in m.f) == 1\n"
    "model.eq5 = Constraint(model.d, model.f, rule=eq5_rule)"
)
WHOLESET = "\n".join([EQ1, EQ2, EQ3, EQ4, EQ5])

D_EQ1 = (
    "For each die, the number of face-versus-face wins it is credited with against the next die "
    "in the cycle, counted across all pairs of one of its faces against one of the next die's "
    "faces, must equal the common win count we are tracking. In other words every die ends up "
    "with the same number of winning face matchups against its successor."
)
D_EQ2 = (
    "Whenever a face of a die is asserted to beat a face of the next die in the cycle, the value "
    "on that die's face must actually exceed the value on the next die's face by at least one. "
    "This is enforced for every die together with every pairing of one of its faces against one "
    "of the next die's faces, but only when that particular face matchup is asserted as a win; "
    "when the matchup is not asserted the requirement is switched off by a large allowance so it "
    "places no real restriction."
)
D_EQ3 = (
    "Within each die the face values must strictly increase from one face to the next in the "
    "fixed face order, so that going from any face to the one immediately after it the value goes "
    "up by at least one. This applies to every adjacent pair of faces on every die, which also "
    "guarantees the faces of a die all carry different values. The very first face has no face "
    "before it, so the requirement starts from the second face onward."
)
D_EQ4 = (
    "The value placed on each die face must equal the number drawn from whichever single pool "
    "slot is selected to supply it. For every die-and-face position, summing each candidate pool "
    "value weighted by whether that pool slot is the one chosen for this position recovers the "
    "value assigned to that face."
)
D_EQ5 = (
    "Every slot of the candidate value pool must be used exactly once across the whole design. "
    "For each pool slot, exactly one die-face position draws its value from that slot, so the "
    "assignment of pool values to face positions is a one-to-one matching."
)

ORDINAL = (
    "To build the complete model, enforce the following relationships in order. "
    "First, " + D_EQ1[0].lower() + D_EQ1[1:] + " "
    "Second, " + D_EQ2[0].lower() + D_EQ2[1:] + " "
    "Third, " + D_EQ3[0].lower() + D_EQ3[1:] + " "
    "Fourth, " + D_EQ4[0].lower() + D_EQ4[1:] + " "
    "Finally, " + D_EQ5[0].lower() + D_EQ5[1:]
)

records = [
    {"description": D_EQ1, "expected_pyomo": EQ1},
    {"description": D_EQ2, "expected_pyomo": EQ2},
    {"description": D_EQ3, "expected_pyomo": EQ3},
    {"description": D_EQ4, "expected_pyomo": EQ4},
    {"description": D_EQ5, "expected_pyomo": EQ5},
    {"description": ORDINAL, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "dicex_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
