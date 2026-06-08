#!/usr/bin/env python
"""Builder for the port_lp (bond portfolio) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "port_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "b", "members": ["municip-a", "municip-b", "corporate", "us-ser-e", "us-ser-f"],
         "doc": "the available bonds that can be invested in"},
        {"name": "g", "members": ["corporate", "us-ser-e", "us-ser-f"],
         "doc": "a designated subset of the bonds forming a group that carries a minimum-investment requirement"},
    ],
    "params": [
        {"name": "rating", "index": "b", "kind": "quality",
         "doc": "the credit rating score of each bond, where a lower number is a safer bond"},
        {"name": "maturity", "index": "b", "kind": "duration",
         "doc": "the maturity of each bond in years"},
        {"name": "yld", "index": "b", "kind": "return",
         "doc": "the gross yield of each bond stated as a percentage, so a value of 5 means five percent"},
        {"name": "taxrate", "index": "b", "kind": "rate",
         "doc": "the fraction of each bond's yield that is lost to tax, between zero and one"},
    ],
    "vars": [
        {"name": "investment", "index": "b", "domain": "NonNegativeReals",
         "doc": "the amount invested in each bond"},
        {"name": "tinvest", "index": "", "domain": "NonNegativeReals",
         "doc": "the total amount invested across all bonds, bounded between zero and ten"},
        {"name": "ret", "index": "", "domain": "Reals",
         "doc": "the total after-tax return of the portfolio"},
    ],
    "objective": {"sense": "maximize", "expr_var": "ret"},
}

NARRATIVE = (
    "We are choosing how to allocate money across a set of available bonds. For each bond "
    "we decide how much to invest, and we also track the total amount invested and the "
    "portfolio's total after-tax return. Each bond has its own credit rating, maturity, "
    "gross yield, and tax rate. The objective is to maximize the total after-tax return "
    "of the portfolio."
)

GROUPMIN = (
    "def groupmin_rule(model):\n"
    "    return sum(model.investment[g] for g in model.g) >= 4\n"
    "model.groupmin = Constraint(rule=groupmin_rule)"
)
RDEF = (
    "def rdef_rule(model):\n"
    "    return sum(model.rating[b] * model.investment[b] for b in model.b) <= 1.4 * model.tinvest\n"
    "model.rdef = Constraint(rule=rdef_rule)"
)
MDEF = (
    "def mdef_rule(model):\n"
    "    return sum(model.maturity[b] * model.investment[b] for b in model.b) <= 5.0 * model.tinvest\n"
    "model.mdef = Constraint(rule=mdef_rule)"
)
TDEF = (
    "def tdef_rule(model):\n"
    "    return model.tinvest == sum(model.investment[b] for b in model.b)\n"
    "model.tdef = Constraint(rule=tdef_rule)"
)
IDEF = (
    "def idef_rule(model):\n"
    "    return model.ret == sum(model.yld[b] / 100 * (1 - model.taxrate[b]) * model.investment[b] for b in model.b)\n"
    "model.idef = Constraint(rule=idef_rule)"
)

WHOLESET = "\n".join([GROUPMIN, RDEF, MDEF, TDEF, IDEF])

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, the combined amount invested in the bonds belonging to the designated group "
    "must reach at least a required minimum level. "
    "Second, the rating-weighted total of the bond investments must not exceed the total "
    "amount invested scaled by the maximum allowable average rating. "
    "Third, the maturity-weighted total of the bond investments must not exceed the total "
    "amount invested scaled by the maximum allowable average maturity. "
    "Fourth, the total amount invested must equal the sum of the amounts invested across "
    "all bonds. "
    "Finally, the portfolio's total after-tax return must equal the sum over all bonds of "
    "each bond's investment multiplied by its yield after converting the yield from a "
    "percentage and after removing the portion lost to tax."
)

records = [
    {"description": (
        "The bonds in the designated group must together receive a sufficient allocation. "
        "The combined amount invested across the bonds in that group must be at least the "
        "required minimum level."),
     "expected_pyomo": GROUPMIN},
    {"description": (
        "The portfolio must not be too risky on average. Weighting each bond's investment by "
        "its credit rating and adding these up, the total must not exceed the total amount "
        "invested scaled by the highest average rating the portfolio is allowed to carry."),
     "expected_pyomo": RDEF},
    {"description": (
        "The portfolio must not be too long-dated on average. Weighting each bond's investment "
        "by its maturity and adding these up, the total must not exceed the total amount invested "
        "scaled by the longest average maturity the portfolio is allowed to carry."),
     "expected_pyomo": MDEF},
    {"description": (
        "The total amount invested must be consistent with the individual allocations. The total "
        "investment equals the sum of the amounts invested across all bonds."),
     "expected_pyomo": TDEF},
    {"description": (
        "The total after-tax return must be consistent with the individual allocations. For each "
        "bond, take the amount invested, apply the bond's yield expressed as a percentage, and "
        "keep only the portion that survives tax. The total after-tax return equals the sum of "
        "these amounts across all bonds."),
     "expected_pyomo": IDEF},
    {"description": WHOLESET_DESC,
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "port_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
