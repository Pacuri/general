# Metal business card — back side

Vectorized from the original hand sketch: the email address doubles as an
annotated diagram — `nikola` is labeled **me**, `nikolytics.com` is labeled
**website**, and the `@` sits between them, deliberately unclaimed.

## Variants

| File | Labels | Feel |
|------|--------|------|
| `card-back-schematic.svg` | Inter, uppercase, letterspaced | Clean, technical, "engineered" |
| `card-back-handwritten.svg` | Caveat (handwriting) | Keeps the sketch's human touch |

The email itself is set in **JetBrains Mono Medium** in both variants — a
monospace face fits the analytics/engineering brand and gives the callout
brackets exact character boundaries to align to.

Design details:
- The `e-mail` label breaks the top border of the rounded box, schematic-legend
  style (a cleaned-up version of the label floating above the box in the sketch).
- Square under-brackets replace the sketch's wobbly braces; each has a short
  center leader pointing to its label.

## Production specs

- **Physical size:** 88.9 × 50.8 mm (standard 3.5″ × 2″ card), 1 SVG unit = 0.1 mm
- **Single-colour artwork:** everything black = engraved/etched
- **All text converted to outlines** — no fonts needed by the engraver
- **Line weight:** 0.34 mm; smallest text ≈ 2 mm cap height (well above the
  ~0.15 mm / 1 mm minimums typical for fiber-laser engraving)
- **Clear margin:** ≥ 12 mm to card edges on all sides
- No bleed needed (artwork nowhere near edges); corner radius of the card
  itself is up to the manufacturer (mockups assume ~2.8 mm)

## Regenerating

`generate.py` rebuilds both SVGs from scratch (shapes text with HarfBuzz,
outlines glyphs with fontTools). Fonts are not committed; it expects
JetBrains Mono, Inter and Caveat TTFs (all OFL-licensed, available via
`@fontsource/*` npm packages or Google Fonts).

```
pip install fonttools uharfbuzz brotli cairosvg
python3 generate.py
```

`previews/` contains white-background renders plus mockups on black-anodized
and stainless finishes.
