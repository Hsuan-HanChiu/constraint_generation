# Boundary Cases — constraint-gen dataset

Reference table for the modeling-boundary heldout set (per 2026-06-03 standup with 小白). These are the records that should NOT go into the main SFT training set — they mark where the build + solve + Z3-equivalence pipeline cannot certify a constraint, and why. Localizing the boundary to the exact constraint (not the whole model) preserves the "mostly linear, still gradable" context while making the excluded piece explicit.

Key lesson this evidences: do not trust static parser tags or model-level impressions. The "nonlinear-flagged" regex was wrong for the overwhelming majority of models; the true label only emerges from build → solve/check → symbolic equivalence, and when something fails you localize it to the exact constraint and reason.

## A. Out-of-theory nonlinear constraints (constraint-level heldout)

For each model below, every OTHER constraint is linear and graded EQUIVALENT and stays in the main set. Only the single named constraint is excluded — it is outside the theory Z3 decides (linear arithmetic over ints/reals), not merely "hard".

| Model | Excluded constraint | Out-of-theory reason | Rest of model |
|---|---|---|---|
| stockcc_mip | defobj | objective/cost defined with a variable in the denominator (1.5·Dv / x) | 3 linear constraints graded + kept |
| cmo_mip | defpv, defpvres | present value discounts cashflows by (1+yield)^(−t) — variable raised to a power | 19 linear constraints graded + kept |
| trnspwl_mip | defsqrt | genuine square-root cost curve (irrational coefficients) | 6 linear constraints graded + kept |
| trip_mip | flow_conservation_const | right-hand side is a fresh np.random.normal(...) draw — not a function, non-reproducible | 4 linear constraints graded + kept |

## B. Non-build models (model-level heldout)

These never build under the shipped code/data, so no constraint can be graded until a code/data fix lands. Useful as "the model itself is broken" boundary examples.

| Model | Failure |
|---|---|
| RTN_mip | needs the networkx module (missing import dependency) |
| bchoil_mip | data KeyError on Param `cap` index 2 (data/shape mismatch) |
| ccoil_mip | calls undefined function `_get_pair_val` |

## C. Other boundaries (data-reachability, not nonlinearity — informational)

Distinct from A/B: these build and grade, but a subset of constraints is unreconstructable from `model.*` alone or inactive under the shipped data. Kept in the main set for the gradable part; noted here so the taxonomy is complete.

| Model | Boundary |
|---|---|
| STN_mip | only 2 of ~6 constraint families gradable — the rest depend on coefficient tables held in module-level Python dicts never attached to the Pyomo model |
| icut_mip | only `obj_def` is active; the entire cut family is Constraint.Skip-ped under the shipped data (no instances to grade) |

## Proposed split (for Hsuan-Han's call)

- (a) main SFT = every EQUIVALENT-graded constraint across the 110 done models (850 records minus the heldout below).
- (b) verifier-rejection negatives = the relation-flip perturbations the harness already generates as grading controls and Z3 flags non-equivalent (free).
- (c) boundary heldout = section A constraints + section B models, never in training.

Open decision: does the boundary heldout stay purely an eval set, or also become a later diagnostic benchmark (does the model recognize that a constraint is out-of-theory and abstain, rather than hallucinate a linear stand-in)?
