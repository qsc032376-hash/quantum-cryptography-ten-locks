#!/bin/bash
#SBATCH --job-name=tier08-osc
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:08:00
#SBATCH --output=logs/tier08-%j.out
set -euo pipefail
: "${T8_VENV:?}" "${T8_SEED:?}" "${T8_VARIANT:?}" "${T8_RESULTS:?}"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
source "$T8_VENV/bin/activate"
if [ "$T8_SEED" = unseeded ]; then
  srun python -B hpc/tier08_osc/run_trial.py --variant "$T8_VARIANT" --unseeded --output "$T8_RESULTS/$T8_VARIANT-unseeded.json"
else
  srun python -B hpc/tier08_osc/run_trial.py --variant "$T8_VARIANT" --seed "$T8_SEED" --output "$T8_RESULTS/$T8_VARIANT-$T8_SEED.json"
fi
