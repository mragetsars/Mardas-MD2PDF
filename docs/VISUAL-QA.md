# Visual QA System

Mardas MD2PDF keeps visual review artifacts outside the permanent source tree.
The scripts in this section write audit outputs under `build/visual-qa/` so they
can be inspected locally or uploaded from CI without adding generated PDFs, PNGs,
or screenshots to the repository.

## Appearance matrix

Use the appearance matrix after changing style, palette, mode, cover, print CSS,
or dark-mode behavior:

```bash
python scripts/audit_appearance_matrix.py \
  --output-dir build/visual-qa/appearance \
  --render-png \
  --clean
```

For a smaller CI-sized subset:

```bash
python scripts/audit_appearance_matrix.py \
  --output-dir build/visual-qa/appearance \
  --styles modern,github \
  --palettes blue,slate \
  --modes light,dark \
  --render-png \
  --clean
```

The script writes PDFs, optional PNG page renders, `manifest.json`, and HTML
galleries for cover and content review.

## PDF feature smoke audit

Use the feature smoke audit after changing Markdown parsing, table handling,
code block rendering, Mermaid, MathJax, captions, or mixed RTL/LTR prose:

```bash
python scripts/audit_pdf_features.py \
  --output-dir build/visual-qa/features \
  --render-png \
  --clean
```

The default feature document includes code metadata, table captions, display
math, Mermaid, footnotes, callouts, and Persian mixed-script punctuation.

## Snapshot comparison

When a known-good PNG snapshot exists, compare it with a candidate snapshot:

```bash
python scripts/compare_visual_snapshots.py \
  build/visual-baseline/features/png \
  build/visual-qa/features/png \
  --output-dir build/visual-qa/diff \
  --max-changed-ratio 0.015 \
  --max-rms-delta 4
```

The comparison script uses a dependency-free PNG reader. It writes `summary.json`
and `SUMMARY.md`, then fails if any matched PNG exceeds the configured thresholds.

## CI artifacts

The CI visual QA job intentionally runs a reduced matrix. It uploads
`build/visual-qa/` as an artifact so reviewers can download the rendered PDFs,
PNG pages, manifests, and HTML galleries. Full local audits can still render all
appearance combinations when deeper review is needed.

## Repository hygiene

Generated visual artifacts belong under `build/visual-qa/` and must not be committed. Keep permanent coverage in scripts, tests, and documentation; keep
actual audit outputs disposable.
