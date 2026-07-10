# Maintenance Workflow

This document keeps routine project work predictable and patch-friendly.

## Local checks

Run the default quality gate before creating a patch or tag:

```bash
./scripts/check.sh
python -m pytest -q tests/test_project_config.py tests/test_book_mode.py tests/test_cross_references.py
```

The script runs Ruff and pytest from the repository root. It disables third-party pytest plugin autoload by default so local virtualenv plugins cannot change release-gate behavior; set `MARDAS_ALLOW_PYTEST_PLUGINS=1` only when intentionally debugging pytest plugins. To include real Chromium render smoke tests, including PDF metadata and outline inspection, enable the optional environment flag:

```bash
MARDAS_RENDER_SMOKE=1 ./scripts/check.sh
```

For slow CI runners, `MARDAS_TIMEOUT_MS` controls the Chromium page timeout and `MARDAS_RENDER_SMOKE_TIMEOUT` controls the outer smoke-command timeout:

```bash
MARDAS_RENDER_SMOKE=1 MARDAS_TIMEOUT_MS=600000 MARDAS_RENDER_SMOKE_TIMEOUT=420 ./scripts/check.sh
```

## Book Mode checks

Changes to the book manifest, chapter assembly, ID namespacing, shared asset resolution, or cross-chapter links require the focused suite:

```bash
python -m pytest -q tests/test_book_mode.py tests/test_pdf_toc_destinations.py
```

Before release, create a representative book with at least two chapters, duplicate heading text, a shared project-root image, and a link from one chapter to a heading in another. Verify the combined HTML contains no absolute machine paths and inspect the PDF TOC, outline, page breaks, named destinations, and link annotations. The consolidated release gate also builds the starter Book Mode project from the cleanly installed wheel.

## Cross-reference checks

Changes to semantic labels, caption normalization, reference localization, generated lists, Book Mode assembly, or PDF destination writing require the focused suite:

```bash
python -m pytest -q tests/test_cross_references.py tests/test_book_mode.py tests/test_pdf_toc_destinations.py
```

Before release, render a representative English/Persian book containing a labeled figure, table, display equation, and code listing. Verify global and chapter-scoped numbering, a reference that crosses chapter boundaries, duplicate/unresolved diagnostics, all requested generated lists, and the corresponding `xref-*` named destinations and link annotations in the PDF. Official guide builds also enable all four reference lists as live renderer samples.

## Bibliography and citation checks

When changing `src/mardas_md2pdf/citations.py`, bibliography configuration, or Book Mode citation assembly, run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q \
  tests/test_citations.py \
  tests/test_book_mode.py \
  tests/test_project_config.py \
  tests/test_security_boundaries.py \
  tests/test_documentation_integrity.py
```

Also rebuild both guides. They load `docs/guides/GUIDE.references.bib` as a live offline source and must produce author-year disambiguation, narrative/grouped citation links, one generated bibliography, and stable `/bib-*` PDF destinations. No release check may require DOI lookup or network metadata retrieval.

## Studio Project Workspace checks

Changes to `src/mardas_md2pdf/workspace.py`, project API routes, Project Explorer, Problems Panel, safe file saving, or Book preview/export require:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q \
  tests/test_studio_project_workspace.py \
  tests/test_gui_assets.py \
  tests/test_studio_sidebar_layout.py \
  tests/test_visual_qa_scripts.py
```

Run both the ordinary Studio browser audit and the project-aware audit against a representative Book Mode project:

```bash
python scripts/audit_studio_visual.py --output-dir build/studio-audit --clean
python scripts/audit_studio_visual.py \
  --project path/to/book-project \
  --output-dir build/studio-project-audit \
  --clean
```

Verify project-relative diagnostics, safe navigation to a chapter line, external-change conflict handling, UTF-8/size boundaries, project-root and symlink rejection, renderer-backed active-file preview, and saved full-book preview/export. The installed-wheel release gate also imports `mardas_md2pdf.workspace`, performs a hash-guarded atomic save, checks `mrs-md2pdf-gui --help` for `--project`, and captures a Chromium project-workspace audit.

## Performance and large-document checks

Performance changes require a before/after benchmark using the same source tree, Chromium executable, Python version, machine load, profile set, repeat count, and timeout. Run the deterministic helper from the repository root:

```bash
python scripts/benchmark_large_documents.py \
  --profiles small,pages50,pages250,pages500,editor-loop \
  --mode both \
  --repeats 3 \
  --timeout-ms 300000 \
  --output-dir build/performance \
  --output build/performance/report.json
```

The `cold` mode starts Chromium for every conversion. The `session` mode reuses one Chromium process while creating a fresh browser context for every repeat. Compare wall-clock distributions, page counts, PDF sizes, browser-launch counts, and peak RSS; do not claim an optimization from one run or from different input profiles.

For targeted reliability checks:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q \
  tests/test_performance_reliability.py \
  tests/test_studio_export_jobs.py \
  tests/test_performance_benchmark.py

MARDAS_RENDER_SMOKE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  python -m pytest -q tests/test_performance_reliability.py
```

Verify that Studio returns `429 export_queue_full` when the bounded queue is exhausted, queued cancellation prevents work from starting, running cancellation is reported as cooperative, completed PDFs are streamed from disk, and an idle worker closes its reusable browser after the configured timeout.

## Generated examples

The guide PDFs in `examples/` are generated artifacts that should match the current Markdown guides. The helper sets a default `SOURCE_DATE_EPOCH` so PDF metadata dates stay deterministic across repeat builds. Regenerate them with:

```bash
./scripts/build_examples.sh
```

Override `SOURCE_DATE_EPOCH` only when a release intentionally needs a different deterministic metadata date. Use `MARDAS_TIMEOUT_MS` when CI or a slow local machine needs a longer browser timeout:

```bash
MARDAS_TIMEOUT_MS=240000 ./scripts/build_examples.sh
```


## Appearance matrix audit

When changing `src/mardas_md2pdf/appearance.py` or any `src/mardas_md2pdf/assets/style-*.css` file, render
every built-in style, palette, and mode combination before shipping the patch:

```bash
python scripts/audit_appearance_matrix.py --output-dir build/appearance-audit --render-png --resume
```

Review the cover and content PNGs for contrast, palette accents, code blocks,
callouts, tables, formulas, and dark-mode background consistency. This audit is
intentionally not part of the default CI path because it launches Chromium for
every combination.

For the complete style/palette/mode and feature-heavy matrix, use the chunked
runner. It skips already completed child manifests when `--resume` is set and
writes active-chunk heartbeat data to `summary.json` while long chunks run:

```bash
python scripts/run_visual_qa_matrix.py --output-dir build/visual-qa/full --render-png --resume
```

## Python distributions

Build wheel and source distribution artifacts with:

```bash
./scripts/build_dist.sh
```

The script removes the previous `dist/` directory before building so stale packages do not get uploaded by mistake. It derives `SOURCE_DATE_EPOCH` from the current commit when possible, fixes locale/timezone-sensitive build inputs, and normalizes the source archive so repeated wheel and sdist builds from the same tree are byte-identical.

## Release artifacts workflow

The `Release Artifacts` GitHub Actions workflow runs on `v*` tags and manual dispatch. It invokes `scripts/release_gate.sh` as the single release contract, including Chromium smoke, guide rebuild and PDF preflight, Visual QA, deterministic distribution builds, clean-wheel installation, packaged-asset and entry-point verification, and checksum generation before uploading artifacts.

## Patch set hygiene

Keep generated patch sets easy to apply:

1. Make one logical change per commit.
2. Keep commit subjects in the existing conventional style: `feat:`, `fix:`, `docs:`, or `chore:`.
3. Run `./scripts/check.sh` before formatting patches.
4. Regenerate `examples/*.pdf` only in a dedicated `docs: refresh guide PDF examples` commit.
5. Keep binary outputs out of normal code commits unless the commit is explicitly about generated assets.


## Workspace cleanup

Generated artifacts should not live in the repository root. Use the cleanup helper
when local test runs, editable installs, or patch application leave cache/build files
behind:

```bash
./scripts/clean_workspace.sh
./scripts/clean_workspace.sh --patches
```

The default cleanup removes Python caches, pytest/ruff caches, build outputs,
editable-install metadata, and the common root-level `output.pdf` scratch file.
The `--patches` option also removes a temporary root-level `patches/` directory
after patch sets have been applied.

## Release gate

Run `./scripts/release_gate.sh` before tagging a release. The gate installs the newly built wheel into a fresh virtual environment, verifies both console entry points and required packaged assets, and writes `dist/CHECKSUMS.sha256`. Set `MARDAS_RELEASE_VISUAL_QA=1` when the full chunked visual matrix is required instead of the reduced smoke matrix.
