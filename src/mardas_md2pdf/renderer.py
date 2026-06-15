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
from urllib.parse import quote, unquote

from playwright.sync_api import Page, sync_playwright
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, Fit, NameObject, NumberObject, TextStringObject

from .appearance import (
    Appearance,
    appearance_body_classes,
    appearance_from_metadata,
    code_style_for_appearance,
    footer_kind,
    math_scale_vars,
    palette_css,
    resolve_appearance,
    style_css_file,
)
from .markdown import MarkdownRenderResult, render_markdown_file


MAX_EMBED_ASSET_BYTES = 20 * 1024 * 1024
ProgressCallback = Callable[[str, float], None]
BRANDING_MODES = ("off", "subtle", "full")
PRODUCT_BRAND_NAME = "Mardas MD2PDF"
PRODUCT_BRAND_FOOTER = "Markdown to PDF Engine"


def validate_branding_mode(value: str | None) -> str:
    """Validate and normalize cover branding mode names."""
    normalized = str(value or "off").strip().lower()
    if normalized not in BRANDING_MODES:
        allowed = ", ".join(BRANDING_MODES)
        raise ValueError(f"must be one of: {allowed}")
    return normalized


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
    style: str | None = None
    palette: str | None = None
    mode: str | None = None
    cover: bool = True
    cover_logo: Path | None = None
    cover_logo_enabled: bool = True
    branding: str | None = None
    brand_name: str | None = None
    brand_logo: Path | None = None
    brand_footer: str | None = None
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



def _resolved_appearance(metadata: dict[str, Any], options: PdfOptions) -> Appearance:
    metadata_appearance = appearance_from_metadata(metadata)
    return resolve_appearance(
        style=options.style or metadata_appearance.style,
        palette=options.palette or metadata_appearance.palette,
        mode=options.mode or metadata_appearance.mode,
    )


def _style_css(appearance: Appearance) -> str:
    return _asset_text(style_css_file(appearance.style, appearance.mode))


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
    return _image_data_uri(options.cover_logo or options.brand_logo or _default_logo_path())


def _metadata_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _metadata_nested_value(metadata: dict[str, Any], section: str, *keys: str) -> Any:
    nested = _metadata_dict(metadata.get(section))
    for key in keys:
        value = nested.get(key)
        if value not in (None, ""):
            return value
    return ""


@dataclass(slots=True)
class CoverBranding:
    mode: str
    name: str
    footer: str
    logo: Path | None
    product: bool = False


@dataclass(slots=True)
class FooterContext:
    title: str
    metadata: str = ""
    lang: str = "en"
    document_direction: str = "ltr"


def _resolve_cover_branding(metadata: dict[str, Any], options: PdfOptions, base_dir: Path) -> CoverBranding:
    branding_meta = _metadata_dict(metadata.get("branding"))
    explicit_mode = (
        options.branding
        or branding_meta.get("mode")
        or _first_metadata_value(metadata, "branding_mode", "brand_mode")
    )

    brand_name = (
        options.brand_name
        or _metadata_nested_value(metadata, "brand", "name", "title", "label")
        or branding_meta.get("name")
        or _first_metadata_value(metadata, "brand_name")
    )
    brand_footer = (
        options.brand_footer
        or _metadata_nested_value(metadata, "brand", "footer", "tagline", "subtitle")
        or branding_meta.get("footer")
        or branding_meta.get("tagline")
        or _first_metadata_value(metadata, "brand_footer", "brand_tagline")
    )

    logo_value = (
        _metadata_nested_value(metadata, "brand", "logo", "image")
        or branding_meta.get("logo")
        or branding_meta.get("image")
        or _first_metadata_value(metadata, "brand_logo")
    )
    metadata_brand_logo = _metadata_path(logo_value, base_dir)
    logo = options.brand_logo or metadata_brand_logo or options.cover_logo

    has_user_brand = bool(_stringify_metadata_value(brand_name) or _stringify_metadata_value(brand_footer) or logo)
    mode = validate_branding_mode(explicit_mode or ("full" if has_user_brand else "off"))

    product_brand = not has_user_brand
    name = _stringify_metadata_value(brand_name) or PRODUCT_BRAND_NAME
    footer = _stringify_metadata_value(brand_footer) or (PRODUCT_BRAND_FOOTER if product_brand else "")

    if not options.cover_logo_enabled:
        logo = None
    if product_brand and mode == "full" and logo is None:
        logo = _default_logo_path()

    return CoverBranding(mode=mode, name=name, footer=footer, logo=logo, product=product_brand)


def _brand_logo_html(branding: CoverBranding) -> str:
    logo_uri = _image_data_uri(branding.logo) if branding.logo else None
    if logo_uri:
        return f'<img class="md2pdf-cover__logo" src="{html.escape(logo_uri)}" alt="{html.escape(branding.name)} logo">'
    initial = (branding.name.strip()[:1] or "M").upper()
    return f'<span class="md2pdf-cover__logo md2pdf-cover__logo--fallback">{html.escape(initial)}</span>'


def _cover_brand_html(branding: CoverBranding) -> str:
    if branding.mode == "off":
        return ""
    if branding.mode == "subtle" and branding.product:
        return (
            '<div class="md2pdf-cover__brand md2pdf-cover__brand--subtle" dir="ltr">'
            '<span class="md2pdf-cover__brand-copy">'
            f'<strong>Generated with {html.escape(PRODUCT_BRAND_NAME)}</strong>'
            '</span>'
            '</div>'
        )
    mark_html = '' if branding.mode == "subtle" else f'<span class="md2pdf-cover__mark">{_brand_logo_html(branding)}</span>'
    footer_html = f'<em>{html.escape(branding.footer)}</em>' if branding.footer else ""
    return (
        f'<div class="md2pdf-cover__brand md2pdf-cover__brand--{html.escape(branding.mode)}" dir="ltr">'
        f'{mark_html}'
        '<span class="md2pdf-cover__brand-copy">'
        f'<strong>{html.escape(branding.name)}</strong>'
        f'{footer_html}'
        '</span>'
        '</div>'
    )


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

    Playwright is asked to prefer CSS page size so the style can control print
    margins. Therefore the selected CLI/GUI page size must also be emitted as a
    late CSS override; otherwise the style-level ``@page { size: A4; }`` wins.
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


def _footer_context(result: MarkdownRenderResult, options: PdfOptions, title: str) -> FooterContext:
    """Build the small running metadata line used in page footers."""
    metadata = result.metadata
    raw_lang = _stringify_metadata_value(metadata.get("lang"))
    document_direction = _resolved_document_direction(result, options, raw_lang)
    lang = raw_lang or ("fa" if document_direction == "rtl" else "en")

    pieces: list[str] = []
    for key in ("version", "status", "date"):
        value = _stringify_metadata_value(metadata.get(key)).strip()
        if value and value not in pieces:
            pieces.append(value)
    course = _stringify_metadata_value(_first_metadata_value(metadata, "course", "institution")).strip()
    if course and course not in pieces:
        pieces.insert(0, course)
    metadata_line = " · ".join(pieces[:3])
    return FooterContext(
        title=str(title or result.title or "Document"),
        metadata=metadata_line,
        lang=lang,
        document_direction=document_direction,
    )


def _footer_page_label(lang: str | None) -> str:
    return "صفحه" if normalize_language(lang).startswith(RTL_LANG_PREFIXES) else "Page"


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
    appearance = resolve_appearance(style=options.style, palette=options.palette, mode=options.mode)
    inline_math_scale, display_math_scale = math_scale_vars(appearance.style)
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
      .md2pdf-cover--branding-off .md2pdf-cover__top {{ min-height: 14mm; }}
      .md2pdf-cover__brand--subtle {{
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        opacity: 0.72;
      }}
      .md2pdf-cover__brand--subtle .md2pdf-cover__brand-copy strong {{
        color: var(--muted, #64748b) !important;
        font-size: 6.4pt !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
      }}
      .md2pdf-cover__brand--subtle .md2pdf-cover__brand-copy em {{
        display: none !important;
      }}
      .md2pdf-document {{
        position: relative;
        z-index: 1;
      }}
      .md2pdf-watermark {{
        z-index: 2 !important;
        mix-blend-mode: multiply;
      }}
      body.md2pdf-style-textbook.md2pdf-mode-dark .md2pdf-watermark {{
        mix-blend-mode: screen;
      }}
      body.md2pdf-style-textbook.md2pdf-mode-dark .md2pdf-watermark--text {{
        color: #f8fafc;
      }}
      body.md2pdf-style-textbook.md2pdf-mode-dark .md2pdf-watermark--image img {{
        filter: invert(1) grayscale(1);
      }}
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
        shape-rendering: geometricPrecision;
        text-rendering: geometricPrecision;
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
      .md2pdf-mermaid-node-detail {{
        fill: none;
        opacity: .66;
        pointer-events: none;
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
      .md2pdf-mermaid-edge-label-group {{
        pointer-events: none;
      }}
      .md2pdf-mermaid-edge-label-bg {{
        fill: var(--md2pdf-mermaid-label-bg, color-mix(in srgb, var(--paper, #ffffff) 92%, transparent));
        stroke: var(--md2pdf-mermaid-label-border, color-mix(in srgb, var(--md2pdf-mermaid-stroke, var(--accent, #2563eb)) 22%, transparent));
        stroke-width: 0.8;
      }}
      .md2pdf-mermaid-edge-label {{
        fill: var(--md2pdf-mermaid-edge-ink, var(--muted, #64748b));
        font-size: 11px;
        font-weight: 750;
        dominant-baseline: middle;
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

      code,
      pre,
      kbd,
      samp,
      .code-block,
      .code-caption,
      .code-table,
      .highlight,
      .md2pdf-caption--code {{
        unicode-bidi: isolate;
      }}
      body.md2pdf-dir-rtl code,
      body.md2pdf-dir-rtl pre,
      body.md2pdf-dir-rtl kbd,
      body.md2pdf-dir-rtl samp,
      body.md2pdf-dir-rtl .code-block,
      body.md2pdf-dir-rtl .code-caption,
      body.md2pdf-dir-rtl .code-table,
      body.md2pdf-dir-rtl .highlight,
      body.md2pdf-dir-rtl .md2pdf-caption--code {{
        direction: ltr;
        text-align: left;
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
      .md2pdf-caption {{
        color: var(--md2pdf-caption-ink, var(--muted, #64748b));
        font-size: var(--md2pdf-caption-size, 8.7pt);
        line-height: 1.48;
        font-weight: 650;
        break-inside: avoid;
        page-break-inside: avoid;
      }}
      .md2pdf-caption--figure,
      .md2pdf-caption--diagram {{
        text-align: center;
      }}
      .md2pdf-caption--code {{
        text-align: start;
      }}
      table > caption.md2pdf-caption--table {{
        caption-side: top;
        padding: 2.2mm 3mm;
        border-bottom: 1px solid var(--line, #dbe3ef);
        background: var(--md2pdf-table-caption-bg, color-mix(in srgb, var(--soft, #f4f7fb) 82%, #ffffff));
        color: var(--md2pdf-table-caption-ink, var(--ink, #172033));
        font: 750 8.6pt/1.45 var(--font-fa), var(--font-en), sans-serif;
        text-align: start;
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
      @media print {{
        .md2pdf-article {{
          orphans: 3;
          widows: 3;
        }}
        h1, h2, h3, h4, h5, h6 {{
          break-after: avoid-page;
          break-inside: avoid;
          page-break-after: avoid;
          page-break-inside: avoid;
          orphans: 3;
          widows: 3;
        }}
        h1 + *, h2 + *, h3 + *, h4 + *, h5 + *, h6 + * {{
          break-before: avoid-page;
          page-break-before: avoid;
        }}
        p, li, blockquote, .callout, .md2pdf-details {{
          orphans: 3;
          widows: 3;
        }}
        blockquote, .callout, .md2pdf-details, .md2pdf-image-placeholder,
        .math.display, .md2pdf-figure, .mermaid-diagram {{
          break-inside: avoid;
          page-break-inside: avoid;
        }}
        .code-block {{
          break-inside: avoid;
          page-break-inside: avoid;
        }}
        .code-block--long, .code-block--very-long {{
          break-inside: auto;
          page-break-inside: auto;
        }}
        .code-block figcaption, .mermaid-diagram figcaption, .md2pdf-figure > figcaption,
        table > caption.md2pdf-caption--table, .md2pdf-caption {{
          break-after: avoid;
          page-break-after: avoid;
          break-inside: avoid;
          page-break-inside: avoid;
        }}
        .code-block pre {{
          white-space: pre-wrap;
          overflow-wrap: anywhere;
          word-break: normal;
        }}
        .code-block--numbered .code pre {{
          white-space: pre-wrap;
          overflow-wrap: anywhere;
        }}
        .table-wrap {{
          break-inside: avoid;
          page-break-inside: avoid;
        }}
        .table-wrap table caption {{
          break-after: avoid-page;
          page-break-after: avoid;
        }}
        .table-wrap--long, .table-wrap--wide, .table-wrap--very-wide {{
          break-inside: auto;
          page-break-inside: auto;
        }}
        .table-wrap--long table, .table-wrap--wide table, .table-wrap--very-wide table {{
          break-inside: auto;
          page-break-inside: auto;
        }}
        thead {{
          display: table-header-group;
        }}
        tr {{
          break-inside: avoid;
          page-break-inside: avoid;
        }}
      }}
      .code-block--numbered .codehilite > .table-wrap {{
        margin: 0;
        border: 0;
        border-radius: 0;
        overflow: hidden;
      }}
      .code-block--numbered .codehilitetable {{
        width: 100%;
        border-collapse: collapse;
        margin: 0;
        background: var(--code-bg, #0f172a) !important;
      }}
      .code-block--numbered .codehilitetable td {{
        border: 0;
        padding: 0 !important;
        background: transparent !important;
        vertical-align: top;
      }}
      .code-block--numbered .linenos {{
        width: 1%;
        color: color-mix(in srgb, var(--code-ink, #e2e8f0) 46%, transparent) !important;
        text-align: right;
        user-select: none;
      }}
      .code-block--numbered .linenos pre {{
        margin: 0 !important;
        padding: 4.2mm 2.2mm 4.2mm 4mm !important;
        background: transparent !important;
        color: inherit !important;
        line-height: inherit;
        text-align: right;
      }}
      body.md2pdf-style-textbook .code-block--numbered .linenos pre,
      body.md2pdf-style-academic .code-block--numbered .linenos pre {{
        padding-top: 3.5mm !important;
        padding-bottom: 3.5mm !important;
      }}
      .code-block--numbered .code {{
        padding: 0 !important;
      }}
      .code-block--numbered .code pre {{
        margin: 0 !important;
      }}
      .codehilite .hll {{
        display: block;
        background-color: color-mix(in srgb, var(--accent-soft, #fef3c7) 72%, transparent) !important;
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
    branding: CoverBranding | None = None,
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
    subtitle_text = _stringify_metadata_value(subtitle)
    subtitle_html = (
        f'<p class="md2pdf-cover__subtitle" dir="auto">{html.escape(subtitle_text)}</p>' if subtitle_text else ""
    )
    summary_html = _paragraph_block_html(description, "md2pdf-cover__summary")
    details_html = ''.join(detail_cards)
    branding = branding or CoverBranding(mode="off", name=PRODUCT_BRAND_NAME, footer=PRODUCT_BRAND_FOOTER, logo=None, product=True)
    brand_html = _cover_brand_html(branding)
    cover_classes = f"md2pdf-cover md2pdf-cover--branding-{branding.mode}"
    if branding.mode == "off":
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
    appearance = _resolved_appearance(result.metadata, options)
    options = replace(options, style=appearance.style, palette=appearance.palette, mode=appearance.mode)
    style_css = _style_css(appearance)
    appearance_css = palette_css(appearance.palette, appearance.mode, appearance.style)
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
    base_dir = options.input_path.resolve().parent
    metadata_logo = _metadata_path(_first_metadata_value(metadata, "cover_logo", "logo"), base_dir)
    if metadata_logo and not options.cover_logo:
        cover_options = replace(options, cover_logo=metadata_logo)
    branding = _resolve_cover_branding(metadata, cover_options, base_dir)

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
            branding=branding,
        )
        if include_cover and options.cover
        else ""
    )
    content = ""
    if include_content:
        content = f"{result.toc_html}{result.body_html}"
    watermark = _watermark_html(options) if include_content and include_watermark else ""

    appearance_classes = appearance_body_classes(appearance)

    return f"""<!doctype html>
<html lang="{html.escape(str(lang))}" dir="{html.escape(document_direction)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base href="{base_href}">
  <title>{html.escape(str(title))}</title>
  <style>{font_faces}</style>
  <style>{result.pygments_css}</style>
  <style>{style_css}</style>
  <style>{appearance_css}</style>
  <style>{css_variables}</style>
  {_mathjax_block(options)}
</head>
<body class="{html.escape(appearance_classes)} {html.escape(body_classes)}" dir="{html.escape(document_direction)}">
  {watermark}
  <main class="md2pdf-document">
    <article class="md2pdf-article">
      {cover}
      {content}
    </article>
  </main>
</body>
</html>"""



def _footer_template(
    context: FooterContext | str,
    style: str = "modern",
    mode: str = "light",
) -> str:
    if isinstance(context, FooterContext):
        title = context.title
        metadata = context.metadata
        lang = context.lang
        document_direction = context.document_direction
    else:
        title = str(context)
        metadata = ""
        lang = "en"
        document_direction = "ltr"

    kind = footer_kind(style, mode)
    color = "#64748b"
    rule_color = "#dbe3ef"
    font_family = "Vazirmatn, 'Noto Sans Arabic', Tahoma, Arial, sans-serif"
    title_weight = "650"
    page_weight = "700"
    if kind == "textbook-light":
        color = "#374151"
        rule_color = "#d1d5db"
    elif kind == "textbook-dark":
        color = "#cbd5e1"
        rule_color = "#475569"
    elif kind == "academic":
        color = "#4b5563"
        rule_color = "#9ca3af"
        font_family = "Georgia, 'Times New Roman', Vazirmatn, serif"
        title_weight = "600"
        page_weight = "600"

    safe_title = html.escape(title)
    safe_meta = html.escape(metadata)
    page_label = html.escape(_footer_page_label(lang))
    title_align = "right" if document_direction == "rtl" else "left"
    meta_html = (
        f'<span dir="auto" style="min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-align:center; opacity:.78; font-weight:600;">{safe_meta}</span>'
        if safe_meta
        else '<span aria-hidden="true"></span>'
    )
    page_html = (
        f'<span dir="ltr" style="direction:ltr; unicode-bidi:isolate; white-space:nowrap; text-align:right; font-weight:{page_weight}; font-family:Arial, sans-serif;">'
        f'{page_label} <span class="pageNumber"></span>/<span class="totalPages"></span></span>'
    )
    return f"""
    <div style="width:100%; font-size:8px; color:{color}; padding:0 16mm; font-family:{font_family};">
      <div style="border-top:1px solid {rule_color}; padding-top:4.5px; display:grid; grid-template-columns:minmax(0,1.4fr) minmax(0,.9fr) minmax(22mm,.6fr); align-items:center; gap:5mm; direction:ltr;">
        <span dir="auto" style="min-width:0; direction:{html.escape(document_direction)}; unicode-bidi:plaintext; text-align:{title_align}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:{title_weight};">{safe_title}</span>
        {meta_html}
        {page_html}
      </div>
    </div>
    """


def _render_pdf(page: Page, html_text: str, options: PdfOptions, path: Path, *, display_footer: bool, footer_context: FooterContext | str) -> None:
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
                "footer_template": _footer_template(footer_context, options.style, options.mode),
            }
        )
    page.pdf(**pdf_kwargs)


def _source_date_epoch() -> datetime | None:
    raw_value = os.environ.get("SOURCE_DATE_EPOCH")
    if raw_value in (None, ""):
        return None
    try:
        timestamp = int(raw_value)
    except ValueError:
        warnings.warn(
            "Ignoring invalid SOURCE_DATE_EPOCH value; expected a Unix timestamp.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    if timestamp < 0:
        warnings.warn(
            "Ignoring negative SOURCE_DATE_EPOCH value; expected a non-negative Unix timestamp.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc)


def _pdf_date(value: datetime | None = None) -> str:
    dt = value or _source_date_epoch() or datetime.now(timezone.utc).astimezone()
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


OutlineSourceEntry = tuple[int, str, str]
LocatedOutlineEntry = tuple[int, str, int, float | None]
NamedDestinationMap = dict[str, tuple[int, float | None, ArrayObject]]


def _outline_source_entries(result: MarkdownRenderResult) -> list[OutlineSourceEntry]:
    """Return clean heading entries for PDF outline creation."""
    entries: list[OutlineSourceEntry] = []
    for entry in result.toc_entries:
        if len(entry) < 3:
            continue
        level = max(1, min(int(entry[0]), 6))
        title = _stringify_metadata_value(entry[1]).strip()
        heading_id = str(entry[2] or "").strip()
        if title and heading_id:
            entries.append((level, title, heading_id))
    return entries


def _destination_object(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def _destination_array(value: Any) -> ArrayObject | None:
    """Resolve a PDF named-destination value to a destination array."""
    value = _destination_object(value)
    if isinstance(value, ArrayObject):
        return value
    if isinstance(value, dict):
        destination = value.get(NameObject("/D")) or value.get("/D")
        destination = _destination_object(destination)
        if isinstance(destination, ArrayObject):
            return destination
    return None


def _walk_destination_name_tree(node: Any) -> list[tuple[str, ArrayObject]]:
    """Return named destinations from a PDF /Names tree."""
    node = _destination_object(node)
    if not isinstance(node, dict):
        return []
    results: list[tuple[str, ArrayObject]] = []
    names = node.get(NameObject("/Names")) or node.get("/Names")
    if isinstance(names, list):
        for index in range(0, len(names), 2):
            try:
                name = str(names[index])
                destination = _destination_array(names[index + 1])
            except Exception:
                continue
            if destination is not None:
                results.append((name, destination))
    kids = node.get(NameObject("/Kids")) or node.get("/Kids")
    if isinstance(kids, list):
        for kid in kids:
            results.extend(_walk_destination_name_tree(kid))
    return results


def _iter_pdf_named_destinations(reader: PdfReader) -> list[tuple[str, ArrayObject]]:
    """Collect Chromium/PDF named destinations from /Dests and /Names."""
    root = reader.trailer.get("/Root", {})
    destinations: list[tuple[str, ArrayObject]] = []

    legacy_dests = _destination_object(root.get(NameObject("/Dests")) or root.get("/Dests"))
    if isinstance(legacy_dests, dict):
        for name, value in legacy_dests.items():
            destination = _destination_array(value)
            if destination is not None:
                destinations.append((str(name), destination))

    names_root = _destination_object(root.get(NameObject("/Names")) or root.get("/Names"))
    if isinstance(names_root, dict):
        dest_tree = names_root.get(NameObject("/Dests")) or names_root.get("/Dests")
        destinations.extend(_walk_destination_name_tree(dest_tree))

    return destinations


def _reader_page_index(reader: PdfReader, page_reference: Any) -> int | None:
    """Map a source page indirect reference back to its page index."""
    ref_id = getattr(page_reference, "idnum", None)
    ref_generation = getattr(page_reference, "generation", None)
    for index, page in enumerate(reader.pages):
        reference = getattr(page, "indirect_reference", None)
        if reference is None:
            continue
        if getattr(reference, "idnum", None) == ref_id and getattr(reference, "generation", None) == ref_generation:
            return index
        if ref_id is None and _destination_object(page_reference) == page:
            return index
    return None


def _destination_top(destination: ArrayObject) -> float | None:
    """Extract the top coordinate from common PDF destination arrays."""
    if len(destination) < 2:
        return None
    fit = str(destination[1])
    coordinate_index = 3 if fit == "/XYZ" else 2 if fit in {"/FitH", "/FitBH"} else None
    if coordinate_index is None or coordinate_index >= len(destination):
        return None
    try:
        return float(destination[coordinate_index])
    except Exception:
        return None


def _copy_pdf_named_destinations(
    writer: PdfWriter,
    reader: PdfReader,
    *,
    page_offset: int = 0,
) -> NamedDestinationMap:
    """Preserve internal PDF destinations while copying/merging pages.

    Chromium emits TOC links as link annotations that point at named
    destinations in the source PDF catalog.  pypdf does not automatically clone
    those catalog-level destinations when pages are copied, leaving the visible
    TOC links present but inert.  This helper recreates the destination name tree
    against the writer's page references and returns a map used by outline
    creation, so viewer bookmarks land on real headings instead of TOC rows.
    """
    copied: NamedDestinationMap = {}
    destinations = _iter_pdf_named_destinations(reader)
    if not destinations:
        return copied

    page_refs = writer.get_object(writer._pages)[NameObject("/Kids")]  # type: ignore[index]
    page_count = len(page_refs)
    for name, destination in destinations:
        if not destination:
            continue
        source_page_index = _reader_page_index(reader, destination[0])
        if source_page_index is None:
            continue
        target_page_index = page_offset + source_page_index
        if target_page_index < 0 or target_page_index >= page_count:
            continue
        copied_destination = ArrayObject([page_refs[target_page_index]])
        copied_destination.extend(destination[1:])
        try:
            writer.add_named_destination_array(TextStringObject(name), copied_destination)
        except Exception:
            continue
        copied[name] = (target_page_index, _destination_top(copied_destination), copied_destination)
    return copied


def _annotation_destination_lookup_names(value: Any) -> list[str]:
    """Return destination-name variants used by PDF link annotations."""
    value = _destination_object(value)
    if isinstance(value, ArrayObject):
        return []
    text = str(value or "").strip()
    if not text:
        return []
    bare = text[1:] if text.startswith("/") else text
    encoded = quote(bare, safe="-._~")
    decoded = unquote(bare)
    names = [text, bare, f"/{bare}", encoded, f"/{encoded}", decoded, f"/{decoded}"]
    unique: list[str] = []
    for name in names:
        if name and name not in unique:
            unique.append(name)
    return unique


def _clone_destination_array(destination: ArrayObject) -> ArrayObject:
    """Return a shallow destination-array copy safe for annotations."""
    clone = ArrayObject()
    clone.extend(destination)
    return clone


def _resolve_named_destination_for_annotation(
    destination: Any,
    named_destinations: NamedDestinationMap,
) -> ArrayObject | None:
    """Resolve a PDF annotation destination name to an explicit array."""
    for name in _annotation_destination_lookup_names(destination):
        record = named_destinations.get(name)
        if record is not None:
            return _clone_destination_array(record[2])
    return None


def _rewrite_pdf_link_annotation_destinations(
    writer: PdfWriter,
    named_destinations: NamedDestinationMap,
) -> None:
    """Rewrite copied TOC link annotations from names to explicit arrays.

    Chromium writes visible TOC links as ``/Dest /heading-id`` annotations.
    After pypdf copies pages and rewrites the catalog, some viewers resolve the
    preserved name tree for bookmarks but leave page annotations inert or point
    them at the original source context.  Replacing annotation destinations with
    explicit destination arrays makes visible TOC links independent of name-tree
    lookup and keeps them aligned with the same real heading coordinates used by
    PDF outline entries.
    """
    if not named_destinations:
        return
    for page in writer.pages:
        annotations = page.get(NameObject("/Annots")) or page.get("/Annots")
        if not annotations:
            continue
        for annotation_ref in annotations:
            try:
                annotation = annotation_ref.get_object()
            except Exception:
                continue
            if str(annotation.get(NameObject("/Subtype")) or annotation.get("/Subtype") or "") != "/Link":
                continue

            direct_destination = annotation.get(NameObject("/Dest")) or annotation.get("/Dest")
            resolved = _resolve_named_destination_for_annotation(direct_destination, named_destinations)
            if resolved is not None:
                annotation[NameObject("/Dest")] = resolved
                continue

            action = annotation.get(NameObject("/A")) or annotation.get("/A")
            action = _destination_object(action)
            if not isinstance(action, dict):
                continue
            if str(action.get(NameObject("/S")) or action.get("/S") or "") != "/GoTo":
                continue
            action_destination = action.get(NameObject("/D")) or action.get("/D")
            resolved = _resolve_named_destination_for_annotation(action_destination, named_destinations)
            if resolved is not None:
                action[NameObject("/D")] = resolved


def _heading_destination_names(heading_id: str) -> list[str]:
    """Return destination-name variants emitted by Chromium for a heading id."""
    heading_id = str(heading_id or "").strip()
    if not heading_id:
        return []
    encoded = quote(heading_id, safe="-._~")
    names = [f"/{encoded}", f"/{heading_id}", encoded, heading_id]
    unique: list[str] = []
    for name in names:
        if name not in unique:
            unique.append(name)
    return unique


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
    outline_entries: list[OutlineSourceEntry],
    *,
    named_destinations: NamedDestinationMap | None = None,
    start_page: int = 0,
) -> list[LocatedOutlineEntry]:
    """Map outline headings to best-effort PDF page indexes.

    Prefer Chromium named destinations because they are the same anchors used by
    the visible TOC links.  Text extraction remains as a fallback for older PDFs
    or unusual readers, but it intentionally comes after destination lookup so
    PDF bookmarks do not accidentally resolve to matching text inside the TOC.
    """
    if not page_texts and not named_destinations:
        return []
    page_count = len(page_texts)
    current_page = max(0, min(start_page, page_count - 1)) if page_count else max(0, start_page)
    located: list[LocatedOutlineEntry] = []

    for level, title, heading_id in outline_entries:
        destination_page: int | None = None
        destination_top: float | None = None
        for destination_name in _heading_destination_names(heading_id):
            if named_destinations and destination_name in named_destinations:
                destination_page, destination_top, _destination = named_destinations[destination_name]
                break

        needle = _normalize_pdf_search_text(title)
        page_index = destination_page if destination_page is not None else current_page
        if destination_page is None and needle and page_texts:
            for index in range(current_page, page_count):
                if needle in page_texts[index]:
                    page_index = index
                    break
        current_page = page_index
        located.append((max(1, min(level, 6)), title, page_index, destination_top))
    return located


def _add_pdf_outline(writer: PdfWriter, outline_entries: list[LocatedOutlineEntry]) -> None:
    """Attach a nested PDF outline to ``writer`` from located heading entries."""
    parents: dict[int, Any] = {}
    page_count = len(writer.pages)
    for level, title, page_index, top in outline_entries:
        if not title or page_index < 0 or page_index >= page_count:
            continue
        parent = parents.get(level - 1)
        fit = Fit.xyz(left=0, top=top, zoom=None) if top is not None else Fit.fit()
        item = writer.add_outline_item(title, page_index, parent=parent, fit=fit)
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


def _add_pdf_page_labels(writer: PdfWriter, *, content_start_page: int = 0) -> None:
    """Add viewer page labels so content numbering restarts after a cover."""
    page_count = len(writer.pages)
    if page_count <= 0:
        return
    start = max(0, min(int(content_start_page or 0), page_count - 1))
    nums = ArrayObject()
    if start > 0:
        nums.append(NumberObject(0))
        nums.append(
            DictionaryObject(
                {
                    NameObject("/S"): NameObject("/D"),
                    NameObject("/St"): NumberObject(1),
                    NameObject("/P"): TextStringObject("Cover "),
                }
            )
        )
    nums.append(NumberObject(start))
    nums.append(DictionaryObject({NameObject("/S"): NameObject("/D"), NameObject("/St"): NumberObject(1)}))
    writer._root_object[NameObject("/PageLabels")] = DictionaryObject({NameObject("/Nums"): nums})


def _copy_pdf_with_metadata(
    input_path: Path,
    output_path: Path,
    metadata: dict[str, str],
    outline_source_entries: list[OutlineSourceEntry] | None = None,
    *,
    outline_start_page: int = 0,
) -> None:
    reader = PdfReader(str(input_path))
    page_texts = _pdf_page_texts(reader) if outline_source_entries else []
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    named_destinations = _copy_pdf_named_destinations(writer, reader)
    _rewrite_pdf_link_annotation_destinations(writer, named_destinations)
    _add_pdf_page_labels(writer, content_start_page=outline_start_page)
    writer.add_metadata(metadata)
    if outline_source_entries:
        _add_pdf_outline(
            writer,
            _locate_outline_pages(
                page_texts,
                outline_source_entries,
                named_destinations=named_destinations,
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
    outline_source_entries: list[OutlineSourceEntry] | None = None,
    *,
    outline_start_page: int = 0,
) -> None:
    writer = PdfWriter()
    page_texts: list[str] = []
    named_destinations: NamedDestinationMap = {}
    for part in parts:
        reader = PdfReader(str(part))
        page_offset = len(writer.pages)
        if outline_source_entries:
            page_texts.extend(_pdf_page_texts(reader))
        for page in reader.pages:
            writer.add_page(page)
        named_destinations.update(_copy_pdf_named_destinations(writer, reader, page_offset=page_offset))
    _rewrite_pdf_link_annotation_destinations(writer, named_destinations)
    _add_pdf_page_labels(writer, content_start_page=outline_start_page)
    if metadata:
        writer.add_metadata(metadata)
    if outline_source_entries:
        _add_pdf_outline(
            writer,
            _locate_outline_pages(
                page_texts,
                outline_source_entries,
                named_destinations=named_destinations,
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
        code_style=code_style_for_appearance(options.style, options.mode),
        unsafe_html=options.unsafe_html,
        allow_remote_images=options.allow_remote_assets,
    )
    _report_progress(progress, "Markdown parsed", 0.16)

    title = options.title or _stringify_metadata_value(result.metadata.get("title")) or result.title
    pdf_metadata = _pdf_metadata(result, options, str(title))
    footer_context = _footer_context(result, options, str(title))
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
                    _render_pdf(page, cover_html, options, cover_pdf, display_footer=False, footer_context=footer_context)

                    content_pdf = tmp / "content.pdf"
                    content_html = build_html(result, options, include_cover=False, include_content=True, include_watermark=True)
                    _report_progress(progress, "Rendering content", 0.72)
                    _render_pdf(page, content_html, options, content_pdf, display_footer=True, footer_context=footer_context)

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
                    _render_pdf(page, html_text, options, content_pdf, display_footer=True, footer_context=footer_context)

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
