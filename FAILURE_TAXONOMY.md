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

## Reframe (2026-06-05 standup): oracle-backed contrastive repair units

The primitive object is not "a mistake" but an **oracle-backed contrastive repair unit**:
`wrong step -> minimal corrected step -> failure type -> oracle / decision procedure -> label`
The 5-category taxonomy is the organizing layer over these units. CausalFlow (arXiv 2605.25338, ingested 2026-06-05) is the motivation/comparison: contrastive causal repair is valuable but bottlenecked by needing a **success oracle**, and its strongest results are on math/code precisely because those have crisp checkers. Our decidable-oracle angle: restrict to settings where correctness is decidable (Z3 per-constraint equivalence) so the units are **verified, not judged**.

### Two error LEVELS (enabled by the whole-set ordinal narrative)
Because the whole-set description is now an explicit ordered intent trace (First, Second, ... Finally), a wrong step can be injected at the INTENT level, not only the algebra level. Each repair unit carries a level:
- **modeling error** — the intent itself is wrong (drop / flip / mis-scope an ordinal item in the narrative).
- **translation error** — the intent is right, the Pyomo is wrong.
The same five categories apply at both levels. The intent-vs-translation axis is pedagogically load-bearing: students conflate "I misunderstood the problem" with "I mis-coded a correct understanding." This axis is only cleanly separable BECAUSE the ordinal narrative externalizes the intent before any algebra appears.

### Oracle asymmetry across the two levels (open design point, 2026-06-05)
The decidable oracle is NOT symmetric across levels:
- **Translation level = fully decidable.** Z3 checks candidate Pyomo vs the reference constraint.
- **Intent level = decidable only relative to a faithful translator.** A corrupted ordinal item is natural language, not directly Z3-checkable. Practical procedure: corrupt one ordinal item, translate it faithfully the way the reference does, and Z3 will show the resulting model diverges from ground truth — so the intent error is DETECTABLE, but attributing it to intent-vs-translation requires a trusted faithful-translation step that holds translation fixed.

Honest boundary for the teaching note and the benchmark claim: the understanding-vs-implementation boundary is only as crisp as our ability to hold the translation step fixed. This is the main open design question if the sub-project is scheduled. (Teaching sequence per 小白: intent trace -> intent-level check -> algebra translation -> translation-level check. Teach intent-error before translation-error.)

> Open question, crisply (小白, 2026-06-05): the distinction is meaningful regardless; the real question is **how much trust/control we need over the faithful translator** to make the intent-level claim strong. The benchmark tests implementation fidelity cleanly (Z3) and tests understanding only under "translator held fixed."

## Oracle vacuity: faithful constraints that the oracle cannot test (new axis, 2026-06-06 standup)

The taxonomy now has TWO questions, not one:
1. **Is the candidate constraint wrong?** -> modeling error / translation error (the original axis).
2. **If it is not wrong, can the oracle discriminate it?** -> informative / sharp oracle  |  vacuous or redundancy-blind oracle  |  symmetry-blind oracle.

**Definition.** Oracle vacuity is when the constraint is semantically valid and faithful, but the chosen oracle/certificate returns the same verdict with or without it — because the constraint is implied, globally redundant, zero-multiplied, or symmetry-cancelled. This is NOT a modeling failure; it is an evaluation/oracle-design failure. Attribute it to oracle design and evaluation resolution, not to model construction.

**Canonical examples (the "faithful but non-discriminable" cases):**
- **CVRP `eq_node_balance`** — per-node flow balance is globally implied by total in-degree ≡ out-degree (an identity over the X matrix), so flipping its `==` stays equivalent. The oracle cannot distinguish the explicit equality from its absence. Redundancy-blind.
- **nonsharp `laerr` / `intcut`** — degenerate Benders certificate: `laerr` is a vacuous `0<=0` (all multipliers zero in shipped data); `intcut` is a symmetric ±1 cut pair. Faithful but nonsharp; the relation-flip control cannot bite. Vacuous / symmetry-blind.

**Consequence for metrics (flag).** A selfcheck FAIL is now ambiguous: it can mean "the candidate is wrong" OR "the constraint is right but the oracle can't tell." When we report dataset quality / model eval, separate these two — collapsing them understates a model that wrote a correct-but-redundant constraint. Raw evidence stays in `BOUNDARY_CASES.md`, which points back to this section.

### Bridge: vacuity is a contrast-set failure (2026-06-07 standup)

**Bridge sentence:** *oracle vacuity = the control fails to induce a discriminating counterfactual.* This stops vacuity being an implementation nuisance and makes it a first-class evaluation concept. The unifying primitive is the **contrast set**: verification is not confirmation, it is *discrimination*, and discrimination requires nearby false worlds that should be rejected. A constraint becomes "real" only when it separates admissible behavior from a plausible counterfactual.

Every verification trick we have collected is the same move — manufacture a nearby false world and demand rejection — at a different level:
- **symbolic contrast** — our relation-flip / `<=0` control (perturb the operator, demand non-equivalence);
- **instance-level contrast** — VRPCoder's one-constraint-violating probe ([[Beyond Objective Equivalence - Constraint Injection for LLM-Based Optimization Modeling on Vehicle Routing Problems]], 2606.04816): a point breaking exactly one constraint, demand rejection;
- **spec-level contrast** — TLA-Prover's Diamond tier ([[TLA-Prover - Verifiable TLA+ Specification Synthesis via Preference-Optimized Low-Rank Adaptation]], 2606.06133): perturb the property, demand the checker catches it;
- **behavioral contrast** — constraint learning from traces (2606.05353): boundary/violation evidence to distinguish a latent constraint from a coincidental regularity.

Vacuity is exactly when the contrast set is empty or collapses under symmetry/redundancy (CVRP: no live symbolic contrast; nonsharp: contrast cancels). Conceptual home = 小白's teaching note "verification requires contrast sets" (in progress).

**Open decision for Hsuan-Han (raised 2026-06-07 standup, awaiting his call).** Upgrade `selfcheck` to emit a per-constraint **contrast-liveness** flag, so verdict and contrast status are inseparable (else a vacuous PASS launders as evidence before any audit). Proposed minimal contract per constraint: `verdict` PASS/FAIL; `contrast_liveness` LIVE/COLLAPSED/UNKNOWN; `collapse_reason` (equivalent | symmetry_cancelled | redundant | solver_timeout | not_attempted); `fail_reason` if FAIL (constraint_wrong | oracle_uncertain | solver_error). Reporting rule: never display an aggregate pass rate without splitting **live-pass vs vacuous-pass**. Cost is real (a second Z3 call per symbolic control to verify the perturbed constraint is genuinely non-equivalent, plus a degenerate-case policy) — his call is (1) in-`selfcheck` vs separate audit pass, and (2) how loud the digest is about vacuous-pass, weighed against doing the harness work now vs after the fine-tuning eval.

### Three-layer spine + the certification/contrast orthogonality (2026-06-08 standup)

The whole line collapses to a **three-layer spine** (小白's framing) that organizes everything above:
- **proposal** — learned / heuristic / creative: an LLM emits a Pyomo constraint, or a learned proxy emits a dual point.
- **certification** — verifies *semantic validity*: Z3 equivalence to the reference, or Proxy-BD's project-and-complete.
- **contrast** — verifies the *test actually discriminates*: the witness-or-UNSAT-core liveness check.

**Definition of a live control (小白, 2026-06-08, verbatim):** *"A control is live only if it can force a discriminating counterfactual; otherwise it is not a control but a redundant restatement of the original test."*

**Certification and contrast are ORTHOGONAL, not nested** — neither subsumes the other:
- certification asks: *is the artifact semantically valid?*
- contrast asks: *does the artifact do discriminating work?*
- A thing can be **valid-but-nonsharp** or **discriminating-but-invalid**, so passing one says nothing about the other.

**Canonical orthogonality example: [[The Proxy Benders Decomposition]] (2606.07403) + `nonsharp_mip`.** Proxy-BD has a proposal layer (learned proxy) and a certification layer (project-and-complete → a *provably valid* Benders cut) but NO contrast layer — and a valid Benders cut can still be **weak / non-sharp** (a correct supporting inequality that barely tightens the relaxation). `nonsharp_mip` is the dataset poster child: faithful (certified valid) yet degenerate (the relation-flip control can't bite). Using the OR-native word "nonsharp" keeps this a familiar bridge, not an invented category.

**Refined decision for Hsuan-Han — make the dataset role-aware by liveness (a SPLIT, not one call).** A valid-but-`COLLAPSED` record is *training-positive but reward-ineligible*:
- **SFT data:** include both LIVE and COLLAPSED valid constraints — both are correct emissions; dropping COLLAPSED ones would teach silent omission of redundant-but-faithful constraints (the failure VRPCoder warns about). But tag COLLAPSED in metadata so downstream readers don't mistake it for a witnessed verification case.
- **Reward / eval (GRPO):** count only LIVE / witnessed constraints as verified wins; exclude or separately bucket COLLAPSED ones, else reward laundering.
- **Reporting:** publish two rates — (1) semantic-validity / constraint-correctness, (2) sharp verified pass-rate (excluding/bucketing COLLAPSED). This avoids both "nonsharp is useless" and reward laundering.

Rule of thumb: *every record needs a role-aware liveness route; COLLAPSED records are training-positive but reward-ineligible unless a later witness/core check revives them as LIVE.* Conceptual home / pedagogy = 小白's teaching note (three-layer spine, LIVE/COLLAPSED dichotomy, Z3 witness-or-core technical box, Proxy Benders as the orthogonality example).

### Satisfaction vs equivalence oracles + the verification spine (2026-06-09 standup)

**Oracle-vacuity is specific to EQUIVALENCE oracles, not all solver-verified checks.** Prompted by [[MathConstraint - Automated Generation of Verified Combinatorial Reasoning Instances for LLMs]] (2605.08498), whose verifier checks *satisfaction*:
- **Satisfaction oracle** — "does this witness satisfy the spec?" Hand it an assignment, solver says yes/no. NO vacuity problem: a witness either satisfies or it doesn't.
- **Equivalence oracle** (ours, Z3 `Xor(candidate, reference)` unsat) — "does this candidate mean the same as the reference?" HAS the vacuity problem: a redundant/implied constraint doesn't change the solution set, so equivalence can't tell whether it contributes. → contrast-liveness machinery is needed *only* for equivalence-style grading, not satisfaction-style. Good teaching pivot: which oracle types need contrast-liveness and which don't.

**Two distinct three-layer spines (don't conflate; they NEST):**
- **SYSTEM spine** (architectural, 2026-06-08): proposal / certification / contrast — how a learned-proposal + formal-check system is built.
- **VERIFICATION spine** (epistemic/debugging, 小白 2026-06-09): harness-correctness / oracle-semantics / contrast-liveness — the ladder of ways a *check* can be meaningless. It is a zoom-in on the certification+contrast half of the system spine.

**Vacuity shows up at BOTH ENDS of the pipeline — unify the verification spine under one question:** *"did this layer do real work, or did it merely not object?"*
- Layer 1 (harness/model build): can pass vacuously because nothing was actually built/exercised. **Canonical case: `bchoil_mip`** — it BUILT without error and the solver was happy, but the key-coercion bug left the arc set EMPTY, so every constraint was trivially satisfied; "satisfied" meant nothing. (More concrete than an abstract "bad harness" warning — teaches well. Lesson: test model builds through the actual harness loader `gh._load_data`+`gh._exec_base`, not a raw `json.load`.)
- Layer 2 (oracle semantics): can be wrong because it checks the wrong proposition (satisfaction when you needed equivalence, etc.).
- Layer 3 (contrast-liveness): can pass vacuously because the control is undiscriminating/redundant (the original oracle-vacuity axis).
Same PASS-shaped failure ("ran, said PASS, tested nothing"), different location.

**Open decision for Hsuan-Han — the GRPO difficulty-controller (timing call; impl owner = constraint-gen harness / me).** MathConstraint's adaptive generator (parameterized difficulty knob → never saturates) is the curriculum a GRPO loop wants (pass/fail reward gives zero gradient on all-pass groups). **Recommendation: MEASURE FIRST, don't build it yet.** Our difficulty is idiosyncrasy-driven (a quirky LP > a big MIP), NOT size-driven like MathConstraint's CSPs, so the static 184-template set may not saturate fast. Run a baseline GRPO with **per-group, per-template, per-failure-mode** pass-rate instrumentation (小白's guardrail), then diagnose which saturation it is before building anything:
1. **true (reasoning) saturation** → the only case a difficulty controller should address;
2. **shortcut saturation** (model exploits template regularity / repeated surface form) → fix with more template/linguistic/schema DIVERSITY, not difficulty scaling;
3. **solver/format saturation** (emits Z3/Pyomo patterns without robust formulation understanding) → fix by tightening the verifier / task interface.
Build the controller only for the families that genuinely (1) saturate, and constrain parameter variation to REALISTIC OR regimes (certified-hard ≠ certified-relevant; don't train the model to be great at degenerate Pyomo).

### From verification to explanation: the three-contrast spine + shadow-price = why-not (2026-06-10 standup)

Bridge (today's Lagrangian digest): **the dual multiplier on a constraint is its shadow price, and a why-not query is formally asking for that shadow price.** "Why not allow more than 3 trucks?" = "what is the marginal value of relaxing this binding constraint?" So the same dual apparatus that decomposes a solve also produces the why-not *explanation*. This turns the constraint-generation skill and the explanation skill into two sides of one coin.

**小白's three-contrast explanation taxonomy** (the note's "verification → explanation" turning point) — and it maps almost 1:1 onto OptiChat's actual query types, so the supervision already exists in `testing_library/feas_test`:
- **A. feasibility contrast** — "did the answer actually change under the intervention?" Grounded in WHAT-IF/new_constraint + WHY-NOT/constraint_rule (the 406 records I built). **Empirical anchor = the 40 vacuous-control records (VACUOUS_CONTROLS.md)** (syntactic flip, oracle unmoved → the A-layer failure made visible).
- **B. optimality contrast** — "if still feasible, did the objective move, by how much?" Grounded in the `expected_obj` field every OptiChat what-if/why-not carries (stored as `_expected_obj` on each built record). Already latent; one extra target, no new mining.
- **C. dual/sensitivity contrast** — "why did it move / what constraint is exerting pressure?" Grounded in OptiChat's SENSITIVITY/ROBUSTNESS queries + `expected_duals` (shadow prices). The explanation layer's ground truth, not post-hoc prose.

**Reframe (小白, the thesis sentence):** the taxonomy doesn't ask OptiChat to become a different benchmark — it exposes that OptiChat *already contains three supervision signals*, but current eval collapses them into answer-correctness / constraint-generation. "Verification → explanation" = recover and train against latent explanatory structure already in the test library.

**Layer-C COVERAGE SURVEY (2026-06-10, ran it):** separating "dual exists" from "dual is usable" (小白's guardrail) — **SENSITIVITY: 283 queries, ALL 283 carry well-formed (numeric-dict) AND alignable (string-keyed) `expected_duals`; 0 messy.** ROBUSTNESS: 449 queries, all with `expected_headroom`. So ~732 clean explanation signals already exist; layer-C is NOT data-starved (e.g. agreste good-land shadow price 507.29, medium 25.25).

**Open decision for Hsuan-Han.** Whether "verification → explanation" becomes a near-term dataset/skill (a layer-C / dual-price explanation set) or stays a documented direction. Recommendation (mine + 小白): given the survey shows high, clean coverage, it's a *viable* extension — but don't overcommit until the dual-quality is confirmed end-to-end (can the duals be grounded to a generated explanation and graded?). Frame: "layer C is a coverage-measured extension, not a promise." His call on timing; impl owner = constraint-gen harness / me.
