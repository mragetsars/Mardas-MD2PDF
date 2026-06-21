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
rounded label uses the packaged Mardas MD2PDF application logo, a dedicated white cover-label variant,
the established product typography, and no drop shadow. User documents should normally keep the default `off` mode unless they
intentionally need branding.

## Official project logo assets

The project now ships the dedicated Mardas MD2PDF logo as package assets:

| Asset | Purpose |
| :--- | :--- |
| `src/mardas_md2pdf/assets/mardas-md2pdf-logo.png` | Canonical full-color application logo used by Studio and preferred product branding paths. |
| `src/mardas_md2pdf/assets/mardas-md2pdf-logo-white.png` | Canonical white transparent application logo used by built-in cover-label branding. |
| `src/mardas_md2pdf/assets/mardas-md2pdf-mark.svg` | Scalable full-color vector companion for integrations that require SVG. |
| `src/mardas_md2pdf/assets/mardas-md2pdf-mark-white.svg` | Scalable white vector companion for integrations that require SVG. |
| `src/mardas_md2pdf/assets/mardas-md2pdf-app-icon.svg` | Rounded-square launcher/app icon artwork for distribution and platform packaging. |
| `src/mardas_md2pdf/assets/mardas-md2pdf-mark-gui-mask.svg` | Studio-only monochrome vector mask so the GUI brand mark inherits the same color as the `Mardas MD2PDF Studio` wordmark in dark and light modes. |
| `docs/guides/images/architecture.svg` and `docs/guides/images/logo.png` | Guide-local documentation media. `architecture.svg` is the sample banner embedded in the manuals; `logo.png` is a clean local logo copy kept for documentation integrity checks and optional guide-local examples. |

The official English and Persian guides should keep `branding.mode: full` without custom
`brand` metadata. That keeps them on the built-in product-branding path, where the cover
label uses the packaged white application-logo variant on top of the active appearance palette. Custom documents
should use `brand.logo` only for their own organization or lab logo.

## Asset layout policy

Project image assets are intentionally split by responsibility so packaging, documentation, and repository presentation do not leak into each other:

| Location | Purpose | Notes |
| :--- | :--- | :--- |
| `src/mardas_md2pdf/assets/` | Packaged runtime assets shipped with the application. | Used by Studio, built-in cover branding, app/distribution icons, GUI HTML, and print style resources. These files are part of the Python package contract. |
| `docs/guides/images/` | Guide-local documentation media used by `GUIDE.en.md` and `GUIDE.fa.md`. | Keep only media that the manuals or guide-integrity tests actually need. These files are not the canonical runtime source for product branding. |
| `README.png` | Repository hero artwork for GitHub and package landing pages. | Never reference this file from guide Markdown or runtime rendering paths. It exists only for repository presentation. |

This layout is the intended clean structure for the project: runtime assets stay inside the package, guide samples stay beside the guides that exercise them, and repository-only artwork stays at the root. When a file is no longer used by one of those scopes, remove it instead of keeping parallel copies without a clear owner.
