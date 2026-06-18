# PET 1-10 ns ORCA Optimization Package

This package contains PET-only structures extracted from `35-PET/eq1.xyz` at
1-10 ns. The LAMMPS timestep is assumed to be 2 fs, so:

```text
1 ns = 500000 steps
10 ns = 5000000 steps
```

The package is split into ten folders:

```text
01ns/
02ns/
...
10ns/
```

Submit all jobs on the cluster:

```bash
cd pet_1_10ns_opt_package
bash submit_all_pet_frames.sh
```

After jobs finish:

```bash
bash check_opt_results.sh
```

Each job requests 64 cores and uses:

```text
M062X def2-SVP D3zero Opt noautostart miniprint pal64
```

`frame_lx_summary.csv` records whether the box length used for unwrapping came
from `35-PET/log` or was estimated from the coordinate span of that XYZ frame.
