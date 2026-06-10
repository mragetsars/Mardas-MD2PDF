# Changelog

All notable changes to Mardas MD2PDF are tracked here.

## 1.6.1 - 2026-06-10

### Fixed

- Tuned dark appearance surfaces per style so `modern`, `github`, `textbook`, and `academic` keep distinct dark backgrounds instead of sharing one generic navy surface.
- Aligned dark cover pages with their content surfaces, including the nearly black `textbook` dark output.
- Tinted light cover decorations with the selected palette so palette changes are visible on the cover as well as content pages.

### Added

- Added an appearance matrix audit helper for rendering every `style × palette × mode` combination after visual-system changes.

## 1.6.0 - 2026-06-10

### Changed

- Replaced the older visual controls with one appearance model built from `--style`, `--palette`, and `--mode`.
- Removed the parallel `--theme` and `--profile` CLI options so the public interface stays small and predictable.
- Updated Studio to expose style, palette, and mode controls directly and to copy the new CLI syntax.

### Added

- Added an appearance registry with built-in styles, palettes, mode validation, and list commands.
- Added `docs/APPEARANCE.md` to document the new visual model and front-matter format.

### Documentation

- Refreshed README, English guide, Persian guide, helper scripts, CI smoke commands, and generated guide PDFs for the new appearance workflow.

## 1.5.7 - 2026-06-10

### Fixed

- Validated CLI and Studio page-size values so typos fail early instead of silently falling back to A4.
- Added structured Studio validation for TOC depth, watermark opacity, direction, and boolean render options.
- Blocked remote `http(s)` image assets by default, with an explicit `--allow-remote-assets` opt-in for trusted documents.
- Replaced blocked or missing images with visible placeholders in the generated PDF.
- Added print-fit handling for wide tables and improved theme-aware watermark layering.
- Honored `SOURCE_DATE_EPOCH` for deterministic PDF metadata and example guide builds.

### Documentation

- Documented the post-audit hardening fixes, remote asset boundary, deterministic guide builds, and Studio validation errors.

## 1.5.6 - 2026-06-10

### Fixed

- Improved Studio render error responses with stable JSON error codes and clearer client-side messages.
- Added a warning when the Studio server binds to a non-local host.
- Persisted Studio workspace settings and local drafts in browser local storage, with a reset control and keyboard shortcuts for common actions.

### Documentation

- Documented the polished Studio workflow in the README and user guides.

## 1.5.5 - 2026-06-10

### Added

- Added PDF viewer outline bookmarks generated from Markdown headings.
- Added an optional Chromium PDF smoke test that verifies rendered PDF metadata and outline entries.

### Documentation

- Documented PDF outline navigation in the README and user guides.

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
