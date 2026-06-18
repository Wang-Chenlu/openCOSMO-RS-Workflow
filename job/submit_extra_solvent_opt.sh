#!/usr/bin/env bash
set -euo pipefail

(cd 32-C5H9NO && sbatch orca_opt.slurm)
(cd 33-C3H8O && sbatch orca_opt.slurm)
