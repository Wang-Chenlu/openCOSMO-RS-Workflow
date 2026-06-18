#!/bin/bash
#SBATCH -J opt_pet_01ns
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p wzhcnormal

module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`

${EXEC} pet_01ns_opt.inp > pet_01ns_opt.out
