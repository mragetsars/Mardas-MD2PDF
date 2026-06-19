# Release Checklist

Use this checklist when preparing a tagged Mardas MD2PDF release.

## Version bump

- Update `pyproject.toml`.
- Update `src/__init__.py`.
- Update the README version badge.
- Update guide front matter and the version-history section in `docs/guides/GUIDE.en.md` and `docs/guides/GUIDE.fa.md`.
- Update `docs/CHANGELOG.md` with the release date and a concise summary.

## Quality gates

Run the local checks before tagging:

```bash
./scripts/check.sh
```

For a full release verification, include the Chromium smoke test and regenerate the guide samples:

```bash
MARDAS_RENDER_SMOKE=1 ./scripts/check.sh
./scripts/build_examples.sh
./scripts/build_dist.sh
./scripts/clean_workspace.sh
```

Use `./scripts/clean_workspace.sh --patches` after local patch application if temporary patch bundles were unpacked into the repository root.

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
