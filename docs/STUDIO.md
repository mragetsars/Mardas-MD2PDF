# Mardas MD2PDF Studio

Mardas MD2PDF Studio is the local browser interface for writing Markdown,
choosing document appearance, attaching local assets, and exporting PDF output.
It uses the same backend renderer as the CLI, so the final PDF is still produced
by the Python pipeline, MathJax, appearance CSS, and Chromium print layout.

## Workflow

Studio is organized around the way a document is usually prepared:

1. **Document** — title, author, output filename, page size, and direction.
2. **Appearance** — visual style, color palette, and light/dark mode.
3. **Branding** — off, subtle, or full cover branding plus optional organization
   name, logo path, and footer text.
4. **Layout** — table of contents, H1 page breaks, and cover visibility.
5. **Advanced** — page footer visibility, watermarking, and attached local assets.

The goal is to keep common choices visible while keeping lower-level export
controls out of the way until they are needed. The sidebar uses accordion
sections and an internal scroll container so long settings content remains
reachable without pushing the whole workspace off screen.

## Appearance cards

Style, mode, and branding are selected with visual cards. Palettes use compact
color swatches so the full palette set stays visible without making the sidebar
feel tall or crowded. These controls map directly to the same render options used
by the CLI:

```yaml
appearance:
  style: modern
  palette: blue
  mode: light
branding:
  mode: off
```

Style controls document shape and layout. Palette controls colors. Mode controls
light or dark output. Branding is off by default so ordinary PDFs do not carry a
large product mark.

## Editor workflow

The editor panel includes a compact Markdown toolbar for common insertions:
bold, italic, link, image, code block, and table. The toolbar does not replace
Markdown knowledge; it reduces repetitive typing while keeping the source plain.

Line numbers are shown beside the editor to make it easier to discuss or debug a
long document. The preview scroll position follows the editor proportionally, so
users can keep the source and approximate preview in the same neighborhood.

Preview updates are debounced. When Studio is waiting for the next preview pass,
the preview header shows a small rendering indicator instead of leaving the user
wondering whether the document is stuck.

## Project files

Use **Save Project** to download a `.mardas.json` Studio project bundle. The
bundle stores the current Markdown source, export options, and attached asset
payloads. Use **Open Project** to restore that workspace later without requiring a
server-side project store.

Project files are intended for local trusted work. They can contain embedded
asset data, so do not commit them or share them publicly unless the document and
all attached files are safe to share.

## Workspace layout

Studio uses draggable panes instead of static view-mode buttons. Drag the
separator between **Export Settings** and the editor to resize the settings
panel. If the panel is dragged below the collapse threshold, it hides itself with
a soft transition. Use the small floating sidebar button in the upper-left corner to
restore it.

The separator between the editor and preview resizes the writing and reading
areas. This keeps the workspace fluid without forcing users through Split,
Editor, Preview, or Zen buttons.

The interface uses thin custom scrollbars and a pure light/dark surface model: a
minimal black/charcoal workspace in dark mode and a clean white/soft-gray
workspace in light mode. Toolbar actions use inline SVG icons and a contained
project logo instead of emoji glyphs, so the interface stays consistent across
operating systems and browsers.

## Local state

Studio stores the current draft, sidebar settings, interface mode, preview
direction, sidebar width, editor width, and collapsed settings state in browser
local storage. Use **Reset State** when you want to clear the saved local draft
and return to a clean workspace.

The top toolbar is grouped into File, Resources, and Export actions. Less
important actions use compact SVG icon buttons with tooltips, while **Export PDF**
remains the primary call to action.

Keyboard shortcuts:

- **Ctrl/Cmd+K** opens the command palette.
- **Ctrl/Cmd+S** saves the Markdown file.
- **Ctrl/Cmd+Shift+S** saves a `.mardas.json` Studio project bundle.
- **Ctrl/Cmd+O** opens a Markdown file.
- **Ctrl/Cmd+Shift+O** opens a Studio project bundle.
- **Ctrl/Cmd+E** exports debug HTML.
- **Ctrl/Cmd+Enter** exports the PDF.
- **Ctrl/Cmd+,** toggles the settings sidebar.

The command palette exposes the same actions without requiring users to memorize
shortcuts: export PDF, export debug HTML, save/open Markdown, save/open project,
attach or clear assets, copy CLI command, switch preview mode, and toggle the
settings panel.

## Attached assets

Attached assets are written into a temporary render directory before export. Use
this for Markdown images and optional brand logos such as `images/logo.png`.
Studio accepts up to 250 assets, 12 MB per asset, and 32 MB total.

Assets can be selected with the **Attach** button or dropped into the workspace.
The asset manager appends new files, skips duplicates and files over the configured
limits, shows total size, allows individual removal, and can set an attached file
as the brand logo path.

## Preview boundary

Studio has two preview modes:

- **Fast** uses the browser-local Markdown preview for instant structural checks.
- **Accurate** asks the Python backend for renderer HTML and loads it into an
  isolated preview frame. This mode is closer to final output and can reveal
  renderer-specific CSS, MathJax, TOC, cover, and asset behavior without starting
  Chromium.

Use **Export debug HTML** when you need to inspect the exact HTML handed to the
PDF renderer. The exported PDF is still the source of truth because it uses the
full Markdown processor, safe asset handling, MathJax, cover renderer, PDF outline
builder, and Chromium print rules.
