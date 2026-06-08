#!/usr/bin/env python
"""Builder for the qp5_lp constraint-generation dataset.

qp5 is the linear approximation of a mean-absolute-deviation portfolio model.
Despite the "qp" name, GAMS solves it 'using lp': all four constraints are
linear (degree 1) and Z3-gradable. The objective minimizes the absolute-
deviation variable. All four constraints are included; nothing is excluded.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "qp5_lp_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "s", "members": ["GAB", "GAP", "GDW", "...", "AMD", "AMER"],
         "doc": "the candidate stocks that can be held in the portfolio"},
        {"name": "d", "members": ["D951128", "D951129", "...", "D960109"],
         "doc": "the historical trading days over which returns are observed"},
    ],
    "params": [
        {"name": "mean", "index": "s", "kind": "return",
         "doc": "the mean daily return of each stock over the observation window, as a fractional return"},
        {"name": "dev", "index": "s,d", "kind": "deviation",
         "doc": "the deviation of a stock's return on a given day from that stock's own mean return, as a fractional return"},
        {"name": "totmean", "index": "", "kind": "return",
         "doc": "the overall average mean return across the candidate stocks, as a fractional return; it is negative for this data"},
    ],
    "vars": [
        {"name": "x", "index": "s", "domain": "NonNegativeReals",
         "doc": "the portfolio weight allocated to each stock, as a fraction of the total budget"},
        {"name": "wplus", "index": "d", "domain": "NonNegativeReals",
         "doc": "the positive part of the portfolio return deviation on each day"},
        {"name": "wmin", "index": "d", "domain": "NonNegativeReals",
         "doc": "the negative part of the portfolio return deviation on each day"},
        {"name": "z", "index": "", "domain": "Reals",
         "doc": "the total absolute deviation of the portfolio return summed over all days"},
    ],
    "objective": {"sense": "minimize", "expr_var": "z"},
}

NARRATIVE = (
    "We are choosing how to spread an investment budget across a set of candidate "
    "stocks, with the weight on each stock to be decided. We have historical daily "
    "returns for every stock over a window of trading days, along with each stock's "
    "average return. We want a portfolio whose day-to-day return stays as close as "
    "possible to its own average, so the goal is to minimize the total absolute "
    "deviation of the portfolio return across all the observed days."
)

WDEF = (
    "def wdef_rule(model, dd):\n"
    "    return model.wplus[dd] - model.wmin[dd] == sum(model.dev[ss, dd] * model.x[ss] for ss in model.s)\n"
    "model.wdef = Constraint(model.d, rule=wdef_rule)"
)
BUDGET = (
    "model.budget = Constraint(expr=sum(model.x[ss] for ss in model.s) == 1.0)"
)
RETCON = (
    "model.retcon = Constraint(expr=sum(model.mean[ss] * model.x[ss] for ss in model.s) >= model.totmean * 1.25)"
)
ZDEF = (
    "model.zdef = Constraint(expr=model.z == sum(model.wplus[dd] + model.wmin[dd] for dd in model.d))"
)
WHOLESET = "\n".join([WDEF, BUDGET, RETCON, ZDEF])

WDEF_DESC = (
    "For each observed day, the portfolio's return deviation that day is split into a "
    "positive part and a negative part. The positive part minus the negative part must "
    "equal the portfolio's overall deviation on that day, which is obtained by combining "
    "each stock's deviation from its own mean on that day weighted by how much of the "
    "budget is placed in that stock."
)
BUDGET_DESC = (
    "The entire budget must be fully allocated. The portfolio weights across all the "
    "candidate stocks must add up to one."
)
RETCON_DESC = (
    "The portfolio must achieve a minimum level of expected return. The budget-weighted "
    "average of the stocks' mean returns must be at least one and a quarter times the "
    "overall average mean return."
)
ZDEF_DESC = (
    "The total absolute deviation of the portfolio is the running total of its daily "
    "deviation magnitudes. It must equal the sum, over every observed day, of that day's "
    "positive deviation part plus its negative deviation part."
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, for each observed day, split that day's portfolio return deviation into a "
    "positive part and a negative part whose difference equals the budget-weighted "
    "combination of each stock's deviation from its own mean on that day. "
    "Second, require the portfolio weights across all candidate stocks to add up to one "
    "so the whole budget is allocated. "
    "Third, require the budget-weighted average of the stocks' mean returns to be at "
    "least one and a quarter times the overall average mean return. "
    "Finally, set the total absolute deviation equal to the sum over all observed days "
    "of each day's positive and negative deviation parts."
)

records = [
    {"description": WDEF_DESC, "expected_pyomo": WDEF},
    {"description": BUDGET_DESC, "expected_pyomo": BUDGET},
    {"description": RETCON_DESC, "expected_pyomo": RETCON},
    {"description": ZDEF_DESC, "expected_pyomo": ZDEF},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "qp5_lp",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
