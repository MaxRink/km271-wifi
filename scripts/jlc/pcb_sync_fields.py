#!/usr/bin/env python3
"""Copy symbol fields + Value + DNP from the schematic onto PCB footprints (no geometry changes).
Reads the KiCad netlist, which (unlike the BOM export) includes symbols excluded from the BOM.
usage (KiCad python): pcb_sync_fields.py board.kicad_pcb board.kicad_sch"""
import os, re, subprocess, sys, tempfile, pcbnew

brd_path, sch_path = sys.argv[1:3]
net_path = os.path.join(tempfile.mkdtemp(), 'sync.net')
subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', net_path, sch_path],
               check=True, capture_output=True)
txt = open(net_path).read()

comps = {}
for m in re.finditer(r'\(comp\s*\(ref "([^"]*)"\)\s*\(value "([^"]*)"\)(.*?)\(tstamps "[^"]*"\)', txt, re.S):
    ref, value, body = m.groups()
    fields = dict(re.findall(r'\(field\s*\(name "([^"]*)"\)\s*(?:"((?:[^"\\]|\\.)*)")?\)', body))
    dnp = re.search(r'\(property\s*\(name "dnp"\)', body) is not None
    comps[ref] = (value, {k: v.replace('\\"', '"') for k, v in fields.items()}, dnp)

brd = pcbnew.LoadBoard(brd_path)
for fp in brd.GetFootprints():
    c = comps.get(fp.GetReference())
    if not c:
        continue
    value, fields, dnp = c
    fp.SetValue(value)
    fp.SetDNP(dnp)
    for k, v in fields.items():
        if k in ('Reference', 'Value', 'Footprint'):
            continue
        new = not fp.HasField(k)
        fp.SetField(k, v)
        if new:
            fp.GetField(k).SetVisible(False)
brd.Save(brd_path)
