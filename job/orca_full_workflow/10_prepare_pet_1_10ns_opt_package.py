#!/usr/bin/env python3
"""Prepare ORCA optimization inputs for PET frames at 1-10 ns."""

from pathlib import Path
import csv


ROOT = Path(__file__).resolve().parents[1]
PET_DIR = ROOT / "35-PET"
LOG_PATH = PET_DIR / "log"
DUMP_PATH = PET_DIR / "eq1.xyz"
PACKAGE_DIR = ROOT / "pet_1_10ns_opt_package"

WATER_LABELS = {"H11", "O12"}
ELEMENT_BY_LABEL = {
    "C1": "C",
    "C2": "C",
    "C3": "C",
    "O4": "O",
    "O5": "O",
    "H6": "H",
    "C7": "C",
    "O8": "O",
    "H9": "H",
    "H10": "H",
}

NCORES = 64
STEPS = [(ns, ns * 500000) for ns in range(1, 11)]
ORCA_KEYWORDS = "M062X def2-SVP D3zero Opt noautostart miniprint pal{}".format(NCORES)

SLURM_TEMPLATE = """#!/bin/bash
#SBATCH -J opt_pet_{label}
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
  echo "Submitting ${dir}/orca_opt.slurm"
  (cd "${dir}" && sbatch orca_opt.slurm)
done
"""

CHECK_RESULTS_TEXT = """#!/usr/bin/env bash
set -euo pipefail

echo "ORCA convergence check:"
grep -H "THE OPTIMIZATION HAS CONVERGED" [0-9][0-9]ns/pet_*ns_opt.out || true

echo
echo "ORCA normal termination check:"
grep -H "ORCA TERMINATED NORMALLY" [0-9][0-9]ns/pet_*ns_opt.out || true

echo
echo "Optimization trajectories:"
ls -lh [0-9][0-9]ns/pet_*ns_opt_trj.xyz 2>/dev/null || true
"""

README_TEXT = """# PET 1-10 ns ORCA Optimization Package

This package contains PET-only structures extracted from `35-PET/eq1.xyz` at
1-10 ns. The LAMMPS timestep is assumed to be 2 fs, so:

```text
1 ns = 500000 steps
10 ns = 5000000 steps
```

The package is split into ten folders:

```text
01ns/
02ns/
...
10ns/
```

Submit all jobs on the cluster:

```bash
cd pet_1_10ns_opt_package
bash submit_all_pet_frames.sh
```

After jobs finish:

```bash
bash check_opt_results.sh
```

Each job requests 64 cores and uses:

```text
M062X def2-SVP D3zero Opt noautostart miniprint pal64
```

`frame_lx_summary.csv` records whether the box length used for unwrapping came
from `35-PET/log` or was estimated from the coordinate span of that XYZ frame.
"""


def read_lx_by_step(log_path):
    values = {}
    if not log_path.is_file():
        return values
    with log_path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            parts = line.split()
            if len(parts) < 3 or not parts[0].isdigit():
                continue
            try:
                values[int(parts[0])] = float(parts[2])
            except ValueError:
                continue
    return values


def read_target_frames(dump_path, target_steps):
    target_steps = set(target_steps)
    frames = {}
    with dump_path.open("r", encoding="utf-8", errors="replace") as stream:
        while True:
            natoms_line = stream.readline()
            if not natoms_line:
                break
            natoms_line = natoms_line.strip()
            if not natoms_line:
                continue
            natoms = int(natoms_line)
            comment = stream.readline().strip()
            atoms = [stream.readline().split() for _ in range(natoms)]
            prefix = "Atoms. Timestep: "
            if comment.startswith(prefix):
                step = int(comment[len(prefix) :])
                if step in target_steps:
                    frames[step] = atoms
    missing = sorted(target_steps - set(frames))
    if missing:
        raise ValueError("Missing target timesteps in {}: {}".format(dump_path, missing))
    return frames


def pet_atoms_from_frame(atoms):
    pet_atoms = []
    all_coords = []
    for fields in atoms:
        if len(fields) != 4:
            raise ValueError("Unexpected XYZ atom line: {}".format(fields))
        label = fields[0]
        coord = [float(value) for value in fields[1:4]]
        all_coords.append(coord)
        if label in WATER_LABELS:
            continue
        if label not in ELEMENT_BY_LABEL:
            raise ValueError("Unknown atom label: {}".format(label))
        pet_atoms.append((ELEMENT_BY_LABEL[label], coord))
    return pet_atoms, all_coords


def coordinate_ranges(coords):
    return [
        (min(coord[i] for coord in coords), max(coord[i] for coord in coords))
        for i in range(3)
    ]


def coordinate_spans(coords):
    return [hi - lo for lo, hi in coordinate_ranges(coords)]


def estimate_lx_from_frame(all_coords):
    # eq1.xyz does not store box bounds. With ~6000 water atoms filling the box,
    # the largest coordinate span is the best available per-frame estimate.
    return max(coordinate_spans(all_coords))


def nearest_image_delta(delta, box_length):
    half = 0.5 * box_length
    if delta > half:
        return delta - box_length
    if delta < -half:
        return delta + box_length
    return delta


def unwrap_sequential(coords, box_length):
    unwrapped = [coords[0]]
    for coord in coords[1:]:
        previous = unwrapped[-1]
        adjusted = []
        for current, prev_value in zip(coord, previous):
            delta = nearest_image_delta(current - prev_value, box_length)
            adjusted.append(prev_value + delta)
        unwrapped.append(adjusted)
    return unwrapped


def center_coordinates(coords):
    center = [sum(coord[i] for coord in coords) / len(coords) for i in range(3)]
    return [[coord[i] - center[i] for i in range(3)] for coord in coords]


def format_coord_line(element, coord):
    return "{:<2s} {:16.8f} {:16.8f} {:16.8f}".format(
        element, coord[0], coord[1], coord[2]
    )


def write_xyz(path, elements, coords, ns, step, lx, lx_source):
    lines = [
        str(len(elements)),
        "PET trimer {} ns, timestep {}, unwrap Lx {:.6f} ({})".format(
            ns, step, lx, lx_source
        ),
    ]
    lines.extend(format_coord_line(element, coord) for element, coord in zip(elements, coords))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_orca_input(path, elements, coords):
    lines = [
        "! {}".format(ORCA_KEYWORDS),
        "%geom",
        "  MaxIter 300",
        "end",
        "",
        "* xyz 0 1",
    ]
    lines.extend(format_coord_line(element, coord) for element, coord in zip(elements, coords))
    lines.append("*")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_text(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


def main():
    if not DUMP_PATH.is_file():
        raise FileNotFoundError(DUMP_PATH)

    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    lx_by_step = read_lx_by_step(LOG_PATH)
    frames = read_target_frames(DUMP_PATH, [step for _, step in STEPS])

    summary_rows = []
    generated = []
    for ns, step in STEPS:
        atoms = frames[step]
        pet_atoms, all_coords = pet_atoms_from_frame(atoms)
        elements = [element for element, _ in pet_atoms]
        raw_coords = [coord for _, coord in pet_atoms]

        if step in lx_by_step:
            lx = lx_by_step[step]
            lx_source = "log"
        else:
            lx = estimate_lx_from_frame(all_coords)
            lx_source = "estimated_from_xyz_span"

        unwrapped = unwrap_sequential(raw_coords, lx)
        centered = center_coordinates(unwrapped)
        raw_spans = coordinate_spans(raw_coords)
        final_spans = coordinate_spans(centered)

        label = "{:02d}ns".format(ns)
        basename = "pet_{}_opt".format(label)
        xyz_name = "pet_{}_pet_unwrapped.xyz".format(label)

        frame_dir = PACKAGE_DIR / label
        frame_dir.mkdir(parents=True, exist_ok=True)
        xyz_path = frame_dir / xyz_name
        inp_path = frame_dir / "{}.inp".format(basename)
        slurm_path = frame_dir / "orca_opt.slurm"

        write_xyz(xyz_path, elements, centered, ns, step, lx, lx_source)
        write_orca_input(inp_path, elements, centered)
        write_text(
            slurm_path,
            SLURM_TEMPLATE.format(label=label, ncores=NCORES, basename=basename),
        )

        generated.extend([xyz_path, inp_path, slurm_path])
        summary_rows.append(
            {
                "ns": ns,
                "step": step,
                "natoms_pet": len(elements),
                "lx_used": "{:.8f}".format(lx),
                "lx_source": lx_source,
                "raw_span_x": "{:.8f}".format(raw_spans[0]),
                "raw_span_y": "{:.8f}".format(raw_spans[1]),
                "raw_span_z": "{:.8f}".format(raw_spans[2]),
                "final_span_x": "{:.8f}".format(final_spans[0]),
                "final_span_y": "{:.8f}".format(final_spans[1]),
                "final_span_z": "{:.8f}".format(final_spans[2]),
            }
        )

    summary_path = PACKAGE_DIR / "frame_lx_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    write_text(PACKAGE_DIR / "submit_all_pet_frames.sh", SUBMIT_ALL_TEXT)
    write_text(PACKAGE_DIR / "check_opt_results.sh", CHECK_RESULTS_TEXT)
    write_text(PACKAGE_DIR / "README_submit.md", README_TEXT)
    (PACKAGE_DIR / "source_eq1.xyz.info_only").write_text(
        "Source dump used to generate this package: {}\n".format(DUMP_PATH),
        encoding="utf-8",
        newline="\n",
    )

    print("Generated PET 1-10 ns ORCA optimization package:")
    print("  {}".format(PACKAGE_DIR.relative_to(ROOT)))
    for path in generated:
        print("  {}".format(path.relative_to(ROOT)))
    print("  {}".format(summary_path.relative_to(ROOT)))
    print("  {}".format((PACKAGE_DIR / "submit_all_pet_frames.sh").relative_to(ROOT)))
    print("  {}".format((PACKAGE_DIR / "check_opt_results.sh").relative_to(ROOT)))


if __name__ == "__main__":
    main()
