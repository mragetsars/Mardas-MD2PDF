from __future__ import annotations

import html
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from .markdown import MarkdownRenderResult, render_markdown_file


@dataclass(slots=True)
class PdfOptions:
    input_path: Path
    output_path: Path
    title: str | None = None
    author: str | None = None
    description: str | None = None
    toc: bool = False
    debug_html: Path | None = None
    page_size: str = "A4"
    margin_top: str = "18mm"
    margin_bottom: str = "20mm"
    margin_x: str = "16mm"
    font_dir: Path | None = None
    chromium_path: str | None = None
    no_header_footer: bool = False
    no_mathjax: bool = False
    timeout_ms: int = 120_000


def _asset_text(relative_path: str) -> str:
    return (resources.files("md2pdf_pro") / "assets" / relative_path).read_text(encoding="utf-8")


def _asset_path(relative_path: str) -> Path:
    return Path(str(resources.files("md2pdf_pro") / "assets" / relative_path))


def _font_faces(font_dir: Path | None) -> str:
    if not font_dir:
        return ""
    font_dir = font_dir.resolve()
    candidates = {
        "Vazirmatn": [
            "Vazirmatn-Regular.woff2",
            "Vazirmatn[wght].woff2",
            "Vazirmatn-Regular.ttf",
            "Vazirmatn.ttf",
        ],
        "Vazirmatn Bold": [
            "Vazirmatn-Bold.woff2",
            "Vazirmatn-Bold.ttf",
        ],
    }
    chunks: list[str] = []
    for family, filenames in candidates.items():
        for filename in filenames:
            path = font_dir / filename
            if path.exists():
                url = path.as_uri()
                weight = "100 900" if "[wght]" in filename else ("800" if "Bold" in family else "400")
                family_name = "Vazirmatn"
                font_format = "truetype" if filename.lower().endswith(".ttf") else "woff2"
                chunks.append(
                    "@font-face {"
                    f"font-family: '{family_name}'; src: url('{url}') format('{font_format}'); "
                    f"font-weight: {weight}; font-style: normal; font-display: swap;"
                    "}"
                )
                break
    return "\n".join(chunks)


def _mathjax_script() -> str:
    path = _asset_path("mathjax/tex-svg-full.js")
    if path.exists():
        return path.read_text(encoding="utf-8")
    # Fallback for editable source trees that intentionally omit vendored MathJax.
    return ""


def build_html(result: MarkdownRenderResult, options: PdfOptions) -> str:
    theme = _asset_text("theme.css")
    font_faces = _font_faces(options.font_dir)
    title = options.title or result.title
    author = options.author or result.metadata.get("author") or ""
    description = options.description or result.metadata.get("description") or result.metadata.get("summary") or ""
    lang = result.metadata.get("lang") or "fa"
    date = result.metadata.get("date") or ""
    base_href = options.input_path.resolve().parent.as_uri() + "/"

    css_variables = f"""
      :root {{
        --page-margin-top: {options.margin_top};
        --page-margin-bottom: {options.margin_bottom};
        --page-margin-x: {options.margin_x};
      }}
    """

    cover_meta = []
    if author:
        cover_meta.append(f"<span>{html.escape(str(author))}</span>")
    if date:
        cover_meta.append(f"<span>{html.escape(str(date))}</span>")
    cover = f"""
      <header class="md2pdf-cover" dir="auto">
        <span class="md2pdf-cover__eyebrow">MD2PDF Pro</span>
        <h1 dir="auto">{html.escape(str(title))}</h1>
        {'<div class="md2pdf-cover__meta" dir="auto">' + ''.join(cover_meta) + '</div>' if cover_meta else ''}
        {'<p class="md2pdf-cover__summary" dir="auto">' + html.escape(str(description)) + '</p>' if description else ''}
      </header>
    """

    mathjax_config = "" if options.no_mathjax else """
      <script>
        window.MathJax = {
          tex: {
            inlineMath: [['\\\\(', '\\\\)'], ['$', '$']],
            displayMath: [['\\\\[', '\\\\]'], ['$$', '$$']],
            processEscapes: true,
            packages: {'[+]': ['ams', 'noerrors', 'noundefined']}
          },
          svg: { fontCache: 'global' },
          options: { enableMenu: false }
        };
      </script>
    """
    mathjax_js = "" if options.no_mathjax else _mathjax_script()
    mathjax_block = ""
    if mathjax_js:
        mathjax_block = f"{mathjax_config}<script>{mathjax_js}</script>"
    elif not options.no_mathjax:
        # Safe fallback: math remains readable in TeX wrappers when MathJax is unavailable.
        mathjax_block = "<!-- MathJax asset missing: equations will remain in TeX form. -->"

    return f"""<!doctype html>
<html lang="{html.escape(str(lang))}" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base href="{base_href}">
  <title>{html.escape(str(title))}</title>
  <style>{font_faces}</style>
  <style>{theme}</style>
  <style>{css_variables}</style>
  <style>{result.pygments_css}</style>
  {mathjax_block}
</head>
<body>
  <main class="md2pdf-document">
    <article class="md2pdf-article">
      {cover}
      {result.toc_html}
      {result.body_html}
    </article>
  </main>
</body>
</html>"""


def _footer_template(title: str) -> str:
    safe_title = html.escape(title)
    return f"""
    <div style="width:100%; font-size:8px; color:#64748b; padding:0 16mm; font-family:Arial, sans-serif;">
      <div style="border-top:1px solid #dbe3ef; padding-top:5px; display:flex; justify-content:space-between; direction:ltr;">
        <span>{safe_title}</span>
        <span><span class="pageNumber"></span>/<span class="totalPages"></span></span>
      </div>
    </div>
    """


def convert(options: PdfOptions) -> Path:
    options.input_path = Path(options.input_path)
    options.output_path = Path(options.output_path)
    result = render_markdown_file(options.input_path, toc=options.toc)
    html_text = build_html(result, options)

    options.output_path.parent.mkdir(parents=True, exist_ok=True)
    if options.debug_html:
        options.debug_html.parent.mkdir(parents=True, exist_ok=True)
        options.debug_html.write_text(html_text, encoding="utf-8")

    executable = options.chromium_path or shutil.which("chromium") or shutil.which("google-chrome")

    with sync_playwright() as p:
        launch_kwargs: dict[str, Any] = {
            "headless": True,
            "args": [
                "--font-render-hinting=medium",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        }
        if executable:
            launch_kwargs["executable_path"] = executable
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(device_scale_factor=1)
        page.set_default_timeout(options.timeout_ms)
        page.set_content(html_text, wait_until="load")
        page.evaluate("() => document.fonts && document.fonts.ready")
        if not options.no_mathjax:
            try:
                page.evaluate(
                    """async () => {
                      if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
                        await window.MathJax.startup.promise;
                      }
                      if (window.MathJax && window.MathJax.typesetPromise) {
                        await window.MathJax.typesetPromise();
                      }
                    }"""
                )
            except Exception:
                # Keep the conversion usable even if a document has invalid TeX.
                pass
        page.emulate_media(media="print")
        title = options.title or result.title
        pdf_kwargs: dict[str, Any] = {
            "path": str(options.output_path),
            "format": options.page_size,
            "print_background": True,
            "prefer_css_page_size": True,
            "margin": {"top": "0", "right": "0", "bottom": "0", "left": "0"},
        }
        if not options.no_header_footer:
            pdf_kwargs.update(
                {
                    "display_header_footer": True,
                    "header_template": "<div></div>",
                    "footer_template": _footer_template(str(title)),
                }
            )
        page.pdf(**pdf_kwargs)
        browser.close()
    return options.output_path
