#!/usr/bin/env bash
set -euo pipefail

for directory in 32-C5H9NO 33-C3H8O; do
  echo "== ${directory} =="
  grep -H "ORCA TERMINATED NORMALLY" "${directory}"/*_opt.out || true
  ls -lh "${directory}"/*_opt_trj.xyz || true
  echo
done
