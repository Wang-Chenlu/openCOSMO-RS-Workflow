#!/usr/bin/env bash
set -euo pipefail

for dir in [0-9][0-9]ns; do
  echo "Submitting ${dir}/orca_cosmors.slurm"
  (cd "${dir}" && sbatch orca_cosmors.slurm)
done
