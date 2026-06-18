#!/usr/bin/env python3
"""Inspect ORCA .orcacosmo files before using them in openCOSMO-RS."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OPEN_COSMORS_ROOT = ROOT.parent / "openCOSMO" / "openCOSMO-RS_py"
LOCAL_OPEN_COSMORS_SRC = OPEN_COSMORS_ROOT / "src"
if LOCAL_OPEN_COSMORS_SRC.exists():
    sys.path.insert(0, str(LOCAL_OPEN_COSMORS_SRC))

from opencosmorspy.input_parsers import SigmaProfileParser  # noqa: E402


def default_files() -> list[Path]:
    generated = ROOT / "opencosmors_orca"
    generated_files = [
        generated / "water_reference.solute.orcacosmo",
        generated / "water_reference.solvent.orcacosmo",
        generated / "paracetamol.solute.orcacosmo",
    ]
    if all(path.is_file() for path in generated_files):
        return generated_files

    official = OPEN_COSMORS_ROOT / "tests" / "COSMO_ORCA"
    return [
        official / "water.orcacosmo",
        official / "ethanol.orcacosmo",
        official / "acetaminophen.orcacosmo",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print descriptors from .orcacosmo files.")
    parser.add_argument("files", nargs="*", help="Optional .orcacosmo files to inspect.")
    return parser.parse_args()


def inspect_file(path: Path) -> None:
    spp = SigmaProfileParser(str(path))
    sigmas, areas = spp.cluster_and_create_sigma_profile()
    spp.calculate_sigma_moments()

    nonzero_bins = int(np.count_nonzero(areas))
    print(f"\n{path}")
    print(f"  atoms            : {len(spp['atm_nr'])}")
    print(f"  surface segments : {len(spp['seg_nr'])}")
    print(f"  sigma bins       : {nonzero_bins} nonzero / {len(sigmas)} total")
    print(f"  area             : {spp['area']:.6f} A^2")
    print(f"  volume           : {spp['volume']:.6f} A^3")
    print(f"  dielectric energy: {spp['energy_dielectric']:.6f} kJ/mol")
    print(f"  sigma moments    : {np.array2string(spp['sigma_moments'], precision=6)}")
    print(
        "  HB donor moments : "
        f"{np.array2string(spp['sigma_hydrogen_bond_donor_moments'][2:5], precision=6)}"
    )
    print(
        "  HB acceptor moments: "
        f"{np.array2string(spp['sigma_hydrogen_bond_acceptor_moments'][2:5], precision=6)}"
    )


def main() -> int:
    args = parse_args()
    files = [Path(path).resolve() for path in args.files] if args.files else default_files()
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
        inspect_file(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
