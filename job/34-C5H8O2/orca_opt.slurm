#!/bin/bash
#SBATCH -J opt_gvl
#SBATCH -N 1
#SBATCH -n 4
#SBATCH -p wzhcnormal

module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`

${EXEC} 34-C5H8O2_opt.inp > 34-C5H8O2_opt.out
