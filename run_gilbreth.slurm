#!/bin/bash
# =============================================================================
# Gilbreth (Purdue RCAC) job: serve Qwen with vLLM, then run the constraint-gen
# eval against it and grade every generation by Z3 logical equivalence.
#
# FILL IN the four <...> placeholders before submitting:  sbatch run_gilbreth.slurm
# =============================================================================
#SBATCH -A <ALLOCATION>            # <-- your Gilbreth queue/allocation (e.g. standby, or a PI account)
#SBATCH -p <PARTITION>             # <-- GPU partition name (check `slist` / `sinfo`)
#SBATCH --gres=gpu:1               # 1 GPU; a 9B model in bf16 (~18GB + KV cache) needs >=24GB (A100/H100; NOT a 16GB V100)
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --job-name=qwen-cgen-eval
#SBATCH --output=eval_%j.out
#SBATCH --error=eval_%j.err

set -euo pipefail

# ---- knobs (override at submit time, e.g. `MODEL=/scratch/.../qwen sbatch ...`) ----
PROJECT_DIR="<PROJECT_DIR>"        # <-- absolute path to ".../OptiChat_test/constraint generation data" on Gilbreth
MODEL="${MODEL:-Qwen/Qwen3.5-9B-Instruct}"   # <-- exact HF repo id OR a local/scratch path (see note 1 below)
PORT="${PORT:-8000}"
VLLM_ENV="${VLLM_ENV:-vllm}"       # conda env that has vllm
GRADE_ENV="${GRADE_ENV:-opti}"     # conda env that has pyomo + z3-solver + openai
N="${N:-1}"                        # samples per record (pass@k)
TEMP="${TEMP:-0.0}"

echo "host: $(hostname)  gpu:"; nvidia-smi -L || true

# RCAC usually uses Lmod + a shared anaconda; adjust if your setup differs.
module purge || true
module load anaconda || true
source "$(conda info --base)/etc/profile.d/conda.sh"

# -------------------------------------------------------------------------
# 1) Launch the vLLM OpenAI-compatible server in the background.
#    NOTE 1 (Gilbreth gotcha): compute nodes typically have NO internet, so a
#    bare HF repo id will fail to download. Pre-stage weights on a login node:
#       huggingface-cli download Qwen/Qwen3.5-9B-Instruct --local-dir $SCRATCH/qwen35-9b
#    then submit with  MODEL=$SCRATCH/qwen35-9b  and set HF_HUB_OFFLINE=1.
# -------------------------------------------------------------------------
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
conda activate "$VLLM_ENV"
echo "starting vLLM for $MODEL on :$PORT ..."
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --served-model-name "$MODEL" \
    --port "$PORT" \
    --dtype bfloat16 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.90 \
    > "vllm_${SLURM_JOB_ID}.log" 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

# 2) Wait for the server to come up (up to ~10 min for weight load).
echo "waiting for vLLM endpoint ..."
for i in $(seq 1 120); do
    if curl -sf "http://localhost:${PORT}/v1/models" >/dev/null 2>&1; then
        echo "vLLM is up after ~$((i*5))s"; break
    fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "vLLM died during startup; see vllm_${SLURM_JOB_ID}.log"; exit 1
    fi
    sleep 5
done

# 3) Run the eval client + Z3 grading in the grading env.
conda activate "$GRADE_ENV"
cd "$PROJECT_DIR"
python eval_harness.py \
    --model "$MODEL" \
    --base-url "http://localhost:${PORT}/v1" \
    --api-key EMPTY \
    --n "$N" \
    --temperature "$TEMP" \
    --workers 8 \
    --out "eval_${SLURM_JOB_ID}.jsonl"

echo "done. results: eval_${SLURM_JOB_ID}.jsonl ; server log: vllm_${SLURM_JOB_ID}.log"
