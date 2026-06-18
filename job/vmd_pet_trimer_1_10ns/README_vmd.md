# VMD PET trimer 1-10 ns viewer

This folder contains VMD-ready files for the PET trimer structures:

```text
pet_trimer_md_1_10ns.xyz
pet_trimer_orca_opt_1_10ns.xyz
load_pet_md_1_10ns.tcl
load_pet_orca_opt_1_10ns.tcl
```

Use VMD from this folder:

```bash
vmd -e load_pet_md_1_10ns.tcl
vmd -e load_pet_orca_opt_1_10ns.tcl
```

Frame mapping:

```text
frame 0 = 01ns
frame 1 = 02ns
...
frame 9 = 10ns
```

`pet_trimer_md_1_10ns.xyz` uses the PET trimer conformations extracted from
the MD trajectory before ORCA optimization.

`pet_trimer_orca_opt_1_10ns.xyz` uses the final ORCA-optimized PET trimer
structures used for COSMORS calculations.
