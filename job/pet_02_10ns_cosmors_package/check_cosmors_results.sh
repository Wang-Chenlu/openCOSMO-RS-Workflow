#!/usr/bin/env bash
set -euo pipefail

echo "ORCA normal termination check:"
grep -H "ORCA TERMINATED NORMALLY" [0-9][0-9]ns/pet_*ns_cosmors.out || true

echo
echo ".orcacosmo files:"
ls -lh [0-9][0-9]ns/*.orcacosmo 2>/dev/null || true
