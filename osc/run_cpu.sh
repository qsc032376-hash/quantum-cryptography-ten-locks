#!/usr/bin/env bash
#SBATCH --job-name=qiskit-smoke
#SBATCH --account=PAS3574
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --output=osc/logs/smoke-%j.out
#SBATCH --error=osc/logs/smoke-%j.err
#
# Qiskit Aer CPU smoke test for OSC Pitzer.
#
# Run it directly and it submits itself with sbatch, so the actual work always
# happens on a compute node:
#
#     ./osc/run_cpu.sh            # or: sbatch osc/run_cpu.sh
#
# Overrides (optional):
#     OSC_ACCOUNT=PAS3574 OSC_PYTHON_MODULE=python/3.12 \
#     OSC_VENV=$HOME/.venvs/qiskit-ten-locks ./osc/run_cpu.sh
#
# Never put passwords, project access codes, tokens or SSH keys in this file.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export OSC_ACCOUNT="${OSC_ACCOUNT:-PAS3574}"
export OSC_PYTHON_MODULE="${OSC_PYTHON_MODULE:-python/3.12}"
export OSC_VENV="${OSC_VENV:-$HOME/.venvs/qiskit-ten-locks}"

# ---- login-node guard: submit instead of computing here --------------------
if [[ -z "${SLURM_JOB_ID:-}" ]]; then
    mkdir -p "$REPO_ROOT/osc/logs"
    echo "Submitting CPU smoke test to Slurm (account=$OSC_ACCOUNT, 4 CPU, 16G, 20 min)"
    # Forward user overrides into the batch job.
    exec sbatch \
        --account="$OSC_ACCOUNT" \
        --export="ALL,OSC_ACCOUNT,OSC_PYTHON_MODULE,OSC_VENV" \
        "$0" "$@"
fi

# ---- running on a compute node --------------------------------------------
cd "$REPO_ROOT"

echo "host:            $(hostname)"
echo "date:            $(date -Is)"
echo "job:             ${SLURM_JOB_ID:-?} (${SLURM_JOB_NAME:-?})"
echo "cpus:            ${SLURM_CPUS_PER_TASK:-?}"
echo "memory:          ${SLURM_MEM_PER_NODE:-?} MB"
echo "python module:   $OSC_PYTHON_MODULE"
echo "virtualenv:      $OSC_VENV"

if command -v module >/dev/null 2>&1; then
    # shellcheck disable=SC1090
    module load "$OSC_PYTHON_MODULE" || echo "warning: could not load $OSC_PYTHON_MODULE" >&2
fi

if [[ ! -f "$OSC_VENV/bin/activate" ]]; then
    echo "FAIL: virtualenv not found at $OSC_VENV" >&2
    echo "Create it once on the login node; see osc/README.md." >&2
    exit 2
fi
# shellcheck disable=SC1091
source "$OSC_VENV/bin/activate"

python -V
exec python osc/smoke_test.py
