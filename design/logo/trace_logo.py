import numpy as np
from PIL import Image
import potrace

im = Image.open("logo-original.png").convert("RGBA")
W, H = im.size
a = np.array(im)
mask = ~(a[:, :, 3] >= 128)  # potracer: False = ink          # solid artwork only (kills stray alpha=1 pixels)
print("ink pixels:", mask.sum())

bmp = potrace.Bitmap(mask)
path = bmp.trace(turdsize=4, alphamax=1.0, opttolerance=0.2)

XS = 1.15  # widen 15%
def fmt(p):
    return f"{p.x * XS:.2f} {p.y:.2f}"

parts = []
for curve in path.curves:
    parts.append(f"M {fmt(curve.start_point)}")
    for seg in curve.segments:
        if seg.is_corner:
            parts.append(f"L {fmt(seg.c)} L {fmt(seg.end_point)}")
        else:
            parts.append(f"C {fmt(seg.c1)} {fmt(seg.c2)} {fmt(seg.end_point)}")
    parts.append("Z")
d = " ".join(parts)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W * XS:.0f} {H}">\n'
       f'<!-- nikolytics logo, vectorized from 1920x540 master PNG, widened 15% horizontally -->\n'
       f'<path fill="#C07F4B" fill-rule="nonzero" d="{d}"/>\n</svg>\n')
open("out/nikolytics-logo.svg", "w").write(svg)
open("out/nikolytics-logo-black.svg", "w").write(svg.replace("#C07F4B", "#000000"))
print("curves:", len(path.curves), "| svg bytes:", len(svg))
