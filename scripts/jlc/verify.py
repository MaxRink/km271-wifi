#!/usr/bin/env python3
"""Regression check of a board against a git baseline (KiCad python).
usage: verify.py <project path, e.g. KM217-WiFi/KM217-WiFi> <baseline git rev>
Reports: pin-level netlist diff (net-name independent), footprint add/remove/move, BOM/CPL/PCB refdes
consistency, hidden refdes, and the nets on connector/LED pins for checking silkscreen labels."""
import csv, os, re, subprocess, sys, tempfile, pcbnew

proj, base = sys.argv[1:3]
tmp = tempfile.mkdtemp()


def netlist(sch):
    out = os.path.join(tmp, os.path.basename(sch) + '.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out, sch],
                   check=True, capture_output=True)
    txt = open(out).read()
    pins = {}
    for m in re.finditer(r'\(net\s*\(code "?\d+"?\)\s*\(name "([^"]*)"\)(.*?)(?=\(net\s*\(code|\Z)', txt, re.S):
        nodes = frozenset(re.findall(r'\(ref "([^"]*)"\)\s*\(pin "([^"]*)"\)', m.group(2)))
        for n in nodes:
            pins[n] = (m.group(1), nodes)
    return pins


def baseline(rel):
    dst = os.path.join(tmp, 'base_' + os.path.basename(rel))
    open(dst, 'wb').write(subprocess.run(['git', 'show', '%s:%s' % (base, rel)], check=True,
                                         capture_output=True).stdout)
    return dst


print('== netlist (pin -> connected pins), baseline', base)
old, new = netlist(baseline(proj + '.kicad_sch')), netlist(proj + '.kicad_sch')
for p in sorted(set(old) | set(new)):
    o, n = old.get(p), new.get(p)
    if o is None:
        print('  + %s.%s  net %s -> %s' % (p[0], p[1], n[0], sorted('%s.%s' % x for x in n[1] - {p})))
    elif n is None:
        print('  - %s.%s  (was net %s)' % (p[0], p[1], o[0]))
    elif o[1] != n[1]:
        print('  ~ %s.%s  %s -> %s  gained %s lost %s' % (p[0], p[1], o[0], n[0],
              sorted('%s.%s' % x for x in n[1] - o[1]), sorted('%s.%s' % x for x in o[1] - n[1])))

print('== placement')
ob, nb = pcbnew.LoadBoard(baseline(proj + '.kicad_pcb')), pcbnew.LoadBoard(proj + '.kicad_pcb')
of = {f.GetReference(): f for f in ob.GetFootprints()}
nf = {f.GetReference(): f for f in nb.GetFootprints()}
for r in sorted(set(of) | set(nf)):
    a, b = of.get(r), nf.get(r)
    if a is None:
        print('  + %s %s at (%.2f, %.2f) %s' % (r, b.GetFPIDAsString(), b.GetPosition().x / 1e6,
              b.GetPosition().y / 1e6, 'B' if b.IsFlipped() else 'F'))
    elif b is None:
        print('  - %s' % r)
    elif (a.GetPosition() != b.GetPosition() or a.GetOrientationDegrees() != b.GetOrientationDegrees()
          or a.IsFlipped() != b.IsFlipped() or a.GetFPIDAsString() != b.GetFPIDAsString()):
        print('  ~ %s %s (%.2f,%.2f,%g) -> %s (%.2f,%.2f,%g)' % (r, a.GetFPIDAsString(), a.GetPosition().x / 1e6,
              a.GetPosition().y / 1e6, a.GetOrientationDegrees(), b.GetFPIDAsString(), b.GetPosition().x / 1e6,
              b.GetPosition().y / 1e6, b.GetOrientationDegrees()))
print('  tracks %d -> %d, vias %d -> %d' % (
    sum(t.GetClass() == 'PCB_TRACK' for t in ob.GetTracks()), sum(t.GetClass() == 'PCB_TRACK' for t in nb.GetTracks()),
    sum(t.GetClass() == 'PCB_VIA' for t in ob.GetTracks()), sum(t.GetClass() == 'PCB_VIA' for t in nb.GetTracks())))

print('== BOM / CPL / PCB refdes')
prod = os.path.join(os.path.dirname(proj), 'production')
bom = set()
for row in csv.DictReader(open(os.path.join(prod, 'bom.csv'), encoding='utf-8-sig')):
    bom |= {d.strip() for d in row['Designator'].split(',')}
    if not row['LCSC Part #'].startswith('C'):
        print('  BOM row without LCSC code:', row['Designator'], row['Value'])
cpl = {r['Designator'] for r in csv.DictReader(open(os.path.join(prod, 'positions.csv'), encoding='utf-8-sig'))}
fit = {r for r, f in nf.items() if not f.IsDNP() and not f.IsExcludedFromBOM()}
print('  BOM %d, CPL %d, fitted PCB %d' % (len(bom), len(cpl), len(fit)))
for name, s in (('BOM', bom), ('CPL', cpl)):
    if s != fit:
        print('  %s mismatch: missing %s extra %s' % (name, sorted(fit - s), sorted(s - fit)))

print('== hidden refdes (not FID/logo)')
print('  ', sorted(r for r, f in nf.items() if not f.Reference().IsVisible() and not r.startswith(('FID', 'LOGO'))))

print('== connector / LED pin nets (for label check)')
for r in sorted(nf):
    if re.match(r'^(J\d+|D\d+|SW\d+)$', r):
        f = nf[r]
        print('  %s %s: %s' % (r, f.GetValue(), ', '.join('%s=%s' % (p.GetNumber(), p.GetNetname())
              for p in sorted(f.Pads(), key=lambda p: (len(p.GetNumber()), p.GetNumber())) if p.GetNumber())))
