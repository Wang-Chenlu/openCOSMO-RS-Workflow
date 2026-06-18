#!/usr/bin/env python3
"""Prepare VMD files for viewing PET trimer structures from 1-10 ns."""

from pathlib import Path
import shutil


JOB = Path(__file__).resolve().parents[1]
OPT_PACKAGE = JOB / "pet_1_10ns_opt_package"
COSMORS_PACKAGE = JOB / "pet_02_10ns_cosmors_package"
FIRST_OPT_FINAL = JOB / "pet_cosmors_hpc_package" / "pet_trimer_opt_final.xyz"
OUT_DIR = JOB / "vmd_pet_trimer_1_10ns"


def parse_xyz_frames(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    frames = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        try:
            natoms = int(lines[index].strip())
        except ValueError as exc:
            raise ValueError("Expected atom count at line {} in {}".format(index + 1, path)) from exc
        comment_index = index + 1
        first_coord = index + 2
        last_coord = first_coord + natoms
        if last_coord > len(lines):
            raise ValueError("Truncated XYZ frame in {}".format(path))
        comment = lines[comment_index] if comment_index < len(lines) else ""
        coords = [line.strip() for line in lines[first_coord:last_coord] if line.strip()]
        if len(coords) != natoms:
            raise ValueError(
                "{} declares {} atoms but frame has {} coordinate lines".format(
                    path, natoms, len(coords)
                )
            )
        frames.append((natoms, comment, coords))
        index = last_coord
    if not frames:
        raise ValueError("No XYZ frames found in {}".format(path))
    return frames


def frame_to_text(natoms, comment, coords):
    return "{}\n{}\n{}\n".format(natoms, comment, "\n".join(coords))


def write_multiframe_xyz(path, frames):
    text = "".join(frame_to_text(natoms, comment, coords) for natoms, comment, coords in frames)
    path.write_text(text, encoding="utf-8", newline="\n")


def copy_single_frame(path, target, comment):
    natoms, _, coords = parse_xyz_frames(path)[-1]
    target.write_text(frame_to_text(natoms, comment, coords), encoding="utf-8", newline="\n")
    return natoms


def collect_md_frames():
    frames = []
    for ns in range(1, 11):
        label = "{:02d}ns".format(ns)
        path = OPT_PACKAGE / label / "pet_{}_pet_unwrapped.xyz".format(label)
        if not path.is_file():
            raise FileNotFoundError(path)
        natoms, _, coords = parse_xyz_frames(path)[0]
        frames.append((natoms, "{} MD extracted unwrapped PET trimer".format(label), coords))
    return frames


def collect_orca_opt_frames():
    frames = []
    first = FIRST_OPT_FINAL
    if not first.is_file():
        raise FileNotFoundError(first)
    natoms, _, coords = parse_xyz_frames(first)[0]
    frames.append((natoms, "01ns ORCA optimized PET trimer", coords))

    for ns in range(2, 11):
        label = "{:02d}ns".format(ns)
        candidates = [
            COSMORS_PACKAGE / label / "pet_{}_opt_final.xyz".format(label),
            OPT_PACKAGE / label / "pet_{}_opt_trj.xyz".format(label),
        ]
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            raise FileNotFoundError(
                "Missing optimized structure for {}. Checked: {}".format(
                    label, ", ".join(str(candidate) for candidate in candidates)
                )
            )
        natoms, _, coords = parse_xyz_frames(path)[-1]
        frames.append((natoms, "{} ORCA optimized PET trimer".format(label), coords))
    return frames


def write_tcl(path, xyz_name, title, material="Opaque"):
    text = r'''# VMD script: {title}
# Run from this folder:
#   vmd -e {script_name}

mol delete all
display projection Orthographic
display depthcue off
axes location Off
color Display Background white

mol new "{xyz_name}" type xyz waitfor all
mol delrep 0 top
mol representation Licorice 0.18 12 12
mol color Element
mol material {material}
mol addrep top

animate goto 0
molinfo top set frame 0

set nframes [molinfo top get numframes]
puts "Loaded {title}"
puts "Frames: $nframes"
puts "Use the VMD frame slider to browse 01ns to 10ns."
puts "Frame index 0 = 01ns, frame index 9 = 10ns."
'''.format(
        title=title,
        script_name=path.name,
        xyz_name=xyz_name,
        material=material,
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def write_readme(path):
    text = """# VMD PET trimer 1-10 ns viewer

This folder contains VMD-ready files for the PET trimer structures:

```text
pet_trimer_md_1_10ns.xyz
pet_trimer_orca_opt_1_10ns.xyz
load_pet_md_1_10ns.tcl
load_pet_orca_opt_1_10ns.tcl
```

Use VMD from this folder:

```bash
vmd -e load_pet_md_1_10ns.tcl
vmd -e load_pet_orca_opt_1_10ns.tcl
```

Frame mapping:

```text
frame 0 = 01ns
frame 1 = 02ns
...
frame 9 = 10ns
```

`pet_trimer_md_1_10ns.xyz` uses the PET trimer conformations extracted from
the MD trajectory before ORCA optimization.

`pet_trimer_orca_opt_1_10ns.xyz` uses the final ORCA-optimized PET trimer
structures used for COSMORS calculations.
"""
    path.write_text(text, encoding="utf-8", newline="\n")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    md_frames = collect_md_frames()
    opt_frames = collect_orca_opt_frames()

    md_xyz = OUT_DIR / "pet_trimer_md_1_10ns.xyz"
    opt_xyz = OUT_DIR / "pet_trimer_orca_opt_1_10ns.xyz"
    write_multiframe_xyz(md_xyz, md_frames)
    write_multiframe_xyz(opt_xyz, opt_frames)

    write_tcl(OUT_DIR / "load_pet_md_1_10ns.tcl", md_xyz.name, "PET trimer MD extracted structures, 1-10 ns")
    write_tcl(OUT_DIR / "load_pet_orca_opt_1_10ns.tcl", opt_xyz.name, "PET trimer ORCA optimized structures, 1-10 ns")
    write_readme(OUT_DIR / "README_vmd.md")

    # Keep single-frame files as a fallback for VMD versions that do not treat
    # multi-frame XYZ as a trajectory.
    single_dir = OUT_DIR / "single_frames"
    single_dir.mkdir(parents=True, exist_ok=True)
    for ns in range(1, 11):
        label = "{:02d}ns".format(ns)
        md_source = OPT_PACKAGE / label / "pet_{}_pet_unwrapped.xyz".format(label)
        copy_single_frame(
            md_source,
            single_dir / "pet_{}_md_unwrapped.xyz".format(label),
            "{} MD extracted unwrapped PET trimer".format(label),
        )

    for i, (natoms, comment, coords) in enumerate(opt_frames, start=1):
        label = "{:02d}ns".format(i)
        (single_dir / "pet_{}_orca_opt_final.xyz".format(label)).write_text(
            frame_to_text(natoms, comment, coords),
            encoding="utf-8",
            newline="\n",
        )

    print("Generated VMD package:")
    print("  {}".format(OUT_DIR.relative_to(JOB)))
    print("  {}".format(md_xyz.relative_to(JOB)))
    print("  {}".format(opt_xyz.relative_to(JOB)))
    print("Frames: MD={}, ORCA optimized={}".format(len(md_frames), len(opt_frames)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
