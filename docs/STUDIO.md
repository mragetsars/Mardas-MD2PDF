# Studio Workflow Contract

The guide section `GUI Workflow` is the canonical user tutorial for Studio. This file records the maintainer-facing Studio behavior contract.

## User-facing source of truth

- The guides explain how to launch `mrs-md2pdf-gui`, edit Markdown, choose export options, and export PDFs.
- README keeps a short Studio overview for GitHub visitors.

## Workflow

Studio is a local browser-based workspace for writing Markdown, previewing renderer-backed HTML, choosing options, and exporting PDF output.

## Appearance cards

Studio appearance cards must expose the same `style`, `palette`, and `mode` choices as the CLI and front matter. Adding or removing an option requires updates in the guide, tests, and appearance contract.

## Editor workflow

The editor workflow includes Markdown editing, approximate preview, accurate renderer-backed preview, PDF export, and debug HTML export. The UI must preserve common shortcuts:

- `Ctrl/Cmd+S` for saving Markdown;
- `Ctrl/Cmd+Shift+S` for saving a project bundle;
- `Ctrl/Cmd+Enter` for export;
- `Ctrl/Cmd+K` for the command palette.

## Project files

Studio project bundles use `.mardas.json` and should preserve Markdown, export options, and attached assets. The UI actions `Save Project` and `Open Project` must remain discoverable.

## Workspace layout

The workspace should keep editor, preview, option panels, and export controls visually separated. Advanced controls should not crowd the primary writing workflow.

## Local state

Browser-local state is a convenience cache, not the canonical source of a project. Users should save Markdown or `.mardas.json` bundles for durable work.

## Attached assets

Drag-and-drop asset handling must keep assets local to the project/export boundary. Studio must not silently fetch remote assets that the CLI would block.

## Preview boundary

The approximate preview may be fast, but the Accurate preview and exported PDF must use the same renderer pipeline as CLI output. `Export debug HTML` should remain available for layout diagnosis.

## Security boundary

Binding Studio to a non-local host exposes Markdown and attached-asset submission to reachable clients. Security details belong in `docs/SECURITY.md`, while the guide should warn ordinary users in concise language.
