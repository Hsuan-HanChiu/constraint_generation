#!/usr/bin/env python
"""Builder for the chem_mip (acetone-synthesis feasibility) constraint-gen dataset.
Run with plain python (no special deps) to (re)generate the JSONL.

chem_mip is a pure-feasibility MIP that checks whether a target chemical can be
synthesized from a stock of available chemicals through a fixed library of
reactions. Both native constraints are LINEAR (polynomial_degree 1): the
reactant-presence logic and the raw-material availability fixings.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "chem_mip_constraint_gen.jsonl"

# ---- shared model vocabulary (same components block in every record) ----
COMPONENTS = {
    "sets": [
        {"name": "R", "members": ["01", "02", "03", "...", "22"],
         "doc": "the chemical reactions in the library; each reaction produces one chemical by consuming a group of other chemicals"},
        {"name": "C", "members": ["1", "2", "3", "...", "34"],
         "doc": "the chemicals in the system, numbered from 1 to 34, covering raw materials, catalysts, intermediates, and the target chemical; chemical 6 is the synthesis target"},
        {"name": "RP", "members": ["(01, 4)", "(02, 6)", "...", "(22, 34)"],
         "doc": "the valid reaction and product pairs; each pair names a reaction together with the single chemical that this reaction produces, and for that pair the reaction has a known group of input chemicals it consumes"},
    ],
    "params": [
        {"name": "rm", "index": "R, C, C", "kind": "incidence",
         "doc": "a zero or one flag indexed by reaction, product chemical, and reactant chemical; it is one when the third chemical is one of the inputs the reaction consumes to make the second chemical, and zero otherwise; only the entries that are one are present, all others default to zero"},
    ],
    "vars": [
        {"name": "y", "index": "C", "domain": "Binary",
         "doc": "one if the chemical can be present or produced in the system, zero if it is absent"},
    ],
    "objective": {"sense": "minimize", "expr_var": "y[6]"},
}

NARRATIVE = (
    "We want to verify whether a particular target chemical can be synthesized from "
    "the chemicals we have on hand using a fixed library of reactions. Some chemicals "
    "are available from the start as raw materials or catalysts, and a few others are "
    "known to be unavailable. Each reaction produces one chemical by consuming a group "
    "of other chemicals. For every chemical we decide whether it can be present in the "
    "system. The objective is to make the presence indicator of the target chemical as "
    "small as possible, which reveals whether that target can be produced at all."
)

# Availability data (constants of the material_cons constraint, embedded as literals
# because the stripped base carries no model-side record of availability).
AVAIL = [2, 3, 5, 10, 12, 13, 17, 22, 25, 26, 28, 31, 33]
UNAVAIL = [16, 19]

# ---- ground-truth Pyomo (self-contained over model.* only) ----
# reaction_cons: for each reaction-product pair, if the product is to be present then
# at least one of the reactants the reaction consumes must be absent is NOT the logic;
# rather, the product can be present only if every required reactant is present.
# Native algebra: (1 - y[prod]) <= sum_react rm[r,prod,react] * (1 - y[react]).
# Re-derive the reactant group in-rule from model.rm (default 0), iterating model.C,
# and Skip pairs with no rm entry so the index matches the native (R, C) rule.
REACTION_CONS = (
    "def reaction_cons_rule(model, r, prod):\n"
    "    if any((r, prod, react) in model.rm for react in model.C):\n"
    "        return sum(model.rm[r, prod, react] * (1 - model.y[react]) for react in model.C if (r, prod, react) in model.rm) >= (1 - model.y[prod])\n"
    "    return Constraint.Skip\n"
    "model.reaction_cons = Constraint(model.R, model.C, rule=reaction_cons_rule)"
)

# material_cons: fix the presence of every chemical whose availability is known. The
# available chemicals are forced present and the unavailable chemicals are forced
# absent; every other chemical is left free (Skip).
MATERIAL_CONS = (
    f"_avail = {AVAIL}\n"
    f"_unavail = {UNAVAIL}\n"
    "def material_cons_rule(model, c):\n"
    "    if c in _avail:\n"
    "        return model.y[c] == 1\n"
    "    elif c in _unavail:\n"
    "        return model.y[c] == 0\n"
    "    return Constraint.Skip\n"
    "model.material_cons = Constraint(model.C, rule=material_cons_rule)"
)

WHOLESET = "\n".join([REACTION_CONS, MATERIAL_CONS])

records = [
    {
        "description": (
            "For each reaction paired with the chemical it produces, that chemical can "
            "be present only when the reaction has its inputs in hand. Require that "
            "whenever the produced chemical is present, the reaction must be able to draw "
            "on its required input chemicals being present as well, so that the produced "
            "chemical cannot be present unless the inputs this reaction consumes to make "
            "it are present. Reactions that do not produce a given chemical place no "
            "requirement for that pairing."
        ),
        "expected_pyomo": REACTION_CONS,
    },
    {
        "description": (
            "Pin down the chemicals whose availability is already settled. Every chemical "
            "that is available on hand from the start must be present in the system, and "
            "every chemical that is known to be unavailable must be absent. Chemicals "
            "whose availability is not predetermined are left free to be decided by the "
            "rest of the model."
        ),
        "expected_pyomo": MATERIAL_CONS,
    },
    {
        "description": "Generate the complete constraint set for this model.",
        "expected_pyomo": WHOLESET,
    },
]

with open(OUT, "w") as f:
    for r in records:
        rec = {
            "problem_id": "chem_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {OUT} ({len(records)} records)")
