#!/bin/bash
# Export STEP with KiCad 10 stock 3D models: board files reference ${KICAD6/8/9_3DMODEL_DIR}/*.wrl,
# which kicad-cli 10 does not resolve. Rewrite to absolute .step paths in a temp copy next to the board.
# usage: export_step.sh board.kicad_pcb out.step
set -e
M=/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels
tmp="$(dirname "$1")/.step_tmp_$(basename "$1")"
sed -E "s#\\\$\{KICAD[0-9]+_3DMODEL_DIR\}#$M#g; s#(${M//\//\\/}[^\"]*)\.wrl\"#\1.step\"#g" "$1" > "$tmp"
kicad-cli pcb export step --subst-models --force -o "$2" "$tmp" 2>&1 | grep -c 'Could not add' || true
rm -f "$tmp" "${tmp%.kicad_pcb}.kicad_prl"
