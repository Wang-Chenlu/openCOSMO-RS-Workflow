#!/bin/bash
#SBATCH -J opt_pet
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p wzhcnormal

module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`

${EXEC} 35-PET_opt.inp > 35-PET_opt.out
