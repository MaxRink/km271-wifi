#!/usr/bin/env python3
"""Write an approximate VRML box model (KiCad units: 1 = 2.54 mm), base on the board.
usage: box_wrl.py out.wrl size_x size_y height [r g b]"""
import sys
sx, sy, h = (float(v) / 2.54 for v in sys.argv[2:5])
r, g, b = (sys.argv[5:8] or ['0.2', '0.2', '0.2'])
open(sys.argv[1], 'w').write(f"""#VRML V2.0 utf8
# approximate outline model (datasheet bounding box), not the vendor model
Transform {{ translation 0 0 {h / 2:.4f} children [ Shape {{
  appearance Appearance {{ material Material {{ diffuseColor {r} {g} {b} }} }}
  geometry Box {{ size {sx:.4f} {sy:.4f} {h:.4f} }} }} ] }}
""")
