#!/usr/bin/env python3
"""Generate vectorized metal-card back designs from the sketch concept.

Card: 88.9 x 50.8 mm. Working units: 1 unit = 0.1 mm (viewBox 889 x 508).
All text converted to outlines via HarfBuzz shaping + fontTools pens.
"""
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

FONTS = "/tmp/claude-0/-home-user-general/22a05b3e-be8d-5d6b-a744-eb534393085f/scratchpad/fonts"
OUT = "/tmp/claude-0/-home-user-general/22a05b3e-be8d-5d6b-a744-eb534393085f/scratchpad/out"

W, H = 889.0, 508.0  # 0.1mm units
CX = W / 2

class Face:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
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
        """Return (path_d, width) with baseline at y=0, x starting at 0."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf)
        scale = size / self.upem
        x = 0.0
        parts = []
        n = len(buf.glyph_infos)
        for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
            gname = self.order[info.codepoint]
            glyph = self.glyphSet[gname]
            spen = SVGPathPen(self.glyphSet)
            tpen = TransformPen(spen, Transform(
                scale, 0, 0, -scale,
                x + pos.x_offset * scale, -pos.y_offset * scale))
            glyph.draw(tpen)
            d = spen.getCommands()
            if d:
                parts.append(d)
            x += pos.x_advance * scale
            if i < n - 1:
                x += tracking
        return " ".join(parts), x


mono = Face(f"{FONTS}/JetBrainsMono-Medium.ttf")
inter = Face(f"{FONTS}/Inter-Medium.ttf")
caveat = Face(f"{FONTS}/Caveat-SemiBold.ttf")

EMAIL = "nikola@nikolytics.com"
EMAIL_SIZE = 46.0

email_d, email_w = mono.shape(EMAIL, EMAIL_SIZE)
adv = email_w / len(EMAIL)  # monospace advance per char
x0 = CX - email_w / 2       # left edge of email text

# ---- vertical layout -------------------------------------------------------
box_y, box_h, box_r = 152.0, 126.0, 14.0
box_pad = 44.0
box_x = x0 - box_pad
box_w = email_w + 2 * box_pad
box_cy = box_y + box_h / 2
email_base = box_cy + (mono.cap * EMAIL_SIZE) / 2  # optically center caps/x band

brk_y = box_y + box_h + 40.0     # bracket horizontal line
brk_tick = 16.0                  # upward end ticks
brk_leader = 20.0                # downward center leader

# char ranges (inset slightly so neighboring brackets don't touch)
me_x1, me_x2 = x0 + 3.0, x0 + 6 * adv - 3.0                 # "nikola"
web_x1, web_x2 = x0 + 7 * adv + 3.0, x0 + 21 * adv - 3.0    # "nikolytics.com"

STROKE = 3.4  # 0.34 mm


def rounded_box_with_gap(x, y, w, h, r, gx1, gx2):
    """Rounded rect whose top edge has a gap [gx1, gx2] for the legend label."""
    return (
        f"M {gx2:.2f} {y:.2f} "
        f"L {x + w - r:.2f} {y:.2f} "
        f"A {r} {r} 0 0 1 {x + w:.2f} {y + r:.2f} "
        f"L {x + w:.2f} {y + h - r:.2f} "
        f"A {r} {r} 0 0 1 {x + w - r:.2f} {y + h:.2f} "
        f"L {x + r:.2f} {y + h:.2f} "
        f"A {r} {r} 0 0 1 {x:.2f} {y + h - r:.2f} "
        f"L {x:.2f} {y + r:.2f} "
        f"A {r} {r} 0 0 1 {x + r:.2f} {y:.2f} "
        f"L {gx1:.2f} {y:.2f}"
    )


def bracket(x1, x2, y, tick, leader):
    cx = (x1 + x2) / 2
    return (
        f"M {x1:.2f} {y - tick:.2f} L {x1:.2f} {y:.2f} L {x2:.2f} {y:.2f} "
        f"L {x2:.2f} {y - tick:.2f} M {cx:.2f} {y:.2f} L {cx:.2f} {y + leader:.2f}"
    )


def place(d, tx, ty):
    return f'<path transform="translate({tx:.2f} {ty:.2f})" d="{d}"/>'


def build(variant):
    """variant: 'schematic' (Inter labels) or 'handwritten' (Caveat labels)."""
    if variant == "schematic":
        lbl = lambda t: inter.shape(t.upper(), 20.0, tracking=4.2)
        top_txt, me_txt, web_txt = "E-MAIL", "ME", "WEBSITE"
        top_size_base = lambda w: (CX - w / 2, box_y + inter.cap * 20.0 / 2)
        lbl_base_y = brk_y + brk_leader + 16.0 + inter.cap * 20.0
    else:
        lbl = lambda t: caveat.shape(t, 44.0, tracking=0.6)
        top_txt, me_txt, web_txt = "e-mail", "me", "website"
        # Caveat is lowercase-ish; center on x-height band
        top_size_base = lambda w: (CX - w / 2, box_y + 0.42 * 44.0 / 2 + 4.0)
        lbl_base_y = brk_y + brk_leader + 16.0 + 0.42 * 44.0 + 6.0

    top_d, top_w = lbl(top_txt)
    me_d, me_w = lbl(me_txt)
    web_d, web_w = lbl(web_txt)

    gap_pad = 20.0
    gx1, gx2 = CX - top_w / 2 - gap_pad, CX + top_w / 2 + gap_pad
    top_x, top_base = top_size_base(top_w)

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="88.9mm" height="50.8mm" '
        f'viewBox="0 0 {W:.0f} {H:.0f}">'
    )
    svg.append(f"""<!--
  Metal business card - BACK - {variant} variant
  Physical size: 88.9 x 50.8 mm (standard). 1 SVG unit = 0.1 mm.
  Single-colour artwork: everything black is engraved / etched.
  All text converted to outlines (no fonts required).
  Line weight: {STROKE / 10:.2f} mm. Keep >= 3 mm from edges (respected).
  Fonts used for outlines: JetBrains Mono Medium (email),
  {"Inter Medium (labels)" if variant == "schematic" else "Caveat SemiBold (labels)"}.
-->""")
    svg.append('<g fill="#000">')
    # email text
    svg.append(place(email_d, x0, email_base))
    # labels
    svg.append(place(top_d, top_x, top_base))
    svg.append(place(me_d, (me_x1 + me_x2) / 2 - me_w / 2, lbl_base_y))
    svg.append(place(web_d, (web_x1 + web_x2) / 2 - web_w / 2, lbl_base_y))
    svg.append("</g>")
    # line work
    svg.append(
        f'<g fill="none" stroke="#000" stroke-width="{STROKE}" '
        f'stroke-linecap="round" stroke-linejoin="round">'
    )
    svg.append(f'<path d="{rounded_box_with_gap(box_x, box_y, box_w, box_h, box_r, gx1, gx2)}"/>')
    svg.append(f'<path d="{bracket(me_x1, me_x2, brk_y, brk_tick, brk_leader)}"/>')
    svg.append(f'<path d="{bracket(web_x1, web_x2, brk_y, brk_tick, brk_leader)}"/>')
    svg.append("</g>")
    svg.append("</svg>")
    return "\n".join(svg)


import os
os.makedirs(OUT, exist_ok=True)
for v in ("schematic", "handwritten"):
    path = f"{OUT}/card-back-{v}.svg"
    with open(path, "w") as f:
        f.write(build(v))
    print("wrote", path)

# quick raster previews on white for inspection
import cairosvg
for v in ("schematic", "handwritten"):
    cairosvg.svg2png(url=f"{OUT}/card-back-{v}.svg",
                     write_to=f"{OUT}/preview-{v}-white.png",
                     output_width=1050, background_color="white")
    print("rendered preview", v)
