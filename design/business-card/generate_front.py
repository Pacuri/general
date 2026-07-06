#!/usr/bin/env python3
"""Card FRONT: the Nikolytics logo alone, centred. 88.9 x 50.8 mm."""
import re

SP = "."
OUT = "."
W, H = 889.0, 508.0

src = open(f"{OUT}/nikolytics-logo-black.svg").read()
d = re.search(r'd="([^"]+)"', src).group(1)
VBW, VBH = 2134.0, 540.0

LW = 520.0                 # 52 mm wide on the card
LH = LW * VBH / VBW
s = LW / VBW
tx, ty = (W - LW) / 2, (H - LH) / 2

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="88.9mm" height="50.8mm" viewBox="0 0 {W:.0f} {H:.0f}">
<!--
  Metal business card - FRONT
  Physical size: 88.9 x 50.8 mm. 1 SVG unit = 0.1 mm.
  Single-colour artwork: everything black is engraved / etched.
  Logo at 52 mm wide, centred; letterforms widened 15%, icon original.
-->
<path fill="#000" transform="translate({tx:.2f} {ty:.2f}) scale({s:.5f})" d="{d}"/>
</svg>
'''
open(f"{OUT}/card-front.svg", "w").write(svg)
print("wrote card-front.svg | logo", LW / 10, "x", round(LH / 10, 1), "mm")

import cairosvg
cairosvg.svg2png(url=f"{OUT}/card-front.svg", write_to=f"{OUT}/preview-front-white.png",
                 output_width=1050, background_color="white")
print("rendered preview")
