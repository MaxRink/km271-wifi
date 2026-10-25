#!/usr/bin/env python3
"""Replace main-board J2 (USB Mini-B) by HRO TYPE-C-31-M-12 with CC resistors R69/R70; local re-route only.
usage (KiCad python): usbc_swap.py KM217-WiFi/KM217-WiFi.kicad_pcb"""
import os, sys

LIB = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/'
f = sys.argv[1]

# 0) text step: drop the Mini-B footprint, insert library footprints (pcbnew.FootprintLoad breaks SWIG typing)
def block(text, start):
    d = 0
    for j in range(start, len(text)):
        d += {'(': 1, ')': -1}.get(text[j], 0)
        if d == 0:
            return j + 1

def lib_fp(lib, name, ref):
    s = open(LIB + lib + '.pretty/' + name + '.kicad_mod').read().strip()
    s = s.replace('(footprint "%s"' % name, '(footprint "%s:%s"\n\t(at 0 0)' % (lib, name), 1)
    return s.replace('"REF**"', '"%s"' % ref, 1)

if '--pcb' not in sys.argv:
  txt = open(f).read()
  i = txt.index('(footprint "the78mole:USB_Mini-B_Wuerth_65100516121_Horizontal"')
  txt = txt[:txt.rfind('\n', 0, i)] + txt[block(txt, i):]
  new = [lib_fp('Connector_USB', 'USB_C_Receptacle_HRO_TYPE-C-31-M-12', 'J2'),
         lib_fp('Resistor_SMD', 'R_0603_1608Metric_Pad0.98x0.95mm_HandSolder', 'R69'),
         lib_fp('Resistor_SMD', 'R_0603_1608Metric_Pad0.98x0.95mm_HandSolder', 'R70')]
  k = txt.rstrip().rfind(')')
  txt = txt[:k] + '\n'.join(new) + '\n' + txt[k:]
  open(f, 'w').write(txt)

  # pcbnew in a fresh process: SWIG lookups return untyped objects after the text step in the same process
  os.execv(sys.executable, [sys.executable, __file__, f, '--pcb'])

import pcbnew
b = pcbnew.LoadBoard(f)
mm = pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
UUID = {'J2': '943bc39b-4ee1-4b6e-8eb5-3ca750d35056', 'R69': '71861642-7a16-4c2c-a819-4501456e7783',
        'R70': '8728987e-89fd-4298-8b98-17731b2c468b'}

def net(name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
    return n

def near(a, x, y, tol=0.02):
    return abs(a.x - mm(x)) < mm(tol) and abs(a.y - mm(y)) < mm(tol)

old_shield = b.FindNet('Net-(J2-Shield)')
FP = {r: b.FindFootprintByReference(r) for r in ('J2', 'R69', 'R70', 'R60', 'R67')}
R60_PAD1 = [p for p in FP['R60'].Pads() if p.GetNumber() == '1'][0]

# 2) new footprints
def place(ref, value, x, y, rot):
    fp = FP[ref]
    fp.SetValue(value)
    fp.SetPath(pcbnew.KIID_PATH('/' + UUID[ref]))
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(rot)
    return fp

j2 = place('J2', 'USB_C', 78.3, 93.35, 180)
r69 = place('R69', '5K1', 79.55, 100.4, 270)
r70 = place('R70', '5K1', 77.05, 100.4, 270)
pads = {'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS',
        'A5': 'Net-(J2-CC1)', 'B5': 'Net-(J2-CC2)', 'SH': '/USB_SHIELD', 'A6': 'unconnected-(J2-D+-PadA6)',
        'B6': 'unconnected-(J2-D+-PadB6)', 'A7': 'unconnected-(J2-D--PadA7)', 'B7': 'unconnected-(J2-D--PadB7)',
        'A8': 'unconnected-(J2-SBU1-PadA8)', 'B8': 'unconnected-(J2-SBU2-PadB8)'}
for p in j2.Pads():
    if p.GetNumber() in pads:
        p.SetNet(net(pads[p.GetNumber()]))
for r, cc in ((r69, 'Net-(J2-CC1)'), (r70, 'Net-(J2-CC2)')):
    for p in r.Pads():
        p.SetNet(net(cc if p.GetNumber() == '1' else 'GND'))
R60_PAD1.SetNet(net('/USB_SHIELD'))

# 3) routing
def trk(layer, w, netname, *pts):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1)); t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(net(netname))
        b.Add(t)

def via(netname, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P(x, y)); v.SetDrill(mm(0.4)); v.SetWidth(mm(0.8)); v.SetNet(net(netname))
    b.Add(v)

F, B = pcbnew.F_Cu, pcbnew.B_Cu
# VBUS: right pads -> existing F.Cu chain to J3; left pads -> via -> B.Cu loop; C19 on B.Cu
trk(F, 0.5, 'VBUS', (80.75, 97.395), (80.75, 99.6), (80.75, 101.0), (80.8, 101.05))
via('VBUS', 80.75, 99.6)
trk(F, 0.5, 'VBUS', (75.85, 97.395), (75.85, 99.0))
via('VBUS', 75.85, 99.0)
trk(B, 0.5, 'VBUS', (75.85, 99.0), (75.85, 100.45), (76.45, 101.05), (80.2, 101.05), (80.75, 100.5), (80.75, 99.6))
trk(B, 0.5, 'VBUS', (80.75, 99.6), (80.25, 99.1), (79.16, 99.1))
# CC1/CC2 -> 5k1 -> GND
trk(F, 0.25, 'Net-(J2-CC1)', (79.55, 97.395), (79.55, 99.49))
trk(F, 0.25, 'Net-(J2-CC2)', (76.55, 97.395), (76.55, 98.3), (77.05, 98.8), (77.05, 99.49))
trk(F, 0.3, 'GND', (79.55, 101.31), (79.65, 102.9))
trk(F, 0.3, 'GND', (77.05, 101.31), (77.05, 102.3))
via('GND', 77.05, 102.3)
# GND contacts
trk(F, 0.5, 'GND', (81.55, 97.395), (81.55, 98.4), (82.0, 98.85), (82.0, 99.0))
via('GND', 82.0, 99.0)
trk(F, 0.5, 'GND', (75.05, 97.395), (75.05, 98.1), (74.6, 98.55), (74.6, 99.6))
via('GND', 74.6, 99.6)
# shield: tie the four shell legs, then to R60 (22R to GND, as before)
trk(F, 0.5, '/USB_SHIELD', (73.98, 92.3), (73.98, 96.48))
trk(F, 0.5, '/USB_SHIELD', (82.62, 92.3), (82.62, 96.48))
trk(B, 0.5, '/USB_SHIELD', (73.98, 96.48), (73.98, 97.2), (82.62, 97.2), (82.62, 96.48))
trk(F, 0.5, '/USB_SHIELD', (82.62, 96.48), (82.62, 97.6), (85.24, 100.22), (85.24, 100.25))

# silkscreen: refdes next to the new parts, keep the USBPWR label
def silk_ref(fp, x, y, rot=0):
    r = fp.Reference(); r.SetPosition(P(x, y)); r.SetTextAngleDegrees(rot)
silk_ref(j2, 84.0, 92.3, 90)
silk_ref(r69, 81.2, 100.4, 90)
silk_ref(r70, 78.3, 100.4, 90)
silk_ref(FP['R67'], 71.2, 101.75, 90)
for d in b.GetDrawings():
    if isinstance(d, pcbnew.PCB_TEXT) and d.GetText() == 'USBPWR':
        d.SetPosition(P(78.3, 102.75))

# 4) remove old J2 copper last: Board.Remove() breaks SWIG typing of later calls in this process
for t in list(b.GetTracks()):
    n = t.GetNetname()
    if n == 'Net-(J2-Shield)':
        b.Remove(t)
    elif t.GetClass() == 'PCB_VIA' and n == 'GND' and any(near(t.GetPosition(), x, y) for x, y in
                                                            [(78.4, 95.4), (76.7, 91.45), (80.15, 91.4)]):
        b.Remove(t)
    elif n == 'VBUS' and t.GetClass() == 'PCB_VIA' and near(t.GetPosition(), 79.9, 101.05):
        b.Remove(t)
    elif n == 'VBUS' and t.GetClass() == 'PCB_TRACK':
        ends = [(t.GetStart().x / 1e6, t.GetStart().y / 1e6), (t.GetEnd().x / 1e6, t.GetEnd().y / 1e6)]
        if any(abs(x - 79.9) < .02 and abs(y - 101.05) < .02 for x, y in ends) or \
           any(abs(x - 79.2) < .02 and abs(y - 99.14) < .02 for x, y in ends):
            b.Remove(t)

if old_shield is not None:
    b.Remove(old_shield)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(f)
print('ok')
