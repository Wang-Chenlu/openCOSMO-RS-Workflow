#!/usr/bin/env bash
set -euo pipefail

echo "ORCA normal termination check:"
grep -H "ORCA TERMINATED NORMALLY" *.out || true

echo
echo ".orcacosmo files:"
ls -lh *.orcacosmo
