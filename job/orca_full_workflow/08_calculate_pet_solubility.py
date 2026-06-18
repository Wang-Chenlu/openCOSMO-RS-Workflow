#!/usr/bin/env python3
"""Calculate PET trimer solubility from ORCA-generated .orcacosmo files.

The script accepts fusion enthalpy in J/g because the PET literature value is
often reported on a mass basis. It converts this value to J/mol using the molar
mass calculated from the PET XYZ structure.
"""

import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np
from scipy import constants
from scipy.optimize import brentq, minimize_scalar


ROOT = Path(__file__).resolve().parents[1]
OPEN_COSMORS_ROOT = ROOT.parent / "openCOSMO" / "openCOSMO-RS_py"
LOCAL_OPEN_COSMORS_SRC = OPEN_COSMORS_ROOT / "src"
if LOCAL_OPEN_COSMORS_SRC.exists():
    sys.path.insert(0, str(LOCAL_OPEN_COSMORS_SRC))

from opencosmorspy.cosmors import COSMORS  # noqa: E402
from opencosmorspy.parameterization import openCOSMORS24a  # noqa: E402


EPS = 1e-15

ATOMIC_WEIGHTS = {
    "H": 1.00794,
    "C": 12.0107,
    "N": 14.0067,
    "O": 15.9994,
    "F": 18.9984032,
    "P": 30.973762,
    "S": 32.065,
    "Cl": 35.453,
    "Br": 79.904,
    "I": 126.90447,
}


def default_results_dir():
    return ROOT / "pet_cosmors_hpc_package"


def parse_solvent(value):
    if "=" in value:
        name, path_text = value.split("=", 1)
        return name, Path(path_text).resolve()
    path = Path(value).resolve()
    name = path.name.replace(".solute.orcacosmo", "").replace(".orcacosmo", "")
    return name, path


def parse_args():
    results_dir = default_results_dir()
    parser = argparse.ArgumentParser(
        description="Calculate PET trimer solubility from openCOSMO-RS activity coefficients."
    )
    parser.add_argument(
        "--solute",
        default=str(results_dir / "pet_trimer.solute.orcacosmo"),
        help="PET trimer .orcacosmo file.",
    )
    parser.add_argument(
        "--solvent",
        action="append",
        default=[
            "GVL={}".format(results_dir / "gvl.solute.orcacosmo"),
            "Formic_acid={}".format(results_dir / "formic_acid.solute.orcacosmo"),
        ],
        help="Solvent as NAME=path.orcacosmo. Repeat for multiple solvents.",
    )
    parser.add_argument(
        "--solute-xyz",
        default=str(results_dir / "pet_trimer_opt_final.xyz"),
        help="PET trimer XYZ file used to calculate molar mass.",
    )
    parser.add_argument(
        "--delta-h-fusion-j-g",
        type=float,
        default=54.3,
        help="PET fusion enthalpy in J/g. Default: 54.3 J/g.",
    )
    parser.add_argument(
        "--t-fusion-k",
        type=float,
        default=533.15,
        help="PET melting/fusion temperature in K. Default: 533.15 K.",
    )
    parser.add_argument(
        "--temperature-k",
        type=float,
        default=298.15,
        help="Solubility calculation temperature in K. Default: 298.15 K.",
    )
    parser.add_argument(
        "--csv",
        help="Optional CSV output path.",
    )
    return parser.parse_args()


def require_file(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def read_xyz_symbols(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3:
        raise ValueError("Invalid XYZ file: {}".format(path))
    natoms = int(lines[0].strip())
    coord_lines = [line.strip() for line in lines[2:] if line.strip()]
    if len(coord_lines) != natoms:
        raise ValueError(
            "{} declares {} atoms but has {} coordinate lines".format(
                path, natoms, len(coord_lines)
            )
        )
    return [line.split()[0] for line in coord_lines]


def formula_and_molar_mass(path):
    counts = {}
    for symbol in read_xyz_symbols(path):
        if symbol not in ATOMIC_WEIGHTS:
            raise ValueError("No atomic weight configured for element '{}'".format(symbol))
        counts[symbol] = counts.get(symbol, 0) + 1

    molar_mass = sum(ATOMIC_WEIGHTS[symbol] * count for symbol, count in counts.items())
    ordered_symbols = []
    for symbol in ["C", "H", "N", "O"]:
        if symbol in counts:
            ordered_symbols.append(symbol)
    for symbol in sorted(counts):
        if symbol not in ordered_symbols:
            ordered_symbols.append(symbol)

    formula = "".join(
        "{}{}".format(symbol, counts[symbol] if counts[symbol] > 1 else "")
        for symbol in ordered_symbols
    )
    return formula, molar_mass


def molar_mass_from_orcacosmo(path):
    counts = {}
    in_xyz = False
    remaining = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == "#XYZ_FILE":
            in_xyz = True
            remaining = None
            continue
        if not in_xyz:
            continue
        if remaining is None:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                remaining = int(stripped)
            except ValueError:
                continue
            continue
        if remaining == 0:
            break
        parts = line.split()
        if len(parts) >= 4 and parts[0] in ATOMIC_WEIGHTS:
            counts[parts[0]] = counts.get(parts[0], 0) + 1
            remaining -= 1

    if not counts:
        raise ValueError("Could not read formula from {}".format(path))
    return sum(ATOMIC_WEIGHTS[symbol] * count for symbol, count in counts.items())


def ln_gamma_solute(crs, x_solute, temperature_k):
    x_solute = min(max(float(x_solute), 0.0), 1.0)
    x = np.array([x_solute, 1.0 - x_solute])
    crs.clear_jobs()
    crs.add_job(x, temperature_k, refst="pure_component")
    return float(crs.calculate()["tot"]["lng"][0][0])


def solve_solubility(solute_file, solvent_file, delta_h_fusion_j_mol, t_fusion_k, temperature_k):
    crs = COSMORS(par=openCOSMORS24a())
    crs.add_molecule([str(solute_file)])
    crs.add_molecule([str(solvent_file)])

    rhs = -delta_h_fusion_j_mol / constants.R * (1.0 / temperature_k - 1.0 / t_fusion_k)
    ln_gamma_inf = ln_gamma_solute(crs, 0.0, temperature_k)
    x_inf = math.exp(rhs - ln_gamma_inf)
    x_inf = min(max(x_inf, EPS), 1.0)

    def residual(x_solute):
        return ln_gamma_solute(crs, x_solute, temperature_k) + math.log(x_solute) - rhs

    lower = EPS
    upper = 1.0 - EPS
    f_lower = residual(lower)
    f_upper = residual(upper)
    if f_lower * f_upper < 0.0:
        x_iter = brentq(residual, lower, upper, xtol=1e-14, rtol=1e-12)
        status = "root"
    else:
        fit = minimize_scalar(
            lambda value: residual(value) ** 2,
            bounds=(lower, upper),
            method="bounded",
            options={"xatol": 1e-14},
        )
        x_iter = float(fit.x)
        status = "minimum_residual"

    ln_gamma_iter = ln_gamma_solute(crs, x_iter, temperature_k)
    return {
        "ln_gamma_inf": ln_gamma_inf,
        "x_inf": x_inf,
        "x_iter": x_iter,
        "ln_gamma_iter": ln_gamma_iter,
        "residual": ln_gamma_iter + math.log(x_iter) - rhs,
        "status": status,
    }


def x_to_g_per_g_solvent(x_solute, solute_molar_mass_g_mol, solvent_molar_mass_g_mol):
    x_solvent = 1.0 - x_solute
    if x_solvent <= 0.0:
        return float("inf")
    return x_solute * solute_molar_mass_g_mol / (x_solvent * solvent_molar_mass_g_mol)


def print_table(rows):
    header = (
        "{:<12}{:>13}{:>13}{:>15}{:>15}{:>15}{:>12}".format(
            "solvent",
            "ln_g_inf",
            "x_inf",
            "g/g_inf",
            "x_iter",
            "g/g_iter",
            "status",
        )
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            "{:<12}{:>13.6g}{:>13.6g}{:>15.6g}{:>15.6g}{:>15.6g}{:>12}".format(
                row["solvent"],
                row["ln_gamma_inf"],
                row["x_inf"],
                row["g_per_g_inf"],
                row["x_iter"],
                row["g_per_g_iter"],
                row["status"],
            )
        )


def write_csv(path, rows):
    fieldnames = [
        "solvent",
        "solvent_molar_mass_g_mol",
        "ln_gamma_inf",
        "x_inf",
        "g_per_g_inf",
        "ln_gamma_iter",
        "x_iter",
        "g_per_g_iter",
        "residual",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})


def main():
    args = parse_args()
    solute_file = require_file(args.solute)
    solute_xyz = require_file(args.solute_xyz)
    solvents = [(name, require_file(path)) for name, path in [parse_solvent(v) for v in args.solvent]]

    formula, solute_molar_mass = formula_and_molar_mass(solute_xyz)
    delta_h_fusion_j_mol = args.delta_h_fusion_j_g * solute_molar_mass

    print("solute file    : {}".format(solute_file))
    print("solute formula : {}".format(formula))
    print("solute M       : {:.6f} g/mol".format(solute_molar_mass))
    print("Delta H fusion : {:.6f} J/g = {:.6f} kJ/mol".format(
        args.delta_h_fusion_j_g,
        delta_h_fusion_j_mol / 1000.0,
    ))
    print("T fusion       : {:.6f} K".format(args.t_fusion_k))
    print("T calculation  : {:.6f} K".format(args.temperature_k))
    print("")

    rows = []
    for solvent_name, solvent_file in solvents:
        solvent_molar_mass = molar_mass_from_orcacosmo(solvent_file)
        result = solve_solubility(
            solute_file,
            solvent_file,
            delta_h_fusion_j_mol,
            args.t_fusion_k,
            args.temperature_k,
        )
        row = {
            "solvent": solvent_name,
            "solvent_molar_mass_g_mol": solvent_molar_mass,
            "g_per_g_inf": x_to_g_per_g_solvent(
                result["x_inf"], solute_molar_mass, solvent_molar_mass
            ),
            "g_per_g_iter": x_to_g_per_g_solvent(
                result["x_iter"], solute_molar_mass, solvent_molar_mass
            ),
        }
        row.update(result)
        rows.append(row)

    print_table(rows)

    if args.csv:
        csv_path = Path(args.csv).resolve()
        write_csv(csv_path, rows)
        print("\nWrote CSV: {}".format(csv_path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
