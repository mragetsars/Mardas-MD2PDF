# Mardas MD2PDF

> Professional Markdown to PDF converter for Persian, English, and mixed RTL/LTR technical documents.

![Language](https://img.shields.io/badge/Language-Python-blue.svg) ![Renderer](https://img.shields.io/badge/Renderer-Playwright%20%2B%20Chromium-green.svg) ![Math](https://img.shields.io/badge/Math-MathJax-purple.svg) ![Version](https://img.shields.io/badge/Version-v1.3.1-success.svg) ![Status](https://img.shields.io/badge/Status-Stable-success.svg)

**Mardas MD2PDF** turns Markdown into polished PDFs with Persian/English typography, MathJax formulas, syntax-highlighted code, local images, front-matter driven covers, hierarchical tables of contents, watermarks, and multiple print themes.

```text
Markdown -> typographic HTML -> Chromium PDF
```

![Mardas MD2PDF](./README.png)

## Quick links

- [English Guide](./GUIDE.en.md) - complete feature tour and usage manual.
- [راهنمای فارسی](./GUIDE.fa.md) - راهنمای کامل امکانات و شیوه استفاده.
- [Examples](./examples/) - Markdown inputs and generated PDF samples.

## Highlights

- Persian, English, and mixed RTL/LTR documents.
- `lang: fa` and `lang: en` aware cover, TOC, callout, and document direction behavior.
- Designed cover page with YAML metadata, custom `cover_label`, logo, authors, summary, date, version, keywords, and more.
- Hierarchical Table of Contents with configurable depth.
- Inline and display math with vendored MathJax and separate sizing.
- Fenced and indented code blocks with Pygments highlighting.
- Tables, task lists, blockquotes, callouts, links, footnotes, and manual page breaks.
- Local Markdown/HTML images embedded as data URIs for stable PDF output.
- Safe raw HTML sanitization by default, with `--unsafe-html` for trusted local files.
- Text or image watermarks on content pages only.
- Four bundled themes: `modern`, `textbook-light`, `textbook-dark`, and `academic`.
- CLI and local browser-based GUI.

## Installation

```bash
git clone https://github.com/mragetsars/Mardas-MD2PDF.git
cd Mardas-MD2PDF
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m playwright install chromium
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m playwright install chromium
```

For development:

```bash
pip install -e .[dev]
pytest
```

## Basic usage

```bash
mrs-md2pdf input.md -o output.pdf
```

With a table of contents and the modern theme:

```bash
mrs-md2pdf input.md -o output.pdf --toc --theme modern
```

With book-like page flow:

```bash
mrs-md2pdf input.md -o output.pdf \
  --toc \
  --toc-depth 4 \
  --toc-page-break \
  --h1-page-break \
  --theme textbook-light
```

Generate debug HTML:

```bash
mrs-md2pdf input.md -o output.pdf --debug-html output.html
```

Launch the GUI:

```bash
mrs-md2pdf-gui
```

## Minimal front matter

```yaml
---
title: "My PDF Report"
subtitle: "A Markdown-powered document"
authors:
  - name: "Mardas"
    email: "mragetsars@yahoo.com"
summary: |
  This text appears on the cover.
  Multiline summaries are supported.
lang: en
dir: ltr
cover_label: "Technical Report"
keywords: [Markdown, PDF, MathJax, RTL]
---
```

Use `lang: fa` for Persian UI labels and RTL defaults, or `lang: en` for English UI labels and LTR defaults. Explicit `dir: rtl` / `dir: ltr` or CLI `--dir` still has priority when you need to force the document shell direction.

## CLI overview

| Option | Purpose |
| :--- | :--- |
| `-o, --output` | Output PDF path. |
| `--toc`, `--toc-depth` | Generate and configure the Table of Contents. |
| `--toc-page-break`, `--h1-page-break` | Control printed page flow. |
| `--theme` | Choose `modern`, `textbook-light`, `textbook-dark`, or `academic`. |
| `--page-size` | Use `A4`, `Letter`, `Legal`, `A4 landscape`, or dimensions like `210mm 297mm`. |
| `--dir` | Force `auto`, `rtl`, or `ltr`. |
| `--no-cover`, `--cover-logo`, `--no-cover-logo` | Control the cover page. |
| `--watermark`, `--watermark-image` | Add content-page watermarks. |
| `--debug-html` | Save intermediate HTML for inspection. |
| `--unsafe-html` | Disable built-in raw HTML sanitization for trusted files. |
| `--no-mathjax` | Disable MathJax loading. |

Run `mrs-md2pdf --help` for the full option list.

## Example outputs

The `examples/` directory includes compact demos and generated PDFs:

- `fa-en-math-code.md` - Persian/English mixed document with math, code, images, cover metadata, and footnotes.
- `en-lang-math-demo.md` - English language/direction demo.
- `guide-en-modern.pdf` - complete English guide rendered as a feature-rich sample PDF.
- `guide-fa-modern.pdf` - complete Persian guide rendered as a feature-rich sample PDF.

## Project structure

```text
Mardas-MD2PDF/
├── src/                 # Python package source
├── src/assets/          # themes, GUI shell, logo, vendored MathJax
├── examples/            # sample Markdown files, images, and PDF outputs
├── tests/               # pytest suite
├── GUIDE.en.md          # complete English guide
├── GUIDE.fa.md          # complete Persian guide
├── README.md            # short project overview
└── pyproject.toml
```

## Testing

```bash
pip install -e .[dev]
pytest
```

The test suite covers direction handling, TOC generation, code highlighting, MathJax preservation, cover metadata, local images, sanitization, multiline footnotes, page-size overrides, language-aware labels, GUI entrypoint availability, and inline/display math sizing, code-span protection, renderer fallback warnings, and custom CSS page sizes.

## Author

Designed for professional Persian/English Markdown publishing by [Meraj Rastegar](https://github.com/mragetsars).

## License

MIT License. See [LICENSE](./LICENSE).
