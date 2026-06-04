# Generic builder (option B) — feasibility result

**Question (Hsuan-Han, 2026-06-02):** is it easy to write ONE general `build_model`
so the dataset doesn't need a hand-written `.py` per model?

**Answer: yes — verified on all 12 models, 300 grading cases, 0 disagreements.**

## Why it's tractable

A constraint-generation grade only needs the SCAFFOLD a constraint references:
the **sets** (so sums expand), the **params** (so numbers substitute), and the
**variables** (so they become Z3 unknowns with the right domain/fixings). It does
**not** need any of the model's own constraints — the Z3 checker isolates and
compares only the single ADDED constraint. The hard part of a model (its
constraints) is exactly the part the base does not need. So a generic builder is
mechanical.

Empirically, **variable bounds and the objective are not load-bearing** for the
grade; **fixings are** (a fixed cell becomes a constant, which changes the
constraint — e.g. tsp's diagonal `x[i,i]=0`). The builder captures fixings,
skips bounds/objective, and still matches the original verdict everywhere.

## Two functions (`generic_builder.py`)

- `generic_build_model(components, data, extras)` → a constraint-free scaffold
  (sets from data, params over their index with values, vars with domain, plus
  fixings). ~90 lines, no model-specific logic.
- `freeze_scaffold(model)` → extracts `(components, data, extras)` from an
  ALREADY-BUILT model. This **auto-migrates** any corpus `.py` with zero hand
  authoring: it captures declared sets, **param values including COMPUTED ones**
  (they exist post-build, so agreste's `a`, `ps`, `ravg`, `prdev`, `pcost` come
  for free), variable domains, mutability, and fixed cells.

The migration tool is: `build_model(data)` (once, from the corpus `.py`) →
`freeze_scaffold` → `(components, data)` self-contained → `generic_build_model`
reconstructs → **verified identical grading verdicts**.

## Verification (`verify_generic.py`)

For each model: build the original `.py` base, freeze it, rebuild generically,
then grade the full dataset battery (correct + relation-flip + coefficient-scale)
on BOTH bases and require identical verdicts.

```
agreste_lp293    44/44   PASS   (5 computed params, var bounds, no fixings)
binpacking_mip   12/12   PASS
tsp1_mip         14/14   PASS   (diagonal + start-city fixings)
gussex1_lp       12/12   PASS
blend_lp57       12/12   PASS   (set-union index)
decomp_lp97      17/17   PASS
csp_mip           9/9    PASS
flowshop_mip     18/18   PASS
fawley_lp        32/32   PASS   (Any-indexed params)
orani_lp         50/50   PASS   (Any-indexed params)
nurses_mip       35/35   PASS   (multi-dim membership sets)
poutil_mip       45/45   PASS   (mutable params, flat data, time-coupling)
TOTAL           300/300  PASS
```

## What it took to reach 12/12

Three introspection refinements during the prototype, all now handled:
1. **Key normalization** — frozen pipe-string keys (`"c1|c1"`) split back to tuples.
2. **Concrete per-component index** — build params/vars over an anonymous Set of
   their captured index members, which sidesteps name-resolution for set unions
   (blend), `Any`-indexed params (fawley, orani), and products.
3. **Mutability capture** — replicate each param's original `mutable` flag; a
   generic `mutable=True` broke poutil where a rule needs implicit float
   conversion of a scalar param.

## Implication for the dataset bundle

Option B is the recommended end state. The shippable bundle becomes:
- one dataset JSONL per model (records),
- one frozen `(components, data)` per model (self-contained, no `.py`),
- `generic_builder.py` + `grade_harness.py`.

No per-model corpus `.py` needed at grade time, and no provenance dependency on
the messy/partly-synthetic original corpus. The corpus `.py` is used once, at
freeze time, then can be dropped. (Option A — keep the `.py` — remains a valid
fallback and is what the registry uses today.)

Next step if approved: add a `freeze` subcommand to the harness that writes the
frozen `(components, data)` for a registered model, and switch grading to the
generic base, keeping the `.py` path as a fallback.
