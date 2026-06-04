# Constraint-Generation Dataset — Design & Detail-Level Options (agreste_lp293)

Built 2026-05-29 at Hsuan-Han's request. Goal: a dataset where the model is given a problem's **givens** (sets, params, vars, objective) plus a **description of how each constraint is added**, and must generate the **constraint code**. Open question Hsuan-Han raised: *how detailed should the description be?* This doc answers it by showing the same constraints at **three detail tiers** so we can pick before generating all 14 constraints.

Companion data file: `agreste_lp293_constraint_gen_sample.jsonl` (the 3 sample constraints × 3 tiers, machine-readable).

---

## 1. Record schema (proposed)

Each model has **one shared context block** (the givens) and **one record per constraint** (the generation target). A training example = context block + one constraint's description (at the chosen tier) → constraint code.

```
context  (shared per model)
  problem_id            "agreste_lp293"
  domain                "agricultural production planning (farm income maximization)"
  sets[]                {name, members, doc}
  params[]              {name, index, kind: indexed|scalar|derived, doc}
  vars[]                {name, index, domain, doc}
  objective             {sense, expr_var, doc}

record   (one per constraint)
  problem_id            "agreste_lp293"
  constraint_name       "landb"
  index_set             "model.s" | null (scalar)
  description_tier      "intent" | "structured" | "formal"
  constraint_description "...the input the model sees..."
  target_pyomo          "...ground-truth Pyomo rule code..."   # the label
  target_math           "...GAMS/algebra form..."               # optional aux label
  difficulty            "easy" | "medium" | "hard"
```

This plugs straight into the Z3-equivalence / GRPO pipeline in [[OptiChat Constraint Generator Taxonomy for Execution-Verified RL]]: `target_pyomo` is the ground truth the verifier checks generated constraints against.

---

## 2. The givens (context block) — "what the model has"

Shared across every constraint record for this model. (Members below are the real ones from `agreste_lp293_data.json`.)

**Sets**
- `c` crops = {cotton-h, banana, sugar-cane, beans-arr, beans-cor, oranges, manioc, corn, sisal}
- `p` cropping activities = {crop-02, crop-05, …, crop-36} (12)
- `s` land types = {good, medium, pasture}
- `sc ⊆ s` crop lands = {good, medium}
- `tm` months = {jan … dec}
- `r` livestock feeding alternatives = {rec-1, rec-2, rec-3}
- `ty` years = {1960 … 1969}
- `dr` family consumption bundle alternatives = {one, two, three}
- `km` technology characteristics = {equipment, fertilizer, seeds, sprouts, itech}
- `ps ⊆ p×s` process-land possibilities (derived: (p,s) where crop p has positive yield on land s)

**Params** (indexed): landc(s), rations(r), xcropl(p,s), ldp(s,s), lio(s,r), labor(p,tm), llab(tm,r), cbndl(c,dr), crev(c,ty), price(c), yield(p,c,s), techc(p,km). **(scalar):** fwage, twage, pwage, vsc, wcbar, famlab, lprice, vetpr, dpm, phi. **(derived):** ravg(c), prdev(c,ty), pcost(p), a(p).

**Vars** (all NonNegativeReals unless noted): xcrop(p,s), xliver(r), xlive, lswitch(s), xprod(c), cons(dr), sales(c), flab(tm), tlab(tm), plab, rationr, pdev(ty), ndev(ty), yfarm (free), revenue, cropcost, labcost, vetcost.

**Objective**: maximize `yfarm` (farm income, cr).

---

## 3. The detail-level question — three tiers, three sample constraints

The three tiers correspond to the input-specificity ladder from the benchmark survey ([[LLM Optimization Modeling Benchmarks - Survey and Comparison]] §5):

- **Tier 1 — Intent only.** One semantic sentence. Names no symbols; the model must recover which sets/params/vars are involved, the algebra, the relation direction, and any index conditions. Hardest; closest to a real user's what-if phrasing.
- **Tier 2 — Structured intent.** Names the index set, the LHS terms mapped to the right vars/params in words, the relation, and the RHS — but not Pyomo syntax and not the formal `$`-guards. The model still assembles the expression. *(Recommended primary tier — see §4.)*
- **Tier 3 — Near-formal spec.** Per-term mapping with exact symbols and index conditions (`$ps(p,s)`, `$sc(s)`); essentially pseudocode one step from Pyomo. Easiest; risks becoming transcription.

### Sample A — `lbal` (scalar equality, **easy**)

Ground truth: `model.lbal = Constraint(expr=model.xlive == sum(model.xliver[r] for r in model.r))`

- **Tier 1**: "Total livestock raised equals the livestock supported across all feeding alternatives."
- **Tier 2**: "A single (non-indexed) equality: the scalar variable `xlive` (total livestock, head) equals the sum over feeding alternatives `r` of `xliver[r]` (head per feed technique)."
- **Tier 3**: "Scalar equality. LHS = `xlive`. RHS = Σ_{r∈r} `xliver[r]`. Relation `==`. No index conditions."

### Sample B — `landb` (indexed over `s`, conditional terms, **hard**)

Ground truth (Pyomo rule): for each `s`, `crop_term (only if s∈sc) + downgrade_term + livestock_term ≤ landc[s]`, where crop_term = Σ_{p:(p,s)∈ps} a[p]·xcrop[p,s], downgrade_term = Σ_{sp∈s} ldp[s,sp]·lswitch[sp], livestock_term = Σ_{r} lio[s,r]·xliver[r].

- **Tier 1**: "For each land type, land used can't exceed land available. Land is used by crops (only on land types that can grow crops), by land converted in from other types, and by livestock feeding."
- **Tier 2**: "Indexed over land type `s`. Left side, three terms: (a) **only when `s` is a crop-land** (`sc` = good, medium): the sum over cropping activities `p` that are feasible on `s` of `a[p]·xcrop[p,s]`; (b) sum over source land types `sp` of `ldp[s,sp]·lswitch[sp]` (downgrading); (c) sum over feed alternatives `r` of `lio[s,r]·xliver[r]`. Relation `≤` available land `landc[s]`."
- **Tier 3**: "∀ `s`: ( [`s∈sc`] · Σ_{p:(p,s)∈ps} a[p]·xcrop[p,s] ) + Σ_{sp∈s} ldp[s,sp]·lswitch[sp] + Σ_{r∈r} lio[s,r]·xliver[r] ≤ landc[s]. Note the `$ps(p,s)` restriction on the crop sum and the `$sc(s)` guard that zeroes the crop term on pasture."

### Sample C — `income` (accounting identity, many terms, **medium**)

Ground truth: `yfarm == revenue + vsc·Σ_dr cons[dr] − labcost − rationr − vetcost − cropcost − phi·Σ_ty (pdev[ty]+ndev[ty]) / card(ty)`

- **Tier 1**: "Farm income equals sales revenue plus the value of food the family keeps to eat, minus labor, ration, veterinary, and cropping costs, minus a risk penalty for year-to-year price swings."
- **Tier 2**: "Scalar equality defining `yfarm`: `revenue` + `vsc`·(Σ over bundles `dr` of `cons[dr]`) − `labcost` − `rationr` − `vetcost` − `cropcost` − `phi`·(Σ over years `ty` of `pdev[ty]+ndev[ty]`)/(number of years)."
- **Tier 3**: "`yfarm` == `revenue` + `vsc`·Σ_{dr} cons[dr] − `labcost` − `rationr` − `vetcost` − `cropcost` − `phi`·Σ_{ty}(pdev[ty]+ndev[ty])/card(ty). card(ty)=10."

---

## 4. Recommendation & open decisions (need Hsuan-Han's call)

**Detail tier — recommend Tier 2 (Structured intent) as the primary training tier.**
- Tier 3 collapses to transcription — the model isn't learning to *model*, just to translate syntax; weak signal for a constraint generator.
- Tier 1 is under-determined: a vague sentence admits several non-equivalent constraints (e.g., does "can't exceed" allow equality? which land counts?), so the ground truth isn't a unique target — bad for an exact/Z3-equivalence reward, though great as a **harder held-out eval**.
- Tier 2 names the pieces (so the target is well-defined and gradeable) but still requires assembling the expression, the relation, and the index logic — that's the actual modeling skill. **Suggest: train on Tier 2, keep a Tier-1 held-out eval to measure real generalization.**

**Two more decisions:**
1. **Generation unit** — per-constraint (context + one description → one constraint) *vs* whole-set (context + all descriptions → all constraints). Recommend **per-constraint**: finer reward granularity, matches the existing `constraint_semantics` data and the what-if use case.
2. **Does context include already-present constraints?** Your spec says givens = sets/params/vars/objective only (no other constraints). Recommend keeping that for the base dataset; an **incremental variant** (generate constraint k given constraints 1..k−1) is worth a separate split for the interactive what-if setting.

**If you confirm Tier 2 + per-constraint**, I'll generate all 14 constraints of agreste_lp293 in the JSONL schema above, then we can run one across OptiChat to sanity-check that a model can actually produce the target from the Tier-2 description.

---

## Edit log

| Date | Author | Reason | What it added |
|------|--------|--------|---------------|
| 2026-05-29 | Hsuan-Han (Telegram msg 1523) | Asked 阿狗 to generate the constraint-generation dataset starting with agreste_lp293, unsure how detailed the description should be | Original request |
| 2026-05-29 | 小雞毛 | Resolve the detail-level question with concrete options | Record schema, context block (real set members), 3 sample constraints × 3 detail tiers, recommendation (Tier 2 primary + Tier 1 held-out eval; per-constraint unit), and the two open design decisions. Companion sample JSONL. |
| 2026-05-30 | Hsuan-Han (Telegram msg 1547) | **Final schema** — re-add the whole-set record and embed components | Each record = `{problem_id, model_narrative, components, description, expected_pyomo}`. `components` = embedded `{sets, params, vars, objective}` (self-contained per record, not fetched by problem_id). 15 records total: 14 per-constraint + 1 whole-set (whole-set has `description = "Generate the complete constraint set for this model."` and `expected_pyomo` = all 14 constraints concatenated). No labels, no task tags. Validated: all targets parse, all records carry exactly the 5 fields. |
| 2026-05-30 | Hsuan-Han (Telegram msg 1542) | **Schema simplification** — strip everything non-essential | (REVISED by msg 1547 above — whole-set + components re-added.) Rebuilt to flat schema `{problem_id, model_narrative, description, expected_pyomo}`. DROPPED: `family`, `form`, `difficulty`, the `task`/`record_type` split, `index_set`, `description_tier`. Cleaned `model_narrative` to describe only the model's decisions + objective — NOT the constraint set (the enumeration was duplicating the per-constraint descriptions). |
| 2026-05-30 | 小白 (standup conv 9a650e47) + 小雞毛 | Add a principled constraint-family taxonomy for the family-probing RIS seed and for OptiChat routing | (SUPERSEDED 2026-05-30 by the schema simplification above — labels removed from the data.) Added `family` (小白's 6-way: balance / capacity / linking / definitional / normalization / deviation) and `form` (equality / inequality) fields to all 14 standalone records. agreste coverage: balance 2, capacity 3, definitional 7, normalization 1, deviation 1, **linking 0** (pure LP → no linking constraints; surfaced that the dataset must include MIPs to cover the linking family). Status labels deferred to the edits/instances/certificate-spine layer, not the base reconstruction records. |
| 2026-05-29 | Hsuan-Han (Telegram msg 1525–1531) | Decisions: **Tier 1 chosen** (Tier 2/3 leak the solution), refined to "semantically complete, symbolically silent"; always pass context (sets/params/vars/objective + model narrative); build **14 standalone + 1 whole-set = 15** items per model; keep all of a model's items on the **same train/test split** (whole-set = union of the 14, so item-level splits contaminate); grade by **Z3 equivalence on code** (not exact match / not expected_obj). Stage-2 extension (extract constraint-generating what-if/why-not items from `test_set/tool_test`) agreed but deferred. | Built `agreste_lp293_constraint_gen.jsonl` (16 records: context + 14 standalone Tier-1 + 1 whole-set). Validated: all targets parse; description leak-scan clean (no var/param symbols or algebra). |
| 2026-06-01 | Hsuan-Han (Telegram msg 1573–1575) | **System-prompt rewrite.** (1) DROP the GRADING section — Z3 logical-equivalence grading is our harness, not the model's concern; correct Pyomo is correct regardless of grader, and the real OptiChat coder prompt has no grading note, so keeping it created a train/deploy mismatch. (2) KEEP the "output ONLY Pyomo code" rule, but understood now as a **Stage-1 reward-extraction convenience** (clean output → trivial, noise-free extraction for the Z3 reward that drives GRPO), NOT a permanent property of the model — Stage 3 re-broadens output to the coder's write-execute-iterate format. Decided in the context of the **3-stage pipeline** (Stage 1 GRPO skill → Stage 2 probe-based act_diff LoRA → Stage 3 coder-adaptation LoRA). | Rewrote `constraint_gen_system_prompt.txt`: removed lines 19–20 (GRADING). Output rules + structural Pyomo guidance retained unchanged. |
