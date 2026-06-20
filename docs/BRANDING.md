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
are examples of Mardas MD2PDF itself. They intentionally do not set custom `brand`
metadata; this keeps the cover on the built-in product branding path, where the compact
rounded label uses the packaged Mardas logo, a dedicated white vector cover-mark variant,
the established product typography, and no drop shadow. User documents should normally keep the default `off` mode unless they
intentionally need branding.

## Official project logo assets

The project now ships the dedicated Mardas MD2PDF logo as package assets:

| Asset | Purpose |
| :--- | :--- |
| `src/mardas_md2pdf/assets/mardas-md2pdf-mark.svg` | Primary full-color product mark used by the Studio UI and document-local examples. |
| `src/mardas_md2pdf/assets/mardas-md2pdf-mark-white.svg` | White vector cover-label variant used on the built-in product-branded guide covers. |
| `src/mardas_md2pdf/assets/mardas-md2pdf-app-icon.svg` | Rounded-square launcher/app icon artwork for distribution and platform packaging. |
| `src/mardas_md2pdf/assets/Mardas.png` | Compatibility raster asset kept for older references and external workflows. |
| `docs/guides/images/logo.svg` | Guide-local copy kept for the project logo asset itself; image/HTML examples now reuse the architecture banner for more coherent sizing samples. |

The official English and Persian guides should keep `branding.mode: full` without custom
`brand` metadata. That keeps them on the built-in product-branding path, where the cover
label uses the packaged white cover-mark variant on top of the active appearance palette. Custom documents
should use `brand.logo` only for their own organization or lab logo.
