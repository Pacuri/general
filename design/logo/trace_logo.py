#!/usr/bin/env python3
"""Vectorize the Nikolytics logo from the 1920x540 master PNG.

Letters and letter-spacing widen by 15%; the brain-gear icon keeps its
original proportions (rigid translate into its new slot).
"""
import numpy as np
from PIL import Image
import potrace

S = 1.15  # horizontal widening for the letterforms

im = Image.open("logo-original.png").convert("RGBA")
W, H = im.size
a = np.array(im)
mask = ~(a[:, :, 3] >= 128)  # potracer: False = ink
print("ink pixels:", (~mask).sum())

bmp = potrace.Bitmap(mask)
path = bmp.trace(turdsize=4, alphamax=1.0, opttolerance=0.2)

def curve_points(curve):
    pts = [curve.start_point]
    for seg in curve.segments:
        pts += [seg.c, seg.end_point] if seg.is_corner else [seg.c1, seg.c2, seg.end_point]
    return pts

# classify curves: icon = bbox centre in the middle band between the wordmarks
curves = list(path.curves)
centers = [sum(p.x for p in curve_points(c)) / len(curve_points(c)) for c in curves]
ICON_LO, ICON_HI = 560.0, 1025.0
groups = ["icon" if ICON_LO < cx < ICON_HI else ("left" if cx <= ICON_LO else "right")
          for cx in centers]

icon_pts = [p.x for c, g in zip(curves, groups) if g == "icon" for p in curve_points(c)]
ia, ib = min(icon_pts), max(icon_pts)  # icon x-extent in the original
print(f"groups: {groups.count('left')} left, {groups.count('icon')} icon, "
      f"{groups.count('right')} right | icon x {ia:.1f}-{ib:.1f}")

def tx(x, group):
    if group == "left":
        return x * S
    if group == "icon":
        return x + (S - 1) * ia            # rigid shift, no stretch
    return x * S - (S - 1) * (ib - ia)     # right: scaled, pulled back by icon's non-growth

parts = []
for curve, g in zip(curves, groups):
    f = lambda p: f"{tx(p.x, g):.2f} {p.y:.2f}"
    parts.append(f"M {f(curve.start_point)}")
    for seg in curve.segments:
        if seg.is_corner:
            parts.append(f"L {f(seg.c)} L {f(seg.end_point)}")
        else:
            parts.append(f"C {f(seg.c1)} {f(seg.c2)} {f(seg.end_point)}")
    parts.append("Z")
d = " ".join(parts)

W_new = int(round(W * S - (S - 1) * (ib - ia)))
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_new} {H}">\n'
       f'<!-- nikolytics logo: traced from 1920x540 master PNG; letterforms '
       f'widened 15%, icon kept at original proportions -->\n'
       f'<path fill="#C07F4B" fill-rule="nonzero" d="{d}"/>\n</svg>\n')
open("out/nikolytics-logo.svg", "w").write(svg)
open("out/nikolytics-logo-black.svg", "w").write(svg.replace("#C07F4B", "#000000"))
print("curves:", len(curves), "| new width:", W_new, "| svg bytes:", len(svg))
