#!/usr/bin/env python3
"""Prepare ORCA COSMORS single-point inputs for optimized PET 02-10 ns frames."""

from pathlib import Path
import csv


ROOT = Path(__file__).resolve().parents[1]
OPT_PACKAGE_DIR = ROOT / "pet_1_10ns_opt_package"
PACKAGE_DIR = ROOT / "pet_02_10ns_cosmors_package"

NCORES = 64
NS_VALUES = range(2, 11)
COSMORS_KEYWORDS = "BLYP def2-SVP noautostart miniprint pal{} COSMORS(ethanol)".format(
    NCORES
)

SLURM_TEMPLATE = """#!/bin/bash
#SBATCH -J cosmo_pet_{label}
#SBATCH -N 1
#SBATCH -n {ncores}
#SBATCH -p wzhcnormal

module purge
source /work/home/chlwang309/apprepo/orca/6.0.0-openmpi416/scripts/env.sh
EXEC=`which orca`

${{EXEC}} {basename}.inp > {basename}.out
"""

SUBMIT_ALL_TEXT = """#!/usr/bin/env bash
set -euo pipefail

for dir in [0-9][0-9]ns; do
  echo "Submitting ${dir}/orca_cosmors.slurm"
  (cd "${dir}" && sbatch orca_cosmors.slurm)
done
"""

CHECK_RESULTS_TEXT = """#!/usr/bin/env bash
set -euo pipefail

echo "ORCA normal termination check:"
grep -H "ORCA TERMINATED NORMALLY" [0-9][0-9]ns/pet_*ns_cosmors.out || true

echo
echo ".orcacosmo files:"
ls -lh [0-9][0-9]ns/*.orcacosmo 2>/dev/null || true
"""

README_TEXT = """# PET 02-10 ns ORCA COSMORS Package

This package contains COSMORS single-point calculations prepared from the final
optimized geometries of PET frames 02-10 ns.

`01ns` is intentionally excluded because it was already calculated previously.

Submit on the cluster:

```bash
cd pet_02_10ns_cosmors_package
bash submit_all_cosmors.sh
```

After jobs finish:

```bash
bash check_cosmors_results.sh
```

Each job requests 64 cores and uses:

```text
BLYP def2-SVP noautostart miniprint pal64 COSMORS(ethanol)
```

For each frame, use the generated `*.solute.orcacosmo` file as a PET conformer
input for later openCOSMO-RS conformer averaging or per-frame comparison.
"""


def parse_xyz_frames(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    frames = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        try:
            natoms = int(line)
        except ValueError:
            raise ValueError("Expected atom count at line {} in {}".format(index + 1, path))
        comment_index = index + 1
        first_coord_index = index + 2
        last_coord_index = first_coord_index + natoms
        if last_coord_index > len(lines):
            raise ValueError("Truncated XYZ frame starting at line {} in {}".format(index + 1, path))
        comment = lines[comment_index]
        coords = [coord.strip() for coord in lines[first_coord_index:last_coord_index]]
        frames.append((natoms, comment, coords))
        index = last_coord_index
    if not frames:
        raise ValueError("No XYZ frames found in {}".format(path))
    return frames


def write_xyz(path, natoms, comment, coords):
    path.write_text(
        "{}\n{}\n{}\n".format(natoms, comment, "\n".join(coords)),
        encoding="utf-8",
        newline="\n",
    )


def write_orca_input(path, coords):
    text = """! {keywords}
* xyz 0 1
{coords}
*
""".format(
        keywords=COSMORS_KEYWORDS,
        coords="\n".join(coords),
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def write_text(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


def main():
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    generated = []

    for ns in NS_VALUES:
        label = "{:02d}ns".format(ns)
        source_dir = OPT_PACKAGE_DIR / label
        trj_path = source_dir / "pet_{}_opt_trj.xyz".format(label)
        out_path = source_dir / "pet_{}_opt.out".format(label)
        if not trj_path.is_file():
            raise FileNotFoundError(trj_path)
        if not out_path.is_file():
            raise FileNotFoundError(out_path)

        natoms, comment, coords = parse_xyz_frames(trj_path)[-1]
        frame_dir = PACKAGE_DIR / label
        frame_dir.mkdir(parents=True, exist_ok=True)

        basename = "pet_{}_cosmors".format(label)
        final_xyz = frame_dir / "pet_{}_opt_final.xyz".format(label)
        inp_path = frame_dir / "{}.inp".format(basename)
        slurm_path = frame_dir / "orca_cosmors.slurm"

        write_xyz(final_xyz, natoms, comment, coords)
        write_orca_input(inp_path, coords)
        write_text(
            slurm_path,
            SLURM_TEMPLATE.format(label=label, ncores=NCORES, basename=basename),
        )

        generated.extend([final_xyz, inp_path, slurm_path])
        summary.append(
            {
                "ns": ns,
                "source_trj": str(trj_path.relative_to(ROOT)),
                "natoms": natoms,
                "final_comment": comment,
                "cosmors_input": str(inp_path.relative_to(ROOT)),
                "expected_solute_orcacosmo": "{}.solute.orcacosmo".format(basename),
            }
        )

    summary_path = PACKAGE_DIR / "cosmors_input_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    write_text(PACKAGE_DIR / "submit_all_cosmors.sh", SUBMIT_ALL_TEXT)
    write_text(PACKAGE_DIR / "check_cosmors_results.sh", CHECK_RESULTS_TEXT)
    write_text(PACKAGE_DIR / "README_submit.md", README_TEXT)

    print("Generated PET 02-10 ns COSMORS package:")
    print("  {}".format(PACKAGE_DIR.relative_to(ROOT)))
    for path in generated:
        print("  {}".format(path.relative_to(ROOT)))
    print("  {}".format(summary_path.relative_to(ROOT)))
    print("  {}".format((PACKAGE_DIR / "submit_all_cosmors.sh").relative_to(ROOT)))
    print("  {}".format((PACKAGE_DIR / "check_cosmors_results.sh").relative_to(ROOT)))


if __name__ == "__main__":
    main()
