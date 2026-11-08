#!/bin/bash
#SBATCH --job-name=tier09-candidate
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=logs/%x-%j.out

set -euo pipefail
: "${TIER09_VENV:?Set TIER09_VENV to a tested virtual environment}"
: "${TIER09_HARNESS:?Set TIER09_HARNESS to the pinned clean harness checkout}"
: "${TIER09_RESULTS:?Set TIER09_RESULTS to an existing private directory}"
: "${TIER09_SEED:?Set TIER09_SEED to a predetermined seed}"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
source "$TIER09_VENV/bin/activate"
srun python hpc/osc/tier09_benchmark.py --version candidate --seed "$TIER09_SEED" --harness "$TIER09_HARNESS" --output-dir "$TIER09_RESULTS"
