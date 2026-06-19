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


## Captions and semantic print blocks

The renderer treats visual blocks as semantic print units so captions stay with
the content they describe:

- Markdown image plus adjacent caption paragraphs become `<figure class="md2pdf-figure">`
  with `.md2pdf-caption--figure`;
- tables can use native `<caption>` elements, or an adjacent paragraph such as
  `Table 1. Results` / `جدول ۱. نتایج`, which is promoted to
  `.md2pdf-caption--table`;
- fenced code titles, filenames, and captions become `.md2pdf-caption--code`;
- Mermaid titles become `.md2pdf-caption--diagram`.

Caption prefixes are intentionally conservative. Ordinary prose is left alone,
while common English and Persian labels such as `Figure`, `Fig.`, `Table`,
`Listing`, `Diagram`, `شکل`, `تصویر`, `جدول`, `کد`, and `نمودار` are recognized.

Print CSS keeps captions from orphaning away from their figure, code listing,
table, or diagram. Table captions use native `caption-side: top` so browser PDF
engines can keep the caption inside the table flow.

## Code blocks

Code blocks are semantic `<figure class="code-block">` elements. During Markdown
post-processing, Mardas records the number of source lines as `data-lines` and
adds print-flow classes for medium and long snippets.

Short code blocks use `break-inside: avoid`; medium code blocks become denser
without forcing a page split; long code blocks use `break-inside: auto` so they
can continue on the next page. Captions still use `break-after: avoid` so the
caption is not orphaned from the code that follows.

The print-density classes are intentionally tiered:

```text
code-block--medium    # 18+ source lines; compact spacing, still kept together where practical
code-block--long      # 36+ source lines; may split to avoid sparse pages
code-block--very-long # 90+ source lines; densest listing treatment
```

## Tables

Tables are wrapped in `.table-wrap`. The wrapper records column and row counts
as `data-md2pdf-columns` and `data-md2pdf-rows` so print rules can distinguish
ordinary tables from compact, medium, wide, or long ones.

Normal tables try to stay together. Medium, wide, and long tables may break
across pages at row boundaries, but rows keep `break-inside: avoid` to prevent
split cells. The medium tier exists to avoid moving a moderately tall table to a
mostly empty page.

```text
table-wrap--compact    # 6+ columns or 12+ rendered rows; tighter cell spacing
table-wrap--medium     # 10+ rendered rows; may split at row boundaries
table-wrap--wide       # 8+ columns
table-wrap--very-wide  # 12+ columns
table-wrap--long       # 18+ rendered rows
```

Wide or tall Mermaid diagrams also receive compact print spacing and smaller
maximum heights so diagram-heavy pages remain dense without clipping the SVG.


## Guide media samples

The official English and Persian guides should render at least one real local
image and one safe HTML image instead of only showing blocked placeholders. Guide
image references stay inside `docs/guides/images/` so they exercise the same
trusted document-local asset boundary used by ordinary Markdown files.

When auditing a generated guide PDF, the Images and Safe HTML section should show
an embedded architecture diagram with a figure caption, followed by a compact
logo image rendered through safe HTML. Blocked placeholders are still tested in
the automated suite, but the public guide examples should demonstrate the
successful path first.


## Final guide consistency checks

The generated guide PDFs are treated as the public visual samples for this
project. After a print-polish patch, audit them for consistency as well as
correctness:

- guide image examples should use the same document-local assets that the PDF
  actually renders;
- example snippets should not drift from the live sample immediately below them;
- duplicated release notes or navigation notes should be collapsed into one
  clear paragraph;
- SVG sample diagrams should keep all labels inside the viewBox so text is not
  clipped at the page edge;
- refreshed `examples/GUIDE.en.pdf` and `examples/GUIDE.fa.pdf` should be
  committed with the same patch that changes guide-facing output.

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

## Caption audit checks

When reviewing generated PDFs after caption changes, check these cases in both
English and Persian guides when they are present:

- image followed by `Figure` / `شکل` caption text;
- table followed or preceded by `Table` / `جدول` caption text;
- fenced code blocks with `title`, `filename`, or `caption` metadata;
- Mermaid fences with titles;
- captions near a page boundary, so they do not separate from the visual block.

## Running footers and page labels

Mardas MD2PDF keeps the cover separate from numbered content pages, then adds a compact running footer to content pages only.  The footer is bidi-safe: mixed Persian/English titles are isolated from the page counter, and the page label is localized when the document language is Persian.

The footer may include a short running metadata line from front matter, preferring course or institution plus version, status, and date.  PDF viewer page labels are also written so content numbering restarts after a cover page while the cover remains part of the PDF file.

## Footnotes and reference polish

Footnote references are rendered as stable numeric markers instead of raw authoring identifiers. Repeated references to the same note receive distinct back-reference anchors, while the note itself remains a single endnote entry. Unresolved references stay visible as plain text instead of becoming broken PDF links.

The print stylesheet aligns markers, note bodies, and back-reference arrows in a three-column grid. The footnote section avoids poor page splits where possible, while nested Markdown inside a note keeps its own direction and list spacing.

## Version 1.8.6 guide media audit

The English and Persian guide PDFs now exercise the successful document-local image path with `docs/guides/images/architecture.svg` and `docs/guides/images/logo.svg`. The blocked-image placeholder remains covered by tests and troubleshooting text, while the public examples show a real semantic figure and a safe HTML image.

## Phase 11 visual audit closure

The Phase 11 guide PDFs should be reviewed as release-facing samples, not just as generated artifacts. The final visual pass checks these areas:

- Mermaid edge labels should be visually readable and should not duplicate characters when text is extracted from the PDF.
- Guide media examples should render document-local SVG assets instead of blocked placeholders.
- RTL documents should keep code, CLI flags, file names, and inline technical identifiers isolated from surrounding Persian text.
- Captions, footnotes, running footers, TOC links, and PDF outline entries should stay synchronized after regenerated examples are committed.

Audit artifacts may be built in `build/` during release checks, but the project should not gain permanent sample files solely for one-off visual audits.
