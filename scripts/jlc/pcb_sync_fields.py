#!/usr/bin/env python3
"""Copy symbol fields + DNP from a schematic BOM CSV onto PCB footprints (no geometry changes).
usage (KiCad python): pcb_sync_fields.py board.kicad_pcb bom.csv
bom.csv: kicad-cli sch export bom --group-by "" --fields "Reference,Value,${DNP},<other fields>" ("DNP" column)"""
import csv, sys, pcbnew

brd = pcbnew.LoadBoard(sys.argv[1])
rows = {r['Reference']: r for r in csv.DictReader(open(sys.argv[2]))}
for fp in brd.GetFootprints():
    r = rows.get(fp.GetReference())
    if not r:
        continue
    fp.SetValue(r.pop('Value'))
    fp.SetDNP(r.pop('DNP') == 'DNP')
    for k, v in r.items():
        if k in ('Reference', 'Footprint', 'Datasheet', 'Description') or not v:
            continue
        new = not fp.HasField(k)
        fp.SetField(k, v)
        if new:
            fp.GetField(k).SetVisible(False)
brd.Save(sys.argv[1])
