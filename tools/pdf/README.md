# Markdown to PDF (Nikolytics document theme)

Renders the markdown documents in `docs/` to styled PDFs in `docs/pdf/`,
using the website's design tokens (background `#031A22`, primary gold
`#C4854A`, chart gold light `#E8A54B`, card/border/input surfaces, muted
foreground `#9DAAAA` body text with `#FAFAFA` emphasis; the full token map
sits at the top of `theme.css`) and Nunito / Nunito Sans type.

## Rebuild

```
cd tools/pdf
npm install
npm run build            # all documents
node build.mjs founder-appendix.md   # a subset, by basename
```

Requires a Chromium binary; the build launches the one at
`/opt/pw-browsers/chromium` (adjust `executablePath` in `build.mjs` for other
machines, e.g. point it at a local Chrome).

## Text fidelity

The source text is never altered. The build enforces this with two gates and
fails if either is violated:

1. The rendered HTML's text is compared character by character against the
   markdown's text content (markdown-it runs with typographer/linkify off, so
   no smart quotes or other substitutions exist).
2. Every block of source text (paragraphs, headings, list items, table cells)
   must be found verbatim in the finished PDF's extracted text (`pdftotext`,
   whitespace-insensitive; needs poppler-utils, skip-able only by editing the
   script).

The only text the PDFs add beyond the source is the page footer (document
title + page number). Styling choices (cover layout, the two-tone title,
colors) add no words and reorder nothing.

## Adding a document

Add an entry to `DOCS` in `build.mjs`: pick `cover: 'full'` (standalone cover
page, sections start on fresh pages) or `cover: 'band'` (hero header on page
one, flowing sections), and set `accentPrefix` to the part of the H1 to tint
amber; the remainder renders white italic. The build asserts the split
reassembles to the exact original title.
