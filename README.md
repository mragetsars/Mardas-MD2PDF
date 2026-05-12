# Mardas MD2PDF

> Markdown to PDF Converter - Persian/English Typography - RTL/LTR Documents - Professional PDF Publishing

![Language](https://img.shields.io/badge/Language-Python-blue.svg)
![Renderer](https://img.shields.io/badge/Renderer-Playwright%20%2B%20Chromium-green.svg)
![Math](https://img.shields.io/badge/Math-MathJax-purple.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

## Overview

This repository contains **Mardas MD2PDF**, a professional Markdown-to-PDF converter designed for clean, readable, and visually polished technical documents.

The main focus of this project is high-quality PDF generation for documents that contain Persian text, English technical terms, mixed RTL/LTR sentences, tables, mathematical formulas, code blocks, images, links, notes, and long academic-style reports.

The project intentionally uses the following rendering pipeline:

```text
Markdown → Typographic HTML → Chromium PDF
```

This architecture gives the project strong control over typography, print CSS, page margins, syntax highlighting, MathJax formulas, table styling, and mixed-direction text rendering.

## Project Objectives

- ✅ Convert Markdown files into polished PDF documents.
- ✅ Preserve readability for Persian, English, and mixed RTL/LTR paragraphs.
- ✅ Render code blocks with language-aware syntax highlighting.
- ✅ Support both fenced code blocks and four-space indented code blocks.
- ✅ Render tables, task lists, links, images, blockquotes, callouts, footnotes, and page breaks.
- ✅ Render inline and display math formulas using vendored MathJax.
- ✅ Generate a hierarchical Table of Contents based on Markdown heading levels.
- ✅ Provide multiple visual themes for different document styles.
- ✅ Keep the command-line interface simple and predictable through `mrs-md2pdf`.

## Features

### Persian and Mixed-Direction Typography

Mardas MD2PDF is designed for documents such as:

```text
این گزارش درباره xv6, system call, kernel, user space و PDF generation است.
```

The document body is RTL by default, while paragraphs, headings, lists, table cells, and captions use direction-aware processing. Code blocks, inline code, paths, commands, formulas, and technical identifiers are kept LTR for readability.

### Hierarchical Table of Contents

When `--toc` is enabled, the converter reads the Markdown heading structure:

```markdown
# Section 1
## Section 1-1
## Section 1-2
### Section 1-2-1
# Section 2
```

and generates a nested, numbered table of contents such as:

```text
1       Section 1
1-1     Section 1-1
1-2     Section 1-2
1-2-1   Section 1-2-1
2       Section 2
```

The maximum heading depth can be controlled with `--toc-depth`.

### Code Block Rendering

The converter supports:

- fenced code blocks, such as ```` ```python ````;
- indented code blocks written with four leading spaces;
- automatic conservative language guessing for raw indented blocks;
- monospace fonts for code;
- Pygments-based syntax highlighting.

Supported examples include C, Python, JavaScript, Bash, GDB traces, HTML, and plain text.

### Math Rendering

Math formulas can be written inline:

```markdown
Energy is $E = mc^2$.
```

or as display math:

```markdown
$$
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}
$$
```

MathJax is vendored inside the project, so formulas can be rendered without relying on a CDN.

## Themes

Mardas MD2PDF currently ships with two print-oriented themes.

### 1. `modern`

A polished, clean, flat theme for general technical documentation.

```bash
mrs-md2pdf input.md -o output.pdf --toc --theme modern
```

Recommended for:

- software documentation;
- proposals;
- technical reports;
- Markdown documents with tables and code blocks.

### 2. `textbook`

A simple academic theme inspired by Persian course notes and university handouts. It uses a flatter layout, light code blocks, simple callouts, and a minimal footer.

```bash
mrs-md2pdf input.md -o output.pdf --toc --theme textbook --no-cover
```

Recommended for:

- university reports;
- lecture notes;
- educational PDFs;
- long Persian documents similar to textbook-style outputs.

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/mragetsars/Mardas-MD2PDF.git
cd Mardas-MD2PDF
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install the Project

```bash
pip install -e .
```

For development tools:

```bash
pip install -e .[dev]
```

### 4. Install Chromium for Playwright

```bash
python -m playwright install chromium
```

If Chromium or Google Chrome is already installed on your system, Mardas MD2PDF can usually detect it automatically. You can also pass a custom executable path with `--chromium-path`.

## Basic Usage

Convert a Markdown file into a PDF:

```bash
mrs-md2pdf input.md -o output.pdf
```

Generate a hierarchical table of contents:

```bash
mrs-md2pdf input.md -o output.pdf --toc
```

Use the textbook theme:

```bash
mrs-md2pdf input.md -o output.pdf --toc --theme textbook --no-cover
```

Export the intermediate HTML for debugging:

```bash
mrs-md2pdf input.md -o output.pdf --debug-html output.html
```

Use a local font directory:

```bash
mrs-md2pdf input.md -o output.pdf --font-dir ./fonts
```

## Command-Line Options

| Option | Description | Default |
|:--|:--|:--|
| `input` | Input Markdown file. | Required |
| `-o`, `--output` | Output PDF path. | Input filename with `.pdf` extension |
| `--title` | Override the document title. | First `#` heading or front matter title |
| `--author` | Override author metadata. | Front matter author |
| `--description` | Override summary/description metadata. | Front matter description/summary |
| `--toc` | Generate a hierarchical table of contents. | Disabled |
| `--toc-depth 1..6` | Maximum heading level included in the TOC. | `6` |
| `--theme modern\|textbook` | Select the visual PDF theme. | `modern` |
| `--no-cover` | Disable the automatic cover section. | Cover enabled |
| `--no-header-footer` | Disable PDF footer/page number template. | Footer enabled |
| `--no-mathjax` | Disable MathJax processing. | MathJax enabled |
| `--debug-html` | Write the intermediate HTML file. | Disabled |
| `--page-size` | PDF page size such as `A4` or `Letter`. | `A4` |
| `--margin-top` | Top page margin. | `18mm` |
| `--margin-bottom` | Bottom page margin. | `20mm` |
| `--margin-x` | Left and right page margins. | `16mm` |
| `--font-dir` | Directory containing Vazirmatn font files. | System fonts |
| `--chromium-path` | Custom Chromium/Chrome executable path. | Auto-detect |
| `--timeout-ms` | Browser timeout in milliseconds. | `120000` |
| `--version` | Print the installed version. | - |

## Front Matter

A Markdown file can start with YAML front matter:

```yaml
---
title: "Operating Systems Lab Report"
author: "Meraj Rastegar"
date: "2026-05-12"
summary: "A clean PDF report generated from Markdown."
lang: fa
---
```

These values are used for the PDF title, cover section, and metadata-like display fields.

## Fonts

For best Persian typography, install **Vazirmatn** on your system or provide the font files through `--font-dir`.

Supported filenames inside `--font-dir`:

```text
Vazirmatn-Regular.woff2
Vazirmatn[wght].woff2
Vazirmatn-Regular.ttf
Vazirmatn.ttf
Vazirmatn-Bold.woff2
Vazirmatn-Bold.ttf
```

Code blocks use a monospace font stack such as JetBrains Mono, Fira Code, Cascadia Code, Menlo, Consolas, and Liberation Mono.

## Page Breaks

Use the following marker to force a new page:

```markdown
---page---
```

or use raw HTML:

```html
<div class="page-break"></div>
```

## Repository Structure

The project is organized as follows:

```text
Mardas-MD2PDF/
├── examples/                         # Example Markdown, HTML and PDF outputs
│   ├── fa-en-math-code.md            # Persian/English sample document
│   ├── fa-en-math-code.pdf           # Sample PDF with modern theme
│   └── fa-en-math-code-textbook.pdf  # Sample PDF with textbook theme
├── scripts/                          # Helper scripts
│   └── install_playwright.sh         # Install Chromium for Playwright
├── src/                              # Python package source code
│   └── mardas_md2pdf/
│       ├── __init__.py               # Package version
│       ├── cli.py                    # Command-line interface
│       ├── markdown.py               # Markdown parsing and HTML post-processing
│       ├── renderer.py               # HTML-to-PDF rendering with Chromium
│       └── assets/
│           ├── theme.css             # Modern theme
│           ├── theme-textbook.css    # Textbook theme
│           └── mathjax/              # Vendored MathJax asset
├── tests/                            # Unit tests
│   └── test_markdown.py              # Markdown rendering tests
├── pyproject.toml                    # Build system and dependencies
├── LICENSE                           # Project license
└── README.md                         # Project documentation
```

## Development & Testing

Run the test suite:

```bash
pytest -q
```

Generate a test PDF:

```bash
mrs-md2pdf examples/fa-en-math-code.md \
  -o examples/fa-en-math-code.pdf \
  --toc \
  --theme modern
```

Generate a textbook-style PDF:

```bash
mrs-md2pdf examples/fa-en-math-code.md \
  -o examples/fa-en-math-code-textbook.pdf \
  --toc \
  --theme textbook \
  --no-cover
```

## Design Notes

- The body of the document is RTL by default.
- Textual blocks use `dir="auto"` to preserve mixed Persian/English readability.
- Code, inline code, shell commands, file paths, stack traces, and math formulas are forced to LTR.
- Tables are wrapped for stable borders, rounded corners, and clean page rendering.
- Shadows are intentionally disabled to avoid Chromium PDF edge artifacts.
- The Table of Contents is generated from actual Markdown heading levels, not from a flat heading list.
- Invalid TeX should not stop the whole PDF generation process.

## Future Improvements

- Add more themes such as `article`, `book`, and `minimal`.
- Add optional Mermaid diagram rendering.
- Add optional automatic heading numbering inside the document body.
- Add automatic figure and table captions.
- Add export targets for standalone HTML and EPUB.
- Add a visual regression test suite for generated PDFs.

## Author

This project is developed and maintained by:

- **Meraj Rastegar** (`@mragetsars`)

## Acknowledgments

- Built with Python, Pygments, MathJax, and Playwright.
- Designed for professional Persian/English technical documents.
