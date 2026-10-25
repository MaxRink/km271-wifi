#!/usr/bin/env python3
"""Attach repo 3D models (3dmodels/) to footprints whose models are missing (KiCad python).
usage: assign_models.py board.kicad_pcb
Vendor models: EasyEDA STEP aligned to the KiCad footprint (rotation/offset from pad fit).
Approximate boxes: generated from the footprint courtyard and the datasheet height."""
import math, os, re, subprocess, sys, pcbnew

f = sys.argv[1]
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
rel = os.path.relpath(os.path.join(repo, '3dmodels'), os.path.dirname(os.path.abspath(f)))
base = '${KIPRJMOD}/' + rel + '/'
STOCK = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'
# footprint id -> (model file, rotate z, offset x, offset y (y up)) or ('box', file, height, rgb)
MODELS = {
    'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12': ('USB-C_HRO_TYPE-C-31-M-12.step', 0, 0.0, 1.575),
    'Transformer_SMD:Transformer_Ethernet_Wuerth_749013011A': ('Wuerth_749013011A.step', 270, 0.0, -0.005),
    'the78mole:WE-MJ-634008137521': ('box', 'Wuerth_634008137521_RJ45_approx.wrl', 13.4, '0.75 0.75 0.75'),
    'the78mole:WE-MM-690367290876': ('box', 'Wuerth_690367290876_WR-MM_approx.wrl', 5.75, '0.8 0.15 0.1'),
    'the78mole:WAGO 2086-1208': ('box', 'WAGO_2086-1208_approx.wrl', 12.0, '0.2 0.2 0.2'),
    'the78mole:SW_SPST_B3SL-1002P': ('${KICAD6_3DMODEL_DIR}/Button_Switch_SMD.3dshapes/SW_SPST_B3SL-1002P.wrl', 0, 0, 0),
    'Package_SO:SO-8_5.3x6.2mm_P1.27mm': ('${KICAD6_3DMODEL_DIR}/Package_SO.3dshapes/SOIC-8_5.3x6.2mm_P1.27mm.wrl', 0, 0, 0),
}

def exists(path):
    p = re.sub(r'\$\{KICAD\d+_3DMODEL_DIR\}', STOCK, path).replace('${KIPRJMOD}', os.path.dirname(os.path.abspath(f)))
    return any(os.path.exists(re.sub(r'\.(wrl|step|stp)$', e, p)) for e in ('.wrl', '.step', '.stp'))

b = pcbnew.LoadBoard(f)
for fp in b.GetFootprints():
    spec = MODELS.get(fp.GetFPIDAsString())
    if not spec:
        continue
    # rebuild the model list: hide missing files, drop entries this script added before (idempotent)
    ours = {spec[1] if spec[0] == 'box' else spec[0]}
    keep = []
    for old in fp.Models():
        if any(old.m_Filename.endswith(o) for o in ours):
            continue
        m = pcbnew.FP_3DMODEL()
        m.m_Filename, m.m_Offset, m.m_Rotation, m.m_Scale = old.m_Filename, old.m_Offset, old.m_Rotation, old.m_Scale
        m.m_Show = old.m_Show and exists(old.m_Filename)
        keep.append(m)
    fp.Models().clear()
    for m in keep:
        fp.Add3DModel(m)
    m = pcbnew.FP_3DMODEL()
    if spec[0] == 'box':
        _, name, h, rgb = spec
        # courtyard bbox in footprint-local coordinates
        bb = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd).BBox()
        if bb.GetWidth() == 0:  # no courtyard in the footprint: use its pads/graphics bounds
            bb = fp.GetBoundingBox(False)
        a = math.radians(fp.GetOrientationDegrees())
        cx, cy = (bb.Centre().x - fp.GetPosition().x) / 1e6, (bb.Centre().y - fp.GetPosition().y) / 1e6
        lx, ly = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)
        w, d = bb.GetWidth() / 1e6, bb.GetHeight() / 1e6
        if round(fp.GetOrientationDegrees()) % 180:
            w, d = d, w
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'box_wrl.py'),
                        os.path.join(repo, '3dmodels', name), str(w), str(d), str(h)] + rgb.split(), check=True)
        m.m_Filename = base + name
        m.m_Offset = pcbnew.VECTOR3D(lx, -ly, 0)
    else:
        name, rz, ox, oy = spec
        m.m_Filename = name if name.startswith('$') else base + name
        m.m_Rotation = pcbnew.VECTOR3D(0, 0, rz)
        m.m_Offset = pcbnew.VECTOR3D(ox, oy, 0)
    fp.Add3DModel(m)
    print(fp.GetReference(), m.m_Filename)
b.Save(f)
