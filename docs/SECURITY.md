# Security Policy

Mardas MD2PDF is a local publishing tool. It is safe by default for normal
Markdown authoring, but it is not a sandbox for hostile documents. Treat
Markdown, front matter, raw HTML, attached Studio assets, logos, watermarks, and
local image references as author-controlled input.

## Supported versions

Security fixes are made on the current `master` branch and the latest tagged
release. When reporting an issue, include the Mardas MD2PDF version, Python
version, operating system, and the command or Studio settings used to render the
PDF.

## Threat model

The project protects against accidental local-file disclosure, unexpected network
fetches, active HTML content, and unsafe Chromium defaults during ordinary local
PDF generation. It does not claim to safely execute arbitrary hostile Markdown on
a shared public service. For untrusted documents, run the converter in a
container, VM, disposable user account, or CI job with a restricted filesystem and
network policy.

## Input boundaries

### Local files and images

- Markdown images, safe-HTML images, and front-matter branding logos are
  resolved relative to the Markdown document.
- Branding assets must be regular supported image files inside the document root;
  absolute paths, parent-directory escapes, and symlink escapes are rejected.
- Safe local images are embedded as `data:` URLs before Chromium renders the PDF.
- Absolute paths, `file:` URLs, parent-directory escapes, missing files, and
  over-limit images are not passed to Chromium as live file reads.
- Relative filesystem links remain visible text but are not exported as local
  `file:` annotations that reveal the producer's filesystem layout.
- Blocked or missing images render as visible placeholders, so authors can see
  what was skipped.

### Remote assets

Remote `http(s)` image assets are blocked by default for privacy,
reproducibility, and offline builds. Use `--allow-remote-assets` only for trusted
documents that intentionally fetch network images. Studio Fast Preview does not
fetch remote or local image paths and disables unsafe or filesystem link schemes;
PDF-like Preview and export remain the authoritative renderer-backed paths.

### Raw HTML

Raw HTML is sanitized by default. The sanitizer removes active content, event
handlers, unsafe URL schemes, style/script injection, iframes, and non-raster
`data:` images. `--unsafe-html` disables this boundary and should be used only
for documents you fully trust.

### MathJax and Mermaid

MathJax is vendored locally so formula rendering does not require a CDN. Mermaid
flowcharts are rendered by the built-in offline subset renderer. Unsupported
Mermaid features may be simplified rather than executed by a browser-side
runtime.

## Studio / GUI boundary

`mrs-md2pdf-gui` is intended for local use. The backend enforces Markdown and
asset size limits and validates render options before calling the renderer. When
binding Studio to a non-local host, remember that reachable users can submit
Markdown and attached assets. Use host-level access controls or a private network
if you expose it beyond `127.0.0.1`.

Studio render endpoints accept only JSON requests from the active Studio page:
the local browser session receives a per-run API token, and `/api/render` plus
`/api/render-html` reject untrusted Host/Origin headers, cross-site Fetch
Metadata, missing tokens, malformed or unbounded request bodies, and non-JSON
media types before rendering begins. Preview freshness is isolated per browser
tab, and PDF exports are concurrency-bounded so repeated clients cannot launch an
unlimited number of Chromium jobs.

## Output integrity

The CLI rejects input, PDF output, and debug-HTML paths that resolve to the same
file, including symlink and hardlink aliases. Final PDF and debug-HTML files are
written to sibling temporary files and atomically replaced only after a complete
successful write, so an interrupted post-processing step does not truncate a
previous valid artifact.

Front matter is parsed with bounded depth, node count, and scalar size. Recursive
YAML aliases and malformed YAML are rejected with controlled diagnostics rather
than being silently ignored or expanded without limits.

## Chromium sandboxing

The CLI option `--chromium-sandbox` controls Chromium sandbox behavior:

- `auto` keeps Chromium sandboxing enabled for normal users and disables it only
  when the process is running as root, where Chromium commonly requires
  `--no-sandbox` in containers.
- `on` always requests sandboxed Chromium.
- `off` passes `--no-sandbox` and should be used only inside trusted containers,
  disposable environments, or isolated CI jobs.

## PDF metadata and reproducibility

Guide/example builds honor `SOURCE_DATE_EPOCH` so repeated release builds do not
churn PDF metadata timestamps. User-generated PDFs may still include author,
title, keyword, and date metadata from front matter; avoid placing sensitive data
in front matter when producing public PDFs.

## Reporting issues

For security-related issues, use a private report when available. Share minimal
reproduction steps and avoid attaching confidential documents. Include whether
`--unsafe-html`, `--allow-remote-assets`, custom branding assets, or non-local
Studio binding were used.
