#!/usr/bin/env python3
"""Summarize PET-in-GVL solubility at 25 C and 100 C."""

import csv
from pathlib import Path


JOB = Path(__file__).resolve().parents[1]
OUT = JOB / "pet_solubility_25C_100C_summary.csv"

SOURCES = {
    "25C": [
        JOB / "pet_1_10ns_solubility_results" / "pet_1_10ns_solubility_summary.csv",
    ],
    "100C": [
        JOB / "pet_1_10ns_solubility_results_373K" / "pet_1_10ns_solubility_summary.csv",
    ],
}

ORDER = [
    ("GVL", "GVL"),
]


def read_summary(paths):
    values = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                values[(row["solvent"], row["quantity"])] = row
    return values


def get_float(row, key):
    return float(row[key])


def main():
    collected = {label: read_summary(paths) for label, paths in SOURCES.items()}
    rows = []
    for solvent_key, label in ORDER:
        for temp_label, temp_k in [("25C", 298.15), ("100C", 373.15)]:
            source = collected[temp_label]
            inf = source[(solvent_key, "g_per_g_inf")]
            itr = source[(solvent_key, "g_per_g_iter")]
            rows.append(
                {
                    "solvent": label,
                    "temperature_label": temp_label,
                    "temperature_K": temp_k,
                    "g_per_g_iter_mean": get_float(itr, "mean"),
                    "g_per_g_iter_median": get_float(itr, "median"),
                    "g_per_g_iter_stdev": get_float(itr, "stdev"),
                    "g_per_g_iter_min": get_float(itr, "min"),
                    "g_per_g_iter_max": get_float(itr, "max"),
                    "g_per_g_inf_mean": get_float(inf, "mean"),
                    "g_per_g_inf_median": get_float(inf, "median"),
                    "g_per_g_inf_n_nonfinite": int(inf.get("n_nonfinite") or 0),
                }
            )

    fieldnames = [
        "solvent",
        "temperature_label",
        "temperature_K",
        "g_per_g_iter_mean",
        "g_per_g_iter_median",
        "g_per_g_iter_stdev",
        "g_per_g_iter_min",
        "g_per_g_iter_max",
        "g_per_g_inf_mean",
        "g_per_g_inf_median",
        "g_per_g_inf_n_nonfinite",
    ]
    with OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(OUT)
    print("{:<22}{:<8}{:>14}{:>14}{:>14}{:>14}".format(
        "solvent", "T", "mean_iter", "median", "min", "max"
    ))
    print("-" * 86)
    for row in rows:
        print("{:<22}{:<8}{:>14.6g}{:>14.6g}{:>14.6g}{:>14.6g}".format(
            row["solvent"],
            row["temperature_label"],
            row["g_per_g_iter_mean"],
            row["g_per_g_iter_median"],
            row["g_per_g_iter_min"],
            row["g_per_g_iter_max"],
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
