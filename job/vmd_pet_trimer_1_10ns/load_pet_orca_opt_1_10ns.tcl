# VMD script: PET trimer ORCA optimized structures, 1-10 ns
# Run from this folder:
#   vmd -e load_pet_orca_opt_1_10ns.tcl

mol delete all
display projection Orthographic
display depthcue off
axes location Off
color Display Background white

mol new "pet_trimer_orca_opt_1_10ns.xyz" type xyz waitfor all
mol delrep 0 top
mol representation Licorice 0.18 12 12
mol color Element
mol material Opaque
mol addrep top

animate goto 0
molinfo top set frame 0

set nframes [molinfo top get numframes]
puts "Loaded PET trimer ORCA optimized structures, 1-10 ns"
puts "Frames: $nframes"
puts "Use the VMD frame slider to browse 01ns to 10ns."
puts "Frame index 0 = 01ns, frame index 9 = 10ns."
