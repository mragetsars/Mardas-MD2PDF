# Project Documentation

This directory uses a **guide-first documentation model**.

The complete user-facing manual is the guide pair in `docs/guides/`. Those guides are also live renderer samples: they teach the feature, show runnable Markdown examples, and are rebuilt into the official PDFs under `examples/`.

The other documents in this directory are intentionally **maintenance references**. They should not become a second user manual. They record implementation contracts, QA commands, asset ownership, release gates, and security boundaries that maintainers need when changing the renderer, Studio, packaging, or release workflow.

## Canonical user guides

- [English guide](./guides/GUIDE.en.md) — canonical English user manual and live rendering sample.
- [راهنمای فارسی](./guides/GUIDE.fa.md) — canonical Persian user manual and RTL/Persian live rendering sample.

Generated PDF versions are stored in `examples/GUIDE.en.pdf` and `examples/GUIDE.fa.pdf`.

## Maintainer and release operations

- [Changelog](./CHANGELOG.md) — version-by-version release ledger.
- [Release checklist](./RELEASE.md) — release gate, build, tag, and artifact workflow.
- [Maintenance workflow](./MAINTENANCE.md) — routine local checks, build examples, distribution build, and patch hygiene.
- [Security policy](./SECURITY.md) — trust boundaries for Markdown, HTML, assets, Studio, Chromium, and PDF metadata.
- [Documentation system](./DOCUMENTATION.md) — ownership policy for guides, reference notes, changelog, and generated examples.

## Maintenance references for feature areas

These files support the guide; they do not replace it.

- [Appearance maintenance notes](./APPEARANCE.md)
- [Cover branding and asset contract](./BRANDING.md)
- [Markdown fidelity parser contract](./MARKDOWN-FIDELITY.md)
- [PDF navigation contract](./PDF-NAVIGATION.md)
- [PDF typography and print-flow contract](./PDF-TYPOGRAPHY.md)
- [Persian and RTL quality](./PERSIAN-RTL.md)
- [Studio workflow contract](./STUDIO.md)
- [Visual QA system](./VISUAL-QA.md)

## Rule of thumb

When writing for users, update the guides. When documenting an invariant that prevents regressions, update the relevant maintenance reference and add or update tests.
