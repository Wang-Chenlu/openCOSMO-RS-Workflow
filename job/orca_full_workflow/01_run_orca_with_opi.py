#!/usr/bin/env python3
"""Run the ORCA/OPI part of the openCOSMO-RS solubility workflow.

This follows the OPI tutorial pattern:
    Calculator -> !COSMORS(ethanol) -> ORCA -> *.orcacosmo files

The script needs an ORCA/OPI Python environment. It will not work in a plain
Python environment where the `opi` package and ORCA executable are unavailable.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = Path(__file__).resolve().parent
STRUCTURE_DIR = WORKFLOW_DIR / "structures"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate .orcacosmo files with ORCA/OPI.")
    parser.add_argument(
        "--workdir",
        default=str(ROOT / "opencosmors_orca"),
        help="Directory where ORCA input/output files will be written.",
    )
    parser.add_argument(
        "--solvent",
        default="ethanol",
        help="Solvent name used in ORCA's !COSMORS(...) keyword. Default: ethanol.",
    )
    parser.add_argument("--ncores", type=int, default=4, help="ORCA CPU cores.")
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Do not delete an existing workdir before running.",
    )
    return parser.parse_args()


def require_opi():
    try:
        from opi.core import Calculator
        from opi.output.core import Output
        from opi.input.structures.structure import Structure
    except ModuleNotFoundError as exc:
        print(
            "OPI is not available in this Python environment.\n"
            "Run this script from the ORCA/OPI environment described in the PDF, "
            "or install/configure OPI according to your ORCA installation.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    return Calculator, Output, Structure


def setup_calc(calculator_cls, structure, basename: str, workdir: Path, solvent: str, ncores: int):
    calc = calculator_cls(basename=basename, working_dir=workdir)
    calc.structure = structure
    calc.input.add_arbitrary_string(f"!COSMORS({solvent})")
    calc.input.ncores = ncores
    return calc


def run_calc(calc, output_cls) -> None:
    calc.write_input()
    print(f"Running ORCA calculation: {calc.basename}")
    calc.run()
    output = calc.get_output()
    if not output.terminated_normally():
        raise RuntimeError(f"ORCA did not terminate normally for {calc.basename}")
    print(f"Finished ORCA calculation: {calc.basename}")


def main() -> int:
    args = parse_args()
    Calculator, Output, Structure = require_opi()

    workdir = Path(args.workdir).resolve()
    if workdir.exists() and not args.keep_workdir:
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    water_xyz = STRUCTURE_DIR / "water.xyz"
    paracetamol_xyz = STRUCTURE_DIR / "paracetamol.xyz"

    water_structure = Structure.from_xyz(water_xyz)
    paracetamol_structure = Structure.from_xyz(paracetamol_xyz)

    water_calc = setup_calc(
        Calculator,
        water_structure,
        basename="water_reference",
        workdir=workdir,
        solvent=args.solvent,
        ncores=args.ncores,
    )
    run_calc(water_calc, Output)

    paracetamol_calc = setup_calc(
        Calculator,
        paracetamol_structure,
        basename="paracetamol",
        workdir=workdir,
        solvent=args.solvent,
        ncores=args.ncores,
    )
    run_calc(paracetamol_calc, Output)

    print("\nExpected files for the next steps:")
    for path in [
        workdir / "water_reference.solute.orcacosmo",
        workdir / "water_reference.solvent.orcacosmo",
        workdir / "paracetamol.solute.orcacosmo",
    ]:
        print(f"  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
