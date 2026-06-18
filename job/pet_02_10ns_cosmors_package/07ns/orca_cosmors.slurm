#!/bin/bash
#SBATCH -J cosmo_pet_07ns
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p wzhcnormal

module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`

${EXEC} pet_07ns_cosmors.inp > pet_07ns_cosmors.out
