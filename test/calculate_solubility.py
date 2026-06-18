#!/usr/bin/env python3
"""Calculate solid solubility with openCOSMO-RS activity coefficients."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import constants
from scipy.optimize import brentq, minimize_scalar


SCRIPT_DIR = Path(__file__).resolve().parent
OPEN_COSMORS_ROOT = SCRIPT_DIR.parent / "openCOSMO" / "openCOSMO-RS_py"
LOCAL_OPEN_COSMORS_SRC = OPEN_COSMORS_ROOT / "src"
if LOCAL_OPEN_COSMORS_SRC.exists():
    sys.path.insert(0, str(LOCAL_OPEN_COSMORS_SRC))

from opencosmorspy import COSMORS  # noqa: E402
from opencosmorspy.parameterization import openCOSMORS24a  # noqa: E402


EPS = 1e-15


@dataclass
class SolubilityResult:
    solvent: str
    x_infinite_dilution: float
    x_iterative: float
    ln_gamma_infinite_dilution: float
    ln_gamma_iterative: float
    residual: float
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate mole-fraction solubility using openCOSMO-RS and the "
            "simplified solid-liquid equilibrium equation without heat-capacity "
            "correction."
        )
    )
    parser.add_argument("--solute", required=True, help="Solute .orcacosmo/.cosmo file")
    parser.add_argument(
        "--solvent",
        required=True,
        action="append",
        help="Solvent .orcacosmo/.cosmo file. Repeat this option for many solvents.",
    )
    parser.add_argument(
        "--delta-h-fusion-kj-mol",
        required=True,
        type=float,
        help="Solute molar enthalpy of fusion in kJ/mol",
    )
    parser.add_argument(
        "--t-fusion-k",
        required=True,
        type=float,
        help="Solute melting/fusion temperature in K",
    )
    parser.add_argument(
        "--temperature-k",
        default=298.15,
        type=float,
        help="Solubility calculation temperature in K, default: 298.15",
    )
    parser.add_argument(
        "--parameterization",
        default="default_orca",
        choices=["default_orca", "default_turbomole", "24a", "openCOSMORS24a"],
        help="openCOSMO-RS parameterization, default: default_orca",
    )
    parser.add_argument(
        "--csv",
        help="Optional CSV output path",
    )
    return parser.parse_args()


def make_crs(parameterization: str) -> COSMORS:
    if parameterization in {"24a", "openCOSMORS24a"}:
        return COSMORS(par=openCOSMORS24a())
    return COSMORS(par=parameterization)


def resolve_existing_file(path_text: str) -> Path:
    path = Path(path_text).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    return path


def calculate_ln_gamma(crs: COSMORS, x_solute: float, temperature_k: float) -> float:
    x_solute = min(max(float(x_solute), 0.0), 1.0)
    x = np.array([x_solute, 1.0 - x_solute])
    crs.clear_jobs()
    crs.add_job(x, temperature_k, refst="pure_component")
    results = crs.calculate()
    return float(results["tot"]["lng"][0][0])


def calculate_solubility(
    *,
    solute_file: Path,
    solvent_file: Path,
    delta_h_fusion_j_mol: float,
    t_fusion_k: float,
    temperature_k: float,
    parameterization: str,
) -> SolubilityResult:
    crs = make_crs(parameterization)
    crs.add_molecule([str(solute_file)])
    crs.add_molecule([str(solvent_file)])

    rhs = -delta_h_fusion_j_mol / constants.R * (1.0 / temperature_k - 1.0 / t_fusion_k)

    ln_gamma_inf = calculate_ln_gamma(crs, 0.0, temperature_k)
    x_inf = math.exp(rhs - ln_gamma_inf)
    x_inf = min(max(x_inf, EPS), 1.0)

    def equilibrium_residual(x_solute: float) -> float:
        ln_gamma = calculate_ln_gamma(crs, x_solute, temperature_k)
        return ln_gamma + math.log(x_solute) - rhs

    lower = EPS
    upper = 1.0 - EPS
    f_lower = equilibrium_residual(lower)
    f_upper = equilibrium_residual(upper)

    if f_lower == 0.0:
        x_iter = lower
        status = "root"
    elif f_upper == 0.0:
        x_iter = upper
        status = "root"
    elif f_lower * f_upper < 0.0:
        x_iter = brentq(equilibrium_residual, lower, upper, xtol=1e-14, rtol=1e-12)
        status = "root"
    else:
        # If the equilibrium root is outside (0, 1), report the best in-domain point.
        fit = minimize_scalar(
            lambda value: equilibrium_residual(value) ** 2,
            bounds=(lower, upper),
            method="bounded",
            options={"xatol": 1e-14},
        )
        x_iter = float(fit.x)
        status = "minimum_residual"

    ln_gamma_iter = calculate_ln_gamma(crs, x_iter, temperature_k)
    residual = ln_gamma_iter + math.log(x_iter) - rhs

    return SolubilityResult(
        solvent=solvent_file.stem,
        x_infinite_dilution=x_inf,
        x_iterative=x_iter,
        ln_gamma_infinite_dilution=ln_gamma_inf,
        ln_gamma_iterative=ln_gamma_iter,
        residual=residual,
        status=status,
    )


def print_results(results: list[SolubilityResult]) -> None:
    header = (
        f"{'solvent':<18}"
        f"{'x_inf_dil':>14}"
        f"{'x_iter':>14}"
        f"{'ln_gamma_inf':>16}"
        f"{'ln_gamma_iter':>16}"
        f"{'residual':>14}"
        f"{'status':>18}"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        print(
            f"{result.solvent:<18}"
            f"{result.x_infinite_dilution:14.6g}"
            f"{result.x_iterative:14.6g}"
            f"{result.ln_gamma_infinite_dilution:16.6g}"
            f"{result.ln_gamma_iterative:16.6g}"
            f"{result.residual:14.3g}"
            f"{result.status:>18}"
        )


def write_csv(path: Path, results: list[SolubilityResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(SolubilityResult.__annotations__))
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


def main() -> int:
    args = parse_args()

    solute_file = resolve_existing_file(args.solute)
    solvent_files = [resolve_existing_file(path) for path in args.solvent]

    delta_h_fusion_j_mol = args.delta_h_fusion_kj_mol * 1000.0
    results = [
        calculate_solubility(
            solute_file=solute_file,
            solvent_file=solvent_file,
            delta_h_fusion_j_mol=delta_h_fusion_j_mol,
            t_fusion_k=args.t_fusion_k,
            temperature_k=args.temperature_k,
            parameterization=args.parameterization,
        )
        for solvent_file in solvent_files
    ]

    print_results(results)
    if args.csv:
        csv_path = Path(args.csv).expanduser().resolve()
        write_csv(csv_path, results)
        print(f"\nWrote CSV: {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
