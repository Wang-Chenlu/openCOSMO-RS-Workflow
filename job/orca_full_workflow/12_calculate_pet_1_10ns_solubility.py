#!/usr/bin/env python3
"""Calculate PET solubility for 1-10 ns PET conformers one-by-one.

openCOSMO-RS_py currently raises NotImplementedError when more than one COSMO
file is passed as conformers of the same molecule. This script therefore treats
each PET frame as a separate solute calculation and reports per-frame results
plus simple unweighted statistics.
"""

import argparse
import csv
import math
import statistics
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
PET_MOLAR_MASS_G_MOL = 638.5722

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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Calculate PET solubility for 1-10 ns PET conformers."
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
        "--output-dir",
        default=str(ROOT / "pet_1_10ns_solubility_results"),
        help="Directory for CSV outputs.",
    )
    return parser.parse_args()


def require_file(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def collect_pet_conformers():
    conformers = []
    first = ROOT / "pet_cosmors_hpc_package" / "pet_trimer.solute.orcacosmo"
    if first.is_file():
        conformers.append(("01ns", first.resolve()))

    package = ROOT / "pet_02_10ns_cosmors_package"
    for ns in range(2, 11):
        label = "{:02d}ns".format(ns)
        candidates = [
            package / label / "pet_{}_cosmors.solute.orcacosmo".format(label),
            package / "pet_{}_cosmors.solute.orcacosmo".format(label),
        ]
        found = None
        for candidate in candidates:
            if candidate.is_file():
                found = candidate.resolve()
                break
        if found is None:
            raise FileNotFoundError(
                "Missing PET COSMORS file for {}. Checked: {}".format(
                    label, ", ".join(str(c) for c in candidates)
                )
            )
        conformers.append((label, found))
    return conformers


def collect_solvents():
    base = ROOT / "pet_cosmors_hpc_package"
    return [
        ("GVL", require_file(base / "gvl.solute.orcacosmo")),
        ("Formic_acid", require_file(base / "formic_acid.solute.orcacosmo")),
    ]


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


def summarize(rows, key):
    values = [float(row[key]) for row in rows]
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    conformers = collect_pet_conformers()
    solvents = collect_solvents()

    delta_h_fusion_j_mol = args.delta_h_fusion_j_g * PET_MOLAR_MASS_G_MOL
    per_frame_rows = []

    for conformer_label, pet_file in conformers:
        for solvent_name, solvent_file in solvents:
            solvent_m = molar_mass_from_orcacosmo(solvent_file)
            result = solve_solubility(
                pet_file,
                solvent_file,
                delta_h_fusion_j_mol,
                args.t_fusion_k,
                args.temperature_k,
            )
            row = {
                "conformer": conformer_label,
                "solute_file": str(pet_file),
                "solvent": solvent_name,
                "solvent_molar_mass_g_mol": solvent_m,
                "ln_gamma_inf": result["ln_gamma_inf"],
                "x_inf": result["x_inf"],
                "g_per_g_inf": x_to_g_per_g_solvent(
                    result["x_inf"], PET_MOLAR_MASS_G_MOL, solvent_m
                ),
                "ln_gamma_iter": result["ln_gamma_iter"],
                "x_iter": result["x_iter"],
                "g_per_g_iter": x_to_g_per_g_solvent(
                    result["x_iter"], PET_MOLAR_MASS_G_MOL, solvent_m
                ),
                "residual": result["residual"],
                "status": result["status"],
            }
            per_frame_rows.append(row)

    fieldnames = [
        "conformer",
        "solute_file",
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
    per_frame_csv = output_dir / "pet_1_10ns_solubility_per_frame.csv"
    write_csv(per_frame_csv, per_frame_rows, fieldnames)

    summary_rows = []
    for solvent_name, _ in solvents:
        rows = [row for row in per_frame_rows if row["solvent"] == solvent_name]
        for quantity in ["ln_gamma_inf", "x_inf", "g_per_g_inf", "x_iter", "g_per_g_iter"]:
            stats = summarize(rows, quantity)
            summary_rows.append(
                {
                    "solvent": solvent_name,
                    "quantity": quantity,
                    "n_conformers": len(rows),
                    "mean": stats["mean"],
                    "median": stats["median"],
                    "stdev": stats["stdev"],
                    "min": stats["min"],
                    "max": stats["max"],
                }
            )

    summary_csv = output_dir / "pet_1_10ns_solubility_summary.csv"
    write_csv(
        summary_csv,
        summary_rows,
        ["solvent", "quantity", "n_conformers", "mean", "median", "stdev", "min", "max"],
    )

    print("PET conformers:", len(conformers))
    print("Delta H fusion: {:.6f} J/g = {:.6f} kJ/mol".format(
        args.delta_h_fusion_j_g, delta_h_fusion_j_mol / 1000.0
    ))
    print("T fusion      : {:.6f} K".format(args.t_fusion_k))
    print("T calculation : {:.6f} K".format(args.temperature_k))
    print("")
    print("{:<12}{:>16}{:>16}{:>16}{:>16}".format(
        "solvent", "mean g/g_inf", "median g/g_inf", "min", "max"
    ))
    print("-" * 76)
    for solvent_name, _ in solvents:
        rows = [row for row in per_frame_rows if row["solvent"] == solvent_name]
        stats = summarize(rows, "g_per_g_inf")
        print("{:<12}{:>16.6g}{:>16.6g}{:>16.6g}{:>16.6g}".format(
            solvent_name, stats["mean"], stats["median"], stats["min"], stats["max"]
        ))
    print("")
    print("Wrote:", per_frame_csv)
    print("Wrote:", summary_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
