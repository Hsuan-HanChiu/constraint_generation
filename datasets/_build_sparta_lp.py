#!/usr/bin/env python
"""Builder for the sparta_lp (military manpower planning) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "sparta_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "t", "members": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
         "doc": "the planning years in chronological order, numbered consecutively from one; year one is the first year of the horizon and each later year follows the one before it"},
        {"name": "l", "members": [1, 2, 3, 4],
         "doc": "the available lengths of enlistment, measured in whole years; a recruit signed under a given length serves for exactly that many years starting in the year of recruitment and then leaves"},
    ],
    "params": [
        {"name": "infl", "index": "t", "kind": "index",
         "doc": "the inflation index applied to costs in each year, a unitless multiplier that scales the base cost of service in that year"},
        {"name": "req", "index": "t", "kind": "requirement",
         "doc": "the minimum number of enlisted men required to be on duty in each year, in men"},
        {"name": "clen", "index": "l", "kind": "cost",
         "doc": "the base cost of service for a recruit by enlistment length, in dollars per recruit, before applying the year's inflation index"},
    ],
    "vars": [
        {"name": "x", "index": "t,l", "domain": "NonNegativeReals",
         "doc": "the number of recruits taken on in a given year under a given enlistment length"},
        {"name": "e", "index": "t", "domain": "NonNegativeReals",
         "doc": "the number of enlisted men on duty in a given year"},
        {"name": "z", "index": "", "domain": "NonNegativeReals",
         "doc": "the total cost over the whole horizon, in dollars"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We plan military recruitment over a sequence of years. Each year we decide how many "
    "recruits to take on under each available length of enlistment, which in turn determines "
    "how many enlisted men are on duty in each year. Recruits cost money to service, with the "
    "cost depending on the length of enlistment and scaled by that year's inflation index. The "
    "objective is to make the total cost over the whole horizon as small as possible."
)

COST_DEF = (
    "def cost_def_rule(model):\n"
    "    return model.z == sum(model.infl[i] * model.clen[j] * model.x[i, j] for i in model.t for j in model.l)\n"
    "model.cost_def = Constraint(rule=cost_def_rule)"
)
BAL = (
    "def bal_rule(model, i):\n"
    "    return model.e[i] == (model.e[i-1] if i > 1 else 0) + sum(model.x[i, j] - (model.x[i-j, j] if i > j else 0) for j in model.l)\n"
    "model.bal = Constraint(model.t, rule=bal_rule)"
)
MIN_REQ = (
    "def min_req_rule(model, i):\n"
    "    return model.e[i] >= model.req[i]\n"
    "model.min_req = Constraint(model.t, rule=min_req_rule)"
)
WHOLESET = "\n".join([COST_DEF, BAL, MIN_REQ])

records = [
    {"description": (
        "The total cost gathers the servicing cost of every recruit taken on across the whole horizon. "
        "For each year and each length of enlistment, take the number of recruits taken on that year under "
        "that length, value them at the base cost of service for that length, and scale by that year's "
        "inflation index. Set the total cost equal to the sum of these amounts over all years and all "
        "enlistment lengths."),
     "expected_pyomo": COST_DEF},
    {"description": (
        "The number of enlisted men on duty in each year must account for who carries over from the year "
        "before and the recruits arriving and departing that year. For each year, the men on duty equal "
        "the men on duty in the immediately preceding year, plus everyone newly recruited that year across "
        "all enlistment lengths, minus everyone whose service ends that year because the length of their "
        "enlistment has fully elapsed since they were recruited. In the very first year there is nobody "
        "carried over from before, and no one can have departed yet."),
     "expected_pyomo": BAL},
    {"description": (
        "Each year must field enough men to meet the demand for that year. For each year, the number of "
        "enlisted men on duty must be at least the minimum troop requirement for that year."),
     "expected_pyomo": MIN_REQ},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "sparta_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
