#!/usr/bin/env python3
"""Find free spots for JLC fiducials (1 mm Cu, 2 mm mask) per side and optionally place them (KiCad python).
usage: find_fiducial_spots.py board.kicad_pcb [--place]
Spot rules: >= 3.35 mm from board edge (JLC), >= 1.2 mm from same-side copper (tracks/pads/vias),
>= 1.6 mm outside every footprint bbox (fiducial courtyard), >= 0.5 mm from silk. Picks 3 spots per side maximising triangle area."""
import itertools, math, sys, pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
mm, MM = pcbnew.FromMM, 1e6
edge = b.GetBoardEdgesBoundingBox()
outline = pcbnew.SHAPE_POLY_SET()
b.GetBoardPolygonOutlines(outline, False)

def free(side, x, y):
    p = pcbnew.VECTOR2I(int(x), int(y))
    if not outline.Contains(p):
        return False
    if outline.COutline(0).SquaredDistance(p, True) ** 0.5 < 3.35 * MM:
        return False
    for h in range(outline.HoleCount(0)):
        if outline.CHole(0, h).SquaredDistance(p, True) ** 0.5 < 3.35 * MM:
            return False
    cu = pcbnew.F_Cu if side == 'F' else pcbnew.B_Cu
    for t in b.GetTracks():
        if t.IsOnLayer(cu) and t.HitTest(p, int(1.2 * MM + t.GetWidth() / 2)):
            return False
    for f in b.GetFootprints():
        if f.GetReference().startswith('FID'):
            continue
        bb = f.GetBoundingBox(False)
        bb.Inflate(int(1.6 * MM))
        if bb.Contains(p):
            return False
        for pad in f.Pads():
            if pad.IsOnLayer(cu) and pad.HitTest(p, int(1.2 * MM)):
                return False
    silk = pcbnew.F_SilkS if side == 'F' else pcbnew.B_SilkS
    mask = pcbnew.F_Mask if side == 'F' else pcbnew.B_Mask
    for d in b.GetDrawings():
        if d.GetLayer() in (silk, mask, cu) and d.HitTest(p, int(1.5 * MM)):
            return False
    return True

res = {}
for side in 'FB':
    pts = [(x, y) for x in range(edge.GetLeft(), edge.GetRight(), int(MM))
           for y in range(edge.GetTop(), edge.GetBottom(), int(MM)) if free(side, x, y)]
    best, area = None, 0
    # coarse subsample to keep it fast
    cand = pts[::max(1, len(pts) // 120)]
    for a, c, d in itertools.combinations(cand, 3):
        ar = abs((c[0]-a[0])*(d[1]-a[1]) - (d[0]-a[0])*(c[1]-a[1]))
        if ar > area:
            best, area = (a, c, d), ar
    res[side] = best
    print(side, len(pts), 'free;', best and [(round(x/MM, 2), round(y/MM, 2)) for x, y in best])

if '--place' in sys.argv:
    lib = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Fiducial.pretty'
    old = {f.GetReference(): f for f in b.GetFootprints() if f.GetReference().startswith('FID')}
    n = 1
    for side, spots in res.items():
        for x, y in spots or []:
            ref = 'FID%d' % n; n += 1
            fp = old.pop(ref, None)
            if fp is None:
                fp = pcbnew.FootprintLoad(lib, 'Fiducial_1mm_Mask2mm')
                fp.SetReference(ref)
                fp.Reference().SetVisible(False)
                b.Add(fp)
            if fp.IsFlipped() != (side == 'B'):
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    for fp in old.values():
        b.Remove(fp)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(sys.argv[1])
