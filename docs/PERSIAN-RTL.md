# Persian and RTL Quality

Mardas MD2PDF is designed for documents that mix Persian prose, English identifiers, code, numbers, formulas, tables, and PDF navigation. This document records the rules used by the renderer to keep that output readable.

## Direction model

The document shell direction is resolved from CLI options, front matter, language metadata, and finally the content itself. Individual content blocks are still profiled after Markdown rendering so mixed documents can use more precise layout hints.

Phase 12 adds deterministic direction classes during HTML post-processing:

| Class | Meaning |
| :--- | :--- |
| `md2pdf-rtl-text` | The block contains RTL strong text only. |
| `md2pdf-ltr-text` | The block contains LTR strong text only. |
| `mixed-script` | The block contains both RTL and LTR strong text. |
| `mixed-numeral` | The block mixes ASCII digits with Persian/Arabic digits. |
| `persian-numeral` | The block contains Persian/Arabic digits only. |
| `latin-numeral` | The block contains ASCII digits only. |
| `persian-punctuation` | The block contains Persian punctuation such as `،`، `؛`، or `؟`. |
| `rtl-ascii-punctuation` | An RTL-dominant block contains ASCII punctuation such as `?`, `,`, or `;` and should be reviewed. |

These classes do not rewrite the author's text. They provide stable CSS hooks for print layout, PDF extraction, and future visual-regression checks.

## Mixed Persian/English prose

Persian documents commonly contain English identifiers such as `Playwright`, `MathJax`, `GitHub Actions`, `PDF`, `HTML`, `CSS`, and version numbers such as `1.9.0`. Keep those identifiers in normal text or inline code. The renderer isolates mixed-script blocks with `unicode-bidi: plaintext` so the visual order stays closer to the author's intent.

Recommended:

```md
در خروجی PDF مقدار `version` و شناسه `MathJax` باید خوانا بمانند.
```

Avoid manually inserting invisible bidi control characters unless you are debugging a very specific viewer issue.

## Numbers

Both Persian and Latin digits are supported. When both appear in one block, the renderer marks the block with `mixed-numeral` and uses tabular numeric shaping in print CSS. Single-style numeric blocks are also classified as `persian-numeral` or `latin-numeral` so future visual tests can distinguish formal Persian prose from technical identifiers.

Recommended:

```md
نسخه 1.9.1 و شماره ۱۴۰۵ باید در یک جمله خوانا بمانند.
```

Use one numeral style consistently in formal final documents when possible, but keep Latin digits for semantic version strings, package versions, command output, and code identifiers.

## Punctuation

Persian punctuation should normally use `،`، `؛`، and `؟`. The renderer does not rewrite author text, but it marks Persian punctuation with `persian-punctuation` and ASCII punctuation inside RTL-dominant text with `rtl-ascii-punctuation`. This gives reviewers and later visual-regression tests a stable way to catch cases where `?` or `;` may need author cleanup.

Recommended:

```md
آیا خروجی PDF آماده است؟ بله، نسخه 1.9.1 پایدار است؛
```

Review manually:

```md
آیا خروجی PDF آماده است? بله، نسخه 1.9.1 پایدار است;
```

## Tables

Tables are profiled by cell direction. A Persian-heavy table receives `table-wrap--rtl`; English-heavy cells receive `table-cell--ltr`; mixed cells receive `table-cell--mixed`. This keeps the table shell RTL while preserving English identifiers and technical values.

Recommended:

```md
| بخش | مقدار | شناسه |
|---|---|---|
| نسخه | version 1.9.1 و ۱.۹.۱ | PDF |
| وضعیت | پایدار | stable |
```

## Captions and figures

Persian captions are detected with prefixes such as `شکل`، `تصویر`، `جدول`، `کد`، and `نمودار`. Captions remain attached to the associated figure, table, code listing, or Mermaid diagram and are isolated for RTL/LTR layout.

Recommended:

```md
![نمودار معماری](images/architecture.svg)

*شکل ۱. نمای کلی معماری.*
```

Caption elements receive caption-specific hooks such as `md2pdf-caption--persian`, `md2pdf-caption--numbered`, `md2pdf-caption--persian-number`, `md2pdf-caption--latin-number`, and `md2pdf-caption--mixed-number` when they include Persian labels, numbers, or technical identifiers.

## Persian navigation and references

Generated navigation labels are owned by the renderer, so Persian documents can localize those generated numbers without rewriting author prose. In `lang: fa` documents, the printed table of contents receives `md2pdf-toc--rtl`, generated section numbers receive `persian-generated-number`, and the visible section number text is shaped with Persian digits. The raw heading IDs and link targets remain stable ASCII/Unicode anchors.

Footnote references and footnote markers also use localized generated numbers in Persian documents. The footnote section receives `footnotes--rtl`, while the backlink IDs remain ASCII-safe and deterministic. PDF viewer page labels keep content numbering restarted after the cover page and use a localized cover prefix such as `جلد ` for Persian output.

These rules affect generated labels only. Version strings, command output, code, filenames, and author-written prose are preserved exactly as written.

## Verification checklist

When changing RTL or Persian output, check these areas in both generated HTML and PDF:

- mixed Persian/English paragraphs;
- inline code inside Persian paragraphs;
- version numbers and Persian/Latin digits;
- Persian punctuation and ASCII punctuation inside RTL text;
- RTL tables with English identifiers;
- Persian captions for images, tables, code, and Mermaid diagrams;
- printed TOC labels and PDF viewer outline labels;
- footnotes and footer page labels.
