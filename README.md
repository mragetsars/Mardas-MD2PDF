# Mardas MD2PDF

> **Professional Markdown to PDF converter for Persian, English, and mixed RTL/LTR technical documents**

![Language](https://img.shields.io/badge/Language-Python-blue) ![Renderer](https://img.shields.io/badge/Renderer-Playwright%20%2B%20Chromium-green) ![Math](https://img.shields.io/badge/Math-MathJax-purple) ![Version](https://img.shields.io/badge/Version-v1.5.1-success) ![Status](https://img.shields.io/badge/Status-Stable-success)

## Overview

This repository contains **Mardas MD2PDF**, a Markdown-to-PDF publishing tool designed for clean Persian, English, and mixed-language documents.

The project converts Markdown into print-ready PDF files with support for RTL/LTR direction handling, Persian-friendly typography, cover pages, tables of contents, GitHub-style Markdown features, MathJax formulas, enhanced syntax-highlighted code, Mermaid flowcharts, local images, footnotes, callouts, safe HTML, watermarks, and multiple visual profiles.

The main goal of the project is to make technical Markdown documents publishable as polished PDF outputs without forcing the author to leave the Markdown workflow.

```text
Markdown -> Structured HTML -> Chromium PDF
```

![Mardas MD2PDF](./README.png)

## Architecture

The system is organized around a browser-based rendering pipeline. Markdown is first parsed and normalized, then converted into a complete HTML document with theme CSS, cover metadata, table of contents, MathJax configuration, and print rules. Finally, Playwright controls Chromium to generate the final PDF.

### Markdown Processing

The Markdown layer handles front matter, heading collection, table of contents generation, GitHub-style task lists, alerts, autolinks, heading anchors, image captions, enhanced code blocks, Mermaid diagrams, footnotes, safe HTML, local image embedding, math protection, and direction-aware document metadata.

### PDF Rendering

The renderer builds the final printable HTML, applies the selected theme, configures page size and margins, renders MathJax when enabled, separates the cover from numbered content pages, applies optional watermarks, and exports the result through Chromium.

### Interfaces

The project provides two user-facing interfaces:

- `mrs-md2pdf` for command-line and automation workflows.
- `mrs-md2pdf-gui` for local browser-based editing, previewing, option selection, and PDF export.

## Documentation

The README is intentionally short and is meant to introduce the project. Complete usage details are maintained in the guide files:

- [English Guide](./GUIDE.en.md)
- [راهنمای فارسی](./GUIDE.fa.md)

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
mrs-md2pdf input.md -o output.pdf --toc --profile github
```

Launch the GUI:

```bash
mrs-md2pdf-gui
```

## Repository Structure

The project is organized as follows:

```text
Mardas-MD2PDF/
├── src/                    # Python package source
│   ├── markdown.py         # Markdown parsing, front matter, TOC, math, Mermaid, footnotes, safe HTML
│   ├── mermaid.py          # Offline Mermaid flowchart-to-SVG renderer
│   ├── renderer.py         # HTML assembly, themes/profiles, MathJax, Chromium PDF rendering
│   ├── cli.py              # Command-line interface
│   ├── gui.py              # Local browser-based GUI backend
│   └── assets/             # Themes, GUI shell, logo, and vendored MathJax files
├── tests/                  # Automated pytest test suite
├── scripts/                # Helper scripts
├── examples/               # Generated PDF examples from the guide files
├── GUIDE.en.md             # Complete English user guide
├── GUIDE.fa.md             # Complete Persian user guide
├── README.png              # Project preview image
├── pyproject.toml          # Package metadata and dependencies
└── README.md               # Project introduction
```

## Examples

The `examples/` directory contains generated PDF outputs of the guide files:

```text
examples/
├── GUIDE.en.pdf
└── GUIDE.fa.pdf
```

These files are intended to show the real PDF output produced by the current documentation.

## Testing

```bash
pip install -e .[dev]
pytest
```

The test suite covers Markdown transformation, GitHub-style features, direction handling, table of contents generation, enhanced code highlighting, Mermaid SVG rendering, MathJax preservation, safe HTML, footnotes, local images, renderer options, GUI availability, page-size handling, and fallback warnings.

## Contributors

This project was developed and maintained by:

- **[Meraj Rastegar](https://github.com/mragetsars)**

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
