# PET openCOSMO-RS workflow

This repository contains a reproducible workflow for estimating PET trimer
solubility in GVL with ORCA-generated `.orcacosmo` files and
`openCOSMO-RS_py`.

The current workspace is organized as:

```text
openCOSMO/   reference notes; third-party PDFs/source are intentionally omitted
test/        official paracetamol/openCOSMO-RS example reproduction
job/         PET production workflow, ORCA inputs, COSMORS files, results
```

## Main results

The repository keeps only the PET-in-GVL results. The recommended comparison
metric is `g_per_g_iter`, because it solves the composition-dependent
openCOSMO-RS activity coefficient equation instead of using only the
infinite-dilution approximation.

| Solvent | 25 C mean g/g_iter | 100 C mean g/g_iter |
|---|---:|---:|
| GVL | 0.104234 | 0.632521 |

Full summary:

```text
job/pet_solubility_25C_100C_summary.csv
```

## Key scripts

Recalculate 25 C GVL:

```powershell
python job\orca_full_workflow\12_calculate_pet_1_10ns_solubility.py
```

Recalculate 100 C GVL:

```powershell
python job\orca_full_workflow\12_calculate_pet_1_10ns_solubility.py --temperature-k 373.15 --output-dir job\pet_1_10ns_solubility_results_373K
python job\orca_full_workflow\16_summarize_25C_100C_results.py
```

Prepare VMD PET trimer viewer files:

```powershell
python job\orca_full_workflow\17_prepare_vmd_pet_trimer_1_10ns.py
```

## Notes

- The external `openCOSMO-RS_py` source tree and literature PDFs are excluded
  from Git to avoid redistributing third-party/copyrighted materials and nested
  repositories.
- Raw MD trajectory dumps and large ORCA output logs are excluded. The smaller
  structures, inputs, COSMORS files, results, and scripts are kept.
- The ORCA COSMORS inputs use `COSMORS(ethanol)` following the OPI example, but
  the PET calculations use only `*.solute.orcacosmo` files in openCOSMO-RS.
