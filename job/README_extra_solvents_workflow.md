# PET solubility in 32-C5H9NO and 33-C3H8O

This workflow adds two extra solvents to the existing PET/openCOSMO-RS workflow.

## 1. Geometry optimization on the cluster

Upload these folders/files to the cluster together with the existing workflow:

```text
32-C5H9NO/32-C5H9NO.xyz
32-C5H9NO/32-C5H9NO_opt.inp
32-C5H9NO/orca_opt.slurm
33-C3H8O/33-C3H8O.xyz
33-C3H8O/33-C3H8O_opt.inp
33-C3H8O/orca_opt.slurm
submit_extra_solvent_opt.sh
check_extra_solvent_opt.sh
```

Submit:

```bash
bash submit_extra_solvent_opt.sh
```

Check:

```bash
bash check_extra_solvent_opt.sh
```

Download these files after normal termination:

```text
32-C5H9NO/32-C5H9NO_opt.out
32-C5H9NO/32-C5H9NO_opt_trj.xyz
33-C3H8O/33-C3H8O_opt.out
33-C3H8O/33-C3H8O_opt_trj.xyz
```

## 2. Prepare COSMORS single-point jobs locally

After downloading the optimization outputs, run locally:

```powershell
python orca_full_workflow\13_prepare_extra_solvent_cosmors_package.py
```

This creates:

```text
pet_extra_solvent_cosmors_package/
```

Upload that folder to the cluster.

## 3. COSMORS single-point jobs on the cluster

Submit:

```bash
cd pet_extra_solvent_cosmors_package
bash submit_all_cosmors.sh
```

Check:

```bash
bash check_cosmors_results.sh
```

Download the needed files:

```text
pet_extra_solvent_cosmors_package/nmp.solute.orcacosmo
pet_extra_solvent_cosmors_package/isopropanol.solute.orcacosmo
```

## 4. openCOSMO-RS solubility calculation

Run locally after downloading the two `.solute.orcacosmo` files:

```powershell
python orca_full_workflow\14_calculate_pet_extra_solvents_solubility.py
```

Default temperature is 298.15 K. To calculate at another temperature:

```powershell
python orca_full_workflow\14_calculate_pet_extra_solvents_solubility.py --temperature-k 453.15
```

Outputs:

```text
pet_extra_solvent_solubility_results/pet_extra_solvent_solubility_per_frame.csv
pet_extra_solvent_solubility_results/pet_extra_solvent_solubility_summary.csv
```

