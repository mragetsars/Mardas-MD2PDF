# Mardas MD2PDF

> Markdown to PDF Converter - Persian/English Typography - RTL/LTR Documents - Professional PDF Publishing

![Language](https://img.shields.io/badge/Language-Python-blue.svg)
![Renderer](https://img.shields.io/badge/Renderer-Playwright%20%2B%20Chromium-green.svg)
![Math](https://img.shields.io/badge/Math-MathJax-purple.svg)
![Version](https://img.shields.io/badge/Version-v1.0.0-success.svg)
![Status](https://img.shields.io/badge/Status-Stable-success.svg)

---

## 📌 Overview

**Mardas MD2PDF** is a professional Markdown-to-PDF engine for clean, readable, and visually polished technical documents.

The project is especially focused on Persian documents that also contain English technical terms, mixed RTL/LTR sentences, tables, mathematical formulas, code blocks, images, links, notes, long academic reports, and software documentation.

The rendering pipeline is intentionally simple and powerful:

```text
Markdown → Typographic HTML → Chromium PDF
```

This pipeline gives the project strong control over typography, print CSS, page margins, syntax highlighting, MathJax formulas, table styling, cover pages, watermarks, and mixed-direction text rendering.

---

## 🎯 Project Objectives

- Convert Markdown files into polished PDF documents.
- Preserve readability for Persian, English, and mixed RTL/LTR paragraphs.
- Render fenced and indented code blocks with syntax highlighting.
- Support tables, task lists, links, images, blockquotes, callouts, footnotes, and page breaks.
- Render inline and display math formulas using vendored MathJax.
- Generate a hierarchical Table of Contents from Markdown heading levels.
- Generate a designed cover page that is not counted in document page numbering.
- Support optional page-flow controls for TOC and top-level headings.
- Support optional text or image watermarks on content pages only.
- Provide multiple visual themes for different document styles.
- Provide both a command-line workflow and a local graphical editor/exporter.

---

## ✨ Features

### 📝 Persian and Mixed-Direction Typography

Mardas MD2PDF is designed for documents such as:

```text
این گزارش درباره xv6, system call, kernel, user space و PDF generation است.
```

The document body is RTL by default, while paragraphs, headings, lists, table cells, and captions use direction-aware processing. Code blocks, inline code, paths, commands, formulas, and technical identifiers are kept LTR for readability.

### 📚 Hierarchical Table of Contents

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

### 💻 Code Block Rendering

The converter supports:

- fenced code blocks, such as ```` ```python ````;
- indented code blocks written with four leading spaces;
- automatic conservative language guessing for raw indented blocks;
- monospace fonts for code;
- Pygments-based syntax highlighting.

Supported examples include C, Python, JavaScript, Bash, GDB traces, HTML, and plain text.

### 🧮 Math Rendering

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

### 🖼️ Professional Cover Page

By default, Mardas MD2PDF generates a designed cover page using the bundled Mardas logo, document title, author, date, and summary/description.

The cover page is rendered separately from the main document. Therefore:

- the cover has no footer;
- the cover is not counted in page numbering;
- watermarks are not applied to the cover;
- the cover background reaches the full page edge.

Disable the cover:

```bash
mrs-md2pdf input.md -o output.pdf --no-cover
```

Use a custom cover logo:

```bash
mrs-md2pdf input.md -o output.pdf --cover-logo ./assets/logo.png
```

Hide only the logo while keeping the cover layout:

```bash
mrs-md2pdf input.md -o output.pdf --no-cover-logo
```

### 💧 Watermark Support

Mardas MD2PDF can add a watermark to every content page. The cover page is intentionally excluded.

Text watermark:

```bash
mrs-md2pdf input.md -o output.pdf --watermark "DRAFT"
```

Image watermark:

```bash
mrs-md2pdf input.md -o output.pdf --watermark-image ./Mardas.png
```

Control opacity and size:

```bash
mrs-md2pdf input.md -o output.pdf \
  --watermark-image ./Mardas.png \
  --watermark-opacity 0.05 \
  --watermark-width 95mm
```

### 📖 Page Flow Controls

For reports, books, and course notes, you may want the TOC and top-level headings to behave like printed books.

Start the main content on a new page after the table of contents:

```bash
mrs-md2pdf input.md -o output.pdf --toc --toc-page-break
```

Start every `#` heading on a new page:

```bash
mrs-md2pdf input.md -o output.pdf --h1-page-break
```

Both options can be used together:

```bash
mrs-md2pdf input.md -o output.pdf --toc --toc-page-break --h1-page-break
```

---

## 🖥️ Graphical Interface

Mardas MD2PDF also includes a local browser-based GUI named **Mardas MD2PDF Studio**.

Start it with:

```bash
mrs-md2pdf-gui
```

Then open the shown local URL in your browser. By default, the app opens automatically.

The GUI lets users:

- open and edit Markdown files;
- preview Markdown while editing;
- choose the PDF theme;
- enable or disable TOC;
- set TOC depth;
- enable TOC page break and H1 page break;
- set title, author, page size, output filename, and watermark text;
- export the final PDF through the same Python rendering engine;
- copy an equivalent CLI command.

The GUI is intended for users who prefer visual configuration over command-line flags.

---

## 🎨 Themes

Mardas MD2PDF ships with multiple print-oriented themes.

### 1. `modern`

A polished, colorful, flat theme for general technical documentation. Its cover uses blue, cyan, violet, and pink gradients.

```bash
mrs-md2pdf input.md -o output.pdf --toc --theme modern
```

Recommended for:

- software documentation;
- proposals;
- technical reports;
- Markdown documents with tables and code blocks.

### 2. `textbook-light`

A light course-note theme inspired by Persian university handouts. It is intentionally simple, clean, and neutral. Its cover uses grayscale gradients.

```bash
mrs-md2pdf input.md -o output.pdf --toc --theme textbook-light
```

Recommended for:

- university reports;
- lecture notes;
- educational PDFs;
- long Persian documents similar to textbook-style outputs.

### 3. `textbook-dark`

A dark course-note theme for screen reading and low-light review. It mirrors the simplicity of `textbook-light`: black paper, light text, gray borders, monochrome code blocks, and minimal color.

```bash
mrs-md2pdf input.md -o output.pdf --toc --theme textbook-dark
```

Recommended for:

- digital notes;
- long screen-reading sessions;
- draft PDFs shared for review;
- technical material with many code blocks.

### 4. `academic`

A formal report theme with a warmer academic visual style. Its cover uses brown, warm, maroon, and muted red gradients.

```bash
mrs-md2pdf input.md -o output.pdf --toc --theme academic
```

Recommended for:

- formal reports;
- printable university documents;
- thesis-like Markdown reports;
- documents that need a calmer, less colorful visual style.

---

## 🚀 Getting Started

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

---

## ⚙️ Basic Usage

Convert a Markdown file into a PDF:

```bash
mrs-md2pdf input.md -o output.pdf
```

Generate a hierarchical table of contents:

```bash
mrs-md2pdf input.md -o output.pdf --toc
```

Use a textbook-style report layout:

```bash
mrs-md2pdf input.md -o output.pdf \
  --toc \
  --toc-depth 6 \
  --toc-page-break \
  --h1-page-break \
  --theme textbook-light
```

Use the dark textbook theme:

```bash
mrs-md2pdf input.md -o output.pdf \
  --toc \
  --theme textbook-dark
```

Launch the GUI:

```bash
mrs-md2pdf-gui
```

Generate the intermediate HTML for debugging:

```bash
mrs-md2pdf input.md -o output.pdf --debug-html output.html
```

---

## 🧩 CLI Options

| Option | Description |
|:--|:--|
| `input` | Input Markdown file. |
| `-o`, `--output` | Output PDF path. If omitted, the input filename is used with `.pdf`. |
| `--title` | Override document title. Otherwise front matter or first `#` heading is used. |
| `--author` | Override author metadata. |
| `--description` | Override summary/description metadata. |
| `--toc` | Generate a hierarchical table of contents. |
| `--toc-depth 1..6` | Maximum heading level included in TOC. Default: `6`. |
| `--toc-page-break` | Put the main document content on a new page after the TOC. |
| `--h1-page-break` | Start every top-level `#` heading on a new page. |
| `--theme` | Choose `modern`, `textbook-light`, `textbook-dark`, or `academic`. |
| `--page-size` | PDF page size such as `A4` or `Letter`. |
| `--margin-top` | Top page margin. Default: `18mm`. |
| `--margin-bottom` | Bottom page margin. Default: `20mm`. |
| `--margin-x` | Left/right page margin. Default: `16mm`. |
| `--font-dir` | Directory containing local Vazirmatn font files. |
| `--chromium-path` | Path to Chromium/Chrome executable. |
| `--debug-html` | Save intermediate HTML for inspection. |
| `--no-cover` | Disable automatic cover page. |
| `--cover-logo` | Use a custom logo on the cover. |
| `--no-cover-logo` | Hide the logo while keeping the cover page. |
| `--watermark` | Add a text watermark to content pages. |
| `--watermark-image` | Add an image watermark to content pages. |
| `--watermark-opacity` | Watermark opacity between `0` and `1`. Default: `0.065`. |
| `--watermark-width` | CSS width for image watermarks. Default: `105mm`. |
| `--no-header-footer` | Disable page number footer. |
| `--no-mathjax` | Do not load MathJax. |
| `--timeout-ms` | Browser rendering timeout in milliseconds. |
| `--version` | Print the installed version. |

---

## 🗂️ Project Structure

```text
Mardas-MD2PDF/
├── src/
│   ├── assets/
│   │   ├── Mardas.png
│   │   ├── gui.html
│   │   ├── theme-modern.css
│   │   ├── theme-textbook-light.css
│   │   ├── theme-textbook-dark.css
│   │   ├── theme-academic.css
│   │   └── mathjax/
│   ├── __init__.py
│   ├── cli.py
│   ├── gui.py
│   ├── markdown.py
│   └── renderer.py
├── examples/
│   └── fa-en-math-code.md
├── tests/
│   └── test_markdown.py
├── scripts/
│   └── install_playwright.sh
├── pyproject.toml
├── README.md
└── LICENSE
```

### Important Files

- `src/cli.py`: command-line interface and argument parsing.
- `src/gui.py`: local HTTP server for the graphical Markdown editor and PDF exporter.
- `src/markdown.py`: Markdown parsing, TOC generation, direction handling, footnotes, math protection, and code highlighting.
- `src/renderer.py`: HTML assembly, cover rendering, watermarking, Chromium PDF rendering, and PDF merging.
- `src/assets/gui.html`: browser UI for editing Markdown and configuring exports.
- `src/assets/theme-modern.css`: modern theme.
- `src/assets/theme-textbook-light.css`: light textbook theme.
- `src/assets/theme-textbook-dark.css`: dark textbook theme.
- `src/assets/theme-academic.css`: formal academic theme.

---

## 🧪 Testing

Install the project first:

```bash
pip install -e .[dev]
```

Run the test suite:

```bash
pytest
```

The current tests cover:

- mixed Persian/English direction handling;
- fenced code highlighting;
- indented code block wrapping and language guessing;
- tables and display math;
- hierarchical TOC numbering and nesting;
- explicit public theme choices;
- hidden unbranded-cover option behavior;
- GUI entrypoint availability.

---

## 🧾 Front Matter

Mardas MD2PDF reads optional YAML front matter:

```yaml
---
title: "گزارش کار پروژه دوم آزمایشگاه سیستم عامل"
author: "تیم Mardas MD2PDF"
date: "2026-05-12"
summary: "یک گزارش فنی درباره system call در xv6"
lang: fa
---
```

These fields are used for title detection, cover page metadata, document language, and HTML metadata.

---

## 📄 Markdown Extensions

Supported syntax includes:

- headings `#` to `######`;
- tables;
- fenced code blocks;
- indented code blocks;
- task lists;
- blockquotes;
- callouts;
- images;
- inline code;
- footnotes;
- inline and display math;
- manual page breaks.

Manual page break:

```html
<div class="md2pdf-page-break"></div>
```

---

## 🛠️ Development Notes

The project avoids direct low-level PDF drawing for document content. Instead, it uses browser-grade layout through Chromium. This makes typography, tables, RTL/LTR behavior, MathJax SVG output, and print CSS much easier to control.

The cover page is rendered as a separate full-bleed PDF and then merged with the content PDF. This keeps cover numbering and watermark behavior clean while allowing the cover background to reach the paper edges.

The source package intentionally uses a flattened `src/` layout: the package name is still `mardas_md2pdf`, but source files live directly in `src/` to keep the repository tree compact.

---

## 🔮 Future Improvements

- Add automatic PDF outline/bookmarks.
- Add per-section page numbering styles.
- Add automatic theme previews in the README.
- Add optional source-code line numbers.
- Add GUI support for custom cover logos and image watermarks.
- Add automatic document quality checks after rendering.

---

## 👤 Author

**Mardas MD2PDF**  
Designed for professional Persian/English Markdown publishing.

---

## 📜 License

This project is licensed under the MIT License.
