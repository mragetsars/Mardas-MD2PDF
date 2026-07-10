# Maintenance Workflow

This document keeps routine project work predictable and patch-friendly.

## Local checks

Run the default quality gate before creating a patch or tag:

```bash
./scripts/check.sh
python -m pytest -q tests/test_project_config.py
```

The script runs Ruff and pytest from the repository root. It disables third-party pytest plugin autoload by default so local virtualenv plugins cannot change release-gate behavior; set `MARDAS_ALLOW_PYTEST_PLUGINS=1` only when intentionally debugging pytest plugins. To include real Chromium render smoke tests, including PDF metadata and outline inspection, enable the optional environment flag:

```bash
MARDAS_RENDER_SMOKE=1 ./scripts/check.sh
```

For slow CI runners, `MARDAS_TIMEOUT_MS` controls the Chromium page timeout and `MARDAS_RENDER_SMOKE_TIMEOUT` controls the outer smoke-command timeout:

```bash
MARDAS_RENDER_SMOKE=1 MARDAS_TIMEOUT_MS=600000 MARDAS_RENDER_SMOKE_TIMEOUT=420 ./scripts/check.sh
```

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
