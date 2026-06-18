# Folder layout

The workspace is organized into three top-level folders:

```text
openCOSMO/
test/
job/
```

## openCOSMO

Reference materials and the official openCOSMO-RS_py source code:

```text
openCOSMO/openCOSMO-RS_py/
openCOSMO/openCOSMO-RS - OPI nightly Docs.pdf
openCOSMO/Müller 等 - 2025 - Predicting solvation free energies for neutral molecules in any solvent with openCOSMO-RS.pdf
```

`openCOSMO/_move_residue_openCOSMO-RS_py/` is a leftover `.git` directory from
the folder move. It is not used by the calculation scripts.

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

PET production workflow files, ORCA inputs/outputs, COSMORS packages, and
solubility results:

```text
job/31-CH2O2/
job/32-C5H9NO/
job/33-C3H8O/
job/34-C5H8O2/
job/35-PET/
job/orca_full_workflow/
job/pet_cosmors_hpc_package/
job/pet_02_10ns_cosmors_package/
job/pet_1_10ns_solubility_results/
job/pet_extra_solvent_solubility_results/
```

Recalculate PET solubility for GVL/formic acid:

```powershell
python job\orca_full_workflow\12_calculate_pet_1_10ns_solubility.py
```

Recalculate PET solubility for NMP/isopropanol:

```powershell
python job\orca_full_workflow\14_calculate_pet_extra_solvents_solubility.py
```

