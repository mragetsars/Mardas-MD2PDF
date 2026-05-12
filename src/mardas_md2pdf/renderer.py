from __future__ import annotations

import base64
import html
import mimetypes
import shutil
import tempfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright
from pypdf import PdfWriter

from .markdown import MarkdownRenderResult, render_markdown_file


@dataclass(slots=True)
class PdfOptions:
    input_path: Path
    output_path: Path
    title: str | None = None
    author: str | None = None
    description: str | None = None
    toc: bool = False
    toc_depth: int = 6
    toc_page_break: bool = False
    h1_page_break: bool = False
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
    theme: str = "modern"
    cover: bool = True
    cover_logo: Path | None = None
    cover_logo_enabled: bool = True
    watermark_text: str | None = None
    watermark_image: Path | None = None
    watermark_opacity: float = 0.065
    watermark_width: str = "105mm"


def _asset_text(relative_path: str) -> str:
    return (resources.files("mardas_md2pdf") / "assets" / relative_path).read_text(encoding="utf-8")


def _asset_path(relative_path: str) -> Path:
    return Path(str(resources.files("mardas_md2pdf") / "assets" / relative_path))


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
    return ""


def _theme_css(theme_name: str) -> str:
    theme_name = (theme_name or "modern").strip().lower()
    if theme_name == "textbook":
        return _asset_text("theme-textbook.css")
    return _asset_text("theme.css")


def _code_style(theme_name: str) -> str:
    return "friendly" if (theme_name or "").strip().lower() == "textbook" else "github-dark"


def _path_uri(path: Path | None) -> str | None:
    if not path:
        return None
    return path.resolve().as_uri()


def _image_data_uri(path: Path | None) -> str | None:
    """Embed local images as data URIs so Chromium PDF can render them reliably."""
    if not path:
        return None
    path = path.resolve()
    if not path.exists():
        return None
    mime_type = mimetypes.guess_type(str(path))[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _default_logo_path() -> Path | None:
    path = _asset_path("Mardas.png")
    return path if path.exists() else None


def _cover_logo_uri(options: PdfOptions) -> str | None:
    if not options.cover_logo_enabled:
        return None
    return _image_data_uri(options.cover_logo or _default_logo_path())


def _watermark_html(options: PdfOptions) -> str:
    if options.watermark_image:
        image_uri = _image_data_uri(options.watermark_image)
        if image_uri:
            return (
                '<div class="md2pdf-watermark md2pdf-watermark--image" aria-hidden="true" '
                f'style="--watermark-opacity: {options.watermark_opacity}; --watermark-width: {html.escape(options.watermark_width)};">'
                f'<img src="{html.escape(image_uri)}" alt="">'
                '</div>'
            )
    if options.watermark_text:
        return (
            '<div class="md2pdf-watermark md2pdf-watermark--text" aria-hidden="true" '
            f'style="--watermark-opacity: {options.watermark_opacity};">'
            f'{html.escape(options.watermark_text)}'
            '</div>'
        )
    return ""


def _layout_css(options: PdfOptions) -> str:
    classes: list[str] = []
    css_chunks = [
        f"""
      :root {{
        --page-margin-top: {options.margin_top};
        --page-margin-bottom: {options.margin_bottom};
        --page-margin-x: {options.margin_x};
      }}
    """
    ]
    if options.toc_page_break:
        classes.append("md2pdf-toc-break")
    if options.h1_page_break:
        classes.append("md2pdf-h1-break")
    return "\n".join(css_chunks), " ".join(classes)


def _cover_html(title: str, author: str, date: str, description: str, options: PdfOptions) -> str:
    cover_meta = []
    if author:
        cover_meta.append(f"<span>{html.escape(str(author))}</span>")
    if date:
        cover_meta.append(f"<span>{html.escape(str(date))}</span>")
    logo_uri = _cover_logo_uri(options)
    logo_html = (
        f'<img class="md2pdf-cover__logo" src="{html.escape(logo_uri)}" alt="Mardas logo">'
        if logo_uri
        else ""
    )
    return f"""
      <header class="md2pdf-cover" dir="auto">
        <div class="md2pdf-cover__brand" dir="ltr">
          {logo_html}
          <span>Mardas MD2PDF</span>
        </div>
        <div class="md2pdf-cover__content">
          <span class="md2pdf-cover__eyebrow">Markdown to PDF Engine</span>
          <h1 dir="auto">{html.escape(str(title))}</h1>
          {'<div class="md2pdf-cover__meta" dir="auto">' + ''.join(cover_meta) + '</div>' if cover_meta else ''}
          {'<p class="md2pdf-cover__summary" dir="auto">' + html.escape(str(description)) + '</p>' if description else ''}
        </div>
      </header>
    """


def _mathjax_block(options: PdfOptions) -> str:
    if options.no_mathjax:
        return ""
    mathjax_config = """
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
    mathjax_js = _mathjax_script()
    if mathjax_js:
        return f"{mathjax_config}<script>{mathjax_js}</script>"
    return "<!-- MathJax asset missing: equations will remain in TeX form. -->"


def build_html(
    result: MarkdownRenderResult,
    options: PdfOptions,
    *,
    include_cover: bool = True,
    include_content: bool = True,
    include_watermark: bool = True,
) -> str:
    theme = _theme_css(options.theme)
    font_faces = _font_faces(options.font_dir)
    title = options.title or result.title
    author = options.author or result.metadata.get("author") or ""
    description = options.description or result.metadata.get("description") or result.metadata.get("summary") or ""
    lang = result.metadata.get("lang") or "fa"
    date = result.metadata.get("date") or ""
    base_href = options.input_path.resolve().parent.as_uri() + "/"
    css_variables, body_classes = _layout_css(options)

    cover = _cover_html(str(title), str(author), str(date), str(description), options) if include_cover and options.cover else ""
    content = ""
    if include_content:
        content = f"{result.toc_html}{result.body_html}"
    watermark = _watermark_html(options) if include_content and include_watermark else ""

    return f"""<!doctype html>
<html lang="{html.escape(str(lang))}" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base href="{base_href}">
  <title>{html.escape(str(title))}</title>
  <style>{font_faces}</style>
  <style>{result.pygments_css}</style>
  <style>{theme}</style>
  <style>{css_variables}</style>
  {_mathjax_block(options)}
</head>
<body class="{html.escape(body_classes)}">
  {watermark}
  <main class="md2pdf-document">
    <article class="md2pdf-article">
      {cover}
      {content}
    </article>
  </main>
</body>
</html>"""


def _footer_template(title: str, theme_name: str = "modern") -> str:
    if (theme_name or "").strip().lower() == "textbook":
        return """
    <div style="width:100%; font-size:9px; color:#374151; padding:0 18mm; font-family:Arial, sans-serif; direction:ltr; text-align:right;">
      <span class="pageNumber"></span>
    </div>
    """
    safe_title = html.escape(title)
    return f"""
    <div style="width:100%; font-size:8px; color:#64748b; padding:0 16mm; font-family:Arial, sans-serif;">
      <div style="border-top:1px solid #dbe3ef; padding-top:5px; display:flex; justify-content:space-between; direction:ltr;">
        <span>{safe_title}</span>
        <span><span class="pageNumber"></span>/<span class="totalPages"></span></span>
      </div>
    </div>
    """


def _render_pdf(page: Page, html_text: str, options: PdfOptions, path: Path, *, display_footer: bool, title: str) -> None:
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
            pass
    page.emulate_media(media="print")
    pdf_kwargs: dict[str, Any] = {
        "path": str(path),
        "format": options.page_size,
        "print_background": True,
        "prefer_css_page_size": True,
        "margin": {"top": "0", "right": "0", "bottom": "0", "left": "0"},
    }
    if display_footer and not options.no_header_footer:
        pdf_kwargs.update(
            {
                "display_header_footer": True,
                "header_template": "<div></div>",
                "footer_template": _footer_template(str(title), options.theme),
            }
        )
    page.pdf(**pdf_kwargs)


def _merge_pdfs(parts: list[Path], output_path: Path) -> None:
    writer = PdfWriter()
    for part in parts:
        writer.append(str(part))
    with output_path.open("wb") as fh:
        writer.write(fh)
    writer.close()


def convert(options: PdfOptions) -> Path:
    options.input_path = Path(options.input_path)
    options.output_path = Path(options.output_path)
    result = render_markdown_file(
        options.input_path, toc=options.toc, toc_depth=options.toc_depth, code_style=_code_style(options.theme)
    )
    title = options.title or result.title

    options.output_path.parent.mkdir(parents=True, exist_ok=True)

    full_debug_html = build_html(result, options, include_cover=True, include_content=True, include_watermark=True)
    if options.debug_html:
        options.debug_html.parent.mkdir(parents=True, exist_ok=True)
        options.debug_html.write_text(full_debug_html, encoding="utf-8")

    executable = options.chromium_path or shutil.which("chromium") or shutil.which("google-chrome")

    with tempfile.TemporaryDirectory(prefix="mardas-md2pdf-") as tmpdir:
        tmp = Path(tmpdir)
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

            if options.cover:
                cover_pdf = tmp / "cover.pdf"
                cover_html = build_html(result, options, include_cover=True, include_content=False, include_watermark=False)
                _render_pdf(page, cover_html, options, cover_pdf, display_footer=False, title=str(title))

                content_pdf = tmp / "content.pdf"
                content_html = build_html(result, options, include_cover=False, include_content=True, include_watermark=True)
                _render_pdf(page, content_html, options, content_pdf, display_footer=True, title=str(title))

                browser.close()
                _merge_pdfs([cover_pdf, content_pdf], options.output_path)
            else:
                html_text = build_html(result, options, include_cover=False, include_content=True, include_watermark=True)
                _render_pdf(page, html_text, options, options.output_path, display_footer=True, title=str(title))
                browser.close()
    return options.output_path
