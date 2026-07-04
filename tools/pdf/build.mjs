// Renders docs/*.md to styled PDFs (docs/pdf/*.pdf) with the Nikolytics
// dark-teal/amber theme, then verifies the text survived 1:1.
//
// Text-fidelity guarantees baked in:
//   - markdown-it runs with typographer/linkify/smart-anything OFF, so the
//     text content of the source passes through unchanged; only markdown
//     syntax (#, **, |, ---) is consumed as structure.
//   - No CSS text-transform, no auto-hyphenation, ligatures disabled.
//   - After rendering, the full text of the HTML is compared character by
//     character (whitespace-normalized) against the text extracted from the
//     markdown source; the build fails on any difference.
//   - The finished PDF is additionally checked with pdftotext: every block
//     (paragraph, heading, list item, table cell) must appear verbatim.
//
// Usage: node build.mjs

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import MarkdownIt from 'markdown-it';
import { chromium } from 'playwright-core';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '..', '..');
const docsDir = path.join(repo, 'docs');
const outDir = path.join(docsDir, 'pdf');

// accentPrefix: leading part of the H1 shown in amber; the remainder is
// rendered white italic (site-hero style). Concatenation is asserted to
// equal the original title exactly.
const DOCS = [
  {
    file: 'nikolytics-operating-manual.md',
    cover: 'full',
    accentPrefix: 'Nikolytics ',
    sectionPerPage: true,
  },
  {
    file: 'founder-appendix.md',
    cover: 'band',
    accentPrefix: 'Founder Appendix ',
    sectionPerPage: false,
  },
  {
    file: 'decision-log-2026-07-04.md',
    cover: 'band',
    accentPrefix: 'Nikolytics Decision Log, ',
    sectionPerPage: false,
  },
];

/* ---------------- fonts: inline @fontsource woff2 files as data URIs ---------------- */

function inlineFontCss(pkg, cssName) {
  const base = path.join(here, 'node_modules', '@fontsource', pkg);
  const css = fs.readFileSync(path.join(base, cssName), 'utf8');
  const blocks = css.match(/@font-face\s*\{[\s\S]*?\}/g) || [];
  const kept = blocks.filter((b) => /-latin(-ext)?-/.test(b)); // latin + latin-ext subsets
  return kept
    .map((b) => {
      const m = b.match(/url\(\.\/files\/([^)]+\.woff2)\)/);
      if (!m) return '';
      const b64 = fs.readFileSync(path.join(base, 'files', m[1])).toString('base64');
      return b.replace(
        /src:[^;]+;/,
        `src: url(data:font/woff2;base64,${b64}) format('woff2');`
      );
    })
    .join('\n');
}

function buildFontCss() {
  const parts = [];
  for (const css of ['400.css', '400-italic.css', '700.css', '700-italic.css']) {
    parts.push(inlineFontCss('nunito-sans', css));
  }
  for (const css of ['800.css', '800-italic.css', '900.css', '900-italic.css']) {
    parts.push(inlineFontCss('nunito', css));
  }
  parts.push(inlineFontCss('jetbrains-mono', '400.css'));
  return parts.join('\n');
}

/* ---------------- markdown ---------------- */

function makeMd() {
  // 'default' preset = CommonMark + GFM tables/strikethrough; html:false keeps
  // any literal markup visible as typed; typographer stays off (no smart quotes).
  const md = new MarkdownIt({ html: false, linkify: false, typographer: false, breaks: false });
  md.renderer.rules.table_open = () => '<div class="tablewrap"><table>\n';
  md.renderer.rules.table_close = () => '</table></div>\n';
  return md;
}

/* ---------------- text extraction for fidelity checks ---------------- */

const collapse = (s) => s.replace(/\s+/g, ' ').trim();

// Every block-level run of text in the markdown source, in document order.
function mdTextBlocks(tokens) {
  const blocks = [];
  const walkInline = (children) => {
    let s = '';
    for (const c of children) {
      if (c.type === 'text' || c.type === 'code_inline') s += c.content;
      else if (c.type === 'softbreak' || c.type === 'hardbreak') s += ' ';
      else if (c.children) s += walkInline(c.children);
    }
    return s;
  };
  for (const t of tokens) {
    if (t.type === 'inline') blocks.push(walkInline(t.children));
    else if (t.type === 'fence' || t.type === 'code_block') blocks.push(t.content);
  }
  return blocks;
}

function htmlToText(html) {
  return html
    .replace(/^[\s\S]*?<body[^>]*>/, '')
    .replace(/<\/body>[\s\S]*$/, '')
    // inline elements vanish without inserting whitespace...
    .replace(/<\/?(?:strong|em|code|span|a|s|del)(?:\s[^>]*)?>/g, '')
    // ...block elements become separators
    .replace(/<[^>]+>/g, '\n')
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&');
}

/* ---------------- document assembly ---------------- */

const FULL_DECOS = `
  <div class="deco sqo" style="top:1.05in; left:0.55in;"></div>
  <div class="deco sq"  style="top:2.3in; right:0.7in; opacity:.75"></div>
  <div class="deco dm"  style="bottom:2.1in; left:0.85in;"></div>
  <div class="deco dot" style="bottom:1.2in; right:1.1in;"></div>
  <div class="deco dot" style="top:1.6in; right:2.2in; opacity:.6"></div>
  <div class="deco sqo" style="bottom:0.95in; right:0.55in; width:8px; height:8px; opacity:.7"></div>`;

const BAND_DECOS = `
  <div class="deco sqo" style="top:0.32in; right:0.12in;"></div>
  <div class="deco dot" style="top:0.85in; right:0.95in;"></div>
  <div class="deco dm"  style="top:0.5in; right:1.85in; opacity:.8"></div>`;

function buildDoc(cfg, sourceMd, fontCss, themeCss) {
  const md = makeMd();
  const tokens = md.parse(sourceMd, {});
  const bodyHtml = md.renderer.render(tokens, md.options, {});

  // Peel off the leading <h1> (and the meta paragraph right after it, if any)
  // to restyle them as the cover. Nothing is added, removed, or reworded.
  const h1m = bodyHtml.match(/^<h1>([\s\S]*?)<\/h1>\n?/);
  if (!h1m) throw new Error(`${cfg.file}: no leading <h1>`);
  let rest = bodyHtml.slice(h1m[0].length);
  const title = h1m[1];

  let metaHtml = null;
  const pm = rest.match(/^<p>([\s\S]*?)<\/p>\n?/);
  if (pm) {
    metaHtml = pm[1];
    rest = rest.slice(pm[0].length);
  }

  if (!title.startsWith(cfg.accentPrefix)) {
    throw new Error(`${cfg.file}: accentPrefix does not match title "${title}"`);
  }
  const t1 = cfg.accentPrefix;
  const t2 = title.slice(cfg.accentPrefix.length);
  if (t1 + t2 !== title) throw new Error(`${cfg.file}: title split corrupted the text`);

  const coverClass = cfg.cover === 'full' ? 'cover' : 'cover-band';
  const cover =
    `<section class="${coverClass}"><div class="glow"></div>` +
    (cfg.cover === 'full' ? FULL_DECOS : BAND_DECOS) +
    `<div class="cover-rule"></div>` +
    `<h1><span class="t1">${t1}</span><span class="t2">${t2}</span></h1>` +
    (metaHtml ? `<div class="meta-card"><p>${metaHtml}</p></div>` : '') +
    `</section>`;

  const bodyClass = cfg.sectionPerPage ? 'doc-sectioned' : 'doc-flow';
  const html =
    `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title>` +
    `<style>${fontCss}\n${themeCss}</style></head>` +
    `<body class="${bodyClass}">${cover}<main>\n${rest}</main></body></html>`;

  // -------- fidelity gate #1: HTML text === markdown text, in order --------
  const want = collapse(mdTextBlocks(tokens).join(' '));
  const got = collapse(htmlToText(html));
  if (want !== got) {
    let i = 0;
    while (i < Math.min(want.length, got.length) && want[i] === got[i]) i++;
    throw new Error(
      `${cfg.file}: HTML text diverges from source at char ${i}:\n` +
        `  source: ...${want.slice(Math.max(0, i - 60), i + 60)}...\n` +
        `  html:   ...${got.slice(Math.max(0, i - 60), i + 60)}...`
    );
  }

  return { html, title, blocks: mdTextBlocks(tokens) };
}

/* ---------------- PDF-level verification ---------------- */

function verifyPdf(pdfPath, blocks, title) {
  let txt = execFileSync('pdftotext', ['-raw', '-enc', 'UTF-8', pdfPath, '-'], {
    maxBuffer: 64 * 1024 * 1024,
  }).toString('utf8');

  // Whitespace-insensitive: pdftotext reconstructs spaces heuristically at
  // font-run boundaries (e.g. fallback-font glyphs like ≤ → −), so spacing is
  // not comparable here. Character-and-spacing fidelity is already guaranteed
  // by gate #1 on the HTML; this gate proves every character sequence was
  // actually rendered into the PDF.
  const squash = (s) => s.replace(/\s+/g, '');
  // Excise footer furniture so blocks that span page breaks reassemble
  // cleanly: pdftotext separates pages with \f and page N's footer reads
  // "<title>  N / M", so the exact squashed footer string is known per page.
  const pages = txt.split('\f');
  if (pages.length && pages[pages.length - 1].trim() === '') pages.pop();
  const total = pages.length;
  const flat = pages
    .map((p, i) => squash(p).replaceAll(squash(title) + `${i + 1}/${total}`, ''))
    .join('');
  const missing = [];
  for (const b of blocks) {
    if (b.trim() && !flat.includes(squash(b))) missing.push(collapse(b));
  }
  return missing;
}

function glyphReport(source, pdfPath) {
  const txt = execFileSync('pdftotext', ['-enc', 'UTF-8', pdfPath, '-'], {
    maxBuffer: 64 * 1024 * 1024,
  }).toString('utf8');
  const bad = [];
  for (const ch of ['§', '×', 'ć', '→', '−', '≈', '≤', '≥', '"']) {
    const inSrc = source.split(ch).length - 1;
    const inPdf = txt.split(ch).length - 1;
    if (inSrc > 0 && inPdf < inSrc) bad.push(`${ch}: source ${inSrc}, pdf ${inPdf}`);
  }
  return bad;
}

/* ---------------- footer stamping ----------------
   Chromium's displayHeaderFooter paints an opaque white strip over the
   bottom margin, which ruins the full-bleed dark pages; instead the footer
   (doc title left, "N / M" right) is drawn into the finished PDF here. */

async function stampFooters(pdfPath, title, { skipFirstPage }) {
  const doc = await PDFDocument.load(fs.readFileSync(pdfPath));
  const font = await doc.embedFont(StandardFonts.Helvetica);
  const pages = doc.getPages();
  const total = pages.length;
  const size = 7.5;
  const y = 0.34 * 72;
  const inset = 0.85 * 72;
  const mutedTeal = rgb(0x7e / 255, 0x98 / 255, 0x9e / 255);
  const amber = rgb(0xd8 / 255, 0x9b / 255, 0x62 / 255);
  pages.forEach((pg, i) => {
    if (skipFirstPage && i === 0) return; // no footer on a full cover page
    const label = `${i + 1} / ${total}`;
    pg.drawText(title, { x: inset, y, size, font, color: mutedTeal });
    const w = font.widthOfTextAtSize(label, size);
    pg.drawText(label, { x: pg.getSize().width - inset - w, y, size, font, color: amber });
  });
  fs.writeFileSync(pdfPath, await doc.save());
}

/* ---------------- main ---------------- */

const only = process.argv.slice(2); // optionally pass md basenames to build a subset

fs.mkdirSync(outDir, { recursive: true });
const fontCss = buildFontCss();
const themeCss = fs.readFileSync(path.join(here, 'theme.css'), 'utf8');

// The environment pre-installs Chromium at a stable symlink; use it instead of
// downloading a playwright-core-pinned build.
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
try {
  const page = await browser.newPage();
  for (const cfg of DOCS) {
    if (only.length && !only.includes(cfg.file)) continue;
    const srcPath = path.join(docsDir, cfg.file);
    const source = fs.readFileSync(srcPath, 'utf8');
    const { html, title, blocks } = buildDoc(cfg, source, fontCss, themeCss);

    await page.setContent(html, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);

    const outPath = path.join(outDir, cfg.file.replace(/\.md$/, '.pdf'));
    await page.pdf({
      path: outPath,
      format: 'Letter',
      printBackground: true,
      preferCSSPageSize: true, // margins come from @page in theme.css
      displayHeaderFooter: false,
      margin: { top: '0', bottom: '0', left: '0', right: '0' },
    });
    await stampFooters(outPath, title, { skipFirstPage: cfg.cover === 'full' });

    // -------- fidelity gate #2: every source block appears in the PDF --------
    const missing = verifyPdf(outPath, blocks, title);
    const glyphs = glyphReport(source, outPath);
    const size = (fs.statSync(outPath).size / 1024).toFixed(0);
    if (missing.length || glyphs.length) {
      console.error(`FAIL ${cfg.file}`);
      for (const m of missing.slice(0, 8)) console.error(`  missing block: ${m.slice(0, 120)}`);
      for (const g of glyphs) console.error(`  glyph: ${g}`);
      process.exitCode = 1;
    } else {
      console.log(`OK   ${path.relative(repo, outPath)}  (${size} KB, ${blocks.length} text blocks verified in PDF, HTML char-identical to source)`);
    }
  }
} finally {
  await browser.close();
}
