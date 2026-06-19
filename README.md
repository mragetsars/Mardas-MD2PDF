# Mardas MD2PDF

> **Professional Markdown to PDF converter for Persian, English, and mixed RTL/LTR technical documents**

![Language](https://img.shields.io/badge/Language-Python-blue) ![Renderer](https://img.shields.io/badge/Renderer-Playwright%20%2B%20Chromium-green) ![Math](https://img.shields.io/badge/Math-MathJax-purple) ![Version](https://img.shields.io/badge/Version-v1.12.0-success) ![Status](https://img.shields.io/badge/Status-Stable-success) ![CI](https://github.com/mragetsars/Mardas-MD2PDF/actions/workflows/ci.yml/badge.svg)

## Overview

This repository contains **Mardas MD2PDF**, a Markdown-to-PDF publishing tool designed for clean Persian, English, and mixed-language documents.

The project converts Markdown into print-ready PDF files with support for RTL/LTR direction handling, Persian-friendly typography, cover pages, tables of contents, PDF outline bookmarks, GitHub-style Markdown features, MathJax formulas, enhanced syntax-highlighted code, Mermaid flowcharts, local images, footnotes, callouts, safe HTML, watermarks, and a clean appearance system built around styles, palettes, and light/dark modes.

The main goal of the project is to make technical Markdown documents publishable as polished PDF outputs without forcing the author to leave the Markdown workflow.

```text
Markdown -> Structured HTML -> Chromium PDF
```

![Mardas MD2PDF](./README.png)

## Architecture

The system is organized around a browser-based rendering pipeline. Markdown is first parsed and normalized, then converted into a complete HTML document with appearance CSS, cover metadata, table of contents, MathJax configuration, and print rules. Finally, Playwright controls Chromium to generate the final PDF.

### Markdown Processing

The Markdown layer also normalizes visual captions for images, tables, code listings, and Mermaid diagrams so the PDF layer can keep each caption with its associated print block.

The Markdown layer handles front matter, heading collection, table of contents and PDF outline generation, GitHub-style task lists, alerts, autolinks, heading anchors, image captions, enhanced code blocks with titles, line numbers, line highlights, and line-start metadata, Mermaid diagrams, extended callouts, footnotes, safe HTML, local image embedding with blocked placeholders, print-fit wide tables, math protection, and direction-aware document metadata.

### PDF Rendering

Print-flow rules now keep headings with their first block, protect ordinary paragraphs from orphan/widow lines, and let long code blocks or large tables split only when avoiding the split would waste page space.

PDF navigation is kept consistent across both navigation layers: the visible table of contents and the PDF viewer outline/bookmarks both jump to the same real heading destinations after metadata writing and cover/content merging.

The renderer builds the final printable HTML, validates page size and margin options, applies the selected style, palette, and mode, renders MathJax when enabled, separates the cover from numbered content pages, applies mode-aware watermark overlays, writes PDF metadata and bookmarks, adds stable page labels and running footers, and exports the result through Chromium.

### Interfaces

The project provides two user-facing interfaces:

- `mrs-md2pdf` for command-line and automation workflows.
- `mrs-md2pdf-gui` for local browser-based editing, previewing, option selection, PDF export, and browser-local workspace persistence.

## Documentation

The README is intentionally short and is meant to introduce the project. Complete usage details are maintained in the guide files:

- [English Guide](./docs/guides/GUIDE.en.md)
- [راهنمای فارسی](./docs/guides/GUIDE.fa.md)
- [Changelog](./docs/CHANGELOG.md)
- [Release checklist](./docs/RELEASE.md)
- [Maintenance workflow](./docs/MAINTENANCE.md)
- [Appearance system](./docs/APPEARANCE.md)
- [Cover branding](./docs/BRANDING.md)
- [Studio workflow](./docs/STUDIO.md)
- [Markdown fidelity](./docs/MARKDOWN-FIDELITY.md)
- [PDF navigation](./docs/PDF-NAVIGATION.md)
- [PDF typography and print flow](./docs/PDF-TYPOGRAPHY.md)
- [Visual QA system](./docs/VISUAL-QA.md)
- [Security policy](./docs/SECURITY.md)

Generated PDF versions of the guides are available in the [`examples/`](./examples/) directory.

## Quick Start

```bash
git clone https://github.com/mragetsars/Mardas-MD2PDF.git
cd Mardas-MD2PDF
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m playwright install chromium
```

Render a PDF:

```bash
mrs-md2pdf input.md -o output.pdf --toc --style github --palette blue --mode light
```

Cover branding is off by default so exported PDFs belong to the document owner. Enable explicit branding only when desired:

```bash
mrs-md2pdf input.md -o output.pdf --branding full --brand-name "Acme Research Lab"
```

Explore appearance choices:

```bash
mrs-md2pdf --list-styles
mrs-md2pdf --list-palettes
mrs-md2pdf --list-modes
```

Launch the GUI:

```bash
mrs-md2pdf-gui
```

The Studio interface groups export settings into Document, Appearance, Branding, Layout, and Advanced sections. Appearance and branding choices use visual cards, while advanced controls such as watermarks and local assets stay collapsed until needed. Studio can now save and reopen `.mardas.json` project files containing Markdown, export options, and attached assets; it also supports drag-and-drop asset management, accurate renderer-backed HTML preview, debug HTML export, and a command palette via **Ctrl/Cmd+K**. Use **Ctrl/Cmd+S** for Markdown, **Ctrl/Cmd+Shift+S** for a project bundle, and **Ctrl/Cmd+Enter** to export the PDF. When Studio is bound to a non-local host, the backend prints a warning because reachable users can submit Markdown and attached assets. See [Studio workflow](./docs/STUDIO.md) for details.

## Repository Structure

The project is organized as follows:

```text
Mardas-MD2PDF/
├── src/mardas_md2pdf/      # Python package source
│   ├── markdown.py         # Markdown parsing, front matter, TOC, math, Mermaid, footnotes, safe HTML
│   ├── mermaid.py          # Offline Mermaid flowchart-to-SVG renderer
│   ├── renderer.py         # HTML assembly, appearance CSS, MathJax, Chromium PDF rendering
│   ├── cli.py              # Command-line interface
│   ├── gui.py              # Local browser-based GUI backend
│   └── assets/             # Style CSS, GUI shell, logo, and vendored MathJax files
├── docs/                   # Guides, changelog, release, maintenance, security, and feature references
│   └── guides/             # Complete English and Persian user guides
├── examples/               # Generated PDF examples from the guide files
├── scripts/                # Helper scripts for checks, examples, distributions, visual QA, and cleanup
├── tests/                  # Automated pytest test suite
├── pyproject.toml          # Package metadata and dependencies
├── .github/workflows/      # CI and release artifact automation
├── LICENSE                 # MIT license
└── README.md               # Project introduction
```

## Examples

The `examples/` directory contains generated PDF outputs of the guide files:

```text
examples/
├── GUIDE.en.pdf
└── GUIDE.fa.pdf
```

These files are intended to show the real PDF output produced by the current documentation. They are also used as release-facing print samples during typography and media audits.


## Security Model

Mardas MD2PDF is intended for local publishing workflows. By default, local images are resolved relative to the Markdown file, embedded before Chromium renders the PDF, and unresolved or out-of-bound image paths are replaced with a visible blocked placeholder instead of being loaded through the document `<base>` URL. Remote `http(s)` images are blocked by default for privacy; use `--allow-remote-assets` only for trusted documents that intentionally fetch network images. Raw HTML is sanitized unless `--unsafe-html` is used, and safe `data:` image URLs are limited to common raster formats.

Chromium sandboxing is configurable with `--chromium-sandbox auto|on|off`; the default `auto` keeps sandboxing enabled for normal users and disables it only when running as root in container-style environments. See [docs/SECURITY.md](./docs/SECURITY.md) for the full trust boundary.

## Testing

```bash
pip install -e .[dev]
./scripts/check.sh
```

Clean local build and patch artifacts when the working tree starts to feel noisy:

```bash
./scripts/clean_workspace.sh
./scripts/clean_workspace.sh --patches  # also remove a temporary root-level patches/ directory
```


The official guide PDFs also exercise document-local image embedding with semantic figure captions and safe HTML image sizing.

The release process also audits the generated English and Persian guide PDFs visually, including Mermaid labels, local media samples, TOC navigation, footnotes, running footers, and RTL/LTR code isolation.

The test suite covers Markdown transformation, GitHub-style features, direction handling, table of contents and outline generation, enhanced code highlighting, code-fence metadata, Mermaid SVG rendering, MathJax preservation, extended callouts, safe HTML, footnotes, local and remote image boundaries, renderer options, GUI availability, Studio option validation, page-size handling, wide-table print fitting, workspace persistence, deterministic example metadata, appearance validation, and fallback warnings. For visual changes to styles, palettes, or light/dark mode, run `python scripts/audit_appearance_matrix.py --output-dir build/appearance-audit --render-png` and inspect the generated matrix.

## Contributors

This project was developed and maintained by:

- **[Meraj Rastegar](https://github.com/mragetsars)**

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
