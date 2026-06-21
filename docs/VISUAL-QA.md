# Visual QA System

The guides teach what users should inspect visually. This file records the maintainer-facing visual QA artifact workflow. Visual QA outputs belong under `build/visual-qa/` or another `build/` subdirectory and must not be committed.

## User-facing source of truth

- The guide sections `PDF Preflight Checks`, `Final Publishing Checklist`, `Appearance`, `Code Blocks`, `Mermaid Flowcharts`, `Images and Safe HTML`, and `GUI Workflow` explain what the user sees.
- This file explains which scripts generate temporary audit artifacts.

## Appearance matrix

```bash
python scripts/audit_appearance_matrix.py --output-dir build/visual-qa/appearance --render-png --resume
```

Use this after style, palette, mode, code-block, Mermaid, table, or callout visual changes.

## PDF feature smoke audit

```bash
python scripts/audit_pdf_features.py --output-dir build/visual-qa/features --render-png --resume
```

Use this for feature-heavy renderer changes across code, Mermaid, images, tables, footnotes, watermarks, and TOC behavior.

## Chunked full-matrix runner

```bash
python scripts/run_visual_qa_matrix.py --output-dir build/visual-qa/matrix --max-cases 1 --render-png --clean
```

Use the chunked runner when the full matrix is too slow for one process. Increase cases only when the environment can handle it.

## PDF preflight

```bash
python scripts/check_pdf_preflight.py examples/GUIDE.en.pdf examples/GUIDE.fa.pdf --pages 1,2 --timeout 60
```

Preflight checks text extraction, PDF opening, selected pages, metadata, and basic structural health. It does not replace human visual inspection.

## Snapshot comparison

```bash
python scripts/compare_visual_snapshots.py --baseline build/visual-qa/baseline --candidate build/visual-qa/candidate
```

Snapshot comparison is useful after typography or layout changes, but differences still need human interpretation.

## Studio visual smoke

```bash
python scripts/audit_studio_visual.py --output-dir build/visual-qa/studio --timeout 30 --clean
```

Use this after Studio layout, preview, asset, or workflow changes.

## CI artifacts

The CI workflow uploads Visual QA artifacts so failures can be inspected without committing generated PNG/PDF audit outputs. Artifact directories should remain under `build/visual-qa/` or another ignored `build/` path.

## Repository hygiene

- `build/visual-qa/` and other audit outputs are temporary.
- Visual QA artifacts must not be committed.
- Generated guide PDFs are the only release-facing generated PDF examples, and they are rebuilt intentionally through `scripts/build_examples.sh`.
