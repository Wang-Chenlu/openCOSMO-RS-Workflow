#!/usr/bin/env bash
set -euo pipefail

for script in run_*.slurm; do
  echo "Submitting ${script}"
  sbatch "${script}"
done
