# PDF Typography and Print Flow

Mardas MD2PDF renders Markdown through Chromium, so final PDF quality depends on
both semantic HTML and print-focused CSS. This document tracks the print-flow
rules used to keep long technical documents readable.

## Page-flow goals

The renderer tries to keep related content together without making long pages
fragile:

- headings stay with the first block that follows them;
- ordinary paragraphs and list items use `orphans` / `widows` protection;
- figures, Mermaid diagrams, callouts, details blocks, math displays, and image
  placeholders avoid splitting across pages;
- short code blocks stay together, while long code blocks may split instead of
  leaving large blank areas;
- long or wide tables may split across pages, while individual table rows avoid
  splitting;
- table headers are repeated by Chromium where the PDF engine supports table
  header groups.

## Code blocks

Code blocks are semantic `<figure class="code-block">` elements. During Markdown
post-processing, Mardas records the number of source lines as `data-lines` and
adds print-flow classes for long snippets:

```text
code-block--long       # 36+ source lines
code-block--very-long  # 90+ source lines
```

Short code blocks use `break-inside: avoid`; long code blocks use `break-inside:
auto` so they can continue on the next page. Captions still use `break-after:
avoid` so the caption is not orphaned from the code that follows.

## Tables

Tables are wrapped in `.table-wrap`. The wrapper records column and row counts
as `data-md2pdf-columns` and `data-md2pdf-rows` so print rules can distinguish
ordinary tables from wide or long ones:

```text
table-wrap--wide       # 8+ columns
table-wrap--very-wide  # 12+ columns
table-wrap--long       # 18+ rows
```

Normal tables try to stay together. Wide and long tables may break across pages,
but rows keep `break-inside: avoid` to prevent split cells.

## Audit checklist

When changing print typography, render the guides and inspect at least these
areas:

- table of contents page flow;
- a section that begins near the bottom of a page;
- a short code block with a caption;
- a long code block with line numbers;
- a wide table;
- a long table;
- a Mermaid diagram;
- an image with a caption;
- a footnote-heavy page.

Use the normal example build command so refreshed PDFs can be committed with the
same patch that changes print behavior:

```bash
bash scripts/build_examples.sh
```
