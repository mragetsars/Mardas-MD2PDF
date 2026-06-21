# Documentation System

Mardas MD2PDF documentation follows a **guide-first** model: the English and Persian guides are the canonical user manuals, the official feature walkthroughs, and live rendering samples. Supporting docs under `docs/` are maintainer references and QA contracts, not parallel tutorials.

## Goals

The documentation has four jobs:

1. teach users how to install, configure, and use the converter;
2. demonstrate every user-facing renderer feature with real Markdown samples;
3. preserve QA/release contracts for implementation maintainers;
4. keep generated guide PDFs reproducible and visually reviewable.

## Documentation map

| File | Ownership | Release responsibility |
| :--- | :--- | :--- |
| `README.md` | Project landing page, short overview, quick start, and links. | Keep concise; link to the guides and maintainer references. |
| `docs/README.md` | Directory index for the guide-first documentation model. | Update whenever docs are added, removed, or reclassified. |
| `docs/guides/GUIDE.en.md` | Canonical English user manual and live rendering sample. | Must fully teach user-facing features and start with valid YAML front matter. |
| `docs/guides/GUIDE.fa.md` | Canonical Persian user manual and RTL/Persian live rendering sample. | Must mirror user-facing coverage while preserving Persian readability and RTL samples. |
| `examples/GUIDE.en.pdf` | Generated English guide PDF. | Rebuild with `scripts/build_examples.sh`; never hand-edit. |
| `examples/GUIDE.fa.pdf` | Generated Persian guide PDF. | Rebuild with `scripts/build_examples.sh`; visually inspect RTL output. |
| `docs/CHANGELOG.md` | Release ledger. | Keep descending, accurate, and free of roadmap entries. |
| `docs/RELEASE.md` | Release checklist and artifact workflow. | Update when release mechanics or gates change. |
| `docs/MAINTENANCE.md` | Routine local checks, examples, distributions, and patch hygiene. | Update when scripts or local QA workflow changes. |
| `docs/SECURITY.md` | Trust boundaries and reporting. | Update when input, HTML, asset, Studio, sandbox, or metadata security changes. |
| `docs/APPEARANCE.md` | Appearance implementation contract. | User tutorial lives in the guides; this file records options, tokens, and QA rules. |
| `docs/BRANDING.md` | Cover branding and logo asset contract. | User tutorial lives in the guides; this file records asset ownership and packaging policy. |
| `docs/MARKDOWN-FIDELITY.md` | Markdown parser/renderer fidelity contract. | User tutorial lives in the guides; this file records grammar, aliases, and edge cases. |
| `docs/PDF-NAVIGATION.md` | TOC, outline, destination, metadata, and link QA contract. | User tutorial lives in the guides; this file records verification and debugging rules. |
| `docs/PDF-TYPOGRAPHY.md` | Print-flow, captions, footnotes, media, and page layout contract. | User tutorial lives in the guides; this file records regression-prone layout invariants. |
| `docs/PERSIAN-RTL.md` | Persian/RTL quality contract. | User tutorial lives in the guides; this file records bidi, numeric, table, and release invariants. |
| `docs/STUDIO.md` | Studio behavior contract. | User tutorial lives in the guides; this file records GUI state, preview, export, and asset boundaries. |
| `docs/VISUAL-QA.md` | Visual QA artifact workflow. | User tutorial lives in the guides; this file records scripts, output directories, and CI artifact rules. |

## Guide coverage policy

The guide files must remain valid Markdown documents with valid YAML front matter at byte zero:

```text
---
title: ...
...
---
```

Do not place explanatory prose before the front matter. Doing so prevents metadata extraction and causes the guide cover to fall back to generic values such as `Generated Document`.

The guides are the canonical place for feature education and examples. They should cover at least these areas:

- installation and first PDF workflow;
- front matter, cover metadata, branding, and watermarks;
- language selection, direction, Persian/RTL behavior, mixed text, punctuation, and numerals;
- table of contents, PDF outline/bookmarks, metadata, page labels, and running footers;
- Markdown feature support, GitHub-style alerts, details, links, lists, tables, and page breaks;
- MathJax formulas;
- fenced, indented, titled, numbered, highlighted, and advanced code blocks;
- Mermaid flowcharts with node and edge labels;
- local images, safe HTML images, blocked placeholders, and semantic captions;
- page flow, margins, page sizes, wide tables, code blocks, captions, footnotes, and final checklist;
- Studio GUI workflow, CLI workflow, automation, and preflight checks.

### Reference-document rule

The focused files such as `docs/APPEARANCE.md`, `docs/PDF-TYPOGRAPHY.md`, and `docs/PERSIAN-RTL.md` must not duplicate the complete guide narrative. They should contain:

- a link back to the canonical guide section;
- the implementation contract or parser/renderer invariant;
- release/QA commands and artifacts;
- notes that explain why a regression test exists.

If a detail is helpful for ordinary users, put it in the guide. If it is mainly useful to prevent a future regression, keep it in the focused reference and add a test.

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

`docs/VISUAL-QA.md` documents the visual QA artifact scripts and CI upload workflow. No roadmap file is part of this documentation set.
