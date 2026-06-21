# PDF Typography and Print-Flow Contract

The guides teach page flow, margins, code blocks, tables, captions, images, safe HTML, watermarks, footnotes, and final publishing checks. This file records the layout invariants that maintainers should preserve.

## User-facing source of truth

- Guide sections: `Page Flow and Layout`, `Code Blocks`, `Images and Safe HTML`, `Watermarks`, `Footnotes`, and `Final Publishing Checklist`.
- Generated guide PDFs are the official print samples.

## Page-flow goals

- Headings should stay with the first meaningful block that follows.
- Ordinary paragraphs should avoid orphan/widow lines where Chromium print layout permits it.
- Long code blocks and wide/large tables may split when keeping them together would waste excessive page space.
- Captions should remain attached to their associated semantic block.

## Captions and semantic print blocks

The renderer normalizes captions for figures, tables, code listings, and Mermaid diagrams. This gives print CSS a semantic target for page-break rules.

## Code blocks

Code blocks must preserve:

- monospaced alignment;
- line numbers aligned with code rows;
- highlighted-line indentation and rhythm;
- Persian/Arabic script fallback when code samples contain RTL text;
- long-block continuation without a large blank page.

## Tables

Tables must preserve readable headers, cell direction, mixed numerals, and wide-table print fitting. RTL-specific behavior belongs to the Persian/RTL contract, but page-flow behavior belongs here.

## Guide media samples

The guide media samples intentionally exercise both Markdown image embedding and safe HTML images. The `Images and Safe HTML` guide section must keep at least one document-local image example and one safe HTML image example. blocked placeholders should remain visible for unsafe or missing image paths during negative tests.

## Final guide consistency checks

Before releasing typography or layout changes, rebuild the guide PDFs and inspect:

- cover;
- TOC;
- a code-heavy page;
- a Mermaid page;
- a table-heavy page;
- image/media examples;
- footnotes and final checklist;
- the same areas in the Persian guide.

## Audit checklist

```bash
python -m pytest -q tests/test_pdf_print_typography.py
MARDAS_TIMEOUT_MS=600000 bash scripts/build_examples.sh
python scripts/check_pdf_preflight.py examples/GUIDE.en.pdf examples/GUIDE.fa.pdf --pages 1,2 --timeout 60
```

For appearance changes, add a visual matrix sample:

```bash
python scripts/run_visual_qa_matrix.py --output-dir build/visual-qa/typography --max-cases 1 --render-png --clean
```

## Caption audit checks

Caption changes should verify code, table, image, and diagram captions, including RTL captions in the Persian guide.

## Running footers and page labels

Running footers should remain unobtrusive, direction-aware, and consistent with cover/content page-label behavior.

## Footnotes and reference polish

Footnotes must keep references, repeated-reference backlinks, and RTL/Persian punctuation readable.

## Historical notes

Version 1.8.6 guide media audit and Phase 11 visual audit closure established the current policy that guide media must be document-local, lightweight, and intentionally used by official examples.
