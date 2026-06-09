#!/bin/bash
# =============================================================================
# Gilbreth (Purdue RCAC) job: serve Qwen 3.5 9B with vLLM, then run the
# constraint-gen eval against it and grade every generation by Z3 logical
# equivalence.
#
# Submit:   sbatch run_gilbreth.slurm
# Override a knob at submit time, e.g.:   N=5 TEMP=0.7 sbatch run_gilbreth.slurm
#
# Verified for this machine (2026-06-04):
#   * account `canli`, partition `a100-40gb` (a 9B in bf16 ~18GB fits on 40GB)
#   * single conda env at conda_envs/optichat has BOTH vllm 0.19 and
#     pyomo+z3-solver+openai, so serving and grading share one env
#   * model unsloth/Qwen3.5-9B staged into HF_HOME (compute nodes have no internet)
# =============================================================================
#SBATCH -A canli
#SBATCH -p a100-40gb
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --job-name=qwen-cgen-eval
#SBATCH --output=eval_%j.out
#SBATCH --error=eval_%j.err

set -euo pipefail

# ---- knobs (override at submit time) ---------------------------------------
PROJECT_DIR="${PROJECT_DIR:-/scratch/gilbreth/chiu137/constraint_generation}"
MODEL="${MODEL:-unsloth/Qwen3.5-9B}"   # HF repo id (staged in HF_HOME) or a local path
PORT="${PORT:-8000}"
CONDA_ENV="${CONDA_ENV:-/scratch/gilbreth/chiu137/conda_envs/optichat}"
N="${N:-1}"                            # samples per record (pass@k)
TEMP="${TEMP:-0.6}"                     # Qwen3-recommended; rest of the sampling
                                       # params (top_p=0.95 top_k=20 min_p=0
                                       # presence_penalty=0 repetition_penalty=1)
                                       # are eval_harness.py defaults, logged at startup
WORKERS="${WORKERS:-16}"               # concurrent request+grade threads; vLLM
                                       # batches the in-flight requests server-side.
                                       # Raise (e.g. 32) to push GPU utilization higher.
MAXTOK="${MAXTOK:-16384}"              # generation budget. Qwen3.5 reasoning routinely
                                       # exceeds 4096 (measured: 51% of records truncated
                                       # mid-thought at 4096), so give it room. Must satisfy
                                       # max_prompt(~4689) + MAXTOK <= MAX_MODEL_LEN.
MAX_MODEL_LEN="${MAX_MODEL_LEN:-24576}" # vLLM context = prompt + generation. Qwen3.5-9B
                                       # supports 262144 natively; capped here for KV memory
                                       # on the 40GB A100.

# Compute nodes have no internet: serve from the local HF cache only.
export HF_HOME="${HF_HOME:-/scratch/gilbreth/chiu137/hf_cache}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"

echo "host: $(hostname)  job: ${SLURM_JOB_ID:-local}"
nvidia-smi -L || true

# RCAC: conda lives behind Lmod. Do NOT `module purge` — it strips the external
# MODULEPATH that provides the conda module. Loading it sets $CONDA_HOME + PATH.
module load conda/2025.09 || module load conda
source "$CONDA_HOME/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

# -------------------------------------------------------------------------
# 1) Launch the vLLM OpenAI-compatible server in the background.
# -------------------------------------------------------------------------
echo "starting vLLM for $MODEL on :$PORT ..."
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --served-model-name "$MODEL" \
    --port "$PORT" \
    --dtype bfloat16 \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization 0.90 \
    > "vllm_${SLURM_JOB_ID}.log" 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

# 2) Wait for the server to come up. First-time vLLM startup includes a
#    torch.compile pass (~90s) on top of weight load, so allow up to ~25 min.
#    (eval_harness.py also gates on readiness, so this is belt-and-suspenders;
#    its real job here is to bail early if vLLM dies during startup.)
echo "waiting for vLLM endpoint ..."
for i in $(seq 1 300); do
    if curl -sf "http://localhost:${PORT}/v1/models" >/dev/null 2>&1; then
        echo "vLLM is up after ~$((i*5))s"; break
    fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "vLLM died during startup; see vllm_${SLURM_JOB_ID}.log"; exit 1
    fi
    sleep 5
done

# 3) Run the eval client + Z3 grading (same env), over ALL datasets/*.jsonl.
cd "$PROJECT_DIR"
python eval_harness.py \
    --model "$MODEL" \
    --base-url "http://localhost:${PORT}/v1" \
    --api-key EMPTY \
    --n "$N" \
    --temperature "$TEMP" \
    --workers "$WORKERS" \
    --max-tokens "$MAXTOK" \
    --out "eval_${SLURM_JOB_ID}.jsonl"

echo "done. results: eval_${SLURM_JOB_ID}.jsonl ; server log: vllm_${SLURM_JOB_ID}.log"
