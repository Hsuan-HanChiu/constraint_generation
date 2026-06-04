# Constraint-generation checking harness

`grade_harness.py` — generate a constraint with an LLM (or supply one yourself)
and grade it for **logical equivalence** to the ground truth using OptiChat's
Z3 checker (`benchmarking/z3_constraint_checker.compare_added_constraints`).

## Environment

Run in the `opti` conda env — it has pyomo 6.9.5, z3-solver, and openai:

```
conda run --no-capture-output -n opti python grade_harness.py --help
```

(z3-solver was pip-installed into `opti` on 2026-06-01; openai 2.8.1 already present.)

## Folder structure

```
constraint generation data/
├── grade_harness.py                  # the harness (entry point)
├── constraint_gen_system_prompt.txt  # system prompt the harness sends to the LLM
├── HARNESS_README.md                 # this file
├── .env                              # OPENAI_API_KEY=... (auto-loaded, never committed)
├── datasets/                         # all constraint-gen JSONL datasets
│   ├── agreste_lp293_constraint_gen.jsonl   (LP, 15 records)
│   ├── binpacking_mip_constraint_gen.jsonl  (MIP, 4 records)
│   └── tsp1_mip_constraint_gen.jsonl        (MIP/MTZ, 5 records)
├── reduced_data/                     # small grading instances for big MIPs
│   ├── binpacking_small.json                (6 items, 3 bins)
│   └── tsp1_small.json                      (5 candidate cities, 4 toured)
├── design/                           # design docs + early samples
└── optichat_constraint_testing_results/     # api result logs
```

`--dataset` accepts a bare filename and resolves it under `datasets/`, so
`--dataset binpacking_mip_constraint_gen.jsonl` works from anywhere.

## Commands

**List the dataset records** (index + target constraint names):
```
conda run --no-capture-output -n opti python grade_harness.py list
```
Records 0–13 are per-constraint; record 14 is the whole 14-constraint set.

**Grade an output you already have** (no API call):
```
conda run --no-capture-output -n opti python grade_harness.py grade --record 0 --generated /path/to/output.py
# or paste via stdin:
pbpaste | conda run --no-capture-output -n opti python grade_harness.py grade --record 0 --generated -
```

**Generate with the OpenAI API and grade in one shot:**
```
export OPENAI_API_KEY=sk-...          # or put it in .env
conda run --no-capture-output -n opti python grade_harness.py api --model gpt-5.5 --record 0 --show-generated
# whole dataset + save results:
conda run --no-capture-output -n opti python grade_harness.py api --model gpt-5.5 --all --out results_gpt55.jsonl
# a different dataset:
conda run --no-capture-output -n opti python grade_harness.py api --model gpt-5-mini --dataset binpacking_mip_constraint_gen.jsonl --all
```

**Calibrate a grading instance** (answers "is this instance the right size for Z3?"):
```
conda run --no-capture-output -n opti python grade_harness.py calibrate --dataset binpacking_mip_constraint_gen.jsonl
```
For each per-constraint record it times the self-grade (must be OK) and an
auto-perturbed negative control (relation flipped, should be FAIL). If anything
returns z3_unknown/timeout, the instance is too big — shrink the index sets or
raise the timeout. If everything is fast and the controls are caught, it's
well-sized. (binpacking small instance: ~13 ms worst; agreste: ~34 ms worst.)

**Validate a reduced instance against the full one** (empirical faithfulness check):
```
conda run --no-capture-output -n opti python grade_harness.py validate-instance \
    --dataset binpacking_mip_constraint_gen.jsonl \
    --full-data ../GAMSConversion/data_json/binpacking.json --timeout-large 120000
```
For each constraint it grades a battery (correct + relation-flipped + coefficient-
scaled) on BOTH the reduced instance and the full instance (the full one with a long
timeout), and checks the verdicts MATCH. Any DISAGREEMENT means the reduced instance is
too degenerate — e.g. coincidental parameter values let a wrong constraint pass — and
must be enlarged. This is the empirical answer to "does the small instance behave like
the big one": binpacking 6×3 vs 60×20 returns 9/9 agree, 0 disagree → FAITHFUL.

## Sizing a reduced instance for Z3 (rule of thumb)

Z3's runtime is dominated by the number of **binary/integer variables** in the
instance, because proving NON-equivalence means finding a counterexample (a SAT
search) over those variables. The full binpacking instance (60 items × 20 bins =
1200 binaries) times out at 5 s; the 6×3 reduced instance (18 binaries) grades in
~13 ms.

Pick the **smallest structurally-complete** instance:
- each index set ≈ 3 members (so quantification is non-trivial and "summed over
  the wrong set" errors surface),
- every subset has at least one member **in** and one **out** (so guard/scope
  errors surface),
- every 2-D coupling (e.g. `y[i,j]`, `ldp[s,sp]`) has ≥ 2 members per dimension.

Then **measure, don't guess**: run `calibrate`. If the controls are caught and
timing is well under the 5 s budget, you're done. If you see z3_unknown, the
instance is too big — shrink it (or raise the timeout for that one model).

## How grading works (the important detail)

The agreste base model **ships with all 14 constraints**. For constraint-
*generation* grading the base must NOT already contain the target, or the
comparison is meaningless (the "added" set comes back empty). So the harness:

1. builds the full base model,
2. parses the target constraint name(s) from the record's `expected_pyomo`
   (`model.<name> = Constraint(...)`),
3. **deletes those from the base**,
4. deep-copies the stripped base twice → adds the LLM's constraint to one,
   the ground truth to the other,
5. runs `compare_added_constraints` → Z3 `Xor(actual, expected)` unsat ⇒ equivalent.

The check is **logical equivalence**, not string match — reordered terms, a
flipped relation (`a <= b` vs `b >= a`), renamed constraints, and algebraically
equivalent rewrites all pass. (Validated: a reordered/flipped rewrite of `landb`
grades EQUIVALENT; GPT-5.5's `landb` grades NOT EQUIVALENT.)

## Adding more models

Extend `MODEL_REGISTRY` in `grade_harness.py` with the new `problem_id` →
`{base_py, data_json}` paths. The data JSON must follow the
`{sets, scalar_params, indexed_params}` schema (pipe-separated multi-dim keys).

## Notes / limits

- The OpenAI call is intentionally minimal (no `temperature`/`max_tokens`) for
  compatibility with newer models. Adjust in `generate_openai` if needed.
- Z3 timeout is 5 s/constraint (the checker default); a timeout grades as
  `⚠️ UNGRADED` (reason `z3_unknown_or_timeout`), not as a failure.
- `OPENAI_API_KEY` must be set (or passed via `--api-key`). Not stored in the repo.
