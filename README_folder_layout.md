# Folder layout

The workspace is organized into three top-level areas:

```text
openCOSMO/
test/
job/
```

## openCOSMO

Reference materials for openCOSMO-RS:

```text
openCOSMO/README.md
```

The official `openCOSMO-RS_py` source tree and literature PDFs are not tracked
in Git. Put them under `openCOSMO/` locally when reproducing the workflow.

## test

Official/example reproduction files:

```text
test/reproduce_official_solubility_example.py
test/calculate_solubility.py
test/opencosmors_orca_direct/
test/orca_hpc_package/
test/orca_hpc_results/
```

Run the official solubility reproduction from the workspace root:

```powershell
python test\reproduce_official_solubility_example.py
```

## job

PET/GVL production workflow files, ORCA inputs/outputs, COSMORS packages, and
solubility results:

```text
job/34-C5H8O2/
job/35-PET/
job/orca_full_workflow/
job/pet_cosmors_hpc_package/
job/pet_02_10ns_cosmors_package/
job/pet_1_10ns_solubility_results/
job/pet_1_10ns_solubility_results_373K/
```

Recalculate PET solubility for GVL:

```powershell
python job\orca_full_workflow\12_calculate_pet_1_10ns_solubility.py
```
