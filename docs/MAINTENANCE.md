# Maintenance Workflow

This document keeps routine project work predictable and patch-friendly.

## Local checks

Run the default quality gate before creating a patch or tag:

```bash
./scripts/check.sh
```

The script runs Ruff and pytest from the repository root. To include real Chromium render smoke tests, including PDF metadata and outline inspection, enable the optional environment flag:

```bash
MARDAS_RENDER_SMOKE=1 ./scripts/check.sh
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

## Python distributions

Build wheel and source distribution artifacts with:

```bash
./scripts/build_dist.sh
```

The script removes the previous `dist/` directory before building so stale packages do not get uploaded by mistake.

## Release artifacts workflow

The `Release Artifacts` GitHub Actions workflow runs on `v*` tags and manual dispatch. It installs the package, runs the quality gate with the Chromium smoke test enabled, rebuilds the guide PDFs, builds Python distributions, and uploads both artifact groups for the release owner to attach to a GitHub Release.

## Patch set hygiene

Keep generated patch sets easy to apply:

1. Make one logical change per commit.
2. Keep commit subjects in the existing conventional style: `feat:`, `fix:`, `docs:`, or `chore:`.
3. Run `./scripts/check.sh` before formatting patches.
4. Regenerate `examples/*.pdf` only in a dedicated `docs: refresh guide PDF examples` commit.
5. Keep binary outputs out of normal code commits unless the commit is explicitly about generated assets.
