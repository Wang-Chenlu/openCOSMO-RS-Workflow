#!/usr/bin/env bash
set -euo pipefail

echo "ORCA convergence check:"
grep -H "THE OPTIMIZATION HAS CONVERGED" [0-9][0-9]ns/pet_*ns_opt.out || true

echo
echo "ORCA normal termination check:"
grep -H "ORCA TERMINATED NORMALLY" [0-9][0-9]ns/pet_*ns_opt.out || true

echo
echo "Optimization trajectories:"
ls -lh [0-9][0-9]ns/pet_*ns_opt_trj.xyz 2>/dev/null || true
