#!/usr/bin/env python3
"""Write direct ORCA input files for the COSMORS step.

Use this if you have ORCA available as a command-line executable but do not use
OPI. The input keyword mirrors the local PDF tutorial's OPI call:

    calc.input.add_arbitrary_string("!COSMORS(ethanol)")
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = Path(__file__).resolve().parent
STRUCTURE_DIR = WORKFLOW_DIR / "structures"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create ORCA .inp files for COSMORS.")
    parser.add_argument(
        "--workdir",
        default=str(ROOT / "opencosmors_orca_direct"),
        help="Directory where ORCA input files will be written.",
    )
    parser.add_argument("--solvent", default="ethanol", help="Solvent in !COSMORS(...).")
    parser.add_argument("--ncores", type=int, default=4, help="Number of ORCA cores.")
    parser.add_argument(
        "--method",
        default="BLYP def2-SVP noautostart miniprint",
        help="ORCA method keywords before palN and COSMORS(...).",
    )
    return parser.parse_args()


def read_xyz_coordinates(xyz_source: Path) -> list[str]:
    lines = xyz_source.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3:
        raise ValueError(f"Invalid XYZ file: {xyz_source}")
    return [line for line in lines[2:] if line.strip()]


def write_input(
    workdir: Path,
    basename: str,
    xyz_source: Path,
    solvent: str,
    ncores: int,
    method: str,
) -> Path:
    xyz_target = workdir / xyz_source.name
    shutil.copy2(xyz_source, xyz_target)

    coordinates = "\n".join(read_xyz_coordinates(xyz_source))
    inp_path = workdir / f"{basename}.inp"
    inp_text = f"""! {method} pal{ncores} COSMORS({solvent})
* xyz 0 1
{coordinates}
*
"""
    inp_path.write_text(inp_text, encoding="utf-8")
    return inp_path


def main() -> int:
    args = parse_args()
    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    inputs = [
        write_input(
            workdir,
            basename="water_reference",
            xyz_source=STRUCTURE_DIR / "water.xyz",
            solvent=args.solvent,
            ncores=args.ncores,
            method=args.method,
        ),
        write_input(
            workdir,
            basename="paracetamol",
            xyz_source=STRUCTURE_DIR / "paracetamol.xyz",
            solvent=args.solvent,
            ncores=args.ncores,
            method=args.method,
        ),
    ]

    print("Wrote ORCA input files:")
    for inp in inputs:
        print(f"  {inp}")

    print("\nRun from that directory with:")
    for inp in inputs:
        print(f"  orca {inp.name} > {inp.with_suffix('.out').name}")

    print("\nExpected .orcacosmo files after successful ORCA runs:")
    for path in [
        workdir / "water_reference.solute.orcacosmo",
        workdir / "water_reference.solvent.orcacosmo",
        workdir / "paracetamol.solute.orcacosmo",
    ]:
        print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
