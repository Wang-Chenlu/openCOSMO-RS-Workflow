# PET openCOSMO-RS workflow

This repository contains a reproducible workflow for estimating PET trimer
solubility with ORCA-generated `.orcacosmo` files and `openCOSMO-RS_py`.

The current workspace is organized as:

```text
openCOSMO/   reference notes and generated Chinese manual
test/        official paracetamol/openCOSMO-RS example reproduction
job/         PET production workflow, ORCA inputs, COSMORS files, results
```

## Main results

The recommended comparison metric is `g_per_g_iter`, because NMP can exceed the
physical range in the infinite-dilution approximation.

| Solvent | 25 C mean g/g_iter | 100 C mean g/g_iter |
|---|---:|---:|
| GVL | 0.104234 | 0.632521 |
| NMP | 0.823519 | 1.45845 |
| CH2O2 / formic acid | 0.00108275 | 0.00225337 |
| ISOPROPANOL | 0.0212363 | 0.522767 |

Full summary:

```text
job/pet_solubility_25C_100C_summary.csv
```

## Key scripts

Recalculate 25 C GVL/formic acid:

```powershell
python job\orca_full_workflow\12_calculate_pet_1_10ns_solubility.py
```

Recalculate 25 C NMP/isopropanol:

```powershell
python job\orca_full_workflow\14_calculate_pet_extra_solvents_solubility.py
```

Recalculate 100 C results:

```powershell
python job\orca_full_workflow\12_calculate_pet_1_10ns_solubility.py --temperature-k 373.15 --output-dir job\pet_1_10ns_solubility_results_373K
python job\orca_full_workflow\14_calculate_pet_extra_solvents_solubility.py --temperature-k 373.15 --output-dir job\pet_extra_solvent_solubility_results_373K
python job\orca_full_workflow\16_summarize_25C_100C_results.py
```

Generate Chinese PPTs:

```powershell
python job\orca_full_workflow\15_make_latest_cn_ppts.py
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
  structures, inputs, COSMORS files, results, scripts, and PPT summaries are
  kept.
- The ORCA COSMORS inputs use `COSMORS(ethanol)` following the OPI example, but
  the PET calculations use only `*.solute.orcacosmo` files in openCOSMO-RS.

