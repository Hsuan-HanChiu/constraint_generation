#!/usr/bin/env python
"""Builder for the mws_mip (maximum weighted score mode-choice estimator) constraint-generation dataset.

mws_mip is flagged nonlinear, but BOTH of its constraints are linear in the decision
variables: y, Xnms and omega are all precomputed parameters, so beta*Xnms and
omega*(1-z) are linear. Both constraints are therefore included.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "mws_mip_constraint_gen.jsonl"

COMPONENTS = {
    "sets": [
        {"name": "p", "members": ["DCOST", "CARS", "DOVTT", "DIVTT", "INTCPT"],
         "doc": "the explanatory variables of the mode-choice model; each member names one feature whose coefficient is being estimated, with INTCPT acting as the intercept term"},
        {"name": "T", "members": [1, 2, 3, 4],
         "doc": "the set of sampled households (observations), indexed by integers; each member is one observation in the estimation sample"},
    ],
    "params": [
        {"name": "y", "index": "T", "kind": "data",
         "doc": "the binary observed outcome for each household, taking value 1 or 0; it records which choice the household actually made and is the target the fitted score is supposed to agree with in sign"},
        {"name": "Xnms", "index": "T,p", "kind": "data",
         "doc": "the standardized value of each explanatory variable for each household; the raw feature values are centered and scaled before use, so these are fixed real numbers known in advance"},
        {"name": "omega", "index": "T", "kind": "big-M",
         "doc": "a per-household large constant used to switch off the sign-agreement requirement when its indicator is zero; each value is large enough that when the indicator is off the requirement is trivially satisfied for that household"},
        {"name": "delta", "index": "", "kind": "bound",
         "doc": "a single positive constant that bounds the magnitude of every estimated coefficient; each coefficient is constrained to lie between its negative and positive value"},
    ],
    "vars": [
        {"name": "z", "index": "T", "domain": "Binary",
         "doc": "the per-household sign-agreement indicator; equals 1 when the fitted linear score agrees in sign with that household's observed outcome and 0 otherwise"},
        {"name": "beta", "index": "p", "domain": "Reals",
         "doc": "the estimated coefficient on each explanatory variable; bounded in magnitude by delta, with the coefficient on the first explanatory variable fixed to one for identification"},
        {"name": "mws", "index": "", "domain": "Reals",
         "doc": "a single scalar that holds the count of households whose fitted score agrees in sign with the observed outcome; this is the quantity being maximized"},
    ],
    "objective": {"sense": "maximize", "expr_var": "mws"},
}

NARRATIVE = (
    "We fit a discrete-choice model to a sample of households by choosing a coefficient for each "
    "explanatory variable. For each household we form a linear score from its standardized feature "
    "values weighted by these coefficients, and we track whether that score agrees in sign with the "
    "household's observed binary outcome. The coefficient on the first explanatory variable is fixed "
    "for identification and the remaining coefficients are free within a bounded range. The objective "
    "is to choose the coefficients so as to maximize the number of households whose fitted score "
    "agrees in sign with their observed outcome."
)

OBJFUN = (
    "def objfun_rule(m):\n"
    "    return m.mws == sum(m.z[t] for t in m.T)\n"
    "model.objfun = Constraint(rule=objfun_rule)"
)

COSG = (
    "def cosg_rule(m, t):\n"
    "    return (1 - 2 * m.y[t]) * sum(m.beta[p] * m.Xnms[t, p] for p in m.p) <= m.omega[t] * (1 - m.z[t])\n"
    "model.cosg = Constraint(model.T, rule=cosg_rule)"
)

WHOLESET = "\n".join([OBJFUN, COSG])

records = [
    {"description": (
        "The objective tally must equal the total number of households flagged as having their fitted "
        "score agree in sign with their observed outcome. In other words the scalar that is being "
        "maximized is set equal to the count of households whose agreement indicator is turned on."),
     "expected_pyomo": OBJFUN},
    {"description": (
        "For each household, its agreement indicator may only be turned on when the fitted linear score "
        "actually agrees in sign with that household's observed outcome. The household's score is the "
        "sum over the explanatory variables of its standardized feature value times the corresponding "
        "coefficient. When the observed outcome is one the score should be nonnegative and when it is "
        "zero the score should be nonpositive, and this sign requirement is enforced only while the "
        "indicator is on. Whenever the indicator is off the requirement is relaxed by the household's "
        "large constant so it places no real restriction on the coefficients."),
     "expected_pyomo": COSG},
    {"description": "Generate the complete constraint set for this model.",
     "expected_pyomo": WHOLESET},
]

with open(OUT, "w") as f:
    for r in records:
        f.write(json.dumps({
            "problem_id": "mws_mip",
            "model_narrative": NARRATIVE,
            "components": COMPONENTS,
            "description": r["description"],
            "expected_pyomo": r["expected_pyomo"],
        }, ensure_ascii=False) + "\n")
print(f"wrote {OUT} ({len(records)} records)")
