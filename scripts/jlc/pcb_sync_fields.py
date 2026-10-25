#!/usr/bin/env python3
"""Copy Value/LCSC/MPN/DNP from a schematic BOM CSV onto PCB footprints (no geometry changes).
usage (KiCad python): pcb_sync_fields.py board.kicad_pcb bom.csv
bom.csv from: kicad-cli sch export bom --fields 'Reference,Value,LCSC,MPN,${DNP}' --group-by '' """
import csv, sys, pcbnew

brd = pcbnew.LoadBoard(sys.argv[1])
rows = {r['Reference']: r for r in csv.DictReader(open(sys.argv[2]))}
for fp in brd.GetFootprints():
    r = rows.get(fp.GetReference())
    if not r:
        continue
    fp.SetValue(r['Value'])
    for k in ('LCSC', 'MPN'):
        if r.get(k):
            fp.SetField(k, r[k])
            fp.GetField(k).SetVisible(False)
    fp.SetDNP(r['DNP'] == 'DNP')
    no_part = not r.get('LCSC')
    fp.SetExcludedFromBOM(no_part)
    fp.SetExcludedFromPosFiles(no_part)
brd.Save(sys.argv[1])
