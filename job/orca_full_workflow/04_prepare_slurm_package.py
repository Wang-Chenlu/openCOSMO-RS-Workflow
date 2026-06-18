#!/usr/bin/env python3
"""Prepare a SLURM submission package for ORCA COSMORS calculations."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SLURM_TEMPLATE = """#!/bin/bash
#SBATCH -J {job_name}
#SBATCH -N 1
#SBATCH -n {ncores}
#SBATCH -p {partition}

{module_lines}
EXEC=`which orca`

${{EXEC}} {input_name} > {base_name}.out
"""


SUBMIT_ALL_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail

for script in run_*.slurm; do
  echo "Submitting $script"
  sbatch "$script"
done
"""


CHECK_RESULTS_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail

echo "ORCA normal termination check:"
grep -H "ORCA TERMINATED NORMALLY" *.out || true

echo
echo ".orcacosmo files:"
ls -lh *.orcacosmo
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a SLURM package for ORCA inputs.")
    parser.add_argument(
        "--input-dir",
        default=str(ROOT / "opencosmors_orca_direct"),
        help="Directory containing .inp and .xyz files.",
    )
    parser.add_argument(
        "--package-dir",
        default=str(ROOT / "orca_hpc_package"),
        help="Output directory for the SLURM package.",
    )
    parser.add_argument("--ncores", type=int, default=4, help="SLURM cpus-per-task.")
    parser.add_argument("--mem", default="8G", help="Kept for compatibility; not used by the default cluster template.")
    parser.add_argument("--time", default="02:00:00", help="Kept for compatibility; not used by the default cluster template.")
    parser.add_argument(
        "--partition",
        default="wzhcnormal",
        help="SLURM partition name. Change this to match your cluster.",
    )
    parser.add_argument(
        "--module-line",
        action="append",
        default=[],
        help=(
            "Line inserted before ORCA_CMD setup, e.g. "
            "--module-line \"module load orca/6.0.1\". Repeat for several lines."
        ),
    )
    parser.add_argument(
        "--orca-cmd",
        default="",
        help="Optional ORCA executable path inserted as export ORCA_CMD=...",
    )
    return parser.parse_args()


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def module_lines(args: argparse.Namespace) -> str:
    lines = list(args.module_line)
    if args.orca_cmd:
        lines.append(f"export PATH={shell_quote(str(Path(args.orca_cmd).resolve().parent))}:$PATH")
    if not lines:
        return "module purge\nsource /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh"
    return "\n".join(lines)


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    package_dir = Path(args.package_dir).resolve()

    if not input_dir.is_dir():
        raise FileNotFoundError(input_dir)

    inp_files = sorted(input_dir.glob("*.inp"))
    if not inp_files:
        raise FileNotFoundError(f"No .inp files found in {input_dir}")

    package_dir.mkdir(parents=True, exist_ok=True)

    for pattern in ["*.inp", "*.xyz"]:
        for source in input_dir.glob(pattern):
            shutil.copy2(source, package_dir / source.name)

    rendered_module_lines = module_lines(args)
    for inp_file in inp_files:
        base_name = inp_file.stem
        job_name = f"orca_{base_name}"
        slurm_text = SLURM_TEMPLATE.format(
            job_name=job_name,
            input_name=inp_file.name,
            base_name=base_name,
            ncores=args.ncores,
            partition=args.partition,
            module_lines=rendered_module_lines,
        )
        write_executable(package_dir / f"run_{base_name}.slurm", slurm_text)

    write_executable(package_dir / "submit_all.sh", SUBMIT_ALL_TEMPLATE)
    write_executable(package_dir / "check_results.sh", CHECK_RESULTS_TEMPLATE)

    print(f"Prepared SLURM package: {package_dir}")
    print("Contents to upload:")
    for path in sorted(package_dir.iterdir()):
        print(f"  {path.name}")
    print("\nOn the cluster:")
    print(f"  cd {package_dir.name}")
    print("  bash submit_all.sh")
    print("  bash check_results.sh")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
