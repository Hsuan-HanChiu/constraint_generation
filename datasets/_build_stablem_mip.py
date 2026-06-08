#!/usr/bin/env python
"""Builder for the stablem_mip (stable marriage) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "stablem_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "m", "members": ["Alan", "Bob", "Carl", "Dan"],
         "doc": "the men to be matched"},
        {"name": "w", "members": ["Alice", "Brenda", "Cindy", "Debbie"],
         "doc": "the women to be matched"},
    ],
    "params": [
        {"name": "wp", "index": "w,m", "kind": "preference",
         "doc": "the rank each woman assigns to each man, where 1 is her most preferred man and larger numbers are less preferred"},
        {"name": "mp", "index": "m,w", "kind": "preference",
         "doc": "the rank each man assigns to each woman, where 1 is his most preferred woman and larger numbers are less preferred"},
    ],
    "vars": [
        {"name": "match", "index": "w,m", "domain": "Binary",
         "doc": "matching indicator; equals 1 if the woman is matched with the man and 0 otherwise"},
        {"name": "rank", "index": "", "domain": "Reals",
         "doc": "the total woman preference rank of the matching"},
    ],
    "objective": {"sense": "minimize", "expr_var": "rank"},
}

NARRATIVE = (
    "We pair a group of men with an equal group of women into couples. For each possible "
    "man and woman we decide whether they are matched together. Every woman ranks the men "
    "from most to least preferred, and likewise every man ranks the women. The objective is "
    "to make the total of the woman preference ranks across the chosen couples as small as "
    "possible."
)

ONEM = (
    "def onem_rule(model, w):\n"
    "    return sum(model.match[w, m] for m in model.m) == 1\n"
    "model.onem = Constraint(model.w, rule=onem_rule)"
)
ONEW = (
    "def onew_rule(model, m):\n"
    "    return sum(model.match[w, m] for w in model.w) == 1\n"
    "model.onew = Constraint(model.m, rule=onew_rule)"
)
STABLE = (
    "def stable_rule(model, w, m):\n"
    "    terms = [model.match[w, mm] for mm in model.m if value(model.wp[w, mm]) > value(model.wp[w, m])]\n"
    "    terms += [model.match[ww, m] for ww in model.w if value(model.mp[m, ww]) > value(model.mp[m, w])]\n"
    "    if not terms:\n"
    "        return Constraint.Skip\n"
    "    return sum(terms) <= 1\n"
    "model.stable = Constraint(model.w, model.m, rule=stable_rule)"
)
DEFRANK = (
    "def defrank_rule(model):\n"
    "    return model.rank == sum(model.wp[w, m] * model.match[w, m] for w in model.w for m in model.m)\n"
    "model.defrank = Constraint(rule=defrank_rule)"
)
WHOLESET = "\n".join([ONEM, ONEW, STABLE, DEFRANK])

records = [
    {"description": (
        "Each woman must end up paired with exactly one man. For every woman, the matches that "
        "place her with a man add up to a single pairing across all the men."),
     "expected_pyomo": ONEM},
    {"description": (
        "Each man must end up paired with exactly one woman. For every man, the matches that place "
        "him with a woman add up to a single pairing across all the women."),
     "expected_pyomo": ONEW},
    {"description": (
        "The matching must be stable, meaning no man and woman would both rather be with each other "
        "than with their assigned partners. For each woman and man, consider every man she ranks "
        "higher than this one and every woman he ranks higher than this one. At most one of those "
        "more preferred pairings is allowed to be active, so the two of them cannot both have a "
        "partner they like less. When neither of them ranks anyone above the other this requirement "
        "is automatically met and is left out."),
     "expected_pyomo": STABLE},
    {"description": (
        "The total woman preference rank measures how good the matching is for the women overall. "
        "Set the total rank equal to the sum, over every woman and man, of the rank that woman "
        "assigns to that man weighted by whether they are matched together."),
     "expected_pyomo": DEFRANK},
    {"description": (
        "To build the complete model, enforce the following relationships in order. First, each "
        "woman is paired with exactly one man. Second, each man is paired with exactly one woman. "
        "Third, the matching is stable so that no man and woman both prefer each other over their "
        "assigned partners, by allowing at most one of their mutually more preferred pairings to be "
        "active and skipping the requirement when neither ranks anyone above the other. Finally, the "
        "total woman preference rank is set equal to the sum over every couple of the rank the woman "
        "assigns to her partner weighted by whether they are matched."),
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "stablem_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
