#!/usr/bin/env python
"""Builder for the openpit_mip (dynamic open-pit mining) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "openpit_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "p", "members": ["p1", "p2", "p3"],
         "doc": "the set of pits that can be mined"},
        {"name": "s", "members": ["s1", "s2", "s3"],
         "doc": "the set of extraction segments within a pit, listed in the fixed order in which they must be mined; the first member is the topmost segment and each later member lies deeper and can only be reached after the ones above it"},
        {"name": "t", "members": ["t1", "t2", "t3"],
         "doc": "the set of extraction periods in chronological order; the first member is the opening period and each later member follows the one before it"},
    ],
    "params": [
        {"name": "nev", "index": "p,s", "kind": "benefit",
         "doc": "the net extraction benefit earned per unit of material taken from a segment of a pit, in value per unit; it may be negative for segments whose material costs more to handle than it returns"},
        {"name": "evo", "index": "p,s", "kind": "volume",
         "doc": "the total volume of material contained in a segment of a pit, in units; this is the most that can ever be taken from that segment across the whole horizon"},
        {"name": "demand", "index": "t", "kind": "demand",
         "doc": "the product demand that must be met in each period, in units"},
        {"name": "delta", "index": "t", "kind": "discount",
         "doc": "the discount factor applied to value earned in each period, a dimensionless multiplier that weights earlier periods more than later ones"},
    ],
    "vars": [
        {"name": "b", "index": "p,s,t", "domain": "Binary",
         "doc": "equals 1 if a segment of a pit is available to be extracted in a period and 0 otherwise"},
        {"name": "e", "index": "p,s,t", "domain": "Binary",
         "doc": "equals 1 if a segment is the last (deepest) segment whose extraction sequence ends in a period for that pit, and 0 otherwise"},
        {"name": "open", "index": "p,s", "domain": "Binary",
         "doc": "equals 1 if a segment of a pit is ever activated for extraction over the whole horizon, and 0 otherwise"},
        {"name": "ej", "index": "p,t", "domain": "Integers",
         "doc": "the position in the segment ordering of the last segment whose sequence ends in a period for a pit; bounded between 0 and the number of segments"},
        {"name": "out", "index": "p,s,t", "domain": "NonNegativeReals",
         "doc": "the amount of material extracted from a segment of a pit in a period, in units"},
        {"name": "pout", "index": "p,t", "domain": "NonNegativeReals",
         "doc": "the total material output of a pit in a period, in units; bounded above by eighty percent of that period's demand"},
        {"name": "obj_var", "index": "", "domain": "Reals",
         "doc": "the total discounted net income earned over the whole horizon, in value"},
    ],
    "objective": {"sense": "maximize", "expr_var": "obj_var"},
}

NARRATIVE = (
    "We plan how to mine a group of open pits over a sequence of time periods. Each pit is "
    "divided into segments stacked from top to bottom, and the segments of a pit have to be "
    "taken in order from the top down. In every period we decide which segments are available "
    "to extract, how far down the extraction has progressed in each pit, how much material to "
    "take from each segment, and the resulting output of each pit. Material taken from a segment "
    "earns a net benefit per unit that can be positive or negative, and value earned in later "
    "periods is discounted relative to earlier periods. The objective is to maximize the total "
    "discounted net income over the whole horizon."
)

EONE = (
    "def eone_rule(m, p, t):\n"
    "    return sum(m.e[p, s, t] for s in m.s) == 1\n"
    "model.eone = Constraint(model.p, model.t, rule=eone_rule)"
)
ETWO = (
    "def etwo_rule(m, p, t):\n"
    "    s_ord = {ss: i + 1 for i, ss in enumerate(m.s)}\n"
    "    return m.ej[p, t] == sum(s_ord[s] * m.e[p, s, t] for s in m.s)\n"
    "model.etwo = Constraint(model.p, model.t, rule=etwo_rule)"
)
ETHREE = (
    "def ethree_rule(m, p, t):\n"
    "    t_list = list(m.t)\n"
    "    i = t_list.index(t)\n"
    "    if i == len(t_list) - 1:\n"
    "        return Constraint.Skip\n"
    "    return m.ej[p, t] <= m.ej[p, t_list[i + 1]]\n"
    "model.ethree = Constraint(model.p, model.t, rule=ethree_rule)"
)
BRUN = (
    "def brun_rule(m, p, s, t):\n"
    "    s_list = list(m.s); t_list = list(m.t)\n"
    "    si = s_list.index(s); ti = t_list.index(t)\n"
    "    rhs = 0\n"
    "    if si > 0:\n"
    "        rhs += m.b[p, s_list[si - 1], t] - m.e[p, s_list[si - 1], t]\n"
    "    if ti > 0:\n"
    "        rhs += m.e[p, s, t_list[ti - 1]]\n"
    "    if (not ti) and (not si):\n"
    "        rhs += 1\n"
    "    return m.b[p, s, t] == rhs\n"
    "model.brun = Constraint(model.p, model.s, model.t, rule=brun_rule)"
)
DEFPOUT = (
    "def defpout_rule(m, p, t):\n"
    "    return m.pout[p, t] == sum(m.out[p, s, t] for s in m.s)\n"
    "model.defpout = Constraint(model.p, model.t, rule=defpout_rule)"
)
DEM = (
    "def dem_rule(m, t):\n"
    "    return sum(m.pout[p, t] for p in m.p) == m.demand[t]\n"
    "model.dem = Constraint(model.t, rule=dem_rule)"
)
OPENDEF = (
    "def opendef_rule(m, p, s, t):\n"
    "    return m.open[p, s] >= m.b[p, s, t]\n"
    "model.opendef = Constraint(model.p, model.s, model.t, rule=opendef_rule)"
)
OPENLOW = (
    "def openlow_rule(m, p, s):\n"
    "    return m.open[p, s] <= sum(m.b[p, s, t] for t in m.t)\n"
    "model.openlow = Constraint(model.p, model.s, rule=openlow_rule)"
)
OUTLIM = (
    "def outlim_rule(m, p, s, t):\n"
    "    return m.out[p, s, t] <= m.evo[p, s] * m.b[p, s, t]\n"
    "model.outlim = Constraint(model.p, model.s, model.t, rule=outlim_rule)"
)
OUTALL = (
    "def outall_rule(m, p, s):\n"
    "    s_list = list(m.s); si = s_list.index(s)\n"
    "    if si == len(s_list) - 1:\n"
    "        rhs = 0\n"
    "    else:\n"
    "        rhs = m.evo[p, s] * m.open[p, s_list[si + 1]]\n"
    "    return sum(m.out[p, s, t] for t in m.t) >= rhs\n"
    "model.outall = Constraint(model.p, model.s, rule=outall_rule)"
)
OUTMAX = (
    "def outmax_rule(m, p, s):\n"
    "    return sum(m.out[p, s, t] for t in m.t) <= m.evo[p, s] * m.open[p, s]\n"
    "model.outmax = Constraint(model.p, model.s, rule=outmax_rule)"
)
DEFOBJ = (
    "def defobj_rule(m):\n"
    "    return m.obj_var == sum(m.delta[t] * m.nev[p, s] * m.out[p, s, t]\n"
    "                            for p in m.p for s in m.s for t in m.t)\n"
    "model.defobj = Constraint(rule=defobj_rule)"
)

WHOLESET = "\n".join([EONE, ETWO, ETHREE, BRUN, DEFPOUT, DEM, OPENDEF,
                      OPENLOW, OUTLIM, OUTALL, OUTMAX, DEFOBJ])

# (intent, description, expected_pyomo)
ITEMS = [
    ("the extraction sequence of every pit ends in exactly one segment in each period",
     "In every period, each pit's extraction sequence must end at exactly one of its segments. "
     "For each pit and period, exactly one segment is marked as the one where the extraction "
     "sequence ends.",
     EONE),
    ("link the ending position of each pit to which segment its sequence ends at",
     "For each pit and period, record how deep the extraction has reached by tying the ending "
     "position to whichever segment the sequence ends at. The ending position equals the place "
     "of that ending segment in the top-to-bottom ordering of the pit's segments.",
     ETWO),
    ("the ending depth of each pit can only move deeper as time goes on",
     "Within each pit the extraction can only progress downward over time and never move back "
     "up. For each pit, the ending position reached in a period must be at least as deep as the "
     "ending position reached in the period before it.",
     ETHREE),
    ("a segment becomes available in a period only by following its predecessor and the prior period",
     "A segment of a pit becomes available to extract in a period according to how the "
     "extraction has unfolded above it and before it. For each pit, segment, and period, "
     "availability comes from the segment directly above it having been available but not yet "
     "where the sequence ended in that same period, plus that same segment having been where "
     "the sequence ended in the previous period. The topmost segment in the opening period is "
     "available from the start.",
     BRUN),
    ("each pit's total output in a period is the sum of what is taken from its segments",
     "The total output of a pit in a period is built up from what is extracted across its "
     "segments. For each pit and period, the pit's output equals the sum of the material taken "
     "from all of its segments in that period.",
     DEFPOUT),
    ("the combined output of all pits in a period must meet that period's demand",
     "In every period the pits together must supply exactly the required amount. For each "
     "period, the outputs of all pits add up to that period's demand.",
     DEM),
    ("a segment must be activated whenever it is available to extract in any period",
     "A segment of a pit counts as activated whenever it is available to extract in any period. "
     "For each pit, segment, and period, the segment being available in that period forces it "
     "to be marked activated.",
     OPENDEF),
    ("a segment is only activated if it is available in at least one period",
     "A segment of a pit may be marked activated only if it is actually available to extract in "
     "at least one period. For each pit and segment, activation cannot exceed the number of "
     "periods in which the segment is available.",
     OPENLOW),
    ("material can be taken from a segment in a period only when it is available, up to its volume",
     "Material can be taken from a segment in a period only if that segment is available then, "
     "and never more than the volume the segment holds. For each pit, segment, and period, the "
     "amount extracted is at most the segment's total volume when it is available, and is forced "
     "to zero when it is not.",
     OUTLIM),
    ("a segment must be fully mined out before the segment below it can be activated",
     "A segment must be completely mined out before the segment directly below it in the same "
     "pit can be activated. For each pit and segment, the material taken from that segment "
     "across all periods must reach its full volume whenever the next deeper segment is "
     "activated. The deepest segment has nothing below it and so carries no such requirement.",
     OUTALL),
    ("the total taken from a segment over the horizon cannot exceed its volume and is zero unless activated",
     "Over the whole horizon, no more than a segment's volume can be taken from it, and nothing "
     "can be taken unless the segment is activated. For each pit and segment, the material taken "
     "across all periods is at most the segment's volume when it is activated and zero otherwise.",
     OUTMAX),
    ("total discounted net income is the sum over all extractions of discounted per-unit benefit",
     "The total discounted net income accumulates the value of every bit of material extracted, "
     "weighted by its per-unit benefit and discounted by the period in which it is taken. Set "
     "the total income equal to the sum over all pits, segments, and periods of the discount "
     "factor times the per-unit net benefit times the amount extracted.",
     DEFOBJ),
]

# Whole-set ordinal narrative composed from per-constraint intents, in whole-set order.
ordinals = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
            "Eighth", "Ninth", "Tenth", "Eleventh"]
parts = ["To build the complete model, enforce the following relationships in order."]
for i, (intent, _, _) in enumerate(ITEMS):
    lead = ordinals[i] if i < len(ITEMS) - 1 else "Finally"
    parts.append(f"{lead}, {intent}.")
WHOLESET_DESC = " ".join(parts)

records = [{"description": d, "expected_pyomo": e} for (_, d, e) in ITEMS]
records.append({"description": WHOLESET_DESC, "expected_pyomo": WHOLESET})

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "openpit_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
