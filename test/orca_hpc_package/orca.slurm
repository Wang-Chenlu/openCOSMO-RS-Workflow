#!/bin/bash
#SBATCH -J orca_cosmors
#SBATCH -N 1
#SBATCH -n 4
#SBATCH -p wzhcnormal
#SBATCH --array=0-1

module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`

INPUTS=(water_reference.inp paracetamol.inp)
INPUT=${INPUTS[$SLURM_ARRAY_TASK_ID]}
BASE=${INPUT%.inp}

${EXEC} ${INPUT} > ${BASE}.out
