#!/bin/bash
#SBATCH -J cosmo_ipa
#SBATCH -N 1
#SBATCH -n 4
#SBATCH -p wzhcnormal

module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`

${EXEC} isopropanol.inp > isopropanol.out
