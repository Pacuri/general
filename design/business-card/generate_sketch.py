#!/usr/bin/env python3
"""Sketch-faithful card back: Playpen Sans email, Caveat labels,
hand-drawn box + natural brackets. 1 unit = 0.1 mm, 889 x 508."""
import math, random
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

SP = "."
FONTS, OUT = "./fonts", "."
W, H = 889.0, 508.0
CX = W / 2

class Face:
    def __init__(self, path):
        data = open(path, "rb").read()
        face = hb.Face(data)
        self.hbfont = hb.Font(face)
        self.upem = face.upem
        self.tt = TTFont(path)
        self.glyphSet = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        try:
            self.cap = self.tt["OS/2"].sCapHeight / self.upem
        except Exception:
            self.cap = 0.7

    def shape(self, text, size, tracking=0.0):
        """-> (path_d, width, cluster_x, (ink_ymin, ink_ymax))
        cluster_x[i] = x where char i starts, plus one final entry = width.
        ink extents are relative to the baseline, y-down (negative = above)."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf)
        scale = size / self.upem
        x = 0.0
        parts = []
        cluster_x = {}
        ymin, ymax = 0.0, 0.0
        n = len(buf.glyph_infos)
        for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
            cluster_x.setdefault(info.cluster, x)
            glyph = self.glyphSet[self.order[info.codepoint]]
            tf = Transform(scale, 0, 0, -scale,
                           x + pos.x_offset * scale, -pos.y_offset * scale)
            spen = SVGPathPen(self.glyphSet)
            glyph.draw(TransformPen(spen, tf))
            d = spen.getCommands()
            if d:
                parts.append(d)
            bpen = BoundsPen(self.glyphSet)
            glyph.draw(TransformPen(bpen, tf))
            if bpen.bounds:
                ymin = min(ymin, bpen.bounds[1])
                ymax = max(ymax, bpen.bounds[3])
            x += pos.x_advance * scale
            if i < n - 1:
                x += tracking
        xs = [cluster_x.get(i, x) for i in range(len(text))] + [x]
        return " ".join(parts), x, xs, (ymin, ymax)


# ---------- hand-drawn stroke helpers ----------------------------------------
rng = random.Random(20260706)

def _noise_fn(amp):
    """Smooth 1-D noise over t in [0,1]: two seeded sine components."""
    f1, f2 = rng.uniform(1.5, 2.6), rng.uniform(3.2, 5.2)
    p1, p2 = rng.uniform(0, math.tau), rng.uniform(0, math.tau)
    a2 = amp * 0.5
    return lambda t: (amp * math.sin(f1 * math.tau * t + p1)
                      + a2 * math.sin(f2 * math.tau * t + p2))

def hand_points(pts, wobble=1.8, step=26.0, closed=False):
    """Subdivide polyline pts and offset perpendicular with smooth noise.
    Corner points stay near their anchors (tiny jitter only)."""
    out = []
    segs = list(zip(pts, pts[1:] + ([pts[0]] if closed else [])))
    for (x1, y1), (x2, y2) in segs:
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        n = max(2, int(L / step))
        amp_scale = min(1.0, L / 220.0)  # short edges wobble much less
        nf = _noise_fn(wobble * amp_scale)
        for k in range(n):
            t = k / n
            off = nf(t) * math.sin(math.pi * t)  # pinned flat at both ends
            out.append((x1 + dx * t + nx * off, y1 + dy * t + ny * off))
    if not closed:
        out.append(pts[-1])
    return out

def catmull_path(pts, closed=False):
    """Catmull-Rom through pts -> cubic Bezier path string."""
    if closed:
        ext = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        ext = [pts[0]] + pts + [pts[-1]]
    d = [f"M {ext[1][0]:.2f} {ext[1][1]:.2f}"]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C {c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} {p2[0]:.2f} {p2[1]:.2f}")
    if closed:
        d.append("Z")
    return " ".join(d)

def hand_box(x, y, w, h, wobble=2.2, corner_jitter=2.5):
    """Closed hand-drawn rectangle with slightly imperfect corners."""
    j = lambda: rng.uniform(-corner_jitter, corner_jitter)
    corners = [(x + j(), y + j()), (x + w + j(), y + j()),
               (x + w + j(), y + h + j()), (x + j(), y + h + j())]
    return catmull_path(hand_points(corners, wobble=wobble, closed=True), closed=True)

def hand_bracket(x1, x2, y, t1, t2, wobble=1.6):
    """Bracket: tick, across, tick — one natural stroke.
    Positive ticks point up (under-bracket); negative point down (over-bracket)."""
    pts = [(x1 + rng.uniform(-2, 2), y - t1), (x1, y), (x2, y),
           (x2 + rng.uniform(-2, 2), y - t2)]
    return catmull_path(hand_points(pts, wobble=wobble))


# ---------- layout ------------------------------------------------------------
playpen = Face(f"{FONTS}/PlaypenSans-Bold.ttf")
caveat = Face(f"{FONTS}/Caveat-SemiBold.ttf")

EMAIL = "nikola@nikolytics.com"

# size email to ~640 units wide
_, w100, _, _ = playpen.shape(EMAIL, 100.0)
EMAIL_SIZE = 100.0 * 640.0 / w100
email_d, email_w, cx_list, (e_ymin, e_ymax) = playpen.shape(EMAIL, EMAIL_SIZE)
x0 = CX - email_w / 2

def span(i, j, inset=4.0):
    return x0 + cx_list[i] + inset, x0 + cx_list[j] - inset

me_x1, me_x2 = span(0, 6)      # "nikola"
web_x1, web_x2 = span(7, 21)   # "nikolytics.com"
all_x1, all_x2 = span(0, 21)   # whole address, for the e-mail over-bracket

LBL_SIZE = 47.0
top_d, top_w, _, (t_ymin, t_ymax) = caveat.shape("e-mail", LBL_SIZE, tracking=0.6)
me_d, me_w, _, _ = caveat.shape("me", LBL_SIZE, tracking=0.6)
web_d, web_w, _, (w_ymin, w_ymax) = caveat.shape("website", LBL_SIZE, tracking=0.6)

# vertical composition, mirrored around the address so top and bottom
# groups sit at identical ink-to-bracket and bracket-to-label distances
email_base = 288.0                       # provisional; block is re-centred below
brk_y = email_base + e_ymax + 24.0       # under-brackets: 2.4 mm below lowest ink
lbl_base = brk_y - w_ymin + 26.0         # bottom labels: ink top 2.6 mm below line
top_brk_y = email_base + e_ymin - 24.0   # over-bracket: 2.4 mm above highest ink
top_base = top_brk_y - t_ymax - 26.0     # e-mail label: ink bottom 2.6 mm above line

# centre the whole block on the card
block_top = top_base + t_ymin
block_bottom = lbl_base + w_ymax
shift = H / 2 - (block_top + block_bottom) / 2
email_base += shift; brk_y += shift; lbl_base += shift
top_brk_y += shift; top_base += shift

STROKE = 3.6
SCALE = 0.576  # shrink the whole composition, centred on the card

def place(d, tx, ty, rot=0.0):
    r = f" rotate({rot:.2f})" if rot else ""
    return f'<path transform="translate({tx:.2f} {ty:.2f}){r}" d="{d}"/>'

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="88.9mm" height="50.8mm" viewBox="0 0 {W:.0f} {H:.0f}">')
svg.append(f"""<!--
  Metal business card - BACK - sketch variant (Rev C)
  Physical size: 88.9 x 50.8 mm. 1 SVG unit = 0.1 mm.
  Single-colour artwork: everything black is engraved / etched.
  All text converted to outlines (no fonts required).
  Line weight: {STROKE * SCALE / 10:.2f} mm (composition scaled to {SCALE:.0%}).
  Faces: Playpen Sans Bold 700 (email), Caveat SemiBold (labels).
  Brackets are hand-drawn strokes (seeded, reproducible).
-->""")
svg.append(f'<g transform="translate({CX:.1f} {H / 2:.1f}) scale({SCALE}) translate({-CX:.1f} {-H / 2:.1f})">')
svg.append('<g fill="#000">')
svg.append(place(email_d, x0, email_base))
svg.append(place(top_d, CX - top_w / 2, top_base, rot=-1.6))
svg.append(place(me_d, (me_x1 + me_x2) / 2 - me_w / 2, lbl_base, rot=-2.0))
svg.append(place(web_d, (web_x1 + web_x2) / 2 - web_w / 2, lbl_base, rot=-1.2))
svg.append("</g>")
svg.append(f'<g fill="none" stroke="#000" stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round">')
svg.append(f'<path d="{hand_bracket(all_x1, all_x2, top_brk_y, -19.0, -21.0)}"/>')
svg.append(f'<path d="{hand_bracket(me_x1, me_x2, brk_y, 20.0, 17.0)}"/>')
svg.append(f'<path d="{hand_bracket(web_x1, web_x2, brk_y, 18.0, 21.0)}"/>')
svg.append("</g>")
svg.append("</g>")
svg.append("</svg>")

import os
os.makedirs(OUT, exist_ok=True)
path = f"{OUT}/card-back-sketch.svg"
open(path, "w").write("\n".join(svg))
print("wrote", path)

import cairosvg
cairosvg.svg2png(url=path, write_to=f"{OUT}/preview-sketch-white.png",
                 output_width=1050, background_color="white")
print("rendered preview")
