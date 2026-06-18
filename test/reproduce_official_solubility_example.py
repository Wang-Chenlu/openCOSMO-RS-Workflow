#!/usr/bin/env python3
"""Step-by-step reproduction of the official openCOSMO-RS solubility example."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from scipy import constants
from scipy.optimize import brentq


ROOT = Path(__file__).resolve().parent
OPEN_COSMORS_ROOT = ROOT.parent / "openCOSMO" / "openCOSMO-RS_py"
OPEN_COSMORS_SRC = OPEN_COSMORS_ROOT / "src"
if OPEN_COSMORS_SRC.exists():
    sys.path.insert(0, str(OPEN_COSMORS_SRC))

from opencosmorspy.cosmors import COSMORS  # noqa: E402
from opencosmorspy.parameterization import openCOSMORS24a  # noqa: E402


SOLUTE_FILE = OPEN_COSMORS_ROOT / "tests" / "COSMO_ORCA" / "acetaminophen.orcacosmo"
SOLVENT_FILES = [
    OPEN_COSMORS_ROOT / "tests" / "COSMO_ORCA" / "water.orcacosmo",
    OPEN_COSMORS_ROOT / "tests" / "COSMO_ORCA" / "ethanol.orcacosmo",
    OPEN_COSMORS_ROOT / "tests" / "COSMO_ORCA" / "acetic_acid.orcacosmo",
    OPEN_COSMORS_ROOT / "tests" / "COSMO_ORCA" / "cyclohexane.orcacosmo",
]

DELTA_H_FUSION = 27.1 * 1000.0  # J/mol
T_FUSION = 443.6  # K
TEMPERATURE = 298.15  # K

EXPERIMENTAL_X = {
    "water": 0.002068248,
    "ethanol": 0.066236658,
    "acetic_acid": 0.031816953,
    "cyclohexane": None,
}


def print_step(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def validate_inputs() -> None:
    print_step("Step 1 - Check input files")
    print(f"solute: {SOLUTE_FILE}")
    if not SOLUTE_FILE.is_file():
        raise FileNotFoundError(SOLUTE_FILE)

    for solvent_file in SOLVENT_FILES:
        print(f"solvent: {solvent_file}")
        if not solvent_file.is_file():
            raise FileNotFoundError(solvent_file)


def make_model(solvent_file: Path) -> COSMORS:
    crs = COSMORS(par=openCOSMORS24a())
    crs.add_molecule([str(SOLUTE_FILE)])
    crs.add_molecule([str(solvent_file)])
    return crs


def calculate_ln_gamma_solute(crs: COSMORS, x_solute: float) -> float:
    x_solute = min(max(float(x_solute), 0.0), 1.0)
    x = np.array([x_solute, 1.0 - x_solute])

    crs.clear_jobs()
    crs.add_job(x, TEMPERATURE, refst="pure_component")
    results = crs.calculate()

    return float(results["tot"]["lng"][0][0])


def solid_liquid_rhs() -> float:
    return -DELTA_H_FUSION / constants.R * (1.0 / TEMPERATURE - 1.0 / T_FUSION)


def infinite_dilution_solubility(ln_gamma_inf: float, rhs: float) -> float:
    return math.exp(rhs - ln_gamma_inf)


def solve_iterative_solubility(crs: COSMORS, rhs: float) -> tuple[float, float]:
    def residual(x_solute: float) -> float:
        ln_gamma = calculate_ln_gamma_solute(crs, x_solute)
        return ln_gamma + math.log(x_solute) - rhs

    lower = 1e-15
    upper = 1.0 - 1e-15
    x_root = brentq(residual, lower, upper, xtol=1e-14, rtol=1e-12)
    return x_root, residual(x_root)


def reproduce_example() -> None:
    validate_inputs()

    print_step("Step 2 - Thermodynamic constants")
    rhs = solid_liquid_rhs()
    print(f"Delta H fusion = {DELTA_H_FUSION / 1000.0:.4g} kJ/mol")
    print(f"T fusion       = {T_FUSION:.4g} K")
    print(f"T calculation  = {TEMPERATURE:.4g} K")
    print(f"RHS            = {rhs:.8f}")

    print_step("Step 3 - Calculate solubilities")
    print(
        f"{'solvent':<14}"
        f"{'ln_gamma_inf':>15}"
        f"{'x_non_iter':>14}"
        f"{'x_iter':>14}"
        f"{'root_resid':>14}"
        f"{'x_exp':>14}"
    )
    print("-" * 85)

    for solvent_file in SOLVENT_FILES:
        solvent_name = solvent_file.stem
        crs = make_model(solvent_file)

        ln_gamma_inf = calculate_ln_gamma_solute(crs, x_solute=0.0)
        x_non_iter = infinite_dilution_solubility(ln_gamma_inf, rhs)
        x_iter, root_residual = solve_iterative_solubility(crs, rhs)
        x_exp = EXPERIMENTAL_X[solvent_name]
        x_exp_text = "N/A" if x_exp is None else f"{x_exp:.6g}"

        print(
            f"{solvent_name:<14}"
            f"{ln_gamma_inf:15.6f}"
            f"{x_non_iter:14.6g}"
            f"{x_iter:14.6g}"
            f"{root_residual:14.3g}"
            f"{x_exp_text:>14}"
        )

    print_step("Step 4 - What the two solubility columns mean")
    print(
        "x_non_iter uses gamma at infinite dilution: x = exp(RHS - ln_gamma_inf).\n"
        "x_iter solves ln(gamma(x)) + ln(x) = RHS, so gamma is recalculated at the "
        "predicted solute concentration.\n"
        "The official notebook uses scipy.fsolve(abs(residual), 1e-5). Here brentq "
        "is used on the signed residual, which gives the actual equation root."
    )


if __name__ == "__main__":
    reproduce_example()
