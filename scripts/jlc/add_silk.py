#!/usr/bin/env python3
"""Add silkscreen labels from a JSON list (KiCad python).
usage: add_silk.py board.kicad_pcb labels.json
labels: [{"text","x","y","layer":"F.SilkS","rot":0,"just":"left|center|right","h":1.0}]
Existing texts with the same content and layer are replaced (idempotent)."""
import json, sys, pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
items = json.load(open(sys.argv[2]))
want = {(i['text'], i.get('layer', 'F.SilkS')) for i in items}
for d in list(b.GetDrawings()):
    if isinstance(d, pcbnew.PCB_TEXT) and (d.GetText(), b.GetStandardLayerName(d.GetLayer())) in want:
        b.Remove(d)
J = {'left': pcbnew.GR_TEXT_H_ALIGN_LEFT, 'center': pcbnew.GR_TEXT_H_ALIGN_CENTER, 'right': pcbnew.GR_TEXT_H_ALIGN_RIGHT}
for i in items:
    t = pcbnew.PCB_TEXT(b)
    t.SetText(i['text'])
    layer = i.get('layer', 'F.SilkS')
    t.SetLayer(b.GetLayerID(layer))
    h = pcbnew.FromMM(i.get('h', 1.0))
    t.SetTextSize(pcbnew.VECTOR2I(int(h * 0.8), h))
    t.SetTextThickness(pcbnew.FromMM(0.15))
    t.SetHorizJustify(J[i.get('just', 'center')])
    t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(i['x']), pcbnew.FromMM(i['y'])))
    t.SetTextAngleDegrees(i.get('rot', 0))
    if layer.startswith('B.'):
        t.SetMirrored(True)
    b.Add(t)
b.Save(sys.argv[1])
