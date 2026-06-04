# Failure Taxonomy + Labeled-Failure-Mode Factory

Scoped sub-project seed, from the 2026-06-04 standup (小雞毛 × 小白). Status: NOT scheduled — preserved as a concrete follow-up. Competes for time with the Gilbreth Qwen eval; priority is Hsuan-Han's call. Related: `BOUNDARY_CASES.md`, the Research Idea Seed digest `Obs/Daily Report/2026-06-04 Digest.md` ("decidable oracle for causal failure attribution"), and the existing relation-flip grading controls in `grade_harness.py`.

## Why
Correct/incorrect is not actionable. Both the teaching note (students) and Agent-Doctor-style attribution (research) need to know WHY a constraint is wrong, in a small set of named, gradable categories — and to back each with a minimal, solver-certified counterexample rather than an LLM's opinion.

## Canonical taxonomy (locked 2026-06-04)
1. **Flipped inequality / relation error** — relation operator reversed or `==`↔inequality.
2. **Missing condition / dropped conjunct** — a required term/clause omitted from the rule.
3. **Wrong quantifier or index set** — the rule ranges over the wrong set (too many / too few indices, wrong membership guard).
4. **Boundary error / over-tightened or over-relaxed bound** — a constant/bound shifted; off-by-one; ≤ vs <.
5. **Role confusion between objective and constraint** — an objective term written as a constraint, or vice versa.

## The core mapping (the "factory")
```
constraint  ->  perturbation operator  ->  taxonomy label  ->  Z3 counterexample  ->  correction pattern
```
For each ground-truth constraint, apply a category-specific MINIMAL perturbation, let Z3 certify it is genuinely non-equivalent (drop perturbations that come out equivalent — e.g. flipping `==` on a binary fix-to-zero), and capture the counterexample assignment as the witness. The witness renders into a human-readable correction pattern ("your constraint admits x=…, y=…, which the requirement forbids").

### Category → perturbation operator (on the native rule / expected_pyomo)
| Category | Minimal perturbation operator |
|---|---|
| 1 Flipped relation | reverse the constraint relop (`<=`↔`>=`, `==`→`<=`) — REUSE the existing `_perturb` control |
| 2 Missing condition | delete one additive term / one conjunct from the body |
| 3 Wrong quantifier/index | widen or narrow the rule's index set or membership guard by one element |
| 4 Boundary error | shift a constant bound by ±1 / swap `<=`↔`<` |
| 5 Role confusion | move an objective term into the constraint body (or relocate a constraint term to the objective accounting) |

## Dual use of the single artifact
- **Teaching note (小白):** per (constraint, category) → minimal counterexample + correction pattern = ready-made "here is the bug class, here is a concrete witness, here is how to fix it" unit.
- **Attribution research (Agent Doctor):** labeled failure modes with decided ground truth → grade any attribution method (CausalFlow, MASPrism, LLM-judge baseline) on precision/recall against the solver-decided label, not against opinion.

## Build path (if scheduled)
Extend the existing grading-control machinery (already does category 1) to emit the other four category operators, constraint-level, each Z3-certified non-equivalent with its counterexample. Output a `failure_modes/*.jsonl` keyed by (problem_id, constraint, category) with {perturbed_pyomo, witness, correction_pattern}. Reuses the dataset and grader untouched; no new model needed to BUILD the factory (a model is only needed later to TEST attribution on it).

## Open question for Hsuan-Han
Build now, or preserve as a scoped follow-up after the Gilbreth Qwen eval? 小白's preference: preserve as a concrete scoped follow-up even if not executed immediately — the build path is unusually clear.
