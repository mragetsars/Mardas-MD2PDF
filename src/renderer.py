from __future__ import annotations

import base64
import html
import mimetypes
import re
import shutil
import tempfile
from dataclasses import dataclass, replace
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
    cover_brand_enabled: bool = True
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


THEME_FILES = {
    "modern": "theme-modern.css",
    "textbook-light": "theme-textbook-light.css",
    "textbook-dark": "theme-textbook-dark.css",
    "academic": "theme-academic.css",
}


def normalize_theme_name(theme_name: str | None) -> str:
    value = (theme_name or "modern").strip().lower()
    return value if value in THEME_FILES else "modern"


def _theme_css(theme_name: str) -> str:
    return _asset_text(THEME_FILES[normalize_theme_name(theme_name)])


def _code_style(theme_name: str) -> str:
    theme = normalize_theme_name(theme_name)
    if theme == "textbook-dark":
        return "bw"
    if theme in {"textbook-light", "academic"}:
        return "friendly"
    return "github-dark"


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


def _first_metadata_value(metadata: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return value
    return ""


def _stringify_metadata_value(value: Any, *, item_separator: str = "، ") -> str:
    """Convert front-matter values into readable cover text.

    YAML front matter may contain strings, numbers, block strings, lists, or
    small dictionaries such as author records. The cover renderer should handle
    all of them without leaking Python list/dict syntax into the PDF.
    """
    if value in (None, ""):
        return ""
    if isinstance(value, (list, tuple, set)):
        return item_separator.join(
            part
            for part in (_stringify_metadata_value(item, item_separator=item_separator) for item in value)
            if part
        )
    if isinstance(value, dict):
        name = value.get("name") or value.get("title") or value.get("label") or ""
        details = []
        for key in ("email", "affiliation", "role"):
            if value.get(key):
                details.append(str(value[key]))
        if name and details:
            return f"{name} ({' - '.join(details)})"
        if name:
            return str(name)
        return item_separator.join(f"{key}: {val}" for key, val in value.items() if val not in (None, ""))
    return str(value)


def _metadata_items(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            items.extend(_metadata_items(item))
        return [item for item in items if item]
    text = _stringify_metadata_value(value)
    return [text] if text else []


def _paragraph_block_html(value: Any, class_name: str) -> str:
    text = _stringify_metadata_value(value, item_separator="\n")
    if not text.strip():
        return ""
    paragraphs = [
        paragraph.strip() for paragraph in re.split(r"\n\s*\n", text.strip()) if paragraph.strip()
    ]
    if not paragraphs:
        return ""
    rendered = []
    for paragraph in paragraphs:
        escaped = html.escape(paragraph).replace("\n", "<br>")
        rendered.append(f'<p dir="auto">{escaped}</p>')
    return f'<div class="{html.escape(class_name)}" dir="auto">{"".join(rendered)}</div>'


def _cover_detail(label: str, value: Any, *, multiline: bool = False) -> str:
    if multiline:
        items = _metadata_items(value)
        if not items:
            return ""
        value_html = "".join(
            f'<span class="md2pdf-cover__detail-line" dir="auto">{html.escape(item)}</span>'
            for item in items
        )
    else:
        text = _stringify_metadata_value(value)
        if not text.strip():
            return ""
        value_html = html.escape(text).replace("\n", "<br>")
    return (
        '<div class="md2pdf-cover__detail" dir="auto">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{value_html}</strong>'
        '</div>'
    )


def _metadata_path(value: Any, base_dir: Path) -> Path | None:
    text = _stringify_metadata_value(value)
    if not text.strip():
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path if path.exists() else None


def _layout_css(options: PdfOptions, *, cover_full_bleed: bool = False) -> str:
    classes: list[str] = []
    css_chunks = [
        f"""
      :root {{
        --page-margin-top: {"0" if cover_full_bleed else options.margin_top};
        --page-margin-bottom: {"0" if cover_full_bleed else options.margin_bottom};
        --page-margin-x: {"0" if cover_full_bleed else options.margin_x};
      }}
    """
    ]
    if cover_full_bleed:
        classes.append("md2pdf-cover-full-bleed")
    if options.toc_page_break:
        classes.append("md2pdf-toc-break")
    if options.h1_page_break:
        classes.append("md2pdf-h1-break")
    return "\n".join(css_chunks), " ".join(classes)


def _cover_html(
    title: str,
    author: Any,
    date: Any,
    description: Any,
    options: PdfOptions,
    *,
    subtitle: Any = "",
    extra_details: list[tuple[str, Any]] | None = None,
    eyebrow: Any = "Generated Document",
) -> str:
    detail_cards: list[str] = []
    author_items = _metadata_items(author)
    if author_items:
        label = "Authors" if len(author_items) > 1 else "Author"
        detail_cards.append(_cover_detail(label, author_items, multiline=True))
    if date:
        detail_cards.append(_cover_detail("Date", date))
    for label, value in extra_details or []:
        card = _cover_detail(label, value, multiline=isinstance(value, (list, tuple, set)))
        if card:
            detail_cards.append(card)
    logo_uri = _cover_logo_uri(options)
    logo_html = (
        f'<img class="md2pdf-cover__logo" src="{html.escape(logo_uri)}" alt="Mardas logo">'
        if logo_uri
        else '<span class="md2pdf-cover__logo md2pdf-cover__logo--fallback">M</span>'
    )
    subtitle_text = _stringify_metadata_value(subtitle)
    subtitle_html = (
        f'<p class="md2pdf-cover__subtitle" dir="auto">{html.escape(subtitle_text)}</p>' if subtitle_text else ""
    )
    summary_html = _paragraph_block_html(description, "md2pdf-cover__summary")
    details_html = ''.join(detail_cards)
    brand_html = ""
    release_html = ""
    cover_classes = "md2pdf-cover"
    if options.cover_brand_enabled:
        brand_html = f"""
          <div class="md2pdf-cover__brand" dir="ltr">
            <span class="md2pdf-cover__mark">{logo_html}</span>
            <span class="md2pdf-cover__brand-copy">
              <strong>Mardas MD2PDF</strong>
              <em>Markdown to PDF Engine</em>
            </span>
          </div>
        """
        release_html = '<span class="md2pdf-cover__release" dir="ltr">PDF Report</span>'
    else:
        cover_classes += " md2pdf-cover--unbranded"

    return f"""
      <header class="{cover_classes}" dir="auto">
        <div class="md2pdf-cover__decor md2pdf-cover__decor--one" aria-hidden="true"></div>
        <div class="md2pdf-cover__decor md2pdf-cover__decor--two" aria-hidden="true"></div>
        <section class="md2pdf-cover__top">
          {brand_html}
          {release_html}
        </section>
        <section class="md2pdf-cover__content">
          <span class="md2pdf-cover__eyebrow">{html.escape(_stringify_metadata_value(eyebrow) or "Generated Document")}</span>
          <h1 dir="auto">{html.escape(str(title))}</h1>
          {subtitle_html}
          {summary_html}
        </section>
        {'<section class="md2pdf-cover__details">' + details_html + '</section>' if details_html else '<div></div>'}
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
    cover_full_bleed: bool = False,
) -> str:
    theme = _theme_css(options.theme)
    font_faces = _font_faces(options.font_dir)
    metadata = result.metadata
    title = options.title or _stringify_metadata_value(metadata.get("title")) or result.title
    author = options.author if options.author is not None else _first_metadata_value(metadata, "authors", "author")
    description = (
        options.description
        if options.description is not None
        else _first_metadata_value(metadata, "description", "summary")
    )
    lang = _stringify_metadata_value(metadata.get("lang")) or "fa"
    date = _first_metadata_value(metadata, "date")
    subtitle = _first_metadata_value(metadata, "subtitle", "subject")
    eyebrow = _first_metadata_value(metadata, "eyebrow", "document_type", "type") or "Generated Document"
    base_href = options.input_path.resolve().parent.as_uri() + "/"
    css_variables, body_classes = _layout_css(options, cover_full_bleed=cover_full_bleed)

    cover_options = options
    metadata_logo = _metadata_path(_first_metadata_value(metadata, "cover_logo", "logo"), options.input_path.resolve().parent)
    if metadata_logo and not options.cover_logo:
        cover_options = replace(options, cover_logo=metadata_logo)

    extra_details: list[tuple[str, Any]] = []
    detail_fields = [
        ("Institution", "institution", "university", "organization"),
        ("Course", "course", "lesson"),
        ("Department", "department"),
        ("Supervisor", "supervisor", "teacher", "advisor"),
        ("Student ID", "student_id", "student_number"),
        ("Group", "group", "team"),
        ("Version", "version"),
        ("Status", "status"),
        ("Keywords", "keywords", "tags"),
    ]
    for label, *keys in detail_fields:
        value = _first_metadata_value(metadata, *keys)
        if value not in (None, ""):
            extra_details.append((label, value))

    cover = (
        _cover_html(
            str(title),
            author,
            date,
            description,
            cover_options,
            subtitle=subtitle,
            extra_details=extra_details,
            eyebrow=eyebrow,
        )
        if include_cover and options.cover
        else ""
    )
    content = ""
    if include_content:
        content = f"{result.toc_html}{result.body_html}"
    watermark = _watermark_html(options) if include_content and include_watermark else ""

    theme_name = normalize_theme_name(options.theme)

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
<body class="md2pdf-theme-{html.escape(theme_name)} {html.escape(body_classes)}">
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
    theme = normalize_theme_name(theme_name)
    if theme == "textbook-light":
        return """
    <div style="width:100%; font-size:9px; color:#374151; padding:0 18mm; font-family:Arial, sans-serif; direction:ltr; text-align:right;">
      <span class="pageNumber"></span>
    </div>
    """
    if theme == "textbook-dark":
        return """
    <div style="width:100%; font-size:9px; color:#cbd5e1; padding:0 18mm; font-family:Arial, sans-serif; direction:ltr; text-align:right;">
      <span class="pageNumber"></span>
    </div>
    """
    if theme == "academic":
        return """
    <div style="width:100%; font-size:8.5px; color:#4b5563; padding:0 18mm; font-family:Georgia, 'Times New Roman', serif; direction:ltr; text-align:center;">
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
                cover_html = build_html(result, options, include_cover=True, include_content=False, include_watermark=False, cover_full_bleed=True)
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
