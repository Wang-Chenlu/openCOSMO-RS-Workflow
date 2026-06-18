#!/usr/bin/env python3
"""Prepare ORCA COSMORS single-point jobs from optimized PET/solvent structures."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "pet_cosmors_hpc_package"

JOBS = [
    {
        "source_dir": "31-CH2O2",
        "trajectory": "31-CH2O2_opt_trj.xyz",
        "final_xyz": "31-CH2O2_opt_final.xyz",
        "basename": "formic_acid",
        "job_name": "cosmo_formic",
        "ncores": 4,
    },
    {
        "source_dir": "34-C5H8O2",
        "trajectory": "34-C5H8O2_opt_trj.xyz",
        "final_xyz": "34-C5H8O2_opt_final.xyz",
        "basename": "gvl",
        "job_name": "cosmo_gvl",
        "ncores": 4,
    },
    {
        "source_dir": "35-PET",
        "trajectory": "35-PET_opt_trj.xyz",
        "final_xyz": "35-PET_opt_final.xyz",
        "basename": "pet_trimer",
        "job_name": "cosmo_pet",
        "ncores": 64,
    },
]

CHARGE = 0
MULTIPLICITY = 1
COSMORS_KEYWORDS_TEMPLATE = (
    "BLYP def2-SVP noautostart miniprint pal{ncores} COSMORS(ethanol)"
)

SLURM_TEMPLATE = """#!/bin/bash
#SBATCH -J {job_name}
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

for script in run_*.slurm; do
  echo "Submitting ${script}"
  sbatch "${script}"
done
"""

CHECK_RESULTS_TEXT = """#!/usr/bin/env bash
set -euo pipefail

echo "ORCA normal termination check:"
grep -H "ORCA TERMINATED NORMALLY" *.out || true

echo
echo ".orcacosmo files:"
ls -lh *.orcacosmo
"""

README_TEMPLATE = """# PET/GVL/Formic Acid ORCA COSMORS Package

This package was generated from the final frames of the completed ORCA geometry
optimizations.

Submit on the cluster:

```bash
cd pet_cosmors_hpc_package
bash submit_all_cosmors.sh
```

After all jobs finish, check:

```bash
bash check_cosmors_results.sh
```

Expected files needed by openCOSMO-RS:

```text
pet_trimer.solute.orcacosmo
gvl.solute.orcacosmo
formic_acid.solute.orcacosmo
```

The extra `*.solvent.orcacosmo` files generated from `COSMORS(ethanol)` are
ethanol reference files and are not used for PET-in-GVL/formic-acid solubility.
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
        if len(coords) != natoms:
            raise ValueError("Frame at line {} has wrong atom count in {}".format(index + 1, path))
        frames.append((natoms, comment, coords))
        index = last_coord_index

    if not frames:
        raise ValueError("No XYZ frames found in {}".format(path))
    return frames


def write_xyz(path, natoms, comment, coords):
    text = "{}\n{}\n{}\n".format(natoms, comment, "\n".join(coords))
    path.write_text(text, encoding="utf-8", newline="\n")


def write_orca_input(path, coords, ncores):
    keywords = COSMORS_KEYWORDS_TEMPLATE.format(ncores=ncores)
    text = """! {keywords}
* xyz {charge} {multiplicity}
{coords}
*
""".format(
        keywords=keywords,
        charge=CHARGE,
        multiplicity=MULTIPLICITY,
        coords="\n".join(coords),
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def write_text(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


def main():
    generated = []
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

    for job in JOBS:
        source_dir = ROOT / job["source_dir"]
        trajectory = source_dir / job["trajectory"]
        if not trajectory.is_file():
            raise FileNotFoundError(trajectory)

        frames = parse_xyz_frames(trajectory)
        natoms, comment, coords = frames[-1]

        final_xyz = source_dir / job["final_xyz"]
        write_xyz(final_xyz, natoms, comment, coords)
        generated.append(final_xyz)

        package_xyz = PACKAGE_DIR / "{}_opt_final.xyz".format(job["basename"])
        shutil.copy2(final_xyz, package_xyz)
        generated.append(package_xyz)

        inp_path = PACKAGE_DIR / "{}.inp".format(job["basename"])
        write_orca_input(inp_path, coords, job["ncores"])
        generated.append(inp_path)

        slurm_path = PACKAGE_DIR / "run_{}.slurm".format(job["basename"])
        write_text(
            slurm_path,
            SLURM_TEMPLATE.format(
                job_name=job["job_name"],
                ncores=job["ncores"],
                basename=job["basename"],
            ),
        )
        generated.append(slurm_path)

    submit_path = PACKAGE_DIR / "submit_all_cosmors.sh"
    check_path = PACKAGE_DIR / "check_cosmors_results.sh"
    readme_path = PACKAGE_DIR / "README_submit.md"
    write_text(submit_path, SUBMIT_ALL_TEXT)
    write_text(check_path, CHECK_RESULTS_TEXT)
    write_text(readme_path, README_TEMPLATE)
    generated.extend([submit_path, check_path, readme_path])

    print("Generated COSMORS package:")
    for path in generated:
        print("  {}".format(path.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
