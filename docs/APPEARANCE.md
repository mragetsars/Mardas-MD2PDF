# Appearance System

Mardas MD2PDF uses one appearance model for the final PDF output:

```text
style + palette + mode
```

This replaces the older split between visual themes and rendering profiles.  The
new model keeps each decision focused and predictable:

- **Style** controls document shape: spacing, cover layout, code block form,
  table density, and heading treatment.
- **Palette** controls accent colors: links, bullets, cover accents, callouts,
  and Mermaid strokes.
- **Mode** controls contrast: light or dark output.

## CLI

```bash
mrs-md2pdf input.md -o output.pdf --style modern --palette blue --mode light
```

Discover available choices with:

```bash
mrs-md2pdf --list-styles
mrs-md2pdf --list-palettes
mrs-md2pdf --list-modes
```

## Front matter

Documents can store appearance choices in front matter:

```yaml
appearance:
  style: modern
  palette: blue
  mode: light
```

Top-level keys are also accepted for compact documents:

```yaml
style: academic
palette: emerald
mode: light
```

CLI values take precedence over front matter when provided by the command line
or Studio.

## Built-in styles

| Style | Purpose |
| :--- | :--- |
| `modern` | Clean rounded document layout for reports and guides. |
| `github` | README-friendly layout for technical documentation. |
| `textbook` | Compact print-first layout for course notes and long documents. |
| `academic` | Formal serif-leaning layout for papers and academic reports. |

## Built-in palettes

| Palette | Purpose |
| :--- | :--- |
| `blue` | Default professional blue accents. |
| `emerald` | Green accents for calm reports and dashboards. |
| `violet` | Purple accents for creative and product documents. |
| `amber` | Warm amber accents for teaching and review documents. |
| `rose` | Rose accents for editorial or highlighted reports. |
| `slate` | Cool neutral accents for understated technical documents. |
| `neutral` | Minimal grayscale accents for formal output. |

## Modes

| Mode | Purpose |
| :--- | :--- |
| `light` | Light paper-like output for ordinary print and sharing. |
| `dark` | Dark output for screen-first documents and high-contrast previews. |

## Studio

Studio exposes the same model in the Appearance panel.  The label at the top of
the settings sidebar always shows the active combination, for example:

```text
modern · blue · light
```

The preview remains approximate; the backend renderer is still the source of
truth for MathJax, Mermaid, cover layout, PDF outlines, and print CSS.
