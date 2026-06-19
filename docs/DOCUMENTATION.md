# Documentation System

This document defines how Mardas MD2PDF documentation is organized and kept release-ready.

## Goals

The documentation has three jobs:

1. help users install and run the converter;
2. explain the renderer, Studio, security, appearance, branding, and PDF output behavior;
3. act as a reproducible rendering sample for English, Persian, RTL/LTR, math, code, Mermaid, local images, tables, footnotes, page flow, and PDF navigation.

Because the English and Persian guides are both user guides and live rendering samples, changes to renderer behavior should update the guide source and regenerated guide PDFs in the same release patch.

## Documentation map

| File | Purpose | Release responsibility |
| :--- | :--- | :--- |
| `README.md` | Short project introduction, core capabilities, and quick start. | Keep concise and link to long-form docs. |
| `docs/README.md` | Index for long-form documentation. | Add links whenever a new reference document is introduced. |
| `docs/guides/GUIDE.en.md` | English user guide and rendering sample. | Must start with valid YAML front matter. |
| `docs/guides/GUIDE.fa.md` | Persian user guide and rendering sample. | Must start with valid YAML front matter and preserve RTL examples. |
| `docs/CHANGELOG.md` | Version-by-version release history. | Keep entries in descending version order. |
| `docs/RELEASE.md` | Release checklist. | Update when release mechanics change. |
| `docs/MAINTENANCE.md` | Routine local checks and build workflow. | Update when scripts or CI gates change. |
| `docs/SECURITY.md` | Trusted/untrusted input boundaries. | Update when renderer or asset handling security changes. |
| `docs/APPEARANCE.md` | Style, palette, and mode reference. | Update when appearance choices or audit rules change. |
| `docs/BRANDING.md` | Cover branding and organization branding reference. | Update when cover/branding behavior changes. |
| `docs/STUDIO.md` | Studio workflow and GUI behavior. | Update when Studio layout, preview, or export behavior changes. |
| `docs/MARKDOWN-FIDELITY.md` | Markdown feature support and edge-case behavior. | Update when parser/renderer fidelity changes. |
| `docs/PDF-NAVIGATION.md` | Visible TOC, PDF outline, destinations, and metadata. | Update when TOC/bookmark behavior changes. |
| `docs/PDF-TYPOGRAPHY.md` | Print flow, captions, footnotes, media samples, and visual audit rules. | Update when PDF layout behavior changes. |
| `docs/PERSIAN-RTL.md` | Persian/RTL authoring rules, mixed text, numbers, captions, and RTL tables. | Update when bidi, Persian, table, caption, or numeric behavior changes. |

## Guide policy

The guide files must remain valid Markdown documents with valid YAML front matter at byte zero:

```text
---
title: ...
...
---
```

Do not place explanatory prose before the front matter. Doing so prevents metadata extraction and causes the guide cover to fall back to generic values such as `Generated Document`.

The guides intentionally contain a compact feature checklist and live examples. Keep those examples focused. If a renderer feature needs a dense stress test, use an external/manual audit artifact rather than turning the public guide into an overloaded test fixture.

### Guide coverage policy

The English and Persian guides are treated as release-facing smoke samples. When a renderer feature changes visible output, the guide source should either include a concise live sample or explicitly point to the focused reference document that carries the sample. The guide should cover at least these areas over time:

- cover metadata and branding;
- generated table of contents and PDF outline behavior;
- mixed Persian/English prose and inline code;
- MathJax inline and display formulas;
- fenced, indented, numbered, titled, and highlighted code blocks;
- Mermaid flowcharts;
- local Markdown images and safe HTML images;
- semantic captions for figures, tables, code listings, and diagrams;
- RTL tables, mixed numerals, Persian punctuation, and generated labels;
- footnotes, backlinks, page breaks, running footers, and page labels.

Keep each live sample compact. Public guides should remain readable documentation first, while still exercising the renderer with representative cases.

## Changelog policy

`docs/CHANGELOG.md` is the release ledger. Keep it structured as:

```text
# Changelog

All notable changes...

## x.y.z - YYYY-MM-DD

### Added / Changed / Fixed / Documentation / Tests

- Concrete user-visible or maintainer-visible change.
```

Rules:

- entries are sorted newest to oldest;
- each version appears once;
- generated guide PDF refreshes belong in the same release patch as the source change;
- development/audit artifacts should not be committed unless they are intended as permanent tooling;
- when a release patch changes user-facing behavior, bump version metadata and refresh the guide PDFs through `scripts/build_examples.sh`.

## Historical changelog reconstruction

The detailed pre-`1.5.0` changelog entries are reconstructed from the public baseline, early project documentation, and the feature set that existed before structured release notes began. They are not intended to imply that every older milestone was tagged as a published GitHub release. Keep the reconstruction conservative:

- describe capabilities that are visible in the baseline code or documentation;
- avoid inventing external release dates, distribution channels, or user counts;
- keep uncertain history under `Notes` rather than `Added` or `Fixed`;
- prefer broad version-shaped milestones such as `1.4.0` GUI baseline or `1.3.0` Markdown feature expansion when exact early patch tags are unavailable.

## Local verification

Before publishing documentation or PDF-output changes, run the normal project checks after installing development dependencies:

```bash
pip install -e .[dev]
python -m pytest -q
MARDAS_RENDER_SMOKE=1 bash scripts/check.sh
bash scripts/build_examples.sh
bash scripts/build_dist.sh
```

For guide-specific issues, visually inspect at least:

- the cover page;
- table of contents pages;
- one code-heavy page;
- one Mermaid page;
- one image/media page;
- the final footnote/checklist page;
- the same areas in the Persian guide.

- `docs/VISUAL-QA.md` documents the visual QA artifact scripts and CI upload workflow.
