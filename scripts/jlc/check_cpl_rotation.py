#!/usr/bin/env python3
"""Verify CPL rotations against JLC's own (EasyEDA) footprints (KiCad python).
For each fitted footprint with an LCSC code: fetch the EasyEDA footprint with easyeda2kicad,
find the rotation (0/90/180/270) + offset that maps our pads (by number) onto JLC's, and compare
with the rotation Fabrication Toolkit wrote to positions.csv.
usage: check_cpl_rotation.py board.kicad_pcb production/positions.csv cache_dir [--pad1-anode C2286,...]
--pad1-anode: LCSC parts whose JLC pad 1 is the anode (KiCad LED/diode pad 1 = cathode):
matched by function, so the pad-number correction is flipped by 180 deg.
--pad-map C306880:1=1+2,2=3+4  maps our pad names to JLC pad names (bridged pin pairs)."""
import csv, math, os, re, subprocess, sys, pcbnew

brd, pos_csv, cache = sys.argv[1:4]
PADMAP = {}
if '--pad-map' in sys.argv:
    for spec in sys.argv[sys.argv.index('--pad-map') + 1].split(';'):
        part, pairs = spec.split(':')
        PADMAP[part] = {a: b.split('+') for a, b in (x.split('=') for x in pairs.split(','))}
ANODE1 = set(sys.argv[sys.argv.index('--pad1-anode') + 1].split(',')) if '--pad1-anode' in sys.argv else set()
os.makedirs(cache, exist_ok=True)
cpl = {r['Designator']: r for r in csv.DictReader(open(pos_csv, encoding='utf-8-sig'))}

def jlc_pads(lcsc):
    out = os.path.join(cache, lcsc)
    if not os.path.isdir(out + '.pretty'):
        subprocess.run(['easyeda2kicad', '--footprint', '--lcsc_id=' + lcsc, '--output', out],
                       capture_output=True, timeout=120)
    mods = [f for f in os.listdir(out + '.pretty')] if os.path.isdir(out + '.pretty') else []
    if not mods:
        return None
    txt = open(os.path.join(out + '.pretty', mods[0])).read()
    pads = {}
    for m in re.finditer(r'\(pad "?([^" ]*)"? \w+ \w+ \(at ([-\d.]+) ([-\d.]+)', txt):
        pads.setdefault(m.group(1), []).append((float(m.group(2)), float(m.group(3))))
    return pads

def rot(p, deg):
    a = math.radians(deg)
    # KiCad: positive rotation is CCW on screen with Y down
    return (p[0] * math.cos(a) + p[1] * math.sin(a), -p[0] * math.sin(a) + p[1] * math.cos(a))

b = pcbnew.LoadBoard(brd)
seen = {}
for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    ref = fp.GetReference()
    if ref not in cpl or not fp.HasField('LCSC') or not fp.GetFieldText('LCSC').startswith('C'):
        continue
    lcsc = fp.GetFieldText('LCSC')
    key = (fp.GetFPIDAsString(), lcsc)
    ours = {}
    for p in fp.Pads():
        if p.GetNumber():
            lp = p.GetFPRelativePosition()
            ours.setdefault(p.GetNumber(), []).append((lp.x / 1e6, lp.y / 1e6))
    if key not in seen:
        theirs = jlc_pads(lcsc)
        if theirs and lcsc in PADMAP:
            theirs = {ours_name: sum((theirs.get(j, []) for j in js), []) for ours_name, js in PADMAP[lcsc].items()}
        best = None
        if theirs:
            common = [n for n in ours if n in theirs]
            for deg in (0, 90, 180, 270):
                pairs = []
                for n in common:
                    rest = list(theirs[n])
                    for q in ours[n]:
                        r = rot(q, deg)
                        if not rest:
                            break
                        k = min(range(len(rest)), key=lambda i: math.hypot(rest[i][0] - r[0], rest[i][1] - r[1]))
                        pairs.append((r, rest.pop(k)))
                if not pairs:
                    break
                for _ in range(2):  # re-match after removing the centroid offset
                    dx = sum(c[0] - a[0] for a, c in pairs) / len(pairs)
                    dy = sum(c[1] - a[1] for a, c in pairs) / len(pairs)
                    pairs2 = []
                    for n in common:
                        rest = list(theirs[n])
                        for q in ours[n]:
                            r = rot(q, deg)
                            if not rest:
                                break
                            k = min(range(len(rest)), key=lambda i: math.hypot(rest[i][0] - r[0] - dx, rest[i][1] - r[1] - dy))
                            pairs2.append((r, rest.pop(k)))
                    pairs = pairs2
                err = max(math.hypot(a[0] + dx - c[0], a[1] + dy - c[1]) for a, c in pairs)
                if best is None or err < best[1]:
                    best = (deg, err, dx, dy, len(pairs))
        seen[key] = best
    best = seen[key]
    side = 'bottom' if fp.IsFlipped() else 'top'
    fp_rot = fp.GetOrientationDegrees() % 360
    cpl_rot = float(cpl[ref]['Rotation']) % 360
    if best is None:
        print(f'{ref:5} {lcsc:9} {side:6} no JLC footprint / no pad match')
        continue
    deg, err, dx, dy, n = best
    if lcsc in ANODE1:
        deg = (deg + 180) % 360
    # required: JLC rotation = board rotation + correction where correction maps JLC's 0deg to ours
    need = (fp_rot + (360 - deg)) % 360 if side == 'top' else None
    ok = 'OK ' if side == 'bottom' or abs(((need - cpl_rot) + 180) % 360 - 180) < 1 else 'BAD'
    print(f'{ref:5} {lcsc:9} {side:6} fp={fp_rot:5.0f} corr={(360-deg)%360:3d} need={need if need is not None else "-":>5} cpl={cpl_rot:5.0f} '
          f'off=({dx:+.2f},{dy:+.2f}) fit={err:.2f}mm/{n}pads {ok}')
