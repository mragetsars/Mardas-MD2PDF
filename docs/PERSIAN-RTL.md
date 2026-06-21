# Persian and RTL Quality Contract

The English and Persian guides are user manuals and live smoke samples. The Persian guide is the canonical user-facing tutorial and live RTL/Persian rendering sample. This file records the implementation and release contract for bidi, mixed-script, numbers, punctuation, tables, captions, navigation, and footnotes.

## User-facing source of truth

- `docs/guides/GUIDE.fa.md` teaches Persian/RTL usage and contains the official live samples.
- `docs/guides/GUIDE.en.md` also includes a compact Persian/RTL smoke sample to ensure mixed-language output works in an English document shell.

## Direction model

Direction is resolved from CLI options, front matter fields, language defaults, and body detection. The renderer emits direction-aware classes so CSS and tests can verify behavior:

- `md2pdf-rtl-text`
- `md2pdf-ltr-text`
- `mixed-script`
- `mixed-numeral`
- `persian-numeral`
- `rtl-ascii-punctuation`

## Mixed Persian/English prose

Latin technical identifiers inside Persian prose must be isolated without changing author text. The author text remains unchanged; isolation is a rendering aid, not a content rewrite.

## Numbers

Persian and Latin numerals may appear in the same sentence or table cell. The renderer must preserve readability and emit `mixed-numeral` / `persian-numeral` hooks where appropriate.

## Punctuation

ASCII punctuation in RTL prose should not visually jump to the wrong side of the phrase. Use `rtl-ascii-punctuation` hooks and focused tests when changing punctuation handling.

## Tables

Persian tables should receive table-level and cell-level direction hooks:

- `table-wrap--rtl`
- `table-wrap--mixed-direction`
- `table-cell--rtl`
- `table-cell--ltr`
- `table-cell--mixed`
- `table-cell--mixed-rtl`

Mixed cells in Persian documents should prefer an RTL base direction while keeping Latin identifiers isolated.

## Captions and figures

Persian captions should remain readable and attached to their content. Relevant hooks include `md2pdf-caption--persian`, `md2pdf-caption--rtl`, and semantic caption classes for figures, tables, code, and diagrams.

## Persian navigation and references

Generated TOC numbers and PDF outline titles must remain readable in RTL output. Watch for:

- `persian-generated-number`
- `toc-list--nested`
- mixed-script headings;
- footer direction;
- page-label text.

## Persian footnotes, captions, and footer audit hooks

Footnotes must preserve RTL paragraph flow and backlinks. The renderer should expose hooks such as `footnotes--rtl` and use logical properties such as `border-inline-start` where practical.

## Persian table and TOC visual audit

The Persian guide must be inspected visually whenever table direction, TOC generation, heading numbering, captions, or footer text changes.

## Guide live-sample coverage

The guides should contain live samples for:

- Persian punctuation;
- Latin/Persian numerals;
- RTL tables;
- mixed-script TOC headings;
- captions;
- footnote backlinks;
- inline code and technical identifiers.

## Persian/RTL release contract

Before releasing a Persian/RTL-visible change, run:

```bash
python -m pytest -q tests/test_persian_rtl_quality.py
MARDAS_RENDER_SMOKE=1 bash scripts/check.sh
MARDAS_TIMEOUT_MS=600000 bash scripts/build_examples.sh
```

Then inspect the Persian guide cover, TOC, tables, code blocks, captions, Mermaid diagrams, footnotes, and final checklist.

## Verification checklist

- Persian text is not reversed.
- Latin identifiers remain readable.
- Mixed numerals remain stable.
- RTL tables use the correct base direction.
- Captions and footnote backlinks remain attached and readable.
- Generated labels and footer text do not fall back to English unless intended.

## Release closeout history

The 1.10.x baseline closes the focused Persian/RTL quality pass: heading IDs, footnote anchors, PDF destinations, and back-links remain deterministic while official guide samples stay compact and readable. Future Persian/RTL changes should update the guide samples only when they improve user education or release-facing smoke coverage.
