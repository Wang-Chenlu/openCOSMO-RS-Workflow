#!/usr/bin/env python3
"""Create ORCA geometry-optimization inputs from XYZ files."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

JOBS = [
    {
        "directory": "34-C5H8O2",
        "xyz": "34-C5H8O2.xyz",
        "basename": "34-C5H8O2_opt",
        "job_name": "opt_gvl",
        "keywords": "M062X def2-TZVP D3zero Opt noautostart miniprint pal4",
        "ncores": 4,
    },
    {
        "directory": "35-PET",
        "xyz": "35-PET.xyz",
        "basename": "35-PET_opt",
        "job_name": "opt_pet",
        "keywords": "M062X def2-SVP D3zero Opt noautostart miniprint pal64",
        "ncores": 64,
    },
]

CHARGE = 0
MULTIPLICITY = 1

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


def read_xyz_coordinates(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3:
        raise ValueError("Invalid XYZ file: {}".format(path))

    try:
        expected_atoms = int(lines[0].strip())
    except ValueError as exc:
        raise ValueError("First XYZ line is not an atom count: {}".format(path)) from exc

    coordinates = [line.strip() for line in lines[2:] if line.strip()]
    if len(coordinates) != expected_atoms:
        raise ValueError(
            "{} declares {} atoms but contains {} coordinate lines".format(
                path, expected_atoms, len(coordinates)
            )
        )
    return coordinates


def write_opt_input(directory, xyz_name, basename, keywords):
    xyz_path = directory / xyz_name
    coordinates = read_xyz_coordinates(xyz_path)
    inp_path = directory / "{}.inp".format(basename)
    inp_text = """! {keywords}
%geom
  MaxIter 300
end

* xyz {charge} {multiplicity}
{coordinates}
*
""".format(
        keywords=keywords,
        charge=CHARGE,
        multiplicity=MULTIPLICITY,
        coordinates="\n".join(coordinates),
    )
    inp_path.write_text(inp_text, encoding="utf-8", newline="\n")
    return inp_path


def write_slurm(directory, basename, job_name, ncores):
    slurm_path = directory / "orca_opt.slurm"
    slurm_path.write_text(
        SLURM_TEMPLATE.format(basename=basename, job_name=job_name, ncores=ncores),
        encoding="utf-8",
        newline="\n",
    )
    return slurm_path


def write_submit_all():
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
    ]
    for job in JOBS:
        lines.append("(cd {directory} && sbatch orca_opt.slurm)".format(**job))
    lines.append("")
    submit_path = ROOT / "submit_all_opt.sh"
    submit_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return submit_path


def main():
    generated = []
    for job in JOBS:
        directory = ROOT / job["directory"]
        if not directory.is_dir():
            raise FileNotFoundError(directory)
        generated.append(
            write_opt_input(directory, job["xyz"], job["basename"], job["keywords"])
        )
        generated.append(
            write_slurm(directory, job["basename"], job["job_name"], job["ncores"])
        )
    generated.append(write_submit_all())

    print("Generated ORCA optimization files:")
    for path in generated:
        print("  {}".format(path.relative_to(ROOT)))


if __name__ == "__main__":
    main()
