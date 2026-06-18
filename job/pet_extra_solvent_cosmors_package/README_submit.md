# Extra solvent ORCA COSMORS package

This package is generated from the final frames of the completed ORCA geometry
optimizations for:

- 32-C5H9NO, written as `nmp`
- 33-C3H8O, written as `isopropanol`

Submit on the cluster:

```bash
cd pet_extra_solvent_cosmors_package
bash submit_all_cosmors.sh
```

After all jobs finish, check:

```bash
bash check_cosmors_results.sh
```

Files needed by openCOSMO-RS:

```text
nmp.solute.orcacosmo
isopropanol.solute.orcacosmo
```
