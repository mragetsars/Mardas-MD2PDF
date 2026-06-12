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
controls out of the way until they are needed.

## Appearance cards

Style, palette, mode, and branding are selected with visual cards. These cards
map directly to the same render options used by the CLI:

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

## Local state

Studio stores the current draft, sidebar settings, layout mode, interface mode,
preview direction, and editor width in browser local storage. Use **Reset State**
when you want to clear the saved local draft and return to a clean workspace.

Keyboard shortcuts:

- **Ctrl/Cmd+S** saves the Markdown file.
- **Ctrl/Cmd+Enter** exports the PDF.
- **Ctrl/Cmd+1** returns to Split layout.
- **Ctrl/Cmd+2** focuses the editor.
- **Ctrl/Cmd+3** focuses the preview.
- **Ctrl/Cmd+4** enters Zen preview.
- **Esc** exits Zen preview.

Zen preview is intentionally transient: Studio does not restore directly into Zen
after a browser refresh. This prevents users from losing access to the main
controls if they close or reload the page while previewing.

## Attached assets

Attached assets are written into a temporary render directory before export. Use
this for Markdown images and optional brand logos such as `images/logo.png`.
Studio accepts up to 250 assets, 12 MB per asset, and 32 MB total.

## Preview boundary

The browser preview is intentionally approximate. It is useful for quick reading
and structure checks, but the exported PDF is the source of truth because it uses
the full Markdown processor, safe asset handling, MathJax, cover renderer, PDF
outline builder, and Chromium print rules.
