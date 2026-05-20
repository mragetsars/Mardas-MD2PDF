---
title: "Mardas MD2PDF Guide"
subtitle: "Complete usage manual and feature sample"
authors:
  - name: "Mardas MD2PDF Team"
    role: "Documentation"
  - name: "Meraj Rastegar"
    email: "mragetsars@yahoo.com"
date: "2026-05-20"
summary: |
  Install, configure, and render professional Markdown PDFs.
  The generated PDF demonstrates cover pages, TOC, math, code, tables, images, HTML, page breaks, and footnotes.
institution: "Mardas Lab"
course: "Markdown Publishing"
version: "1.3.1"
status: "Stable"
keywords:
  - Markdown
  - PDF
  - Persian
  - English
  - RTL/LTR
  - MathJax
  - Playwright
cover_label: "Complete Guide"
lang: en
dir: ltr
---

# Getting Started

Mardas MD2PDF converts Markdown files into polished PDFs by using a browser-grade rendering pipeline:

```text
Markdown -> typographic HTML -> Chromium PDF
```

This approach keeps Markdown authoring simple while giving the renderer strong control over printed layout, MathJax output, local images, cover pages, page breaks, and mixed RTL/LTR typography.

> [!NOTE]
> This file is both a user guide and a visual test case. Render it to PDF to review most of the features supported by the project.

## Installation

Clone the repository, create a virtual environment, install the package, and install Chromium for Playwright:

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

For development and tests:

```bash
pip install -e .[dev]
pytest
```

## First PDF

Create a PDF with the default modern theme:

```bash
mrs-md2pdf input.md -o output.pdf
```

Create a report with a table of contents:

```bash
mrs-md2pdf input.md -o output.pdf --toc --toc-depth 4 --theme modern
```

Create a book-like PDF where the TOC ends on its own page and each top-level heading starts on a new page:

```bash
mrs-md2pdf input.md -o output.pdf \
  --toc \
  --toc-depth 4 \
  --toc-page-break \
  --h1-page-break \
  --theme textbook-light
```

## When to use the GUI

Launch the local editor/exporter:

```bash
mrs-md2pdf-gui
```

The GUI is useful when you want to edit Markdown, preview the document, choose a theme, set export options, attach local image files/folders, and export the PDF without remembering CLI flags.

# Front Matter and Cover Pages

Front matter is optional YAML placed at the beginning of a Markdown file. It controls the cover page, PDF metadata, language, direction, and many document details.

```yaml
---
title: "Mardas MD2PDF Complete Guide"
subtitle: "Feature tour and usage manual"
authors:
  - name: "Mardas MD2PDF Team"
    role: "Documentation"
  - name: "Meraj Rastegar"
    email: "mragetsars@yahoo.com"
summary: |
  Multiline summaries are preserved on the cover.
  Blank lines create separate paragraphs.
institution: "Mardas Lab"
version: "1.3.1"
keywords: [Markdown, PDF, RTL/LTR, MathJax]
cover_label: "Complete Guide"
lang: en
dir: ltr
---
```

## Common fields

| Field | Purpose |
| :--- | :--- |
| `title` | Cover title and PDF metadata title. |
| `subtitle` | Optional text under the title. |
| `author` / `authors` | Single or multiple authors. Author objects may include `name`, `email`, `affiliation`, and `role`. |
| `summary` / `description` | Cover summary and PDF metadata subject. Multiline YAML blocks are supported. |
| `date`, `version`, `status` | Optional cover cards. |
| `institution`, `course`, `department`, `supervisor`, `group`, `student_id` | Optional academic/report metadata cards. |
| `keywords` / `tags` | Cover keyword card and PDF metadata keywords. |
| `cover_label` | Small label above the cover title. |
| `cover_logo` / `logo` | Custom cover logo path relative to the Markdown file. |
| `lang` | Built-in UI language, such as `en` or `fa`. |
| `dir` | Document shell direction: `auto`, `ltr`, or `rtl`. |

## Cover behavior

The cover is rendered separately from the main document. That means:

- the cover is not counted in content page numbering;
- header/footer numbering starts after the cover;
- watermarks are applied to content pages only;
- the cover can use full-bleed theme backgrounds.

Disable the cover:

```bash
mrs-md2pdf input.md -o output.pdf --no-cover
```

Use a custom logo:

```bash
mrs-md2pdf input.md -o output.pdf --cover-logo ./assets/logo.png
```

Hide the logo while keeping the cover:

```bash
mrs-md2pdf input.md -o output.pdf --no-cover-logo
```

# Language, Direction, and Typography

`lang: en` creates an English/LTR document shell, English cover labels, English callout titles, and a `Table of Contents` heading. `lang: fa` creates a Persian/RTL document shell, Persian labels, and `فهرست مطالب`.

The direction resolution order is:

1. CLI `--dir rtl|ltr|auto`
2. front matter `dir`, `direction`, `text_direction`, or `document_direction`
3. language-derived default from `lang`
4. automatic detection from the Markdown body

## Mixed text example

English technical writing can include Persian terms such as راست به چپ, چپ به راست, and فونت فارسی without breaking the surrounding sentence. Persian documents can also include English identifiers such as `Playwright`, `MathJax`, `PDF`, and `RTL/LTR` inside one paragraph.

Inline code remains readable: `mrs-md2pdf input.md -o output.pdf --toc`.

## Direction control tips

- Use `lang: en` for English guides, API documents, and reports.
- Use `lang: fa` for Persian reports and course notes.
- Use `dir: auto` when you want the converter to infer the shell direction.
- Use `--dir ltr` or `--dir rtl` when a CI/CD job must force a specific layout.

# Table of Contents

Enable the TOC with:

```bash
mrs-md2pdf input.md -o output.pdf --toc
```

Control depth:

```bash
mrs-md2pdf input.md -o output.pdf --toc --toc-depth 3
```

Start the body after the TOC on a new page:

```bash
mrs-md2pdf input.md -o output.pdf --toc --toc-page-break
```

The TOC is built from Markdown headings and keeps inline math readable when headings contain formulas such as $E = mc^2$ or $\epsilon$.

# Markdown Features

## Tables

| Feature | Status | Notes |
| :--- | :---: | :--- |
| Mixed RTL/LTR text | ✅ | Paragraphs, headings, list items, and table cells receive direction-aware handling. |
| Local images | ✅ | Markdown and safe HTML images are embedded as data URIs. |
| MathJax | ✅ | Inline and display formulas use separate scaling. |
| Code highlighting | ✅ | Fenced and indented code blocks are highlighted with Pygments. |
| Footnotes | ✅ | Multiline footnotes with Markdown content are supported. |
| Raw HTML sanitizer | ✅ | Unsafe tags and event handlers are removed by default. |

## Task lists

- [x] Write Markdown.
- [x] Configure front matter.
- [x] Render a PDF.
- [ ] Review the output in more than one viewer if the document is critical.

## Blockquotes

> Good PDF publishing is not just text conversion. Typography, page flow, figure stability, contrast, and predictable rendering all matter.

## Callouts

> [!TIP]
> Use `--debug-html output.html` when you need to inspect the exact HTML sent to Chromium.

> [!WARNING]
> Use `--unsafe-html` only for trusted local Markdown because it disables the built-in sanitizer.

# MathJax

Inline math should match the surrounding line height: $E = mc^2$, $\Sigma = I \cdot \epsilon$, and $T = 500$ should sit naturally inside a paragraph.

Display math gets more space and a larger visual scale:

$$
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}
$$

A matrix example:

$$
A = \begin{bmatrix}
1 & 2 \\
3 & 4
\end{bmatrix}, \qquad \det(A) = -2
$$

An aligned equation block:

$$
\begin{aligned}
\text{precision} &= \frac{TP}{TP + FP} \\
\text{recall} &= \frac{TP}{TP + FN}
\end{aligned}
$$

# Code Highlighting

Fenced code blocks show the language label and syntax highlighting.

```python
from dataclasses import dataclass

@dataclass
class Document:
    title: str
    lang: str = "en"


def render_message(doc: Document) -> str:
    return f"Rendering {doc.title} as a polished PDF"

print(render_message(Document("Mardas Guide")))
```

```javascript
const items = ["Markdown", "Persian", "English", "MathJax", "PDF"];
const message = items.map((item, index) => `${index + 1}. ${item}`).join("\n");
console.log(message);
```

```c
int setSeed(void);
int getRandomNumber(int n, int *buf);
int process_information(int pid);
int sort_numbers(const char *src_file);
```

Indented code blocks are also supported:

    SELECT title, lang, version
    FROM documents
    WHERE renderer = 'mardas-md2pdf';

# Images and Safe HTML

Markdown images are resolved relative to the Markdown file and embedded into the generated HTML/PDF.

![Local chart embedded from the examples folder](examples/images/md2pdf-sample-chart.png)

Safe raw HTML images can also be used when you need explicit sizing:

<img src="examples/images/md2pdf-sample-chart.png" width="70%" alt="Local chart embedded with safe HTML">

Raw HTML is sanitized by default. The sanitizer keeps document-oriented elements such as `<div>`, `<span>`, `<table>`, `<figure>`, and `<img>`, while removing active content such as scripts, event handlers, iframes, forms, remote stylesheets, and unsafe URL schemes.

<div class="md2pdf-page-break"></div>

# Page Flow, Watermarks, and Themes

## Manual page breaks

A manual page break can be inserted with safe HTML:

```html
<div class="md2pdf-page-break"></div>
```

## Watermarks

Text watermark:

```bash
mrs-md2pdf input.md -o output.pdf --watermark "DRAFT"
```

Image watermark:

```bash
mrs-md2pdf input.md -o output.pdf \
  --watermark-image ./Mardas.png \
  --watermark-opacity 0.05 \
  --watermark-width 95mm
```

Watermarks are applied to content pages only, not to the cover.

## Themes

| Theme | Best for |
| :--- | :--- |
| `modern` | General documentation, proposals, software reports. |
| `textbook-light` | Course notes, long Persian/English educational PDFs. |
| `textbook-dark` | Screen reading and low-light review. |
| `academic` | Formal reports, university-style documents, thesis-like drafts. |

# CLI Reference

| Option | Description |
| :--- | :--- |
| `input` | Input Markdown file. |
| `-o`, `--output` | Output PDF path. |
| `--title`, `--author`, `--description` | Override metadata from front matter. |
| `--toc`, `--toc-depth` | Enable/configure the Table of Contents. |
| `--toc-page-break`, `--h1-page-break` | Control print page flow. |
| `--theme` | Choose `modern`, `textbook-light`, `textbook-dark`, or `academic`. |
| `--page-size` | `A4`, `Letter`, `Legal`, or a CSS page size. |
| `--dir` | Force `auto`, `ltr`, or `rtl`. |
| `--margin-top`, `--margin-bottom`, `--margin-x` | Control page margins. |
| `--font-dir` | Directory containing local Vazirmatn font files. |
| `--chromium-path` | Custom Chromium/Chrome executable path. |
| `--debug-html` | Save the intermediate HTML. |
| `--no-cover`, `--cover-logo`, `--no-cover-logo` | Configure the cover. |
| `--watermark`, `--watermark-image` | Add watermarks. |
| `--no-header-footer` | Disable the footer. |
| `--no-mathjax` | Do not load MathJax. |
| `--unsafe-html` | Disable raw HTML sanitization. |
| `--timeout-ms` | Browser timeout in milliseconds. |

# Troubleshooting

## Missing browser

Run:

```bash
python -m playwright install chromium
```

or pass a custom browser path:

```bash
mrs-md2pdf input.md -o output.pdf --chromium-path /path/to/chrome
```

## Missing images

Check that image paths are relative to the Markdown file. For GUI exports, attach the image folder/files so the backend can embed them before rendering.

## Math appears as raw TeX

Make sure MathJax is enabled. Avoid `--no-mathjax` unless you intentionally want raw math markers.

## Need to debug layout

Generate intermediate HTML:

```bash
mrs-md2pdf input.md -o output.pdf --debug-html output.html
```

# Footnotes

Footnotes are useful for technical notes and references.[^pipeline]

[^pipeline]: Mardas MD2PDF intentionally uses Chromium for layout instead of drawing every paragraph directly on a PDF canvas.
    This gives the project strong support for CSS print rules, mixed direction text, MathJax SVG output, tables, local images, and syntax-highlighted code.

    - Multiline footnotes are supported.
    - Markdown inside footnotes is preserved.
    - Inline code like `@page` remains readable.

# Final Checklist

Before publishing an important PDF:

- [x] Check the cover metadata.
- [x] Check the TOC language and direction.
- [x] Check a page containing math.
- [x] Check a page containing code.
- [x] Check local images.
- [x] Check footer numbering after the cover.
- [ ] Review the final PDF visually.
