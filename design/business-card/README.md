# Metal business card — back side

Vectorized from the original hand sketch: the email address doubles as an
annotated diagram — `nikola` is labeled **me**, `nikolytics.com` is labeled
**website**, and the `@` sits between them, deliberately unclaimed.

## Current design — Rev B (`card-back-sketch.svg`)

Faithful to the original sketch's composition: `e-mail` label above a closed
hand-drawn box, natural under-brackets, labels directly beneath.

- **Email:** Playpen Sans Light 300
- **Labels (`e-mail`, `me`, `website`):** Caveat SemiBold
- **Box and brackets** are generated hand-drawn strokes — polylines perturbed
  with smooth seeded noise and rounded with Catmull-Rom smoothing, so they
  read as confident marker lines and rebuild identically every run.

## Earlier revision (Rev A, kept for reference)

| File | Labels | Feel |
|------|--------|------|
| `card-back-schematic.svg` | Inter, uppercase, letterspaced | Clean, technical, "engineered" |
| `card-back-handwritten.svg` | Caveat (handwriting) | JetBrains Mono email, crisp geometry |

## Production specs

- **Physical size:** 88.9 × 50.8 mm (standard 3.5″ × 2″ card), 1 SVG unit = 0.1 mm
- **Single-colour artwork:** everything black = engraved/etched
- **All text converted to outlines** — no fonts needed by the engraver
- **Line weight:** 0.36 mm (Rev B) / 0.34 mm (Rev A); smallest text ≈ 2 mm cap
  height (well above the ~0.15 mm / 1 mm minimums typical for fiber-laser engraving)
- **Clear margin:** ≥ 12 mm to card edges on all sides
- No bleed needed (artwork nowhere near edges); corner radius of the card
  itself is up to the manufacturer (mockups assume ~2.8 mm)

## Regenerating

`generate_sketch.py` rebuilds Rev B; `generate.py` rebuilds the Rev A pair.
Both shape text with HarfBuzz and outline glyphs with fontTools. Fonts are
not committed; the scripts expect Playpen Sans, Caveat, JetBrains Mono and
Inter TTFs in `./fonts/` (all OFL-licensed, available via `@fontsource/*`
npm packages or Google Fonts).

```
pip install fonttools uharfbuzz brotli cairosvg
python3 generate.py
```

`previews/` contains white-background renders plus mockups on black-anodized
and stainless finishes.
