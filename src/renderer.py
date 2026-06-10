from __future__ import annotations

import base64
import html
import mimetypes
import os
import re
import shutil
import tempfile
import unicodedata
import warnings
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Page, sync_playwright
from pypdf import PdfReader, PdfWriter

from .markdown import MarkdownRenderResult, render_markdown_file


MAX_EMBED_ASSET_BYTES = 20 * 1024 * 1024
ProgressCallback = Callable[[str, float], None]


def _report_progress(callback: ProgressCallback | None, message: str, fraction: float) -> None:
    """Report best-effort progress without letting UI code break conversion."""
    if callback is None:
        return
    try:
        callback(message, max(0.0, min(1.0, float(fraction))))
    except Exception:
        # Progress hooks are optional UX helpers; PDF generation must not fail
        # because a terminal or GUI progress callback raised unexpectedly.
        return


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
    document_direction: str | None = None
    margin_top: str = "18mm"
    margin_bottom: str = "20mm"
    margin_x: str = "16mm"
    font_dir: Path | None = None
    chromium_path: str | None = None
    chromium_sandbox: str = "auto"
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
    unsafe_html: bool = False
    allow_remote_assets: bool = False
    progress: ProgressCallback | None = None


def _asset_text(relative_path: str) -> str:
    return (resources.files("mardas_md2pdf") / "assets" / relative_path).read_text(encoding="utf-8")


def _asset_path(relative_path: str) -> Path:
    return Path(str(resources.files("mardas_md2pdf") / "assets" / relative_path))


def _font_faces(font_dir: Path | None) -> str:
    if not font_dir:
        return ""
    font_dir = font_dir.resolve()
    if not font_dir.exists() or not font_dir.is_dir():
        warnings.warn(
            f"Font directory not found; falling back to system fonts: {font_dir}",
            RuntimeWarning,
            stacklevel=2,
        )
        return ""
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
    if not chunks:
        warnings.warn(
            f"No Vazirmatn font files found in {font_dir}; falling back to system fonts.",
            RuntimeWarning,
            stacklevel=2,
        )
    return "\n".join(chunks)


def _mathjax_script() -> str:
    path = _asset_path("mathjax/tex-svg-full.js")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


THEME_FILES = {
    "modern": "theme-modern.css",
    "github": "theme-github.css",
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
    if theme in {"github", "textbook-light", "academic"}:
        return "friendly"
    return "github-dark"


def _math_scale_vars(theme_name: str) -> tuple[str, str]:
    """Return CSS font-size scales for inline and display MathJax.

    MathJax SVG dimensions are emitted in ``ex`` units. Chromium resolves those
    units differently across the theme font stacks, so each bundled theme gets a
    small optical correction: inline formulas align with the surrounding text,
    while display formulas remain visibly larger and centered.
    """
    theme = normalize_theme_name(theme_name)
    if theme == "academic":
        return "70%", "105%"
    if theme in {"textbook-light", "textbook-dark"}:
        return "78%", "115%"
    return "100%", "130%"


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
    size = path.stat().st_size
    if size > MAX_EMBED_ASSET_BYTES:
        warnings.warn(
            f"Skipping asset larger than {MAX_EMBED_ASSET_BYTES} bytes: {path}",
            RuntimeWarning,
            stacklevel=2,
        )
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


CSS_PAGE_SIZE_RE = re.compile(
    r"^(?:[A-Za-z][A-Za-z0-9-]*(?:\s+(?:portrait|landscape))?|\d+(?:\.\d+)?(?:mm|cm|in|px|pt)\s+\d+(?:\.\d+)?(?:mm|cm|in|px|pt))$",
    re.IGNORECASE,
)

RTL_LANG_PREFIXES = ("ar", "fa", "he", "iw", "ku", "ps", "sd", "ug", "ur", "yi")

PLAYWRIGHT_NAMED_PAGE_FORMATS = {
    "letter",
    "legal",
    "tabloid",
    "ledger",
    "a0",
    "a1",
    "a2",
    "a3",
    "a4",
    "a5",
    "a6",
}
SUPPORTED_CSS_PAGE_NAMES = PLAYWRIGHT_NAMED_PAGE_FORMATS | {
    "b0",
    "b1",
    "b2",
    "b3",
    "b4",
    "b5",
    "b6",
}
PAGE_SIZE_NAME_RE = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9-]*)(?:\s+(?P<orientation>portrait|landscape))?$",
    re.IGNORECASE,
)

CUSTOM_PAGE_DIMENSIONS_RE = re.compile(
    r"^(?P<width>\d+(?:\.\d+)?(?:mm|cm|in|px|pt))\s+"
    r"(?P<height>\d+(?:\.\d+)?(?:mm|cm|in|px|pt))$",
    re.IGNORECASE,
)


def validate_page_size(value: str | None) -> str:
    """Return a safe PDF page-size expression or raise ``ValueError``.

    Chromium accepts a broad CSS ``@page size`` grammar, but treating arbitrary
    words as valid page sizes makes typos such as ``not-a-size`` silently fall
    back to A4. Keep explicit dimensions flexible, while named sizes are limited
    to the documented built-in families.
    """
    text = (value or "A4").strip()
    if not text:
        return "A4"

    dimension_match = CUSTOM_PAGE_DIMENSIONS_RE.fullmatch(text)
    if dimension_match:
        return text

    name_match = PAGE_SIZE_NAME_RE.fullmatch(text)
    if name_match:
        name = name_match.group("name")
        orientation = name_match.group("orientation")
        if name.lower() in SUPPORTED_CSS_PAGE_NAMES:
            return f"{name} {orientation.lower()}" if orientation else name

    raise ValueError(
        "page size must be a supported named size such as A4 or Letter, "
        'an optional orientation such as "A4 landscape", or explicit dimensions such as "210mm 297mm"'
    )


def _playwright_page_size_kwargs(value: str | None) -> dict[str, str]:
    """Return Playwright-compatible page size arguments.

    Playwright's ``format`` parameter accepts named formats such as A4 and
    Letter, but it rejects CSS size expressions like ``210mm 297mm`` or
    ``A4 landscape``. Those values are already emitted in a late ``@page`` CSS
    rule and honored through ``prefer_css_page_size=True``. For explicit
    width/height pairs we also pass the dimensions directly for renderer
    compatibility.
    """
    text = _css_page_size(value)
    dimension_match = CUSTOM_PAGE_DIMENSIONS_RE.match(text)
    if dimension_match:
        return {
            "width": dimension_match.group("width"),
            "height": dimension_match.group("height"),
        }
    if PAGE_SIZE_NAME_RE.fullmatch(text) and " " not in text and text.lower() in PLAYWRIGHT_NAMED_PAGE_FORMATS:
        return {"format": text}
    return {}


def normalize_language(value: Any, fallback: str = "") -> str:
    text = _stringify_metadata_value(value).strip().replace("_", "-").lower()
    return text or fallback


def _language_direction(lang: str | None) -> str:
    normalized = normalize_language(lang)
    if not normalized:
        return "auto"
    if normalized.startswith(RTL_LANG_PREFIXES):
        return "rtl"
    return "ltr"


def _localized_labels(lang: str | None) -> dict[str, str]:
    normalized = normalize_language(lang, "fa")
    family = "fa" if normalized.startswith(RTL_LANG_PREFIXES) else "en"
    labels = {
        "fa": {
            "generated_document": "سند تولیدشده",
            "pdf_report": "گزارش PDF",
            "author": "نویسنده",
            "authors": "نویسندگان",
            "date": "تاریخ",
            "institution": "مؤسسه",
            "course": "درس / دوره",
            "department": "دپارتمان",
            "supervisor": "راهنما / استاد",
            "student_id": "شماره دانشجویی",
            "group": "گروه",
            "version": "نسخه",
            "status": "وضعیت",
            "keywords": "کلیدواژه‌ها",
        },
        "en": {
            "generated_document": "Generated Document",
            "pdf_report": "PDF Report",
            "author": "Author",
            "authors": "Authors",
            "date": "Date",
            "institution": "Institution",
            "course": "Course",
            "department": "Department",
            "supervisor": "Supervisor",
            "student_id": "Student ID",
            "group": "Group",
            "version": "Version",
            "status": "Status",
            "keywords": "Keywords",
        },
    }
    return labels[family]


def _css_page_size(value: str | None) -> str:
    """Return a safe CSS @page size value.

    Playwright is asked to prefer CSS page size so the theme can control print
    margins. Therefore the selected CLI/GUI page size must also be emitted as a
    late CSS override; otherwise the theme-level ``@page { size: A4; }`` wins.
    """
    try:
        return validate_page_size(value)
    except ValueError:
        return "A4"


def normalize_document_direction(value: Any, *, default: str = "auto") -> str:
    text = _stringify_metadata_value(value).strip().lower()
    if text in {"rtl", "right-to-left", "right_to_left"}:
        return "rtl"
    if text in {"ltr", "left-to-right", "left_to_right"}:
        return "ltr"
    if text in {"auto", "automatic", "detect", "detected", ""}:
        return default if default in {"rtl", "ltr", "auto"} else "auto"
    return default if default in {"rtl", "ltr", "auto"} else "auto"


def _plain_html_text(html_text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _detect_document_direction(text: str, lang: str | None = None) -> str:
    """Choose a stable document-level direction for the root and layout.

    Individual paragraphs still use ``dir=auto``. This function only controls
    the page shell, TOC/list indentation direction, and default alignment.
    """
    rtl = 0
    ltr = 0
    for char in text:
        direction = unicodedata.bidirectional(char)
        if direction in {"R", "AL"}:
            rtl += 1
        elif direction == "L":
            ltr += 1
    if rtl or ltr:
        return "rtl" if rtl >= ltr else "ltr"

    lang_value = (lang or "").strip().lower()
    if lang_value.startswith(RTL_LANG_PREFIXES):
        return "rtl"
    return "ltr"


def _resolved_document_direction(result: MarkdownRenderResult, options: PdfOptions, lang: str) -> str:
    metadata = result.metadata
    requested = normalize_document_direction(
        options.document_direction
        if options.document_direction not in (None, "")
        else _first_metadata_value(metadata, "dir", "direction", "text_direction", "document_direction"),
        default="auto",
    )
    if requested in {"rtl", "ltr"}:
        return requested
    lang_direction = _language_direction(lang)
    if lang_direction in {"rtl", "ltr"}:
        return lang_direction
    sample = " ".join(
        part
        for part in [
            _stringify_metadata_value(metadata.get("title")),
            _stringify_metadata_value(metadata.get("subtitle")),
            _plain_html_text(result.toc_html),
            _plain_html_text(result.body_html),
        ]
        if part
    )
    return _detect_document_direction(sample, lang)


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


def _layout_css(options: PdfOptions, *, cover_full_bleed: bool = False, document_direction: str = "rtl") -> str:
    classes: list[str] = []
    doc_dir = normalize_document_direction(document_direction, default="rtl")
    inline_math_scale, display_math_scale = _math_scale_vars(options.theme)
    css_chunks = [
        f"""
      @page {{
        size: {_css_page_size(options.page_size)};
        margin: {"0" if cover_full_bleed else f"var(--page-margin-top, {options.margin_top}) var(--page-margin-x, {options.margin_x}) var(--page-margin-bottom, {options.margin_bottom})"};
      }}
      :root {{
        --page-margin-top: {"0" if cover_full_bleed else options.margin_top};
        --page-margin-bottom: {"0" if cover_full_bleed else options.margin_bottom};
        --page-margin-x: {"0" if cover_full_bleed else options.margin_x};
        --md2pdf-document-direction: {doc_dir};
        --md2pdf-inline-math-scale: {inline_math_scale};
        --md2pdf-display-math-scale: {display_math_scale};
      }}
      body.md2pdf-dir-rtl .md2pdf-document,
      body.md2pdf-dir-rtl .md2pdf-article {{ direction: rtl; }}
      body.md2pdf-dir-ltr .md2pdf-document,
      body.md2pdf-dir-ltr .md2pdf-article {{ direction: ltr; }}
      body.md2pdf-dir-ltr .md2pdf-cover {{ direction: ltr; }}
      body.md2pdf-dir-rtl .md2pdf-cover {{ direction: rtl; }}
      body .md2pdf-cover__top {{
        direction: ltr;
        justify-content: flex-start;
      }}
      body.md2pdf-dir-ltr .md2pdf-cover__content {{
        margin-left: 0;
        margin-right: auto;
        text-align: left;
      }}
      body.md2pdf-dir-rtl .md2pdf-cover__content {{
        margin-left: auto;
        margin-right: 0;
        text-align: right;
      }}
      body.md2pdf-dir-ltr .md2pdf-cover h1,
      body.md2pdf-dir-ltr .md2pdf-cover__subtitle,
      body.md2pdf-dir-ltr .md2pdf-cover__summary,
      body.md2pdf-dir-ltr .md2pdf-cover__detail {{ text-align: left; }}
      body.md2pdf-dir-rtl .md2pdf-cover h1,
      body.md2pdf-dir-rtl .md2pdf-cover__subtitle,
      body.md2pdf-dir-rtl .md2pdf-cover__summary,
      body.md2pdf-dir-rtl .md2pdf-cover__detail {{ text-align: right; }}
      body.md2pdf-dir-ltr .md2pdf-cover__subtitle {{ margin: -4mm auto 4mm 0; }}
      body.md2pdf-dir-rtl .md2pdf-cover__subtitle {{ margin: -4mm 0 4mm auto; }}
      body.md2pdf-dir-ltr .md2pdf-cover__summary {{ margin: 5mm auto 0 0; }}
      body.md2pdf-dir-rtl .md2pdf-cover__summary {{ margin: 5mm 0 0 auto; }}
      body.md2pdf-dir-ltr .md2pdf-cover__details {{ direction: ltr; }}
      body.md2pdf-dir-rtl .md2pdf-cover__details {{ direction: rtl; }}
      body.md2pdf-dir-ltr .md2pdf-cover__detail {{ direction: ltr; }}
      body.md2pdf-dir-rtl .md2pdf-cover__detail {{ direction: rtl; }}
      body.md2pdf-dir-ltr .md2pdf-cover__detail > span {{
        font-family: var(--font-en), var(--font-fa);
      }}
      body.md2pdf-dir-rtl .md2pdf-cover__detail > span {{
        font-family: var(--font-fa), var(--font-en);
        font-weight: 800;
        letter-spacing: 0;
        text-transform: none;
      }}
      body.md2pdf-dir-ltr .md2pdf-cover__detail > strong {{ font-family: var(--font-en), var(--font-fa); }}
      body.md2pdf-dir-rtl .md2pdf-cover__detail > strong {{ font-family: var(--font-fa), var(--font-en); }}
      body.md2pdf-dir-ltr .callout {{ direction: ltr; text-align: left; }}
      body.md2pdf-dir-rtl .callout {{ direction: rtl; text-align: right; }}
      body.md2pdf-dir-ltr .callout-title,
      body.md2pdf-dir-ltr .callout p {{ text-align: left; }}
      body.md2pdf-dir-rtl .callout-title,
      body.md2pdf-dir-rtl .callout p {{ text-align: right; }}
      body.md2pdf-dir-ltr .md2pdf-details {{ direction: ltr; text-align: left; }}
      body.md2pdf-dir-rtl .md2pdf-details {{ direction: rtl; text-align: right; }}
      .math,
      .md2pdf-article mjx-container {{
        direction: ltr;
        unicode-bidi: isolate;
      }}
      .math.inline {{
        display: inline;
        white-space: nowrap;
        font-size: 1em;
      }}
      .math.inline mjx-container,
      .md2pdf-article mjx-container:not([display="true"]) {{
        display: inline-block !important;
        font-size: var(--md2pdf-inline-math-scale) !important;
        line-height: 0 !important;
        margin: 0 0.06em !important;
        max-width: 100%;
        vertical-align: -0.12em !important;
      }}
      .math.display {{
        display: block;
        margin: 1.25em auto;
        padding: 3mm 2mm;
        overflow: hidden;
        max-width: 100%;
        text-align: center !important;
        page-break-inside: avoid;
        break-inside: avoid;
        font-size: 1em;
      }}
      .math.display mjx-container,
      .md2pdf-article mjx-container[display="true"] {{
        display: block !important;
        font-size: var(--md2pdf-display-math-scale) !important;
        line-height: 1.25 !important;
        margin: 0 auto !important;
        max-width: 100%;
        text-align: center !important;
      }}
      .md2pdf-article mjx-container svg {{ max-width: 100%; }}
      .md2pdf-image-placeholder {{
        display: block;
        margin: 1em 0;
        padding: 3mm 4mm;
        border: 1px dashed var(--line-strong, var(--line, #cbd5e1));
        border-radius: var(--radius, 10px);
        background: color-mix(in srgb, var(--soft, #f8fafc) 82%, transparent);
        color: var(--muted, #64748b);
        font: 600 8.5pt/1.55 var(--font-fa), var(--font-en), sans-serif;
        overflow-wrap: anywhere;
        page-break-inside: avoid;
        break-inside: avoid;
      }}
      .md2pdf-image-placeholder strong {{
        display: block;
        margin-bottom: 1mm;
        color: var(--ink, #172033);
        font-weight: 850;
      }}
      .md2pdf-image-placeholder span {{
        display: block;
      }}
      .table-wrap--wide table {{
        table-layout: fixed;
        width: 100%;
        font-size: min(8.2pt, 0.82em);
        line-height: 1.42;
      }}
      .table-wrap--wide th,
      .table-wrap--wide td {{
        padding: 1.4mm 1.6mm;
        overflow-wrap: anywhere;
        word-break: normal;
        hyphens: auto;
      }}
      .table-wrap--very-wide table {{
        font-size: min(6.8pt, 0.68em);
        line-height: 1.32;
      }}
      .table-wrap--very-wide th,
      .table-wrap--very-wide td {{
        padding: 1mm 1.1mm;
      }}
      .mermaid-diagram {{
        margin: 1.35em auto;
        padding: 4mm;
        border: 1px solid var(--md2pdf-mermaid-figure-border, var(--line, #dbe3ef));
        border-radius: var(--radius, 12px);
        background: var(--md2pdf-mermaid-figure-bg, color-mix(in srgb, var(--softer, #f8fafc) 86%, #ffffff));
        color: var(--md2pdf-mermaid-figure-ink, inherit);
        page-break-inside: avoid;
        break-inside: avoid;
        overflow: hidden;
      }}
      .mermaid-diagram figcaption {{
        margin: 0 0 3mm;
        color: var(--md2pdf-mermaid-caption-ink, var(--muted, #64748b));
        font: 700 8pt/1.4 var(--font-en), var(--font-fa);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        text-align: left;
      }}
      .md2pdf-mermaid-svg {{
        display: block;
        width: 100%;
        max-width: 100%;
        max-height: var(--md2pdf-mermaid-max-height, 185mm);
        height: auto;
        margin-inline: auto;
        object-fit: contain;
        font-family: var(--font-en), var(--font-fa), sans-serif;
      }}
      .mermaid-diagram--tall .md2pdf-mermaid-svg {{
        width: auto;
        max-width: 100%;
        max-height: var(--md2pdf-mermaid-tall-max-height, 185mm);
      }}
      .mermaid-diagram--wide .md2pdf-mermaid-svg {{
        width: 100%;
        max-height: var(--md2pdf-mermaid-wide-max-height, 120mm);
      }}
      .md2pdf-mermaid-bg {{
        fill: var(--md2pdf-mermaid-bg, color-mix(in srgb, var(--soft, #f4f7fb) 74%, #ffffff));
        stroke: var(--md2pdf-mermaid-border, var(--line, #dbe3ef));
        stroke-width: 1;
      }}
      .md2pdf-mermaid-node-shape {{
        fill: var(--md2pdf-mermaid-node-bg, #ffffff);
        stroke: var(--md2pdf-mermaid-stroke, var(--accent, var(--blue, #2563eb)));
        stroke-width: 1.5;
      }}
      .md2pdf-mermaid-node-label {{
        fill: var(--md2pdf-mermaid-node-ink, var(--ink, #172033));
        font-size: 12px;
        font-weight: 700;
        dominant-baseline: middle;
        unicode-bidi: plaintext;
      }}
      .md2pdf-mermaid-edge path {{
        fill: none;
        stroke: var(--md2pdf-mermaid-stroke, var(--accent, var(--blue, var(--line-strong, #2563eb))));
        stroke-width: 1.8;
      }}
      .md2pdf-mermaid-edge-dotted path {{
        stroke-dasharray: 5 4;
      }}
      .md2pdf-mermaid-edge-thick path {{
        stroke-width: 2.8;
      }}
      .md2pdf-mermaid-arrow-head {{
        fill: var(--md2pdf-mermaid-stroke, var(--accent, var(--blue, var(--line-strong, #2563eb))));
      }}
      .md2pdf-mermaid-edge-label {{
        fill: var(--md2pdf-mermaid-edge-ink, var(--muted, #64748b));
        font-size: 11px;
        font-weight: 700;
        paint-order: stroke;
        stroke: var(--md2pdf-mermaid-label-halo, #ffffff);
        stroke-width: 4px;
        stroke-linejoin: round;
        unicode-bidi: plaintext;
      }}
      .md2pdf-page-break {{
        display: block;
        height: 0;
        margin: 0;
        padding: 0;
        border: 0;
        overflow: hidden;
        clear: both;
        break-before: auto;
        page-break-before: auto;
        break-after: page;
        page-break-after: always;
      }}
      .heading-anchor {{
        opacity: 0.34;
        margin-inline-start: 0.35em;
        border: 0;
        color: var(--muted, #64748b);
        font-size: 0.78em;
        text-decoration: none;
      }}
      .heading-anchor:hover {{ opacity: 0.72; }}
      @media print {{
        .heading-anchor {{ display: none !important; }}
      }}
      .md2pdf-figure {{
        margin: 1.35em auto;
        text-align: center;
        page-break-inside: avoid;
        break-inside: avoid;
      }}
      .md2pdf-figure > img {{
        display: block;
        margin: 0 auto;
        max-width: 100%;
        height: auto;
      }}
      .md2pdf-figure > figcaption {{
        margin-top: 2mm;
        color: var(--muted, #64748b);
        font-size: 8.8pt;
        line-height: 1.55;
        text-align: center;
      }}
      .md2pdf-details {{
        margin: 1.2em 0;
        padding: 4mm 4.5mm;
        border: 1px solid var(--md2pdf-details-border, var(--line, #dbe3ef));
        border-radius: var(--radius, 12px);
        background: var(--md2pdf-details-bg, var(--softer, #f8fafc));
        color: var(--md2pdf-details-ink, inherit);
        page-break-inside: avoid;
        break-inside: avoid;
      }}
      .md2pdf-summary {{
        margin-bottom: 2mm;
        font-weight: 850;
        color: var(--md2pdf-details-title, var(--accent, var(--blue, #2563eb)));
      }}
      .code-block--numbered .codehilitetable {{
        width: 100%;
        border-collapse: collapse;
        margin: 0;
        background: var(--code-bg, #0f172a) !important;
      }}
      .code-block--numbered .codehilitetable td {{
        border: 0;
        padding: 0;
        background: transparent !important;
      }}
      .code-block--numbered .linenos {{
        width: 1%;
        padding: 4.2mm 2.2mm 4.2mm 4mm !important;
        color: rgba(226, 232, 240, 0.55) !important;
        text-align: right;
        user-select: none;
      }}
      .code-block--numbered .code {{
        padding: 0 !important;
      }}
      .codehilite .hll {{
        display: block;
        background-color: rgba(250, 204, 21, 0.18) !important;
      }}
    """
    ]
    if cover_full_bleed:
        classes.append("md2pdf-cover-full-bleed")
    classes.append(f"md2pdf-dir-{doc_dir}")
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
    lang: str = "fa",
    document_direction: str = "rtl",
    labels: dict[str, str] | None = None,
) -> str:
    labels = labels or _localized_labels(lang)
    detail_cards: list[str] = []
    author_items = _metadata_items(author)
    if author_items:
        label = labels["authors"] if len(author_items) > 1 else labels["author"]
        detail_cards.append(_cover_detail(label, author_items, multiline=True))
    if date:
        detail_cards.append(_cover_detail(labels["date"], date))
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
    else:
        cover_classes += " md2pdf-cover--unbranded"

    return f"""
      <header class="{cover_classes}" lang="{html.escape(str(lang))}" dir="{html.escape(document_direction)}">
        <div class="md2pdf-cover__decor md2pdf-cover__decor--one" aria-hidden="true"></div>
        <div class="md2pdf-cover__decor md2pdf-cover__decor--two" aria-hidden="true"></div>
        <section class="md2pdf-cover__top" dir="ltr">
          {brand_html}
        </section>
        <section class="md2pdf-cover__content">
          <span class="md2pdf-cover__eyebrow">{html.escape(_stringify_metadata_value(eyebrow) or labels["generated_document"])}</span>
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
    warnings.warn(
        "Bundled MathJax asset missing; equations will remain in TeX form.",
        RuntimeWarning,
        stacklevel=2,
    )
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
    raw_lang = _stringify_metadata_value(metadata.get("lang"))
    document_direction = _resolved_document_direction(result, options, raw_lang)
    lang = raw_lang or ("fa" if document_direction == "rtl" else "en")
    labels = _localized_labels(lang)
    date = _first_metadata_value(metadata, "date")
    subtitle = _first_metadata_value(metadata, "subtitle", "subject")
    eyebrow = (
        _first_metadata_value(
            metadata,
            "cover_label",
            "cover_eyebrow",
            "document_label",
            "eyebrow",
            "document_type",
            "type",
        )
        or labels["generated_document"]
    )
    base_href = options.input_path.resolve().parent.as_uri() + "/"
    css_variables, body_classes = _layout_css(
        options,
        cover_full_bleed=cover_full_bleed,
        document_direction=document_direction,
    )

    cover_options = options
    metadata_logo = _metadata_path(_first_metadata_value(metadata, "cover_logo", "logo"), options.input_path.resolve().parent)
    if metadata_logo and not options.cover_logo:
        cover_options = replace(options, cover_logo=metadata_logo)

    extra_details: list[tuple[str, Any]] = []
    detail_fields = [
        (labels["institution"], "institution", "university", "organization"),
        (labels["course"], "course", "lesson"),
        (labels["department"], "department"),
        (labels["supervisor"], "supervisor", "teacher", "advisor"),
        (labels["student_id"], "student_id", "student_number"),
        (labels["group"], "group", "team"),
        (labels["version"], "version"),
        (labels["status"], "status"),
        (labels["keywords"], "keywords", "tags"),
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
            lang=str(lang),
            document_direction=document_direction,
            labels=labels,
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
<html lang="{html.escape(str(lang))}" dir="{html.escape(document_direction)}">
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
<body class="md2pdf-theme-{html.escape(theme_name)} {html.escape(body_classes)}" dir="{html.escape(document_direction)}">
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
    # Header/footer templates do not inherit the article bidi helpers. Keep the
    # footer slot LTR for stable left/right layout, but isolate the title so a
    # mixed Persian/English title keeps its glyph order and does not leak into
    # the page counter.
    return f"""
    <div style="width:100%; font-size:8px; color:#64748b; padding:0 16mm; font-family:Arial, sans-serif;">
      <div style="border-top:1px solid #dbe3ef; padding-top:5px; display:flex; justify-content:space-between; align-items:center; gap:8mm; direction:ltr;">
        <span dir="ltr" style="direction:ltr; unicode-bidi:isolate; text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-family:Vazirmatn, 'Noto Sans Arabic', Tahoma, Arial, sans-serif;">{safe_title}</span>
        <span dir="ltr" style="direction:ltr; unicode-bidi:isolate; white-space:nowrap; font-family:Arial, sans-serif;"><span class="pageNumber"></span>/<span class="totalPages"></span></span>
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
        except Exception as exc:
            warnings.warn(
                f"MathJax rendering failed; equations may remain in TeX form: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
    page.emulate_media(media="print")
    pdf_kwargs: dict[str, Any] = {
        "path": str(path),
        "print_background": True,
        "prefer_css_page_size": True,
        "margin": {"top": "0", "right": "0", "bottom": "0", "left": "0"},
    }
    pdf_kwargs.update(_playwright_page_size_kwargs(options.page_size))
    if display_footer and not options.no_header_footer:
        pdf_kwargs.update(
            {
                "display_header_footer": True,
                "header_template": "<div></div>",
                "footer_template": _footer_template(str(title), options.theme),
            }
        )
    page.pdf(**pdf_kwargs)


def _pdf_date(value: datetime | None = None) -> str:
    dt = value or datetime.now(timezone.utc).astimezone()
    offset = dt.strftime("%z")
    tz = "Z" if not offset else f"{offset[:3]}'{offset[3:]}'"
    return dt.strftime("D:%Y%m%d%H%M%S") + tz


def _keywords_metadata(metadata: dict[str, Any]) -> str:
    value = _first_metadata_value(metadata, "keywords", "tags")
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_metadata_items(value))
    return _stringify_metadata_value(value, item_separator=", ")


def _pdf_metadata(result: MarkdownRenderResult, options: PdfOptions, title: str) -> dict[str, str]:
    source = result.metadata
    author = options.author if options.author is not None else _first_metadata_value(source, "authors", "author")
    description = (
        options.description
        if options.description is not None
        else _first_metadata_value(source, "description", "summary", "subject")
    )
    data = {
        "/Title": str(title or result.title or "Document"),
        "/Creator": "Mardas MD2PDF",
        "/Producer": "Mardas MD2PDF + Playwright/Chromium + pypdf",
        "/CreationDate": _pdf_date(),
        "/ModDate": _pdf_date(),
    }
    author_text = _stringify_metadata_value(author)
    if author_text:
        data["/Author"] = author_text
    subject_text = _stringify_metadata_value(description)
    if subject_text:
        data["/Subject"] = subject_text
    keywords_text = _keywords_metadata(source)
    if keywords_text:
        data["/Keywords"] = keywords_text
    return data


def _outline_source_entries(result: MarkdownRenderResult) -> list[tuple[int, str]]:
    """Return clean heading entries for PDF outline creation."""
    entries: list[tuple[int, str]] = []
    for entry in result.toc_entries:
        if len(entry) < 2:
            continue
        level = max(1, min(int(entry[0]), 6))
        title = _stringify_metadata_value(entry[1]).strip()
        if title:
            entries.append((level, title))
    return entries


def _normalize_pdf_search_text(value: str) -> str:
    """Normalize extracted PDF text and heading titles for fuzzy page lookup."""
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("‌", " ").replace("‏", " ").replace("‎", " ")
    text = re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)
    return text.casefold()


def _pdf_page_texts(reader: PdfReader) -> list[str]:
    texts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        texts.append(_normalize_pdf_search_text(text))
    return texts


def _locate_outline_pages(
    page_texts: list[str],
    outline_entries: list[tuple[int, str]],
    *,
    start_page: int = 0,
) -> list[tuple[int, str, int]]:
    """Map outline headings to best-effort PDF page indexes.

    Chromium does not expose named destinations after ``page.pdf``. pypdf text
    extraction gives a stable enough fallback for generated documents; when a
    heading cannot be found, the bookmark keeps the previous page so the outline
    remains usable instead of disappearing entirely.
    """
    if not page_texts:
        return []
    page_count = len(page_texts)
    current_page = max(0, min(start_page, page_count - 1))
    located: list[tuple[int, str, int]] = []

    for level, title in outline_entries:
        needle = _normalize_pdf_search_text(title)
        page_index = current_page
        if needle:
            for index in range(current_page, page_count):
                if needle in page_texts[index]:
                    page_index = index
                    break
        current_page = page_index
        located.append((max(1, min(level, 6)), title, page_index))
    return located


def _add_pdf_outline(writer: PdfWriter, outline_entries: list[tuple[int, str, int]]) -> None:
    """Attach a nested PDF outline to ``writer`` from located heading entries."""
    parents: dict[int, Any] = {}
    page_count = len(writer.pages)
    for level, title, page_index in outline_entries:
        if not title or page_index < 0 or page_index >= page_count:
            continue
        parent = parents.get(level - 1)
        item = writer.add_outline_item(title, page_index, parent=parent)
        parents[level] = item
        for child_level in [key for key in parents if key > level]:
            del parents[child_level]


def _should_disable_chromium_sandbox(mode: str) -> bool:
    normalized = (mode or "auto").strip().lower()
    if normalized == "off":
        return True
    if normalized == "on":
        return False
    if normalized != "auto":
        raise ValueError("chromium_sandbox must be one of: auto, on, off")
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid and geteuid() == 0)


def _chromium_launch_args(options: PdfOptions) -> list[str]:
    args = [
        "--font-render-hinting=medium",
        "--disable-dev-shm-usage",
    ]
    if _should_disable_chromium_sandbox(options.chromium_sandbox):
        args.append("--no-sandbox")
    return args


def _copy_pdf_with_metadata(
    input_path: Path,
    output_path: Path,
    metadata: dict[str, str],
    outline_source_entries: list[tuple[int, str]] | None = None,
    *,
    outline_start_page: int = 0,
) -> None:
    reader = PdfReader(str(input_path))
    page_texts = _pdf_page_texts(reader) if outline_source_entries else []
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata(metadata)
    if outline_source_entries:
        _add_pdf_outline(
            writer,
            _locate_outline_pages(
                page_texts,
                outline_source_entries,
                start_page=outline_start_page,
            ),
        )
    with output_path.open("wb") as fh:
        writer.write(fh)
    writer.close()


def _apply_pdf_metadata(pdf_path: Path, metadata: dict[str, str]) -> None:
    tmp_path = pdf_path.with_suffix(pdf_path.suffix + ".metadata.tmp")
    _copy_pdf_with_metadata(pdf_path, tmp_path, metadata)
    tmp_path.replace(pdf_path)


def _merge_pdfs(
    parts: list[Path],
    output_path: Path,
    metadata: dict[str, str] | None = None,
    outline_source_entries: list[tuple[int, str]] | None = None,
    *,
    outline_start_page: int = 0,
) -> None:
    writer = PdfWriter()
    page_texts: list[str] = []
    for part in parts:
        reader = PdfReader(str(part))
        if outline_source_entries:
            page_texts.extend(_pdf_page_texts(reader))
        for page in reader.pages:
            writer.add_page(page)
    if metadata:
        writer.add_metadata(metadata)
    if outline_source_entries:
        _add_pdf_outline(
            writer,
            _locate_outline_pages(
                page_texts,
                outline_source_entries,
                start_page=outline_start_page,
            ),
        )
    with output_path.open("wb") as fh:
        writer.write(fh)
    writer.close()


def convert(options: PdfOptions) -> Path:
    progress = options.progress
    _report_progress(progress, "Reading Markdown", 0.03)

    options.input_path = Path(options.input_path)
    options.output_path = Path(options.output_path)
    result = render_markdown_file(
        options.input_path,
        toc=options.toc,
        toc_depth=options.toc_depth,
        code_style=_code_style(options.theme),
        unsafe_html=options.unsafe_html,
        allow_remote_images=options.allow_remote_assets,
    )
    _report_progress(progress, "Markdown parsed", 0.16)

    title = options.title or _stringify_metadata_value(result.metadata.get("title")) or result.title
    pdf_metadata = _pdf_metadata(result, options, str(title))
    outline_source_entries = _outline_source_entries(result)

    options.output_path.parent.mkdir(parents=True, exist_ok=True)

    full_debug_html = build_html(result, options, include_cover=True, include_content=True, include_watermark=True)
    if options.debug_html:
        options.debug_html.parent.mkdir(parents=True, exist_ok=True)
        options.debug_html.write_text(full_debug_html, encoding="utf-8")
    _report_progress(progress, "HTML prepared", 0.28)

    executable = options.chromium_path or shutil.which("chromium") or shutil.which("google-chrome")

    with tempfile.TemporaryDirectory(prefix="mardas-md2pdf-") as tmpdir:
        tmp = Path(tmpdir)
        with sync_playwright() as p:
            _report_progress(progress, "Starting Chromium", 0.36)
            launch_kwargs: dict[str, Any] = {
                "headless": True,
                "args": _chromium_launch_args(options),
            }
            if executable:
                launch_kwargs["executable_path"] = executable
            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page(device_scale_factor=1)
            page.set_default_timeout(options.timeout_ms)

            try:
                if options.cover:
                    cover_pdf = tmp / "cover.pdf"
                    cover_html = build_html(result, options, include_cover=True, include_content=False, include_watermark=False, cover_full_bleed=True)
                    _report_progress(progress, "Rendering cover", 0.48)
                    _render_pdf(page, cover_html, options, cover_pdf, display_footer=False, title=str(title))

                    content_pdf = tmp / "content.pdf"
                    content_html = build_html(result, options, include_cover=False, include_content=True, include_watermark=True)
                    _report_progress(progress, "Rendering content", 0.72)
                    _render_pdf(page, content_html, options, content_pdf, display_footer=True, title=str(title))

                    _report_progress(progress, "Merging PDF parts", 0.91)
                    cover_page_count = len(PdfReader(str(cover_pdf)).pages)
                    _merge_pdfs(
                        [cover_pdf, content_pdf],
                        options.output_path,
                        pdf_metadata,
                        outline_source_entries,
                        outline_start_page=cover_page_count,
                    )
                else:
                    content_pdf = tmp / "content.pdf"
                    html_text = build_html(result, options, include_cover=False, include_content=True, include_watermark=True)
                    _report_progress(progress, "Rendering PDF", 0.72)
                    _render_pdf(page, html_text, options, content_pdf, display_footer=True, title=str(title))

                    _report_progress(progress, "Writing metadata", 0.91)
                    _copy_pdf_with_metadata(
                        content_pdf,
                        options.output_path,
                        pdf_metadata,
                        outline_source_entries,
                    )
            finally:
                browser.close()
    _report_progress(progress, "PDF created", 1.0)
    return options.output_path
