# Cover Branding

Mardas MD2PDF separates document ownership from product branding. Generated PDFs are
unbranded by default, so ordinary reports, handouts, proposals, and internal documents do
not show a large Mardas MD2PDF label on the cover.

## Branding modes

Use `branding.mode` in front matter or `--branding` on the CLI:

| Mode | Behavior |
| :--- | :--- |
| `off` | Default. No product or organization brand block is shown on the cover. |
| `subtle` | Shows a small generated-with note, intended for informal shared drafts. |
| `full` | Shows a cover brand block. This is appropriate for project guides, branded templates, or documents with an explicit organization brand. |

```yaml
---
title: "Internal Report"
branding:
  mode: off
---
```

```bash
mrs-md2pdf report.md -o report.pdf --branding off
```

## Custom organization branding

When you provide `brand` metadata, the cover can show your own organization instead of
Mardas MD2PDF:

```yaml
---
title: "Lab Report"
branding:
  mode: full
brand:
  name: "Acme Research Lab"
  logo: "assets/acme.png"
  footer: "Internal Technical Report"
---
```

Equivalent CLI options are available for generated or scripted documents:

```bash
mrs-md2pdf report.md -o report.pdf \
  --branding full \
  --brand-name "Acme Research Lab" \
  --brand-logo assets/acme.png \
  --brand-footer "Internal Technical Report"
```

`--cover-logo` remains available as a cover-logo shortcut, but `--brand-logo` is the
preferred name for new branded output.

## Project examples

The built-in English and Persian guides explicitly use `branding.mode: full`, because they
are examples of Mardas MD2PDF itself. User documents should normally keep the default
`off` mode unless they intentionally need branding.
