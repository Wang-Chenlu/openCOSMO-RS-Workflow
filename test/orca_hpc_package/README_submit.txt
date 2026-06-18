Submit this package on the SLURM cluster.

Recommended single command:

  sbatch orca.slurm

This submits an array job for:

  water_reference.inp
  paracetamol.inp

The scripts use the cluster settings from the provided example:

  #SBATCH -N 1
  #SBATCH -n 4
  #SBATCH -p wzhcnormal
  module purge
  source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
  EXEC=`which orca`

Alternative separate submissions:

  sbatch run_water_reference.slurm
  sbatch run_paracetamol.slurm

After jobs finish:

  bash check_results.sh

Expected COSMO files:

  water_reference.solute.orcacosmo
  water_reference.solvent.orcacosmo
  paracetamol.solute.orcacosmo

