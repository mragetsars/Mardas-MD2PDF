# Cover Branding and Asset Contract

The guide sections `Cover Branding` and `Front Matter` are the user-facing source of truth for enabling or disabling branding. This file documents the maintainer-facing asset and packaging contract.

## User-facing source of truth

- The guides explain `branding.mode`, `brand.name`, `brand.logo`, `brand.footer`, `--branding`, `--brand-name`, `--brand-logo`, and `--no-cover-logo`.
- The official guides use full Mardas branding because they document Mardas MD2PDF itself.
- Ordinary user documents are unbranded by default so the output belongs to the author.

## Branding modes

| Mode | Contract |
| :--- | :--- |
| `off` | No Mardas/product mark on the cover. Default for user documents. |
| `subtle` | Small generated-with note. |
| `full` | Full product or organization branding. Intended for explicit brand use. |

Users should use `brand.logo` only for their own organization or lab logo. They should use `brand.logo` only for their own organization or lab logo, not as a way to restyle the built-in Mardas product mark.

## Custom organization branding

```yaml
branding:
  mode: full
brand:
  name: "Acme Research Lab"
  logo: "assets/acme-logo.svg"
  footer: "Internal Technical Report"
```

CLI equivalents are documented in the guides:

```bash
mrs-md2pdf input.md -o output.pdf --branding full --brand-name "Acme Research Lab"
mrs-md2pdf input.md -o output.pdf --branding full --brand-logo ./assets/logo.png
```

## Project examples

The guide PDFs are product documentation, so they intentionally use full Mardas branding. Keep that choice in guide front matter unless the project deliberately changes its public sample identity.

## Official project logo assets

Runtime assets live in `src/mardas_md2pdf/assets/`:

- `mardas-md2pdf-logo.png`
- `mardas-md2pdf-logo-white.png`
- `mardas-md2pdf-mark.svg`
- `mardas-md2pdf-mark-white.svg`
- `mardas-md2pdf-app-icon.svg`
- `mardas-md2pdf-mark-gui-mask.svg`

The guide-local media directory is `docs/guides/images/`. It contains media used by the guide samples, including `logo.png` and `architecture.png`. It is not the canonical runtime asset directory.

`README.png` is a repository landing image for GitHub/package display. It should not be embedded into guide samples or renderer fixtures.

## Asset layout policy

- Runtime/package assets belong in `src/mardas_md2pdf/assets/` and must be included by `pyproject.toml` package-data rules.
- Guide sample media belongs in `docs/guides/images/` and should remain lightweight.
- Generated PDF examples belong in `examples/` and are rebuilt by `scripts/build_examples.sh`.
- Do not add large base64 media blobs or raster images wrapped inside SVG unless performance and PDF size are audited.
