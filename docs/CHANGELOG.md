# Changelog

All notable changes to Mardas MD2PDF are tracked here.

The project follows semantic versioning for user-visible behavior. Patch releases may include documentation, generated guide PDF refreshes, regression tests, and narrowly scoped renderer/Studio fixes.

## 1.13.24 - 2026-06-21

### Documentation
- Reorganized the documentation architecture around a guide-first model: the English and Persian guides are now explicitly the canonical user manuals and live renderer samples, while focused docs are maintainer contracts instead of parallel tutorials.
- Rewrote the feature-reference docs for appearance, branding, Markdown fidelity, PDF navigation, PDF typography, Persian/RTL quality, Studio, and Visual QA to reduce guide/reference duplication and clarify ownership.
- Updated the docs index, documentation policy, README documentation map, and guide notes to make the new ownership model visible.

### Tests
- Added documentation-integrity coverage for the guide-first model and the maintainer-contract classification of focused docs.

## 1.13.23 - 2026-06-21

### Documentation
- Corrected the official advanced-code-fence samples so `{2,5-6}` visibly highlights three existing code rows instead of demonstrating an out-of-range range on a four-line snippet.
- Updated the Studio code insertion template and Markdown fidelity guide to use the same six-line sample, making line-highlight ranges easier to verify visually.

### Tests
- Added regression coverage for visible multi-line highlight ranges and for documentation/Studio samples that keep `{2,5-6}` within the actual code block length.

## 1.13.22 - 2026-06-21

### Fixed
- Removed the final highlighted-code indentation drift by eliminating the highlighted-line padding that shifted highlighted content one character to the right of the following indented code rows.
- Normalized highlighted-line CSS to inherit the code row's font size and line height so advanced numbered code blocks use the same vertical rhythm as ordinary code blocks.

### Tests
- Added regression coverage that highlighted numbered code strips preserve leading spaces, do not reintroduce the old padding offset, and keep the line break outside the `.hll` wrapper.

## 1.13.21 - 2026-06-21

### Fixed
- Fixed the remaining advanced highlighted-code indentation defect by normalizing Pygments highlighted-line HTML so the newline is emitted outside the `.hll` wrapper. This keeps full-row highlight strips without letting the highlighted inline box consume the next line's leading spaces.

### Tests
- Added regression coverage that verifies the line after a highlighted numbered-code row keeps its leading indentation in the generated HTML.

## 1.13.20 - 2026-06-21

### Fixed
- Corrected numbered-code gutter alignment for highlighted advanced code blocks by keeping Pygments line-number spans inline. The previous block display override doubled the effective gutter line spacing and made numbers drift away from code rows.
- Changed highlighted code rows from block boxes to full-width inline-block highlights so highlighted lines remain visually continuous without adding extra line breaks inside `<pre>` layout.

### Tests
- Added regression assertions that numbered-code gutter spans stay inline and highlighted rows use full-width inline-block styling.

## 1.13.19 - 2026-06-21

### Fixed
- Aligned advanced numbered-code gutters with the actual code rows by moving numbered-code sizing and padding to shared per-style code metric tokens, then reusing those same metrics for both the code cell and the line-number gutter.
- Removed another source of numbered-code drift: the gutter no longer depends on hardcoded textbook/academic padding overrides inside the renderer, so future style tuning stays synchronized automatically.

### Tests
- Added regression coverage that every bundled style emits the shared code metric tokens and that numbered-code CSS uses those tokens for gutter/code alignment.

## 1.13.18 - 2026-06-21

### Fixed
- Centered Mermaid edge-label text inside its rounded label chips more reliably for Chromium PDF output by switching chip text to an explicit `tspan` vertical offset instead of relying on SVG baseline heuristics alone.
- Removed the stray dark badge backgrounds that Pygments emits around numbered-code gutter spans so advanced code blocks render clean line numbers without per-line boxes.
- Added support for common pipe-labelled dotted Mermaid edges such as `-.->|no| Retry`, so practical guide diagrams keep the expected label and retry node in offline rendering.

### Tests
- Added regression coverage for Mermaid chip text centering, pipe-labelled dotted Mermaid edges, and clean numbered-code gutter CSS overrides.

### Fixed
- Reworked highlighted code-line backgrounds so advanced fenced-code samples with line numbers stay readable on dark code surfaces in light styles and in dark-mode textbook/academic output, instead of resolving to pale callout-style or light-surface fills.
- Made mixed Persian/Latin table cells in Persian documents resolve to an explicit RTL base direction while keeping Latin identifiers isolated, fixing tables whose Persian descriptions were visually laid out as LTR.

### Tests
- Added regression coverage for code highlight contrast CSS and Persian mixed-script table direction voting.

## 1.13.16 - 2026-06-21

### Fixed
- Improved dark-mode palette tokens so low-saturation palettes such as `slate` and `neutral` keep readable TOC links, headings, and accents on dark textbook/academic surfaces.
- Marked code blocks containing Persian/Arabic script with stable CSS hooks and used Persian-capable font fallback inside those blocks so Persian YAML/string samples render joined and readable.
- Hardened `scripts/build_examples.sh` to render guide PDFs through the shared process-tree-safe command runner and force `--progress off` for non-interactive release builds.

### Tests
- Added coverage for dark-mode palette contrast tokens, RTL-script code-block CSS, and process-tree-safe guide example builds.

## 1.13.15 - 2026-06-21

### Fixed
- Made the `MARDAS_RENDER_SMOKE=1` path in `scripts/check.sh` run the guide render through the process-tree-safe Visual QA command helper so CI/release smoke checks do not hang when Chromium descendants inherit captured output handles.
- Added `MARDAS_RENDER_SMOKE_TIMEOUT` for a bounded outer smoke-render timeout independent of the Chromium `MARDAS_TIMEOUT_MS` page timeout.
- Disabled third-party pytest plugin autoload inside `scripts/check.sh` by default, with `MARDAS_ALLOW_PYTEST_PLUGINS=1` as an explicit opt-in, so local release checks stay deterministic after Playwright smoke renders.

### Documentation
- Synced README badge and English/Persian guide metadata to version `1.13.15`.

### Tests
- Added release-script regression coverage for the process-tree-safe render-smoke wrapper.

## 1.13.14 - 2026-06-21

### Fixed
- Replaced the heavyweight guide architecture SVG wrapper with an optimized document-local PNG so guide builds no longer embed a large base64 raster image inside SVG and then inside HTML.
- Updated English/Persian guide image and safe-HTML samples to use `images/architecture.png` while preserving the approved banner artwork.

### Documentation
- Clarified the guide media asset contract in `docs/BRANDING.md` and `docs/PDF-TYPOGRAPHY.md` so sample media stays lightweight and build-friendly.
- Synced README badge and English/Persian guide metadata to version `1.13.14`.

### Tests
- Updated guide media integrity tests to reject the removed nested-base64 `architecture.svg` path and enforce the optimized PNG contract.

## 1.13.13 - 2026-06-21

### Changed
- Switched the Studio topbar brand mark from the raster logo to a dedicated monochrome SVG mask so the GUI uses a true vector logo.
- Made the Studio brand mark inherit the exact same color as the `Mardas MD2PDF Studio` wordmark in both dark and light interface modes.

### Documentation
- Documented the new Studio-specific vector brand-mask asset in `docs/BRANDING.md`.
- Synced README badge and English/Persian guide metadata to version `1.13.13`.

### Tests
- Extended GUI, packaged-asset, and documentation-integrity tests to enforce the vector-branding contract for Studio.

## 1.13.12 - 2026-06-21

### Changed
- Replaced the guide-local architecture banner artwork with the supplied structured print pipeline illustration so the English and Persian manuals use the cleaner approved visual.
- Replaced the repository `README.png` hero artwork with the supplied dark banner so the public landing image matches the intended product presentation.
- Removed the obsolete `docs/guides/images/logo.svg` file from the guide media contract; the guide directory now keeps only the local `architecture.svg` sample and the approved `logo.png` copy.

### Documentation
- Documented the asset-layout policy for runtime packaged assets, guide-local documentation media, and the repository-level README artwork in `docs/BRANDING.md`.
- Synced README badge and English/Persian guide metadata to version `1.13.12`.

### Tests
- Updated documentation/media integrity tests so malformed guide-local `logo.svg` artwork cannot silently return and the replacement architecture banner contract stays explicit.

## 1.13.11 - 2026-06-21

### Changed
- Adopted the supplied Mardas MD2PDF application logo as canonical packaged full-color and white transparent PNG assets for Studio, cover branding, README artwork, and guide-local documentation assets.
- Centralized built-in product logo resolution and Studio brand-asset routing in `brand_assets.py` so renderer and GUI paths use the same asset contract.
- Refreshed the README hero image to use the dedicated application logo instead of the older generic mark artwork.

### Fixed
- Removed the legacy raster logo fallback from runtime branding and Studio asset routes so built-in branding no longer depends on the old Mardas logo file.

### Tests
- Added regression coverage for canonical app-logo packaging, transparent PNG dimensions, Studio routing, renderer fallback order, and documentation references.

## 1.13.10 - 2026-06-21

### Fixed
- Replaced the chunked Visual QA runner's pipe-captured subprocess execution with the shared process-tree-safe command helper so batch audits report failed child chunks instead of hanging when Chromium or Poppler descendants inherit output handles.
- Aligned the guide media regression contract with the current architecture-banner samples: guide Markdown must use the document-local `images/architecture.svg` sample, keep the packaged `images/logo.svg` asset available, and avoid reintroducing direct logo embeds in the manuals.

### Tests
- Added regression coverage for chunked Visual QA command capture and child-failure reporting.
- Updated guide media integrity coverage so contradictory `images/logo.svg` expectations cannot make the baseline test suite fail.

## 1.13.9 - 2026-06-20

- Added a dedicated white vector cover-label mark for built-in Mardas MD2PDF branding while keeping the full-color mark for Studio and document-local examples.
- Refined guide cover-brand mark sizing across packaged print styles so the logo remains centered in the compact label chip.
- Reworked the official guide architecture/banner SVG for cleaner spacing, alignment, and emerald visual consistency.
- Updated the English and Persian guide safe-HTML image sizing samples to reuse the architecture/banner asset instead of switching to the raw logo.
- Strengthened documentation integrity tests for the white cover-mark asset and the guide image-sample contract.

## 1.13.8 - 2026-06-20

### Fixed
- Fixed Persian checked task-list items so `[x]` markers still become disabled PDF checkboxes after mixed-script isolation wraps the Latin `x`.
- Rebalanced the official guide image samples so the standalone project mark remains compact and no longer forces a nearly blank Persian guide page.
- Updated the guide architecture diagram to use the official Mardas MD2PDF mark instead of the temporary literal `M` placeholder.

### Documentation
- Synced README badge and English/Persian guide metadata to version `1.13.8`.

### Tests
- Added regression coverage for Persian checked task lists and the official guide logo sample sizing.

## 1.13.7 - 2026-06-20

### Changed
- Adopted the dedicated Mardas MD2PDF project logo as packaged SVG assets for the built-in cover brand label and Studio UI.
- Kept the legacy raster compatibility fallback while preferring `mardas-md2pdf-mark.svg` for new built-in product branding.

### Documentation
- Documented the official mark, app icon, guide-local logo copy, and custom-brand usage boundaries in the branding reference.
- Synced README badge and English/Persian guide metadata to version `1.13.7`.

### Tests
- Added regression coverage for the packaged SVG logo asset contract and updated Studio logo checks for the new colored project mark.

## 1.13.6 - 2026-06-20

### Fixed
- Restored the product cover brand label to use the active appearance palette instead of a hard-coded blue product mark, so the official emerald guides keep the old compact label geometry while matching the current cover theme.
- Kept the guide cover brand label shadowless and compact, with the built-in Mardas product logo tinted through the surrounding palette-aware mark frame.

### Documentation
- Synced guide metadata, README badge, and changelog to version `1.13.6`.

### Tests
- Added regression coverage that rejects hard-coded blue product-brand styling and requires the modern emerald guide label to stay palette-aware and shadowless.

## 1.13.5 - 2026-06-20

### Fixed
- Restored the official guide cover label to the exact built-in product-branding path used by the earlier good guide examples: packaged Mardas logo, compact rounded pill, established two-line typography, and no drop shadow.
- Removed the temporary guide-local `images/brand-mark.svg` artwork from the official guides so the cover label no longer renders as a separate custom brand asset.
- Reintroduced product/custom brand classes only as stable render hooks so product labels can keep the classic Mardas styling while custom organization brands remain neutral.

### Documentation
- Clarified that official guides use `branding.mode: full` without custom `brand` metadata to preserve the built-in Mardas product label.

### Tests
- Updated regression coverage to require the official guides to avoid custom brand metadata and to keep the modern emerald cover label shadowless.

## 1.13.4 - 2026-06-20

### Fixed
- Restored the classic guide cover branding label: a compact rounded pill, circular optical logo frame, and the guide-local `images/brand-mark.svg` artwork used by the earlier official examples.
- Removed the product/custom cover-brand class split introduced in the previous branding polish so guide covers do not regress to a squared or overbuilt badge.

### Documentation
- Clarified that official guides intentionally pin the local brand mark to preserve the established guide cover identity.

### Tests
- Restored regression coverage that requires the official guide front matter to keep `brand.logo: images/brand-mark.svg`.

## 1.13.3 - 2026-06-20

### Changed
- Restored the official guide cover branding to use the packaged Mardas product logo instead of the temporary guide-local M-style placeholder mark.
- Refined the cover branding badge frame so product branding keeps the compact professional label while custom organization brands remain neutral and user-owned.
- Reworked the guide SVG brand samples and architecture diagram so they use a Mardas-like organic product mark rather than a literal `M` icon.

### Fixed
- Fixed the Persian guide pipeline code sample so the mixed RTL/LTR text no longer reorders visually inside the code block.

### Tests
- Updated regression coverage for guide branding metadata, packaged product logo usage, and the product/custom cover badge class contract.

## 1.13.2 - 2026-06-20

### Changed
- Strengthened the official guide visual identity so the English and Persian examples use a visibly emerald Mardas cover, callout, table, heading, and footer accent contract instead of only storing `palette: emerald` in front matter.
- Added a compact emerald guide brand mark and wired the official guides to use it for cover branding.
- Updated guide quickstart and automation examples to prefer the same `modern + emerald + light` appearance used by the official examples.

### Fixed
- Fixed remaining guide drift where the cover and semantic callouts still looked blue/violet/yellow despite the guide metadata declaring the emerald palette.

### Tests
- Added regression coverage for the official guide brand mark, guide metadata, and modern-emerald callout/cover CSS contract.

## 1.13.1 - 2026-06-20

### Changed
- Reworked printed footer layout so the running metadata line stays truly centered while titles and page numbers align cleanly on the outer edges in both LTR and RTL guides.
- Standardized both official guides on the `modern + emerald + light` appearance so the documentation, Studio palette, and embedded brand artwork follow one consistent Mardas visual language.
- Refreshed the official guide SVG brand samples with a cleaner Mardas-style logo plate and a matching emerald architecture diagram.

### Fixed
- Fixed asymmetric Persian footer placement where page numbers and document titles no longer sat flush on the expected outer edges.
- Fixed English/Persian guide sample drift caused by using different styles and palettes across the official example PDFs.

### Documentation
- Synced guide metadata, release references, and appearance contracts to version `1.13.1`.

### Tests
- Added regression coverage for footer slot alignment and the shared guide appearance contract.

## 1.13.0 - 2026-06-20

### Fixed

- Reduced PDF preflight font warnings in modern/GitHub output by avoiding environment-specific Inter font embedding in print styles and guide SVG samples.
- Improved footer contrast in dark-mode PDF output so page labels and running metadata stay readable across styles.

### Added

- Added `scripts/check_pdf_preflight.py` for repeatable PDF font, rasterization, and parser-warning checks.
- Added `scripts/run_visual_qa_matrix.py` as a chunked full-matrix Visual QA runner for appearance and feature-heavy PDF audits.
- Added `scripts/release_gate.sh` to consolidate pytest, smoke rendering, guide rebuilds, PDF preflight, bounded Visual QA, and distribution builds into one release command.

### Documentation

- Documented guide-level PDF preflight checks, chunked Visual QA runs, and the consolidated release gate.

### Tests

- Added regression coverage for PDF preflight parsing, explicit appearance triples, chunking contracts, dark footer contrast, guide preflight documentation, and release-gate script wiring.

## 1.12.2 - 2026-06-20

### Fixed

- Stabilized Visual QA subprocess handling so batch renders terminate full process groups on timeout instead of allowing orphaned Chromium or Poppler helpers to hang the matrix.
- Added explicit pdftoppm raster timeouts and clearer failure messages for PDF cases that create a file but do not exit cleanly.
- Polished Studio first-run state messaging so a missing local draft is treated as a clean ready state instead of an error.

### Added

- Added resumable and bounded Visual QA options: `--resume`, `--fail-fast`, `--max-cases`, and `--raster-timeout`.
- Added `--all-appearances` for feature-heavy PDF smoke audits so table, code, Mermaid, MathJax, callout, footnote, caption, and mixed-script coverage can be rendered across the full appearance matrix.
- Added `MARDAS_BUILD_NO_ISOLATION=1` support to `scripts/build_dist.sh` for offline or already-prepared release environments.

### Tests

- Added regression coverage for process-tree timeout handling, bounded all-appearance feature audits, reliable Visual QA CLI controls, Studio first-run status messaging, and the no-isolation build mode.
- Kept release metadata checks compatible with the supported Python 3.10 CI target by avoiding Python 3.11-only `tomllib` in the test suite.

## 1.12.1 - 2026-06-20

### Fixed

- Normalized GitHub/Obsidian callout markers before Persian mixed-script isolation so raw markers such as `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, and `[!WARNING]` never leak into rendered Persian PDFs.
- Preserved Persian-localized callout titles while still isolating Latin technical runs in the callout body.

### Tests

- Added regression coverage for Persian callouts in guides and mixed-script prose so future visual audits fail before raw callout markers reach generated PDFs.

## 1.12.0 - 2026-06-20

### Added

- Added Studio project files (`.mardas.json`) that preserve Markdown, export options, and attached asset data for repeatable local workspaces.
- Added a browser-side asset manager with append-only attachment handling, duplicate/limit checks, drag-and-drop support, per-asset removal, and one-click brand-logo assignment.
- Added accurate Studio preview mode and debug HTML export using the Python renderer HTML endpoint without starting Chromium.
- Added a command palette with professional workflow shortcuts for export, debug HTML, project save/open, asset actions, preview mode switching, and sidebar control.

### Documentation

- Expanded Studio workflow documentation and refreshed public version metadata for version 1.12.0.

### Tests

- Added regression coverage for Studio project bundles, asset manager actions, accurate preview/debug HTML hooks, command palette wiring, and keyboard shortcuts.

## 1.11.0 - 2026-06-19

### Added

- Added a Visual QA system for appearance matrix artifacts, feature-heavy PDF smoke artifacts, dependency-free PNG snapshot comparison, and Studio screenshots.
- Added CI artifact publishing for reduced visual QA outputs under `build/visual-qa/` so reviewers can inspect PDFs, PNG renders, manifests, galleries, and Studio screenshots without committing generated artifacts.

### Documentation

- Added `docs/VISUAL-QA.md` and linked it from the README and documentation index.
- Refreshed guide metadata and public version badges for version 1.11.0.

### Tests

- Added regression coverage for visual QA helper scripts, PNG statistics/diff behavior, filtered appearance audits, snapshot comparison summaries, Visual QA documentation links, and CI artifact wiring.

## 1.10.0 - 2026-06-19

### Fixed

- Improved print-flow density for medium and long technical blocks so moderately large tables, code listings, and Mermaid diagrams consume less vertical space without clipping content.
- Added medium-size print-flow classes for code blocks and tables, allowing semi-large tables to split at row boundaries instead of moving as one sparse page block.

### Documentation

- Updated the PDF typography guide, public README badge, and guide metadata for version 1.10.0.
- Closed the Persian/RTL quality reference with a release-facing contract for mixed-script prose, generated labels, TOC layout, footnotes, captions, table audit hooks, and guide sample policy.
- Linked the Persian/RTL reference from the long-form documentation index.

### Tests

- Added regression coverage for medium code/table flow hints and the corresponding print-density CSS contracts.

## 1.9.9 - 2026-06-19

### Fixed

- Tuned Mermaid diagram contrast in dark mode so diagram panels, SVG backgrounds, node fills, labels, borders, and caption accents use a complete dark-surface variable contract instead of inheriting only generic panel colors.
- Brightened Mermaid strokes and label chips in dark appearance combinations, including low-accent palettes such as neutral and slate, without changing Mermaid parsing or supported syntax.

### Documentation

- Updated the Markdown fidelity reference and guide metadata for version 1.9.9.

### Tests

- Added regression coverage to ensure every dark style/palette combination emits the full Mermaid contrast variable set and that renderer CSS consumes those variables.

## 1.9.8 - 2026-06-19

### Fixed

- Isolated Latin technical runs inside Persian mixed-script prose so trailing ASCII punctuation such as `renderer.`, `GitHub Actions.`, and `PDF navigation?` stays attached to the Latin token during PDF rendering.
- Added print CSS for inline LTR isolation spans and external links inside RTL article content without rewriting author text or inline code.

### Documentation

- Updated the Persian/RTL quality reference and guide smoke metadata for version 1.9.8.

### Tests

- Added regression coverage for Persian mixed-script punctuation isolation and verified that inline code remains semantically unchanged.

## 1.9.7 - 2026-06-15

### Fixed

- Restored the Persian printed table of contents to the compact English-like tree layout, keeping section numbers adjacent to titles instead of spreading them across the page.
- Mirrored nested TOC indentation inward from the RTL edge with start-side tree rules, while preserving heading IDs, visible TOC links, and PDF outline destinations.

### Documentation

- Updated the Persian/RTL documentation to describe compact RTL TOC tree behavior and guide smoke references for version 1.9.7.

### Notes

- Synced packaged release metadata and regression contracts with the documented 1.9.7 baseline after archive drift.

### Tests

- Updated regression coverage so Persian TOC CSS must use compact inline rows and must not reintroduce the wide number/title grid split.

## 1.9.6 - 2026-06-15

### Fixed

- Added first-pass nested-list depth metadata and classes for Persian/RTL printed tables of contents so the hierarchy could be regression-tested without changing heading IDs, link targets, or PDF destinations.
- Introduced bidirectional TOC tree CSS hooks; the compact visual layout was refined in 1.9.7 after PDF review.

### Documentation

- Refreshed guide metadata and Persian/RTL smoke references for the 1.9.6 TOC tree hook pass.
- Expanded `docs/PERSIAN-RTL.md` with RTL TOC tree indentation concepts.

### Tests

- Added regression coverage for nested Persian TOC lists, localized nested section numbers, TOC depth metadata, and bidirectional TOC indentation CSS.

## 1.9.5 - 2026-06-15

### Documentation

- Expanded the official English and Persian guides with compact Persian/RTL live smoke samples covering mixed-script prose, Persian and Latin numerals, semantic table captions, and reused footnote references.
- Clarified the documentation policy that guide files must stay readable user manuals while also serving as representative renderer test cases.
- Extended `docs/PERSIAN-RTL.md` with guide live-sample coverage rules for future Persian/RTL renderer changes.

### Tests

- Added documentation integrity checks that ensure the guides continue to exercise Persian/RTL tables, mixed numerals, captions, and repeated footnote references.

## 1.9.4 - 2026-06-15

### Fixed

- Added table-level visual-audit metadata for Persian/RTL tables, including direction profile, number profile, cell direction counts, and numeric-cell counts.
- Added stable TOC item profile hooks so Persian, Latin, mixed-script, and numbered heading titles can be checked in generated HTML/PDF without changing heading anchors.
- Strengthened captioned table handling for Persian captions so RTL table captions, mixed numerals, and table wrappers expose deterministic audit classes.

### Documentation

- Expanded `docs/PERSIAN-RTL.md` with Persian table and TOC visual-audit guidance.

### Tests

- Added regression coverage for profiled Persian TOC items, table-level audit metadata, captioned Persian tables, and the related print CSS selectors.

## 1.9.3 - 2026-06-15

### Fixed

- Polished Persian footnote body profiling so RTL, LTR, mixed-script, and mixed-number footnote content receive stable visual-audit hooks.
- Added explicit caption direction and number-profile metadata for Persian, Latin, and mixed captions without rewriting author text.
- Improved Persian printed footer wording from slash-separated page totals to a more readable localized `صفحه N از M` phrase.

### Documentation

- Expanded `docs/PERSIAN-RTL.md` with Persian footnote, caption, and footer visual-audit guidance.

### Tests

- Added regression coverage for Persian footnote body profiles, caption audit metadata, and localized footer templates.

## 1.9.2 - 2026-06-15

### Fixed

- Polished Persian generated navigation labels by localizing visible TOC section numbers while preserving stable heading IDs and link targets.
- Localized Persian footnote reference markers and footnote list markers without changing deterministic footnote anchors or backlink IDs.
- Added localized PDF page-label cover prefixes for Persian cover/content PDFs and strengthened caption number classes for Persian, Latin, and mixed-number captions.

### Documentation

- Expanded `docs/PERSIAN-RTL.md` with Persian navigation, footnote, and generated-label rules.

### Tests

- Added regression coverage for Persian TOC numbering, footnote markers, PDF page-label prefixes, and caption number profile classes.

## 1.9.1 - 2026-06-15

### Fixed

- Polished Persian numeral and punctuation profiling by distinguishing Persian-only digits, Latin-only digits, mixed numerals, Persian punctuation, and ASCII punctuation inside RTL-dominant text.
- Added caption-specific RTL hooks for Persian, numbered, and mixed Persian/English captions so figure, table, code, and Mermaid captions remain reviewable in generated HTML/PDF.
- Removed generated Python bytecode from the Phase 12 patch history and documented ignore rules in the apply helper.

### Documentation

- Expanded `docs/PERSIAN-RTL.md` with punctuation review rules, numeral classes, and caption-specific RTL hooks.

### Tests

- Added regression coverage for Persian/Latin numeral classification, RTL punctuation markers, Persian caption hooks, and table-cell punctuation/numeral profiling.

## 1.9.0 - 2026-06-15

### Added

- Started Phase 12 RTL/Persian deep quality work with deterministic direction classes for Persian, English, and mixed-script blocks.
- Added table-level RTL/LTR profiling so Persian-heavy tables, English-heavy cells, mixed-direction cells, and mixed Persian/Latin numerals get explicit print CSS hooks.
- Added `docs/PERSIAN-RTL.md` as the focused reference for Persian/RTL authoring, mixed identifiers, numbers, tables, captions, and verification.

### Fixed

- Improved bidi isolation for mixed Persian/English prose, captions, and tables so generated PDFs keep technical identifiers and numbers readable in RTL documents.

### Tests

- Added regression coverage for Persian RTL block classification, mixed numeral detection, RTL table profiling, and the injected CSS rules.

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

## 1.5.0 - 2026-05-26

### Added

- Established the stable public baseline for the Markdown-to-PDF pipeline: Markdown parsing, structured HTML assembly, print CSS, Playwright/Chromium PDF export, and local CLI usage.
- Shipped the baseline English and Persian guide PDFs as real generated examples rather than static screenshots or hand-authored PDFs.
- Consolidated the first complete user-facing workflow around CLI rendering, front matter, cover pages, table of contents, code blocks, math, Mermaid diagrams, images, footnotes, and local Studio export.

### Changed

- Iteratively refined print layout, code block rendering, table behavior, cover metadata, Mermaid sizing, and guide documentation before the structured changelog began.

### Notes

- This is the first structured baseline. The older entries below are reconstructed from the pre-structured project history, baseline documentation, and the capabilities that existed before the 1.5.x hardening and release-process work.

## 1.4.0 - 2026-05-26

### Added

- Added the first local Studio GUI for browser-based Markdown editing, approximate preview, option selection, asset attachment, and PDF export.
- Added GUI routes and assets for a local single-user publishing workflow while keeping the CLI as the automation-friendly interface.
- Added browser-side controls for core document options such as title, author, TOC, cover, page size, direction, and output filename.

### Changed

- Brought the documentation guides closer to live samples by covering the GUI workflow as well as the command-line workflow.

## 1.3.0 - 2026-05-26

### Added

- Added advanced Markdown features needed for technical publishing: GitHub-style task lists and alerts, footnotes, raw HTML sanitization, heading anchors, local image embedding, and manual page breaks.
- Added MathJax support for inline and display equations, with a bundled/offline MathJax asset for reproducible local rendering.
- Added the offline Mermaid flowchart renderer for practical project-documentation diagrams without relying on a CDN or external Mermaid service.

### Changed

- Improved the Markdown-to-HTML normalization layer so code, math, Mermaid, footnotes, and safe HTML could coexist in the same document without corrupting each other.

## 1.2.0 - 2026-05-26

### Added

- Added Persian, English, and mixed RTL/LTR document support with direction-aware body flow, cover labels, table cells, code blocks, metadata labels, and UI strings.
- Added Persian-friendly typography assumptions and font fallback behavior so generated PDFs remained readable when documents mixed Persian prose with English identifiers.
- Added professional cover-page metadata fields such as title, subtitle, authors, date, institution, course, status, version, and keywords.

### Changed

- Refined page flow, cover structure, and content direction handling for reports, guides, and university-style documents.

## 1.1.0 - 2026-05-26

### Added

- Added the first complete CLI rendering surface with input/output paths, metadata overrides, TOC controls, cover toggles, page size/margin options, progress output, and debug HTML export.
- Added table-of-contents generation from Markdown headings and baseline page-number/footer rendering for printable PDFs.
- Added local-image handling for document assets referenced from Markdown.

### Changed

- Moved the renderer toward a browser-first model where Chromium performs the final print layout from structured HTML and CSS.

## 1.0.0 - 2026-05-26

### Added

- Introduced the core `Markdown -> Structured HTML -> Chromium PDF` architecture.
- Added the initial Python package, renderer entry point, Markdown parsing layer, bundled CSS assets, and Playwright/Chromium PDF export path.
- Added the first documentation skeleton and generated examples that established the project as a local Markdown publishing tool rather than a one-off converter script.

## 0.x - 2026-05-26

### Notes

- Prototype phase for validating the feasibility of using Markdown, HTML/CSS print rules, and Chromium to generate Persian/English technical PDFs.
- Experiments from this period were folded into the `1.0.0` baseline once the converter became a usable project.
