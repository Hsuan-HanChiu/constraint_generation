# Eval harness — running a model on the constraint-gen dataset

Tests a chat LLM on all 850 records (110 models) and grades each generation by
Z3 **logical equivalence** (not string match). Built on top of `grade_harness.py`
(reuses its prompt builder, Z3 grader, and base-model resolution); does not modify it.

## Pieces
- `eval_harness.py` — client + grader. Talks to any OpenAI-compatible endpoint.
- `run_gilbreth.slurm` — SLURM job: serve the model with vLLM, then run the eval.
- `grade_harness.py` — unchanged; provides `grade()`, `build_user_prompt()`, `system_prompt()`.

## What it measures
For each record it sends `system_prompt + (narrative + components + description)`,
takes the model's Pyomo, deletes the target constraint from the base model, adds
candidate + ground truth to two copies, and asks Z3 whether `Xor(cand, ref)` is
unsat → EQUIVALENT. Metrics: **pass@1** (or pass@k with `--n`), broken down by
overall / per-constraint vs whole-set / per-model, plus an unparseable-error count
and the 12 hardest models.

## Quick local smoke test (any OpenAI-compatible server)
```
conda activate opti        # pyomo + z3-solver + openai
python eval_harness.py --model <served-id> --base-url http://localhost:8000/v1 --limit 5
```

## On Gilbreth
1. **Pre-stage weights on a login node** (compute nodes usually have no internet):
   ```
   huggingface-cli download <EXACT_QWEN_REPO> --local-dir $SCRATCH/qwen35-9b
   ```
2. Edit `run_gilbreth.slurm`: set `-A <ALLOCATION>`, `-p <PARTITION>`, `PROJECT_DIR`,
   and the conda env names (`VLLM_ENV` with vllm, `GRADE_ENV`=`opti`).
3. Submit:
   ```
   MODEL=$SCRATCH/qwen35-9b sbatch run_gilbreth.slurm
   ```
4. Output: `eval_<jobid>.jsonl` (per-record samples + verdicts) and the printed summary
   in `eval_<jobid>.out`; vLLM log in `vllm_<jobid>.log`.

## Notes / gotchas
- **GPU memory**: a 9B model in bf16 is ~18GB + KV cache → needs ≥24GB (A100/H100).
  A 16GB V100 will OOM; use a 32GB V100 with `--max-model-len` lowered, or quantize.
- **Two envs**: vLLM (serving) and `opti` (grading client) are separate so heavy ML
  deps don't collide with pyomo/z3. The script activates each at the right step.
- **pass@k**: `--n 5 --temperature 0.7` for pass@5; default is greedy pass@1.
- **Reduced instances**: grading auto-resolves `reduced_data/<id>_small.json` when present,
  so MIPs that would time out Z3 use the small instance automatically — no extra flags.
- **Throughput**: `--workers` controls concurrent request+grade threads; vLLM batches
  the generation side, Z3 grading is the CPU cost. 8 is a safe default.
