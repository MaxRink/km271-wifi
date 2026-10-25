#!/usr/bin/env python3
"""Add/update LCSC (and optional Value/MPN/Footprint) fields on placed symbols.
usage: sch_lcsc.py file.kicad_sch map.json
map.json: {"by_value": {"100n": "C14663", ...}, "by_ref": {"U1": {"LCSC": "...", "Value": "...", "MPN": "...", "Footprint": "..."}}}
Skips DNP symbols and power/virtual symbols (refs starting with '#')."""
import json, re, sys

sch, m = sys.argv[1], json.load(open(sys.argv[2]))
txt = open(sch).read()
lines = txt.split('\n')
out, i, n = [], 0, 0

def prop(block, name):
    mm = re.search(r'\(property "%s" "([^"]*)"' % re.escape(name), block)
    return mm.group(1) if mm else None

def set_prop(block, name, val):
    if prop(block, name) is not None:
        return re.sub(r'(\(property "%s" )"[^"]*"' % re.escape(name), lambda x: x.group(1) + json.dumps(val), block, count=1)
    at = re.search(r'\n\t\t\(at ([^)]*)\)', block).group(1)
    new = ('\t\t(property "%s" %s\n\t\t\t(at %s)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
           '\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n') % (name, json.dumps(val), at)
    k = block.index('\t\t(property "Footprint"')
    return block[:k] + new + block[k:]

while i < len(lines):
    if lines[i] == '\t(symbol':
        j = i + 1
        while lines[j] != '\t)':
            j += 1
        block = '\n'.join(lines[i:j + 1])
        ref, val = prop(block, 'Reference'), prop(block, 'Value')
        if ref and not ref.startswith('#') and '(dnp yes)' not in block:
            upd = dict(m.get('by_ref', {}).get(ref, {}))
            if 'LCSC' not in upd and val in m.get('by_value', {}):
                upd['LCSC'] = m['by_value'][val]
            for k, v in upd.items():
                block = set_prop(block, k, v)
            if upd:
                n += 1
            elif ref[0] not in 'H':
                print('no LCSC for', ref, val, file=sys.stderr)
        out.append(block)
        i = j + 1
    else:
        out.append(lines[i]); i += 1
open(sch, 'w').write('\n'.join(out))
print('updated', n, 'symbols')
