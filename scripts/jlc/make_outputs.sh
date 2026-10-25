#!/bin/bash
# Regenerate JLC fab outputs for one KiCad project into <project>/production/:
# Fabrication Toolkit zip/BOM/CPL, iBOM, schematic + PCB PDF, STEP, renders (assembled + fully populated), DRC/ERC.
# usage: scripts/jlc/make_outputs.sh KM217-WiFi/KM217-WiFi
set -e
b="$1"; d="$(dirname "$b")"; n="$(basename "$b")"; here="$(cd "$(dirname "$0")" && pwd)"
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
PL=~/Documents/KiCad/10.0/scripting/plugins
out="$d/production"; mkdir -p "$out"
(cd "$PL" && "$PY" -m Fabrication-Toolkit.cli -p "$OLDPWD/$b.kicad_pcb" -t -f -e -nI -nB >/dev/null 2>&1)
"$PY" "$PL/InteractiveHtmlBom/InteractiveHtmlBom/generate_interactive_bom.py" --no-browser --dest-dir production \
  --name-format "${n}_ibom" --include-tracks --include-nets --extra-fields "LCSC,MPN" --blacklist "FID*,TP*,H*,JP*" \
  "$b.kicad_pcb" >/dev/null 2>&1
kicad-cli sch export pdf -o "$out/${n}_schematic.pdf" "$b.kicad_sch" >/dev/null 2>&1
kicad-cli pcb export pdf --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts,F.Fab,B.Fab,Cmts.User \
  --mode-multipage -o "$out/${n}_pcb.pdf" "$b.kicad_pcb" >/dev/null 2>&1
"$here/export_step.sh" "$b.kicad_pcb" "$out/${n}.step" >/dev/null
"$here/render.sh" "$b.kicad_pcb" "$out/${n}"
kicad-cli pcb drc --schematic-parity --severity-error -o "$out/drc.rpt" "$b.kicad_pcb" >/dev/null 2>&1
kicad-cli sch erc --severity-error -o "$out/erc.rpt" "$b.kicad_sch" >/dev/null 2>&1
echo "$n: DRC errors $(grep -c '^\[' "$out/drc.rpt"), ERC errors $(grep -c '^\[' "$out/erc.rpt")"
