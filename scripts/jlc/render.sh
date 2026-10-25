#!/bin/bash
# Render top/bottom PNGs: as assembled by JLC (DNP hidden) and fully populated (DNP options shown).
# usage: render.sh board.kicad_pcb out_prefix
set -e
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
b="$1"; o="$2"; tmp="$(dirname "$b")/.render_full_$(basename "$b")"
for s in top bottom; do kicad-cli pcb render --side $s -w 1800 -h 1000 --quality high -o "${o}_${s}.png" "$b" >/dev/null 2>&1; done
"$PY" -c "
import pcbnew,sys
x=pcbnew.LoadBoard(sys.argv[1])
for f in x.GetFootprints(): f.SetDNP(False)
x.Save(sys.argv[2])" "$b" "$tmp" 2>/dev/null
for s in top bottom; do kicad-cli pcb render --side $s -w 1800 -h 1000 --quality high -o "${o}_full_${s}.png" "$tmp" >/dev/null 2>&1; done
rm -f "$tmp" "${tmp%.kicad_pcb}.kicad_prl" "${tmp%.kicad_pcb}.kicad_pro"
