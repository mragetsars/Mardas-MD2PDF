from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any

from . import __version__
from .brand_assets import asset_content_type, gui_brand_asset_filename, packaged_asset_path
from .appearance import code_style_for_appearance, validate_mode_name, validate_palette_name, validate_style_name
from .markdown import render_markdown_file
from .renderer import PdfOptions, build_html, convert, validate_branding_mode, validate_page_size


MAX_GUI_REQUEST_BYTES = 32 * 1024 * 1024
MAX_GUI_MARKDOWN_BYTES = 4 * 1024 * 1024
MAX_GUI_ASSETS = 250
MAX_GUI_ASSET_BYTES = 12 * 1024 * 1024
MAX_GUI_TOTAL_ASSET_BYTES = 32 * 1024 * 1024

STUDIO_PREVIEW_NAMED_PAGE_SIZES: dict[str, tuple[str, str]] = {
    "letter": ("8.5in", "11in"),
    "legal": ("8.5in", "14in"),
    "tabloid": ("11in", "17in"),
    "ledger": ("17in", "11in"),
    "a0": ("841mm", "1189mm"),
    "a1": ("594mm", "841mm"),
    "a2": ("420mm", "594mm"),
    "a3": ("297mm", "420mm"),
    "a4": ("210mm", "297mm"),
    "a5": ("148mm", "210mm"),
    "a6": ("105mm", "148mm"),
    "b0": ("1000mm", "1414mm"),
    "b1": ("707mm", "1000mm"),
    "b2": ("500mm", "707mm"),
    "b3": ("353mm", "500mm"),
    "b4": ("250mm", "353mm"),
    "b5": ("176mm", "250mm"),
    "b6": ("125mm", "176mm"),
}
STUDIO_PREVIEW_PAGE_NAME_RE = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9-]*)(?:\s+(?P<orientation>portrait|landscape))?$",
    re.IGNORECASE,
)
STUDIO_PREVIEW_DIMENSIONS_RE = re.compile(
    r"^(?P<width>\d+(?:\.\d+)?(?:mm|cm|in|px|pt))\s+"
    r"(?P<height>\d+(?:\.\d+)?(?:mm|cm|in|px|pt))$",
    re.IGNORECASE,
)


class StudioRequestError(ValueError):
    """Client-facing Studio request error with a stable JSON error code."""

    def __init__(self, message: str, *, status: int = 400, code: str = "bad_request") -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def _format_bytes(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.0f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} bytes"


def _error_payload(message: str, *, status: int, code: str) -> dict[str, Any]:
    return {"error": message, "status": status, "code": code}


def _decode_json_payload(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StudioRequestError(
            "Render request body must be UTF-8 encoded.", code="invalid_encoding"
        ) from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StudioRequestError(
            f"Render request body must be valid JSON: {exc.msg}.", code="invalid_json"
        ) from exc
    if not isinstance(payload, dict):
        raise StudioRequestError("Render payload must be a JSON object.", code="invalid_payload")
    return payload


def _is_local_bind_host(host: str) -> bool:
    normalized = (host or "").strip().lower().strip("[]")
    return normalized in {"", "localhost", "127.0.0.1", "::1"} or normalized.startswith("127.")


def _studio_bind_warning(host: str) -> str | None:
    if _is_local_bind_host(host):
        return None
    return (
        "Studio is binding to a non-local host. Only use this on trusted networks, "
        "because anyone who can reach the server can submit Markdown and attached assets."
    )




def _json_bool(value: Any, *, default: bool, code: str, label: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    raise StudioRequestError(f"{label} must be true or false.", code=code)


def _json_int_range(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
    code: str,
    label: str,
) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise StudioRequestError(f"{label} must be an integer from {minimum} to {maximum}.", code=code)
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise StudioRequestError(f"{label} must be an integer from {minimum} to {maximum}.", code=code) from exc
    if not minimum <= number <= maximum:
        raise StudioRequestError(f"{label} must be between {minimum} and {maximum}.", code=code)
    return number


def _json_float_range(
    value: Any,
    *,
    default: float,
    minimum: float,
    maximum: float,
    code: str,
    label: str,
) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise StudioRequestError(f"{label} must be a number from {minimum:g} to {maximum:g}.", code=code)
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise StudioRequestError(f"{label} must be a number from {minimum:g} to {maximum:g}.", code=code) from exc
    if not minimum <= number <= maximum:
        raise StudioRequestError(f"{label} must be between {minimum:g} and {maximum:g}.", code=code)
    return number


def _validated_render_options(options: dict[str, Any]) -> dict[str, Any]:
    """Normalize Studio render options and turn bad input into 400 errors."""
    try:
        page_size = validate_page_size(str(options.get("pageSize") or "A4"))
    except ValueError as exc:
        raise StudioRequestError(f"pageSize {exc}", code="invalid_page_size") from exc

    direction = str(options.get("direction") or "").strip().lower()
    if direction not in {"", "auto", "rtl", "ltr"}:
        raise StudioRequestError("direction must be auto, rtl, or ltr.", code="invalid_direction")

    try:
        style = validate_style_name(options.get("style") or "modern")
    except ValueError as exc:
        raise StudioRequestError(str(exc), code="invalid_style") from exc
    try:
        palette = validate_palette_name(options.get("palette") or "blue")
    except ValueError as exc:
        raise StudioRequestError(str(exc), code="invalid_palette") from exc
    try:
        mode = validate_mode_name(options.get("mode") or "light")
    except ValueError as exc:
        raise StudioRequestError(str(exc), code="invalid_mode") from exc
    try:
        branding = validate_branding_mode(options.get("branding") or "off")
    except ValueError as exc:
        raise StudioRequestError(str(exc), code="invalid_branding") from exc

    return {
        "style": style,
        "palette": palette,
        "mode": mode,
        "branding": branding,
        "toc": _json_bool(options.get("toc"), default=True, code="invalid_toc", label="toc"),
        "toc_depth": _json_int_range(
            options.get("tocDepth"),
            default=6,
            minimum=1,
            maximum=6,
            code="invalid_toc_depth",
            label="tocDepth",
        ),
        "toc_page_break": _json_bool(
            options.get("tocPageBreak"), default=True, code="invalid_toc_page_break", label="tocPageBreak"
        ),
        "h1_page_break": _json_bool(
            options.get("h1PageBreak"), default=True, code="invalid_h1_page_break", label="h1PageBreak"
        ),
        "page_size": page_size,
        "direction": direction or None,
        "cover": not _json_bool(options.get("noCover"), default=False, code="invalid_no_cover", label="noCover"),
        "watermark_opacity": _json_float_range(
            options.get("watermarkOpacity"),
            default=0.065,
            minimum=0,
            maximum=1,
            code="invalid_watermark_opacity",
            label="watermarkOpacity",
        ),
        "no_header_footer": _json_bool(
            options.get("noHeaderFooter"), default=False, code="invalid_no_header_footer", label="noHeaderFooter"
        ),
        "no_mathjax": _json_bool(
            options.get("noMathjax"), default=False, code="invalid_no_mathjax", label="noMathjax"
        ),
    }

def _asset_text(name: str) -> str:
    return (resources.files("mardas_md2pdf") / "assets" / name).read_text(encoding="utf-8")


def _safe_filename(value: str | None, default: str = "mardas-document") -> str:
    if not value:
        return default
    keep = []
    for char in value.strip():
        if char.isalnum() or char in {"-", "_", "."}:
            keep.append(char)
        elif char.isspace():
            keep.append("-")
    name = "".join(keep).strip("-_.")
    return name or default


def _safe_asset_path_part(value: str) -> str:
    """Preserve browser-provided asset names while removing path-control bytes."""
    cleaned = "".join(
        char for char in value if char not in {"/", "\\"} and ord(char) >= 32 and ord(char) != 127
    )
    cleaned = cleaned.strip()
    return "" if cleaned in {"", ".", ".."} else cleaned


def _safe_asset_relative_path(value: str | None, fallback: str = "asset") -> Path:
    raw = str(value or fallback).replace("\\", "/").strip()
    parts = [_safe_asset_path_part(part) for part in raw.split("/")]
    safe_parts = [part for part in parts if part]
    return Path(*safe_parts) if safe_parts else Path(_safe_filename(fallback))


def _write_gui_assets(tmp: Path, assets: Any) -> None:
    if not isinstance(assets, list):
        return
    total_bytes = 0
    for index, asset in enumerate(assets[:MAX_GUI_ASSETS]):
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("path") or asset.get("name") or f"asset-{index}")
        data_url = str(asset.get("data") or "")
        if "," not in data_url:
            continue
        header, payload = data_url.split(",", 1)
        if "base64" not in header.lower():
            continue
        try:
            data = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError):
            continue
        if len(data) > MAX_GUI_ASSET_BYTES:
            continue
        if total_bytes + len(data) > MAX_GUI_TOTAL_ASSET_BYTES:
            continue
        rel_path = _safe_asset_relative_path(name, fallback=f"asset-{index}")
        target = tmp / rel_path
        try:
            target.relative_to(tmp)
        except ValueError:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        total_bytes += len(data)

        # Also copy a basename fallback beside document.md. This mirrors the CLI
        # image resolver and helps when a browser only provides selected files
        # without their original directory names.
        if len(rel_path.parts) > 1:
            fallback_target = tmp / rel_path.name
            if not fallback_target.exists():
                fallback_target.write_bytes(data)


def _validate_studio_payload(payload: dict[str, Any]) -> tuple[str, dict[str, Any], list[Any], dict[str, Any], str]:
    markdown = str(payload.get("markdown") or "")
    options = payload.get("options") or {}
    assets = payload.get("assets") or []
    if not isinstance(options, dict):
        raise StudioRequestError("Render options must be a JSON object.", code="invalid_options")
    if not markdown.strip():
        raise StudioRequestError("Markdown content is empty.", code="empty_markdown")
    if len(markdown.encode("utf-8")) > MAX_GUI_MARKDOWN_BYTES:
        raise StudioRequestError(
            "Markdown content is too large. "
            f"Maximum Markdown size is {_format_bytes(MAX_GUI_MARKDOWN_BYTES)}.",
            status=413,
            code="markdown_too_large",
        )
    render_options = _validated_render_options(options)
    filename = _safe_filename(str(options.get("filename") or options.get("title") or "mardas-document"))
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    return markdown, options, assets if isinstance(assets, list) else [], render_options, filename


def _studio_pdf_options(
    *,
    tmp: Path,
    md_path: Path,
    output_path: Path,
    options: dict[str, Any],
    render_options: dict[str, Any],
) -> PdfOptions:
    brand_logo_path = None
    brand_logo_value = str(options.get("brandLogo") or "").strip()
    if brand_logo_value:
        brand_logo_path = tmp / _safe_asset_relative_path(brand_logo_value, fallback="brand-logo")
        if not brand_logo_path.is_file():
            raise StudioRequestError(
                "brandLogo must match an attached asset path.",
                code="invalid_brand_logo",
            )

    return PdfOptions(
        input_path=md_path,
        output_path=output_path,
        title=(str(options.get("title") or "").strip() or None),
        author=(str(options.get("author") or "").strip() or None),
        description=(str(options.get("description") or "").strip() or None),
        toc=render_options["toc"],
        toc_depth=render_options["toc_depth"],
        toc_page_break=render_options["toc_page_break"],
        h1_page_break=render_options["h1_page_break"],
        page_size=render_options["page_size"],
        document_direction=render_options["direction"],
        style=render_options["style"],
        palette=render_options["palette"],
        mode=render_options["mode"],
        cover=render_options["cover"],
        branding=render_options["branding"],
        brand_name=(str(options.get("brandName") or "").strip() or None),
        brand_logo=brand_logo_path,
        brand_footer=(str(options.get("brandFooter") or "").strip() or None),
        watermark_text=(str(options.get("watermark") or "").strip() or None),
        watermark_opacity=render_options["watermark_opacity"],
        no_header_footer=render_options["no_header_footer"],
        no_mathjax=render_options["no_mathjax"],
    )


def _studio_preview_page_dimensions(page_size: str | None) -> tuple[str, str]:
    """Return CSS width and height for Studio's screen-side PDF preview sheet."""
    try:
        page_size = validate_page_size(page_size)
    except ValueError:
        page_size = "A4"

    dimension_match = STUDIO_PREVIEW_DIMENSIONS_RE.fullmatch(page_size)
    if dimension_match:
        return dimension_match.group("width"), dimension_match.group("height")

    name_match = STUDIO_PREVIEW_PAGE_NAME_RE.fullmatch(page_size)
    if not name_match:
        return STUDIO_PREVIEW_NAMED_PAGE_SIZES["a4"]

    width, height = STUDIO_PREVIEW_NAMED_PAGE_SIZES.get(
        name_match.group("name").lower(), STUDIO_PREVIEW_NAMED_PAGE_SIZES["a4"]
    )
    if (name_match.group("orientation") or "").lower() == "landscape":
        width, height = height, width
    return width, height


def _studio_pdf_like_preview_css(page_size: str | None) -> str:
    """Inject screen-only CSS that makes renderer HTML read like a PDF-like sheet preview."""
    page_width, page_height = _studio_preview_page_dimensions(page_size)
    return f"""
  <style id="mardas-studio-preview-css">
    @media screen {{
      :root {{
        --md2pdf-preview-page-width: {page_width};
        --md2pdf-preview-page-height: {page_height};
        --md2pdf-preview-page-gap: 30px;
        --md2pdf-preview-scale: 1;
        --md2pdf-preview-shell-bg: #d8dde6;
        --md2pdf-preview-shell-bg-dark: #050505;
        --md2pdf-preview-label-bg: #eef3fb;
      }}
      html {{
        min-height: 100%;
        background: var(--md2pdf-preview-shell-bg) !important;
        overflow-x: hidden;
      }}
      body {{
        min-height: 100%;
        min-width: 0;
        margin: 0 !important;
        padding: var(--md2pdf-preview-page-gap) 0 !important;
        background: var(--md2pdf-preview-shell-bg) !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        overflow-x: hidden;
      }}
      body.md2pdf-mode-dark {{
        background: var(--md2pdf-preview-shell-bg-dark) !important;
        --md2pdf-preview-label-bg: #111111;
      }}
      .md2pdf-document {{
        width: var(--md2pdf-preview-page-width);
        min-height: var(--md2pdf-preview-page-height);
        margin: 0 auto var(--md2pdf-preview-page-gap) !important;
        padding: var(--page-margin-top) var(--page-margin-x) var(--page-margin-bottom) !important;
        box-shadow: 0 24px 74px rgba(15, 23, 42, .28), 0 0 0 1px rgba(15, 23, 42, .14);
        overflow: visible;
        flex: 0 0 auto;
        position: relative;
        isolation: isolate;
        zoom: var(--md2pdf-preview-scale);
      }}
      @supports not (zoom: 1) {{
        .md2pdf-document {{
          transform: scale(var(--md2pdf-preview-scale));
          transform-origin: top center;
        }}
      }}
      body:not(.md2pdf-mode-dark) .md2pdf-document {{
        background: #ffffff !important;
      }}
      body.md2pdf-mode-dark .md2pdf-document {{
        box-shadow: 0 24px 74px rgba(0, 0, 0, .72), 0 0 0 1px rgba(255, 255, 255, .12);
      }}
      .md2pdf-article {{
        max-width: none !important;
        margin: 0 !important;
        position: relative;
        z-index: 1;
      }}
      .md2pdf-page-break {{
        display: block !important;
        height: auto !important;
        min-height: 0 !important;
        margin: 18mm 0 !important;
        border: 0 !important;
        border-top: 1px dashed color-mix(in srgb, var(--accent, #2563eb) 48%, var(--line, #dbe3ef));
        overflow: visible !important;
        break-after: auto !important;
        page-break-after: auto !important;
        position: relative;
      }}
      .md2pdf-page-break::after {{
        content: "Explicit page break";
        position: absolute;
        left: 50%;
        top: -.85em;
        transform: translateX(-50%);
        padding: .1em .55em;
        border-radius: 999px;
        background: var(--md2pdf-preview-label-bg);
        color: var(--muted, #64748b);
        font: 700 9px/1.4 var(--font-en, Arial, sans-serif);
        letter-spacing: .08em;
        text-transform: uppercase;
        white-space: nowrap;
      }}
    }}
  </style>
  <script id="mardas-studio-preview-scale-script">
    (() => {{
      let refreshHandle = 0;
      const updatePreviewScale = () => {{
        const root = document.documentElement;
        const page = document.querySelector('.md2pdf-document');
        if (!page) return;
        root.style.setProperty('--md2pdf-preview-scale', '1');
        const pageWidth = page.getBoundingClientRect().width;
        const viewportWidth = document.documentElement.clientWidth || window.innerWidth || pageWidth;
        const scale = Math.min(1, Math.max(0.28, (viewportWidth - 32) / Math.max(pageWidth, 1)));
        root.style.setProperty('--md2pdf-preview-scale', scale.toFixed(4));
      }};
      const refreshPreviewPageChrome = () => {{ updatePreviewScale(); }};
      const queueRefresh = () => {{
        if (refreshHandle) cancelAnimationFrame(refreshHandle);
        refreshHandle = requestAnimationFrame(refreshPreviewPageChrome);
      }};
      window.addEventListener('resize', queueRefresh);
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(queueRefresh).catch(() => {{}});
      if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', queueRefresh, {{ once: true }});
      }} else {{
        queueRefresh();
      }}
      setTimeout(queueRefresh, 200);
    }})();
  </script>"""

def _inject_studio_preview_css(html_text: str, *, page_size: str | None) -> str:
    preview_css = _studio_pdf_like_preview_css(page_size)
    return html_text.replace("</head>", f"{preview_css}\n</head>", 1)


def _render_studio_html_payload(payload: dict[str, Any]) -> str:
    markdown, options, assets, render_options, _filename = _validate_studio_payload(payload)
    with tempfile.TemporaryDirectory(prefix="mardas-md2pdf-gui-html-") as tmpdir:
        tmp = Path(tmpdir)
        md_path = tmp / "document.md"
        html_path = tmp / "document.html"
        md_path.write_text(markdown, encoding="utf-8")
        _write_gui_assets(tmp, assets)
        pdf_options = _studio_pdf_options(
            tmp=tmp,
            md_path=md_path,
            output_path=html_path.with_suffix(".pdf"),
            options=options,
            render_options=render_options,
        )
        result = render_markdown_file(
            md_path,
            toc=render_options["toc"],
            toc_depth=render_options["toc_depth"],
            code_style=code_style_for_appearance(render_options["style"], render_options["mode"]),
            unsafe_html=False,
            allow_remote_images=False,
        )
        html_text = build_html(
            result,
            pdf_options,
            include_cover=render_options["cover"],
            include_content=True,
            include_watermark=True,
        )
        html_text = _inject_studio_preview_css(html_text, page_size=render_options["page_size"])
        html_path.write_text(html_text, encoding="utf-8")
        return html_text


class GuiRequestHandler(BaseHTTPRequestHandler):
    server_version = f"MardasMD2PDFGUI/{__version__}"

    def _send_text(self, content: str, *, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, message: str, *, status: int, code: str) -> None:
        self._send_json(_error_payload(message, status=status, code=code), status=status)

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path in {"/", "/index.html"}:
            html = _asset_text("gui.html").replace("__MARDAS_VERSION__", __version__)
            self._send_text(html)
            return
        filename = gui_brand_asset_filename(self.path)
        if filename is not None:
            data = packaged_asset_path(filename).read_bytes()
            content_type = asset_content_type(filename)
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/api/version":
            self._send_json({"version": __version__})
            return
        self._send_text("Not found", status=404, content_type="text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        if self.path not in {"/api/render", "/api/render-html"}:
            self._send_error("Unknown endpoint", status=404, code="not_found")
            return
        try:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_error(
                    "Invalid Content-Length header.", status=400, code="invalid_content_length"
                )
                return
            if length > MAX_GUI_REQUEST_BYTES:
                self._send_error(
                    "Render request is too large. "
                    f"Maximum request size is {_format_bytes(MAX_GUI_REQUEST_BYTES)}.",
                    status=413,
                    code="request_too_large",
                )
                return
            raw = self.rfile.read(length)
            payload = _decode_json_payload(raw)
            if self.path == "/api/render-html":
                html_text = _render_studio_html_payload(payload)
                self._send_text(html_text, content_type="text/html; charset=utf-8")
                return

            markdown, options, assets, render_options, filename = _validate_studio_payload(payload)
            with tempfile.TemporaryDirectory(prefix="mardas-md2pdf-gui-") as tmpdir:
                tmp = Path(tmpdir)
                md_path = tmp / "document.md"
                pdf_path = tmp / filename
                md_path.write_text(markdown, encoding="utf-8")
                _write_gui_assets(tmp, assets)
                pdf_options = _studio_pdf_options(
                    tmp=tmp,
                    md_path=md_path,
                    output_path=pdf_path,
                    options=options,
                    render_options=render_options,
                )
                convert(pdf_options)
                data = pdf_path.read_bytes()

            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except StudioRequestError as exc:
            self._send_error(str(exc), status=exc.status, code=exc.code)
        except Exception as exc:  # pragma: no cover - exercised manually with browser
            self._send_error(f"PDF rendering failed: {exc}", status=500, code="render_failed")

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[Mardas GUI] {self.address_string()} - {fmt % args}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mrs-md2pdf-gui",
        description="Open the local Mardas MD2PDF Studio GUI for editing Markdown and exporting PDFs.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind; default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind; default: 8765")
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), GuiRequestHandler)
    url = f"http://{args.host}:{server.server_port}/"
    print(f"Mardas MD2PDF Studio is running at {url}")
    warning = _studio_bind_warning(args.host)
    if warning:
        print(f"WARNING: {warning}")
    print("Press Ctrl+C to stop.")
    if not args.no_open:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Mardas MD2PDF Studio...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
