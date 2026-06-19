# Changelog

All notable changes to Mardas MD2PDF are tracked here.

The project follows semantic versioning for user-visible behavior. Patch releases may include documentation, generated guide PDF refreshes, regression tests, and narrowly scoped renderer/Studio fixes.

## 1.8.9 - 2026-06-15

### Fixed

- Restored the official English and Persian guide front matter so cover pages again use the intended project title, subtitle, authors, branding, metadata, and full guide-cover layout.
- Removed stray TOC-navigation prose from the YAML front matter of both guides and collapsed duplicated TOC navigation paragraphs in the body.
- Reorganized the changelog into a strictly descending, version-by-version history with complete Phase 11 entries.

### Documentation

- Added `docs/DOCUMENTATION.md` to define the documentation map, guide-as-sample policy, changelog rules, and release documentation workflow.

### Tests

- Added documentation integrity checks for guide front matter, duplicate TOC notes, and changelog ordering.

## 1.8.8 - 2026-06-15

### Fixed

- Completed the Phase 11 visual audit pass for Mermaid label extraction, guide media consistency, and RTL/LTR code isolation.
- Replaced stroked Mermaid edge-label halos with background label chips so PDF text extraction no longer duplicates edge-label glyphs.
- Ensured the public guide Markdown points to document-local SVG assets instead of blocked `README.png` placeholders.

## 1.8.7 - 2026-06-14

### Fixed

- Polished the official guide PDF media audit by synchronizing the documented image snippets with the SVG assets rendered in the live samples.
- Fixed the architecture SVG heading so its leading text is not clipped in generated guide PDFs.
- Collapsed duplicated visible-TOC navigation notes in the English and Persian guides.

## 1.8.6 - 2026-06-14

### Fixed

- Replaced blocked guide image placeholders with document-local SVG assets so the official English and Persian PDF examples demonstrate the successful local-image path.
- Cleaned guide media examples so semantic figure captions and safe HTML images are visible in generated guide PDFs without relying on parent-directory or root-level assets.

## 1.8.5 - 2026-06-14

### Fixed

- Polished PDF footnote references so repeated references use stable numeric markers and unresolved references remain visible instead of becoming broken links.
- Improved printed footnote layout with explicit markers, body content, back-reference links, and page-flow rules that reduce awkward footnote splitting.

### Tests

- Added regression coverage for repeated footnote references, unresolved footnote references, and footnote print CSS.

## 1.8.4 - 2026-06-14

### Fixed

- Polished Chromium PDF running footers with bidi-safe document titles, compact running metadata, localized page labels, and style-aware footer rules.
- Added PDF page labels so viewer page numbering restarts cleanly after a cover page while preserving cover pages as separate front matter.

## 1.8.3 - 2026-06-14

### Fixed

- Promoted common image and table caption patterns into semantic print blocks so captions stay attached to their figure or table in generated PDFs.
- Added consistent caption classes for figures, tables, code listings, and Mermaid diagrams, with print CSS that prevents captions from orphaning away from their associated content.

### Documentation

- Expanded `docs/PDF-TYPOGRAPHY.md` with caption and semantic print-block guidance for English and Persian documents.

### Tests

- Added regression coverage for image captions, table captions, code listing captions, Mermaid diagram captions, and caption-specific print CSS.

## 1.8.2 - 2026-06-14

### Fixed

- Improved PDF print-flow rules so headings stay with following content, paragraphs use orphan/widow protection, and figures, callouts, math displays, Mermaid diagrams, and image placeholders avoid awkward page splits.
- Marked long code blocks and long/wide tables with print-flow hints so compact blocks stay together while large technical blocks can split cleanly instead of leaving large blank pages.

### Documentation

- Added `docs/PDF-TYPOGRAPHY.md` to document print-flow rules, long-code behavior, long-table behavior, and the visual audit checklist for generated PDFs.

### Tests

- Added regression coverage for long code/table print-flow classes and the injected print typography CSS.

## 1.8.1 - 2026-06-14

### Fixed

- Rewrote visible PDF table-of-contents link annotations to explicit heading destinations so printed TOC entries keep working after pypdf metadata writes and cover/content merges.
- Kept PDF viewer outline/bookmarks and visible TOC links bound to the same real heading coordinates instead of relying on viewer-specific named-destination resolution.

### Tests

- Added regression coverage that verifies copied visible TOC link annotations are converted from named destinations to explicit PDF destination arrays.

## 1.8.0 - 2026-06-14

### Fixed

- Preserved Chromium named destinations when pypdf writes metadata or merges cover/content PDFs, restoring clickable table-of-contents links in final PDFs.
- Rebuilt PDF viewer outlines from the same heading IDs used by visible TOC links, so bookmarks jump to real content headings instead of matching TOC rows.
- Added regression coverage for duplicate headings, Persian heading anchors, named destinations, and generated PDF outlines.

### Documentation

- Added `docs/PDF-NAVIGATION.md` and refreshed guide metadata for the PDF navigation fix.

## 1.7.0 - 2026-06-13

### Added

- Improved Markdown feature fidelity for advanced fenced-code metadata, including titles, line numbers, line highlights, aliases, and custom starting line numbers.
- Expanded GitHub/Obsidian-style callout support with additional aliases such as `INFO`, `SUCCESS`, `QUESTION`, `DANGER`, `BUG`, `EXAMPLE`, `QUOTE`, and `ABSTRACT`.
- Added `docs/MARKDOWN-FIDELITY.md` as the dedicated feature reference for supported Markdown syntax and renderer expectations.

### Changed

- Updated the public documentation and guide metadata for the 1.7.0 renderer-fidelity release.

## 1.6.4 - 2026-06-12

### Changed

- Redesigned the Studio sidebar into clear Document, Appearance, Branding, Layout, and Advanced sections.
- Replaced raw style, palette, mode, and branding dropdowns with visual choice cards while keeping the same backend render options.
- Improved Studio CLI-copy output so branding options are included when selected.
- Polished the Studio toolbar, settings sidebar, editor, preview status, and status bar for a clearer daily writing workflow.
- Replaced static Studio view-mode buttons with draggable/resizable panes and an auto-collapsing settings sidebar.
- Retuned the Studio interface to pure light/dark surfaces with thin custom scrollbars and higher-contrast export-button interaction states.
- Replaced emoji-based Studio controls with inline SVG icons, restored the project logo in the header, and refined micro-interactions for cards, accordions, toolbar buttons, and status counters.
- Tightened Studio sidebar scrolling, compacted palette selection into color swatches, improved logo fitting, and raised dark-mode helper-text contrast.

### Added

- Added `docs/STUDIO.md` to document the refined visual workflow and local-export behavior.
- Added a compact Markdown formatting toolbar, editor line numbers, preview render status, and proportional editor-to-preview scroll sync.

## 1.6.3 - 2026-06-10

### Changed

- Made cover branding explicit with `branding.mode: off`, `subtle`, or `full`.
- Changed the default cover behavior to unbranded output, so ordinary user PDFs no longer show a large Mardas MD2PDF brand block.
- Added custom organization branding through `brand.name`, `brand.logo`, `brand.footer`, and matching CLI/Studio options.

### Documentation

- Added `docs/BRANDING.md` and refreshed the English/Persian guides for the new cover branding workflow.

## 1.6.2 - 2026-06-10

### Fixed

- Removed badge-like cover label backgrounds so `cover_label` text no longer looks like an accidental highlight in Persian or English covers.
- Kept academic appearance accents palette-driven instead of forcing the older warm brown/orange palette across all palette choices.
- Aligned numbered code line gutters with code rows and switched highlighted code rows to the active palette accent surface.

### Added

- Added regression checks for palette-pure academic output, non-badge cover labels, and numbered code alignment CSS.

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

## 1.5.0 and earlier - 2026-05-26

### Added

- Established the core Markdown-to-PDF pipeline: Markdown parsing, structured HTML assembly, print CSS, Playwright/Chromium PDF export, and local CLI usage.
- Added Persian, English, and mixed RTL/LTR document support with direction-aware cover pages, content flow, tables, code blocks, and metadata labels.
- Added professional cover pages, tables of contents, page numbers, local image embedding, GitHub-style task lists and alerts, footnotes, raw HTML sanitization, MathJax formulas, and offline Mermaid flowchart rendering.
- Added the first visual system with GitHub, modern, textbook, and academic output looks, plus Persian-friendly typography and generated PDF guide examples.
- Added the local Studio GUI for browser-based editing, preview-oriented option selection, asset attachment, and PDF export.

### Changed

- Iteratively refined print layout, code block rendering, table behavior, cover metadata, Mermaid sizing, and guide documentation before the structured changelog was introduced.

### Notes

- This entry summarizes the public baseline before the structured changelog began. Later entries are kept version-by-version.
