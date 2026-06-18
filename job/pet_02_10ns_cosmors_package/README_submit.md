# PET 02-10 ns ORCA COSMORS Package

This package contains COSMORS single-point calculations prepared from the final
optimized geometries of PET frames 02-10 ns.

`01ns` is intentionally excluded because it was already calculated previously.

Submit on the cluster:

```bash
cd pet_02_10ns_cosmors_package
bash submit_all_cosmors.sh
```

After jobs finish:

```bash
bash check_cosmors_results.sh
```

Each job requests 64 cores and uses:

```text
BLYP def2-SVP noautostart miniprint pal64 COSMORS(ethanol)
```

For each frame, use the generated `*.solute.orcacosmo` file as a PET conformer
input for later openCOSMO-RS conformer averaging or per-frame comparison.
