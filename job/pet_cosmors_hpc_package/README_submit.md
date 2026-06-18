# PET/GVL/Formic Acid ORCA COSMORS Package

This package was generated from the final frames of the completed ORCA geometry
optimizations.

Submit on the cluster:

```bash
cd pet_cosmors_hpc_package
bash submit_all_cosmors.sh
```

After all jobs finish, check:

```bash
bash check_cosmors_results.sh
```

Expected files needed by openCOSMO-RS:

```text
pet_trimer.solute.orcacosmo
gvl.solute.orcacosmo
formic_acid.solute.orcacosmo
```

The extra `*.solvent.orcacosmo` files generated from `COSMORS(ethanol)` are
ethanol reference files and are not used for PET-in-GVL/formic-acid solubility.
