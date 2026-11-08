#!/bin/bash
#SBATCH --job-name=tier05-osc
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:08:00
#SBATCH --output=logs/tier05-%j.out
set -euo pipefail
: "${T5_VENV:?}" "${T5_SEED:?}" "${T5_VARIANT:?}" "${T5_RESULTS:?}"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
source "$T5_VENV/bin/activate"
srun python -B hpc/tier05_osc/run_trial.py --variant "$T5_VARIANT" --seed "$T5_SEED" --output "$T5_RESULTS/$T5_VARIANT-$T5_SEED.json"
