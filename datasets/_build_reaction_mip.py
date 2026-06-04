#!/usr/bin/env python
"""Builder for the reaction_mip (logical reaction-path synthesis) constraint-gen dataset.
Run with plain python (no special deps) to (re)generate the JSONL."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "reaction_mip_constraint_gen.jsonl"

# ---- shared model vocabulary (same components block in every record) ----
COMPONENTS = {
    "sets": [
        {"name": "v", "members": ["y01", "y02", "y03", "..."],
         "doc": "all chemicals in the system, including raw materials, catalysts, intermediates, and the final target chemical"},
        {"name": "rx", "members": ["rxn01", "rxn02", "..."],
         "doc": "the chemical reactions, each of which can produce one chemical from a group of other chemicals"},
        {"name": "yavail", "members": ["y02", "y03", "..."],
         "doc": "the chemicals that are available on hand from the start, namely the raw materials and catalysts we already possess; each of these is forced to be present"},
        {"name": "ynotavail", "members": ["y16", "y19"],
         "doc": "the chemicals that are not available and cannot be obtained; each of these is forced to be absent"},
        {"name": "rxv", "index": "rx,v",
         "doc": "the pairs of a reaction and the chemical that this reaction produces; for each such pair the reaction has a known group of input chemicals that it consumes"},
    ],
    "params": [
        {"name": "logicc", "index": "rx,v,v", "kind": "incidence",
         "doc": "a zero or one flag that is one when the chemical in the third position is one of the input chemicals consumed by the reaction in the first position to make the chemical in the second position, and zero otherwise"},
    ],
    "vars": [
        {"name": "y", "index": "v", "domain": "Binary",
         "doc": "1 if the chemical can be present or produced in the system, 0 if it is absent. Available chemicals are fixed to 1 and unavailable chemicals are fixed to 0"},
        {"name": "totsum", "index": "", "domain": "Reals",
         "doc": "presence indicator of the target chemical, used as the objective value; it equals 1 when the target chemical can be produced and 0 otherwise"},
    ],
    "objective": {"sense": "minimize", "expr_var": "totsum"},
}

NARRATIVE = (
    "We are studying a network of chemical reactions. Some chemicals are available "
    "from the start as raw materials or catalysts, and others are not available at "
    "all. Each reaction can produce one chemical by consuming a group of other "
    "chemicals. We decide for every chemical whether it can be present in the system "
    "or not. The objective is to make the presence indicator of one particular "
    "target chemical as small as possible, which tells us whether that target "
    "chemical can be produced at all."
)

# ---- ground-truth Pyomo (self-contained over model.* only) ----
# leq: for each (rx, v) producible pair, if every input chemical of that reaction is
# present then the produced chemical may be present. Equivalently the number of absent
# inputs is at least the absence of the product. Re-derive the input group in-rule from
# model.logicc (default 0), iterating over model.v.
LEQ = (
    "def leq_rule(model, rx, v):\n"
    "    return sum(1 - model.y[vv] for vv in model.v if value(model.logicc[rx, v, vv]) > 0) >= 1 - model.y[v]\n"
    "model.leq = Constraint(model.rxv, rule=leq_rule)"
)

# totsum_con: define the objective variable as the presence indicator of the target
# chemical. The target is the fixed chemical y06 for this instance.
TOTSUM = (
    "def totsum_rule(model):\n"
    "    return model.totsum == model.y['y06']\n"
    "model.totsum_con = Constraint(rule=totsum_rule)"
)

WHOLESET = "\n".join([LEQ, TOTSUM])

records = [
    {
        "description": (
            "For each reaction together with a chemical it can produce, the reaction "
            "can only make that chemical when all of the input chemicals it consumes "
            "are present. State this as a requirement that the produced chemical may "
            "be present only if every one of the inputs that the reaction uses to make "
            "it is also present."
        ),
        "expected_pyomo": LEQ,
    },
    {
        "description": (
            "Tie the objective value to whether the target chemical can be produced. "
            "Set the objective value equal to the presence indicator of the target "
            "chemical."
        ),
        "expected_pyomo": TOTSUM,
    },
    {
        "description": "Generate the complete constraint set for this model.",
        "expected_pyomo": WHOLESET,
    },
]

with open(OUT, "w") as f:
    for r in records:
        rec = {
            "problem_id": "reaction_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {OUT} ({len(records)} records)")
