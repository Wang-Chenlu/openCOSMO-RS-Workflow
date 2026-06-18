#!/bin/bash
#SBATCH -J opt_ipa
#SBATCH -N 1
#SBATCH -n 4
#SBATCH -p wzhcnormal

module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`

${EXEC} 33-C3H8O_opt.inp > 33-C3H8O_opt.out
