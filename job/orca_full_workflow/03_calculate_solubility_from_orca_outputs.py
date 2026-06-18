#!/usr/bin/env python3
"""Calculate paracetamol solubility from ORCA-generated .orcacosmo files."""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy import constants
from scipy.optimize import brentq


ROOT = Path(__file__).resolve().parents[1]
OPEN_COSMORS_ROOT = ROOT.parent / "openCOSMO" / "openCOSMO-RS_py"
LOCAL_OPEN_COSMORS_SRC = OPEN_COSMORS_ROOT / "src"
if LOCAL_OPEN_COSMORS_SRC.exists():
    sys.path.insert(0, str(LOCAL_OPEN_COSMORS_SRC))

from opencosmorspy.cosmors import COSMORS  # noqa: E402
from opencosmorspy.parameterization import openCOSMORS24a  # noqa: E402


def generated_defaults():
    workdir = ROOT / "opencosmors_orca"
    return (
        workdir / "paracetamol.solute.orcacosmo",
        [
            ("Water", workdir / "water_reference.solute.orcacosmo"),
            ("Ethanol", workdir / "water_reference.solvent.orcacosmo"),
        ],
    )


def official_test_defaults():
    official = OPEN_COSMORS_ROOT / "tests" / "COSMO_ORCA"
    return (
        official / "acetaminophen.orcacosmo",
        [
            ("Water", official / "water.orcacosmo"),
            ("Ethanol", official / "ethanol.orcacosmo"),
        ],
    )


def default_inputs():
    solute, solvents = generated_defaults()
    if solute.is_file() and all(path.is_file() for _, path in solvents):
        return solute, solvents
    return official_test_defaults()


def parse_solvent(value):
    if "=" in value:
        name, path = value.split("=", 1)
        return name, Path(path).resolve()
    path = Path(value).resolve()
    return path.stem, path


def parse_args():
    default_solute, default_solvents = default_inputs()

    parser = argparse.ArgumentParser(
        description="Calculate mole-fraction solubility from .orcacosmo files."
    )
    parser.add_argument("--solute", default=str(default_solute), help="Solute .orcacosmo file.")
    parser.add_argument(
        "--solvent",
        action="append",
        help="Solvent as NAME=path.orcacosmo. Repeat for multiple solvents.",
    )
    parser.add_argument(
        "--delta-h-fusion-kj-mol",
        type=float,
        default=27.1,
        help="Solute fusion enthalpy in kJ/mol. Default: 27.1 for paracetamol example.",
    )
    parser.add_argument(
        "--t-fusion-k",
        type=float,
        default=443.6,
        help="Solute fusion temperature in K. Default: 443.6 for paracetamol example.",
    )
    parser.add_argument(
        "--temperature-k",
        type=float,
        default=298.15,
        help="Calculation temperature in K. Default: 298.15.",
    )
    parser.set_defaults(default_solvents=default_solvents)
    return parser.parse_args()


def ln_gamma_solute(crs, x_solute, temperature_k):
    x_solute = min(max(float(x_solute), 0.0), 1.0)
    x = np.array([x_solute, 1.0 - x_solute])
    crs.clear_jobs()
    crs.add_job(x, temperature_k, refst="pure_component")
    return float(crs.calculate()["tot"]["lng"][0][0])


def solve_solubility(
    solute_file,
    solvent_file,
    delta_h_fusion_j_mol,
    t_fusion_k,
    temperature_k,
):
    crs = COSMORS(par=openCOSMORS24a())
    crs.add_molecule([str(solute_file)])
    crs.add_molecule([str(solvent_file)])

    rhs = -delta_h_fusion_j_mol / constants.R * (1.0 / temperature_k - 1.0 / t_fusion_k)
    ln_gamma_inf = ln_gamma_solute(crs, 0.0, temperature_k)
    x_non_iter = math.exp(rhs - ln_gamma_inf)

    def residual(x_solute):
        return ln_gamma_solute(crs, x_solute, temperature_k) + math.log(x_solute) - rhs

    x_iter = brentq(residual, 1e-15, 1.0 - 1e-15, xtol=1e-14, rtol=1e-12)
    return ln_gamma_inf, x_non_iter, x_iter, residual(x_iter)


def main():
    args = parse_args()
    solute_file = Path(args.solute).resolve()
    solvents = (
        [parse_solvent(value) for value in args.solvent]
        if args.solvent
        else args.default_solvents
    )

    if not solute_file.is_file():
        raise FileNotFoundError(solute_file)
    for _, path in solvents:
        if not path.is_file():
            raise FileNotFoundError(path)

    print(f"solute: {solute_file}")
    print(f"Delta H fusion: {args.delta_h_fusion_kj_mol:g} kJ/mol")
    print(f"T fusion      : {args.t_fusion_k:g} K")
    print(f"T calculation : {args.temperature_k:g} K\n")

    print(
        f"{'solvent':<14}"
        f"{'ln_gamma_inf':>15}"
        f"{'x_non_iter':>14}"
        f"{'x_iter':>14}"
        f"{'root_resid':>14}"
    )
    print("-" * 71)
    for name, solvent_file in solvents:
        ln_gamma_inf, x_non_iter, x_iter, residual = solve_solubility(
            solute_file=solute_file,
            solvent_file=solvent_file,
            delta_h_fusion_j_mol=args.delta_h_fusion_kj_mol * 1000.0,
            t_fusion_k=args.t_fusion_k,
            temperature_k=args.temperature_k,
        )
        print(
            f"{name:<14}"
            f"{ln_gamma_inf:15.6f}"
            f"{x_non_iter:14.6g}"
            f"{x_iter:14.6g}"
            f"{residual:14.3g}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
