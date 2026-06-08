#!/usr/bin/env python
"""Builder for the clad_mip (censored least absolute deviations) constraint-generation dataset."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "clad_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "T", "members": ["h1", "h2", "h3"],
         "doc": "the sample households (observations) in the survey, one index per record"},
        {"name": "p", "members": ["rateMar", "Age", "YearsMa", "Intcpt"],
         "doc": "the explanatory variables (regressors) of the linear predictor, including an intercept term"},
    ],
    "params": [
        {"name": "Xnms", "index": "T,p", "kind": "design-matrix",
         "doc": "the normalized design matrix giving the value of each regressor for each household; columns are mean and variance normalized"},
        {"name": "ynms", "index": "T", "kind": "response",
         "doc": "the normalized left-censored dependent variable (observed response) for each household"},
        {"name": "omega", "index": "T", "kind": "big-M",
         "doc": "a tight valid big-M coefficient per household, used to switch the two sides of the max disjunction on or off; nonnegative"},
        {"name": "RHS", "index": "", "kind": "threshold",
         "doc": "the normalized censoring threshold below which the response is censored; the floor value of the max"},
        {"name": "delta", "index": "", "kind": "bound",
         "doc": "the box domain half-width allowed for each estimated coefficient; nonnegative"},
    ],
    "vars": [
        {"name": "beta", "index": "p", "domain": "Reals",
         "doc": "the estimated regression coefficient for each explanatory variable; unrestricted in sign"},
        {"name": "phi", "index": "T", "domain": "Reals",
         "doc": "for each household the value of the linear predictor passed through a max against the censoring threshold, that is the larger of the linear predictor and the threshold"},
        {"name": "gamma", "index": "T", "domain": "Binary",
         "doc": "a per-household binary selector that picks which branch of the max disjunction is active for that household"},
        {"name": "sm", "index": "T", "domain": "NonNegativeReals",
         "doc": "the negative-side slack capturing the part of the residual where the prediction exceeds the response"},
        {"name": "sp", "index": "T", "domain": "NonNegativeReals",
         "doc": "the positive-side surplus capturing the part of the residual where the response exceeds the prediction"},
    ],
    "objective": {"sense": "minimize", "expr_var": "obj"},
}

NARRATIVE = (
    "We fit a censored least-absolute-deviations regression to a sample of households. We choose a "
    "regression coefficient for each explanatory variable, and for each household we track the fitted "
    "censored prediction together with the positive and negative pieces of its residual against the "
    "observed response. The objective is to make the total absolute deviation as small as possible, "
    "minimizing the sum over all households of both the positive and the negative residual pieces."
)

CON_PHI_A = (
    "def con_phi_a_rule(model, t):\n"
    "    return model.phi[t] >= sum(model.beta[pp] * model.Xnms[t, pp] for pp in model.p)\n"
    "model.con_phi_a = Constraint(model.T, rule=con_phi_a_rule)"
)
CON_PHI_B = (
    "def con_phi_b_rule(model, t):\n"
    "    return model.phi[t] >= model.RHS\n"
    "model.con_phi_b = Constraint(model.T, rule=con_phi_b_rule)"
)
CON_PHI_C = (
    "def con_phi_c_rule(model, t):\n"
    "    return model.phi[t] <= sum(model.beta[pp] * model.Xnms[t, pp] for pp in model.p) + model.omega[t] * (1 - model.gamma[t])\n"
    "model.con_phi_c = Constraint(model.T, rule=con_phi_c_rule)"
)
CON_PHI_D = (
    "def con_phi_d_rule(model, t):\n"
    "    return model.phi[t] <= model.RHS + model.omega[t] * model.gamma[t]\n"
    "model.con_phi_d = Constraint(model.T, rule=con_phi_d_rule)"
)
CON_S = (
    "def con_s_rule(model, t):\n"
    "    return model.ynms[t] - model.phi[t] + model.sm[t] - model.sp[t] == 0\n"
    "model.con_s = Constraint(model.T, rule=con_s_rule)"
)
WHOLESET = "\n".join([CON_PHI_A, CON_PHI_B, CON_PHI_C, CON_PHI_D, CON_S])

DESC_A = (
    "For each household the censored prediction must be at least as large as that household's linear "
    "predictor, which is the sum across all explanatory variables of the regression coefficient times "
    "the household's value of that variable."
)
DESC_B = (
    "For each household the censored prediction must be at least the censoring threshold, so the "
    "prediction never falls below the floor set by that threshold."
)
DESC_C = (
    "For each household the censored prediction must not exceed its linear predictor unless the branch "
    "selector for that household turns this side off. When the selector is set so this branch is "
    "active, the prediction is capped at the linear predictor; when the selector is set the other way, "
    "the big-M allowance for that household relaxes the cap so it does not bind."
)
DESC_D = (
    "For each household the censored prediction must not exceed the censoring threshold unless the "
    "branch selector for that household turns this side off. When the selector is set so this branch is "
    "active, the prediction is capped at the threshold; when the selector is set the other way, the "
    "big-M allowance for that household relaxes the cap so it does not bind."
)
DESC_S = (
    "For each household the observed response must equal the censored prediction adjusted by the two "
    "residual pieces, so the response minus the prediction plus the negative-side slack minus the "
    "positive-side surplus comes out to zero."
)

WHOLESET_DESC = (
    "To build the complete model, enforce the following relationships in order. "
    "First, " + DESC_A[0].lower() + DESC_A[1:] + " "
    "Second, " + DESC_B[0].lower() + DESC_B[1:] + " "
    "Third, " + DESC_C[0].lower() + DESC_C[1:] + " "
    "Fourth, " + DESC_D[0].lower() + DESC_D[1:] + " "
    "Finally, " + DESC_S[0].lower() + DESC_S[1:]
)

records = [
    {"description": DESC_A, "expected_pyomo": CON_PHI_A},
    {"description": DESC_B, "expected_pyomo": CON_PHI_B},
    {"description": DESC_C, "expected_pyomo": CON_PHI_C},
    {"description": DESC_D, "expected_pyomo": CON_PHI_D},
    {"description": DESC_S, "expected_pyomo": CON_S},
    {"description": WHOLESET_DESC, "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "clad_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
