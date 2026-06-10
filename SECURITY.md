# Security Policy

Mardas MD2PDF is designed for local Markdown publishing. Treat Markdown files,
attached GUI assets, cover logos, watermarks, and raw HTML as trusted author
content unless you explicitly run the converter inside an isolated environment.

## Supported input boundary

The default renderer keeps a conservative boundary around local files:

- Markdown and safe-HTML images are resolved relative to the Markdown file.
- Absolute paths, `file:` URLs, parent-directory escapes, and unresolved local
  image paths are not passed through to Chromium as live file reads.
- Local images that can be embedded safely are converted to `data:` URLs before
  the print step.
- Raw HTML is sanitized by default, removing active content, event handlers,
  unsafe URL schemes, and non-raster `data:` image URLs.
- `--unsafe-html` disables the raw HTML sanitizer and should be used only for
  documents you fully trust.

## Chromium sandboxing

The CLI option `--chromium-sandbox` controls Chromium sandbox behavior:

- `auto` keeps Chromium sandboxing enabled for normal users and disables it only
  when the process is running as root, where Chromium commonly requires
  `--no-sandbox` in containers.
- `on` always requests sandboxed Chromium.
- `off` passes `--no-sandbox` and should be used only in trusted containers or
  isolated CI jobs.

## Reporting issues

For security-related issues, please open a private report when possible or share
minimal reproduction steps without attaching sensitive documents. Include the
Mardas MD2PDF version, Python version, operating system, and the command used to
render the PDF.
