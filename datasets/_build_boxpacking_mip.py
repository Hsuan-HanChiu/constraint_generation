#!/usr/bin/env python
"""Builder for the boxpacking_mip (3D container packing) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "boxpacking_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "b", "members": ["b1", "b2", "b3"],
         "doc": "the boxes available to be packed into the container"},
        {"name": "o", "members": ["o1", "o2", "o3", "o4", "o5", "o6"],
         "doc": "the six possible orientations in which a box can be rotated, each one a different assignment of the box's three side lengths to the x, y and z axes"},
        {"name": "d", "members": ["x", "y", "z"],
         "doc": "the three spatial axes of the container"},
        {"name": "bo", "members": [["b1", "o1"], ["b1", "o4"], ["b2", "o1"], ["b2", "o3"], ["b3", "o1"]],
         "doc": "the box-orientation pairs that are actually allowed; a box may only be rotated into one of the orientations listed for it here, and orientations not listed for a box are unavailable to that box"},
    ],
    "params": [
        {"name": "dim_o", "index": "b,o,d", "kind": "dimension",
         "doc": "the side length a box would occupy along each axis if it were placed in a given orientation, in centimetres"},
        {"name": "box_vol", "index": "b", "kind": "volume",
         "doc": "the volume of each box, in cubic metres"},
        {"name": "dim_cont", "index": "d", "kind": "dimension",
         "doc": "the interior length of the container along each axis, in centimetres"},
    ],
    "vars": [
        {"name": "OMEGA", "index": "b", "domain": "Binary",
         "doc": "placement indicator for a box; 1 if the box is placed inside the container and 0 if it is left out"},
        {"name": "ALPHA", "index": "bo", "domain": "Binary",
         "doc": "orientation-selection indicator defined only over the allowed box-orientation pairs; 1 if the box is placed in that orientation and 0 otherwise"},
        {"name": "RELPOS", "index": "b,b,d", "domain": "Binary",
         "doc": "relative-position indicator for an ordered pair of boxes along an axis; 1 if the first box is positioned before the second box along that axis, meaning the first box's far edge along that axis is at or below the second box's near edge"},
        {"name": "LOC", "index": "b,d", "domain": "NonNegativeReals",
         "doc": "the coordinate of the near corner of a box along each axis, in centimetres, measured from the container origin"},
        {"name": "DIM", "index": "b,d", "domain": "NonNegativeReals",
         "doc": "the realized side length a box occupies along each axis once its orientation is chosen, in centimetres"},
        {"name": "VOL", "index": "", "domain": "Reals",
         "doc": "the total volume of all boxes placed in the container, in cubic metres"},
    ],
    "objective": {"sense": "maximize", "expr_var": "VOL"},
}

NARRATIVE = (
    "We are loading boxes into a single rectangular container. For each box we decide "
    "whether to place it in the container at all, and if we do, which orientation to "
    "rotate it into and where to position it along each axis. The goal is to make the "
    "total volume of the boxes we manage to fit into the container as large as possible."
)

DEF_DIM = (
    "def eq_def_DIM_rule(model, b, d):\n"
    "    return model.DIM[b, d] == sum(model.dim_o[b, o, d] * model.ALPHA[b, o] for o in model.o if (b, o) in model.bo)\n"
    "model.eq_def_DIM = Constraint(model.b, model.d, rule=eq_def_DIM_rule)"
)
COUPLE = (
    "def eq_couple_ALPHA_OMEGA_rule(model, b):\n"
    "    return sum(model.ALPHA[b, o] for o in model.o if (b, o) in model.bo) == model.OMEGA[b]\n"
    "model.eq_couple_ALPHA_OMEGA = Constraint(model.b, rule=eq_couple_ALPHA_OMEGA_rule)"
)
INSIDE = (
    "def eq_inside_container_rule(model, b, d):\n"
    "    return model.LOC[b, d] + model.DIM[b, d] <= model.dim_cont[d] * model.OMEGA[b]\n"
    "model.eq_inside_container = Constraint(model.b, model.d, rule=eq_inside_container_rule)"
)
DEACTIVATE = (
    "def eq_deactivate_RELPOS_rule(model, b1, b2, d):\n"
    "    if model.b.ord(b1) >= model.b.ord(b2):\n"
    "        return Constraint.Skip\n"
    "    return model.RELPOS[b1, b2, d] + model.RELPOS[b2, b1, d] <= model.OMEGA[b1]\n"
    "model.eq_deactivate_RELPOS = Constraint(model.b, model.b, model.d, rule=eq_deactivate_RELPOS_rule)"
)
DEF_RELPOS = (
    "def eq_def_RELPOS_rule(model, b1, b2):\n"
    "    if model.b.ord(b1) < model.b.ord(b2):\n"
    "        return sum(model.RELPOS[b1, b2, d] + model.RELPOS[b2, b1, d] for d in model.d) >= model.OMEGA[b1] + model.OMEGA[b2] - 1\n"
    "    return Constraint.Skip\n"
    "model.eq_def_RELPOS = Constraint(model.b, model.b, rule=eq_def_RELPOS_rule)"
)
NO_OVERLAP = (
    "def eq_no_overlap_rule(model, b1, b2, d):\n"
    "    if b1 == b2:\n"
    "        return Constraint.Skip\n"
    "    return model.LOC[b1, d] + model.DIM[b1, d] <= model.LOC[b2, d] + model.dim_cont[d] * (1 - model.RELPOS[b1, b2, d])\n"
    "model.eq_no_overlap = Constraint(model.b, model.b, model.d, rule=eq_no_overlap_rule)"
)
DEF_VOL = (
    "def eq_def_VOL_rule(model):\n"
    "    return model.VOL == sum(model.box_vol[b] * model.OMEGA[b] for b in model.b)\n"
    "model.eq_def_VOL = Constraint(rule=eq_def_VOL_rule)"
)
WHOLESET = "\n".join([DEF_DIM, COUPLE, INSIDE, DEACTIVATE, DEF_RELPOS, NO_OVERLAP, DEF_VOL])

per = [
    {"description": (
        "For each box and each axis, the side length the box takes up along that axis "
        "must match the side length it would have in whichever orientation was chosen for "
        "it. Only the orientations that are allowed for that box can contribute, and exactly "
        "the one that is selected determines the side length along that axis."),
     "intent": "tie each box's realized side length along every axis to the side length implied by its chosen orientation",
     "expected_pyomo": DEF_DIM},
    {"description": (
        "For each box, an orientation is chosen exactly when the box is placed in the "
        "container. If the box is placed, precisely one of its allowed orientations must be "
        "selected, and if the box is left out, none of its orientations may be selected."),
     "intent": "select exactly one allowed orientation for a box if and only if that box is placed",
     "expected_pyomo": COUPLE},
    {"description": (
        "For each box and each axis, a placed box must lie entirely within the container "
        "along that axis, so its near corner plus the side length it occupies cannot reach "
        "beyond the container's interior length on that axis. A box that is not placed takes "
        "up no room along any axis."),
     "intent": "keep every placed box fully inside the container along each axis",
     "expected_pyomo": INSIDE},
    {"description": (
        "For each unordered pair of distinct boxes and each axis, at most one of the two "
        "boxes can be positioned before the other along that axis, and only when the boxes "
        "are actually placed. If a box is left out, no relative-position relationship along "
        "any axis may be active for the pairs it belongs to."),
     "intent": "allow a relative-position relationship along an axis for a pair only when the boxes are placed, and never in both directions at once",
     "expected_pyomo": DEACTIVATE},
    {"description": (
        "For each unordered pair of distinct boxes, whenever both boxes are placed in the "
        "container they must be separated along at least one axis, with one box positioned "
        "before the other on that axis. If at most one of the two is placed, no such "
        "separation is required."),
     "intent": "force any two placed boxes to be separated along at least one axis",
     "expected_pyomo": DEF_RELPOS},
    {"description": (
        "For each ordered pair of distinct boxes and each axis, if the first box is "
        "positioned before the second along that axis then the first box must finish before "
        "the second begins, so the first box's near corner plus its side length on that axis "
        "cannot exceed the second box's near corner. When the first box is not positioned "
        "before the second along that axis the requirement is relaxed and does not bind."),
     "intent": "prevent two boxes from overlapping by enforcing the gap along whichever axis separates them",
     "expected_pyomo": NO_OVERLAP},
    {"description": (
        "The total packed volume equals the combined volume of every box that is placed in "
        "the container, counting each placed box's own volume and ignoring boxes left out."),
     "intent": "accumulate the total packed volume as the sum of the volumes of the placed boxes",
     "expected_pyomo": DEF_VOL},
]

ordinals = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Finally"]
parts = [f"{ordinals[i]}, {per[i]['intent']}." for i in range(len(per))]
WHOLESET_DESC = ("To build the complete model, enforce the following relationships in order. "
                 + " ".join(parts))

records = [{"description": r["description"], "expected_pyomo": r["expected_pyomo"]} for r in per]
records.append({"description": WHOLESET_DESC, "expected_pyomo": WHOLESET})

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "boxpacking_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
