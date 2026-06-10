# Changelog

All notable changes to Mardas MD2PDF are tracked here.

## 1.5.4 - 2026-06-10

### Added

- Added reusable maintenance scripts for local checks, guide PDF generation, and Python distribution builds.
- Added a release artifact workflow for tagged builds that uploads Python distributions and regenerated guide PDFs.
- Added release metadata tests to keep version strings, guide metadata, changelog entries, and maintenance scripts in sync.

### Documentation

- Documented the maintenance workflow and updated the release checklist to use the shared scripts.

## 1.5.3 - 2026-06-10

### Fixed

- Blocked unresolved local image sources with a transparent placeholder so Chromium cannot read parent-directory, absolute, missing, or oversized image paths through the document base URL.
- Restricted safe raw-HTML `data:` image URLs to common raster formats and rejected obfuscated URL control characters.
- Made Chromium sandbox mode configurable with `--chromium-sandbox auto|on|off`, keeping sandboxing on for normal users while preserving root/container compatibility.

### Documentation

- Added `SECURITY.md` and documented trusted input boundaries in the README and guides.

## 1.5.2 - 2026-06-10

### Fixed

- Hardened local Markdown image embedding so document-local images still work, while absolute paths, `file:` URLs, parent-directory escapes, and current-working-directory fallbacks are no longer embedded silently.
- Limited Mardas MD2PDF Studio render payloads, Markdown size, asset count, per-asset size, and total attached asset size.

### Added

- Added GitHub Actions CI for linting, pytest, and a Chromium render smoke test.
- Added a release checklist for consistent version bumps, generated examples, tags, and release notes.

### Documentation

- Documented the local-image trust boundary and GUI asset limits.
- Documented the CI and release workflow used to keep patch sets and releases consistent.

## 1.5.1 - 2026-05-26

### Changed

- Bumped the project to version 1.5.1 after progress feedback and Mermaid print-safety work.
- Refreshed the generated guide PDF examples.
