#!/usr/bin/env python3
"""Extract a PET-only structure from a LAMMPS XYZ dump for ORCA optimization."""

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PET_DIR = ROOT / "35-PET"
LOG_PATH = PET_DIR / "log"
DUMP_PATH = PET_DIR / "eq1.xyz"

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
ORCA_KEYWORDS_TEMPLATE = "M062X def2-SVP D3zero Opt noautostart miniprint pal{ncores}"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract PET from LAMMPS XYZ dump and write ORCA opt input."
    )
    parser.add_argument(
        "--step",
        type=int,
        default=500000,
        help="LAMMPS timestep to extract. 500000 = 1 ns when timestep is 2 fs.",
    )
    parser.add_argument(
        "--label",
        default="1ns",
        help="Label used in the extracted XYZ filename.",
    )
    parser.add_argument(
        "--ncores",
        type=int,
        default=4,
        help="ORCA PAL core count written to the input keyword.",
    )
    parser.add_argument(
        "--write-main-input",
        action="store_true",
        help="Also overwrite 35-PET_opt.inp.",
    )
    return parser.parse_args()


def read_lx_at_step(log_path, step):
    with log_path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit() and int(parts[0]) == step:
                return float(parts[2])
    raise ValueError("Could not find step {} in {}".format(step, log_path))


def read_frame(dump_path, step):
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
            if comment == "Atoms. Timestep: {}".format(step):
                return atoms
    raise ValueError("Could not find timestep {} in {}".format(step, dump_path))


def nearest_image_delta(delta, box_length):
    half = 0.5 * box_length
    if delta > half:
        return delta - box_length
    if delta < -half:
        return delta + box_length
    return delta


def unwrap_sequential(coords, box_length):
    if not coords:
        return []
    unwrapped = [coords[0]]
    for coord in coords[1:]:
        prev = unwrapped[-1]
        adjusted = []
        for current, previous in zip(coord, prev):
            delta = nearest_image_delta(current - previous, box_length)
            adjusted.append(previous + delta)
        unwrapped.append(adjusted)
    return unwrapped


def center_coordinates(coords):
    center = [sum(coord[i] for coord in coords) / len(coords) for i in range(3)]
    return [[coord[i] - center[i] for i in range(3)] for coord in coords]


def pet_atoms_from_frame(atoms):
    pet_atoms = []
    for fields in atoms:
        if len(fields) != 4:
            raise ValueError("Unexpected XYZ atom line: {}".format(fields))
        label = fields[0]
        if label in WATER_LABELS:
            continue
        if label not in ELEMENT_BY_LABEL:
            raise ValueError("Unknown atom label: {}".format(label))
        coord = [float(value) for value in fields[1:4]]
        pet_atoms.append((ELEMENT_BY_LABEL[label], coord))
    return pet_atoms


def write_xyz(path, elements, coords, step):
    lines = [
        str(len(elements)),
        "PET trimer extracted from eq1.xyz timestep {}".format(step),
    ]
    for element, coord in zip(elements, coords):
        lines.append(
            "{:<2s} {:16.8f} {:16.8f} {:16.8f}".format(
                element, coord[0], coord[1], coord[2]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_orca_input(path, elements, coords, ncores):
    lines = [
        "! {}".format(ORCA_KEYWORDS_TEMPLATE.format(ncores=ncores)),
        "%geom",
        "  MaxIter 300",
        "end",
        "",
        "* xyz 0 1",
    ]
    for element, coord in zip(elements, coords):
        lines.append(
            "{:<2s} {:16.8f} {:16.8f} {:16.8f}".format(
                element, coord[0], coord[1], coord[2]
            )
        )
    lines.append("*")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def coordinate_range(coords):
    return [
        (min(coord[i] for coord in coords), max(coord[i] for coord in coords))
        for i in range(3)
    ]


def main():
    args = parse_args()
    lx = read_lx_at_step(LOG_PATH, args.step)
    frame_atoms = read_frame(DUMP_PATH, args.step)
    pet_atoms = pet_atoms_from_frame(frame_atoms)
    elements = [element for element, _ in pet_atoms]
    raw_coords = [coord for _, coord in pet_atoms]
    unwrapped = unwrap_sequential(raw_coords, lx)
    centered = center_coordinates(unwrapped)

    xyz_path = PET_DIR / "35-PET_{}_pet_unwrapped.xyz".format(args.label)
    inp_path = PET_DIR / "35-PET_{}_opt.inp".format(args.label)
    write_xyz(xyz_path, elements, centered, args.step)
    write_orca_input(inp_path, elements, centered, args.ncores)

    if args.write_main_input:
        write_orca_input(PET_DIR / "35-PET_opt.inp", elements, centered, args.ncores)

    print("Extracted timestep:", args.step)
    print("Lx used for unwrap:", lx)
    print("PET atoms:", len(elements))
    print("Raw coordinate range:", coordinate_range(raw_coords))
    print("Unwrapped centered coordinate range:", coordinate_range(centered))
    print("Wrote:", xyz_path.relative_to(ROOT))
    print("Wrote:", inp_path.relative_to(ROOT))
    if args.write_main_input:
        print("Updated:", (PET_DIR / "35-PET_opt.inp").relative_to(ROOT))


if __name__ == "__main__":
    main()
