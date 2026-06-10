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


## Palette purity rules

Styles should not force a brand color.  They may define spacing, density,
corner radius, typography, and cover structure, but accent color should come
from the selected palette.  This is especially important for the `academic`
style: its formal layout stays intact across palettes, while callouts, cover
accents, Mermaid strokes, TOC numbers, and code captions follow `--palette`.

Cover labels such as `cover_label: "Complete Guide"` are rendered as plain
label text with an accent rule, not as a filled badge.  That keeps Persian and
English covers from looking as if a printing highlight was accidentally left on
top of the label.

## Visual audit workflow

After changing style CSS, palette colors, or mode behavior, render the full
appearance matrix and review both the cover and a content page:

```bash
python scripts/audit_appearance_matrix.py --output-dir build/appearance-audit --render-png
```

The matrix covers every built-in `style × palette × mode` combination.  Dark
mode deliberately uses style-specific surfaces: `modern` stays deep navy,
`github` follows a GitHub-like dark surface, `textbook` uses a near-black print
surface, and `academic` uses a neutral charcoal surface.  Palettes remain accent
choices in both modes, so a dark document should keep the selected accent
without making all styles look identical.
