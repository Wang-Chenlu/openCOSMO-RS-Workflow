#!/usr/bin/env bash
set -euo pipefail

(cd 31-CH2O2 && sbatch orca_opt.slurm)
(cd 34-C5H8O2 && sbatch orca_opt.slurm)
(cd 35-PET && sbatch orca_opt.slurm)
