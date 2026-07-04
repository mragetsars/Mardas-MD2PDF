# Release Checklist

Use this checklist when preparing a tagged Mardas MD2PDF release.

## Version bump

- Update `pyproject.toml`.
- Update `src/__init__.py`.
- Update the README version badge.
- Update guide front matter and the version-history section in `docs/guides/GUIDE.en.md` and `docs/guides/GUIDE.fa.md`.
- Update `docs/CHANGELOG.md` with the release date and a concise summary.

## Quality gates

Run the local checks before tagging. The check helper keeps pytest isolated from unrelated third-party plugins unless `MARDAS_ALLOW_PYTEST_PLUGINS=1` is explicitly set:

```bash
./scripts/check.sh
```

For a full release verification, use the consolidated release gate:

```bash
./scripts/release_gate.sh
```

The gate runs the same core commands release maintainers previously ran manually: `./scripts/check.sh`, `./scripts/build_examples.sh`, `./scripts/build_dist.sh`, and optional cleanup via `./scripts/clean_workspace.sh`.

For exhaustive local visual review, opt in to the full chunked Visual QA matrix:

```bash
MARDAS_RELEASE_VISUAL_QA=1 ./scripts/release_gate.sh
```

When a release runner is slow, use `MARDAS_TIMEOUT_MS` for Chromium's page timeout and `MARDAS_RENDER_SMOKE_TIMEOUT` for the outer `./scripts/check.sh` smoke-render command timeout.

Use `./scripts/clean_workspace.sh --patches` after local patch application if temporary patch bundles were unpacked into the repository root.

The release gate writes PDF preflight data to `build/release/pdf-preflight.json` and one-case Visual QA smoke artifacts to `build/release/visual-qa-smoke/` unless `MARDAS_RELEASE_VISUAL_QA=1` is set. The full visual matrix is chunked and resumable: rerun `python scripts/run_visual_qa_matrix.py --output-dir build/release/visual-qa --render-png --resume` to skip chunks whose manifests are already complete. The matrix summary records active-chunk heartbeat data so a slow runner can be inspected while it is still running.

Open the generated PDFs and visually check the cover, table of contents, page numbers, code blocks, formulas, Mermaid diagrams, local images, wide tables, blocked-image placeholders, watermarks, and footnotes. When changing appearance CSS or palette behavior, also run `python scripts/audit_appearance_matrix.py --output-dir build/appearance-audit --render-png --resume` and review the full style/palette/mode matrix. The example build helper sets `SOURCE_DATE_EPOCH` by default so repeated guide builds do not churn metadata dates. In offline or pre-provisioned release environments, `MARDAS_BUILD_NO_ISOLATION=1 ./scripts/build_dist.sh` reuses the current environment instead of creating an isolated build environment.

## Commit style

Keep commit subjects short and conventional. Existing history uses subjects such as:

```text
feat: add PDF export progress feedback
fix: harden display math and pagebreak directives
docs: refresh guide PDF examples
chore: bump version to 1.5.1
```

Prefer one concern per commit so generated patches stay reviewable.

## Tagging

After the final commit is in place and CI is green:

```bash
git tag vX.Y.Z
git push origin master --tags
```

The `Release Artifacts` workflow runs on `v*` tags and uploads the Python distributions and regenerated guide PDFs. Create the GitHub Release from the tag, copy the matching `docs/CHANGELOG.md` entry into the release notes, and attach the workflow artifacts.


## Maintenance docs

See [`docs/MAINTENANCE.md`](./MAINTENANCE.md) for the daily check, example-generation, distribution-build, and patch-set workflow.
