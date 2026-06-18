# ORCA to openCOSMO-RS Solubility Workflow

This folder follows the local PDF tutorial, but splits the workflow into
reproducible command-line steps.

## Step 0 - Environment

The current machine does not expose an `orca` command or the Python `opi`
package in the active shell. Step 1 therefore needs to be run from your
ORCA/OPI environment.

The openCOSMO-RS post-processing steps use the local checkout at:

```text
../openCOSMO-RS_py
```

## Step 1 - Generate ORCA COSMO files

Run this only after ORCA and OPI are available:

```powershell
python orca_full_workflow\01_run_orca_with_opi.py --ncores 4 --solvent ethanol
```

If you have ORCA as a command-line executable but do not use OPI, first write
direct ORCA input files:

```powershell
python orca_full_workflow\00_write_direct_orca_inputs.py --ncores 4 --solvent ethanol
```

Then run the printed `orca *.inp > *.out` commands from the generated directory.

For a SLURM supercomputer, prepare a submission package:

```powershell
python orca_full_workflow\04_prepare_slurm_package.py `
  --partition wzhcnormal `
  --ncores 4
```

Upload the generated `orca_hpc_package` directory to the cluster and run:

```bash
sbatch orca.slurm
bash check_results.sh
```

The current cluster template follows the example files provided by the user:

```bash
module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`
```

`orca.slurm` is an array job for:

```text
water_reference.inp
paracetamol.inp
```

Alternatively, submit the two jobs separately:

```bash
sbatch run_water_reference.slurm
sbatch run_paracetamol.slurm
```

It runs two ORCA calculations:

```text
water_reference + !COSMORS(ethanol)
paracetamol     + !COSMORS(ethanol)
```

Expected outputs:

```text
opencosmors_orca/water_reference.solute.orcacosmo   # water
opencosmors_orca/water_reference.solvent.orcacosmo  # ethanol
opencosmors_orca/paracetamol.solute.orcacosmo       # paracetamol
```

## Step 2 - Inspect the ORCA outputs

```powershell
python orca_full_workflow\02_inspect_orcacosmo.py
```

If generated ORCA files are present, the script inspects them. Otherwise it
falls back to the official test `.orcacosmo` files bundled with
`openCOSMO-RS_py`.

## Step 3 - Calculate solubility

```powershell
python orca_full_workflow\03_calculate_solubility_from_orca_outputs.py
```

This uses:

```text
Delta H fusion = 27.1 kJ/mol
T fusion       = 443.6 K
T calculation  = 298.15 K
```

for the paracetamol example. Replace these values for a different solid
solute.

## Using your own molecule

1. Put the solute XYZ structure in `structures/`.
2. Add or adapt an ORCA/OPI calculation in `01_run_orca_with_opi.py`.
3. Use the generated solute `.orcacosmo` as `--solute`.
4. Use generated or existing solvent `.orcacosmo` files as `--solvent`.
5. Provide the solute's own fusion enthalpy and fusion temperature.

Example:

```powershell
python orca_full_workflow\03_calculate_solubility_from_orca_outputs.py `
  --solute path\to\solute.orcacosmo `
  --solvent Water=path\to\water.orcacosmo `
  --solvent Ethanol=path\to\ethanol.orcacosmo `
  --delta-h-fusion-kj-mol 27.1 `
  --t-fusion-k 443.6 `
  --temperature-k 298.15
```
