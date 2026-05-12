from __future__ import annotations

import argparse
import json
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any

from . import __version__
from .renderer import PdfOptions, convert, normalize_theme_name


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

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path in {"/", "/index.html"}:
            html = _asset_text("gui.html").replace("__MARDAS_VERSION__", __version__)
            self._send_text(html)
            return
        if self.path == "/api/version":
            self._send_json({"version": __version__})
            return
        self._send_text("Not found", status=404, content_type="text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        if self.path != "/api/render":
            self._send_json({"error": "Unknown endpoint"}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            markdown = str(payload.get("markdown") or "")
            options = payload.get("options") or {}
            if not markdown.strip():
                raise ValueError("Markdown content is empty.")

            theme = normalize_theme_name(str(options.get("theme") or "modern"))
            filename = _safe_filename(str(options.get("filename") or options.get("title") or "mardas-document"))
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

            with tempfile.TemporaryDirectory(prefix="mardas-md2pdf-gui-") as tmpdir:
                tmp = Path(tmpdir)
                md_path = tmp / "document.md"
                pdf_path = tmp / filename
                md_path.write_text(markdown, encoding="utf-8")

                pdf_options = PdfOptions(
                    input_path=md_path,
                    output_path=pdf_path,
                    title=(str(options.get("title") or "").strip() or None),
                    author=(str(options.get("author") or "").strip() or None),
                    description=(str(options.get("description") or "").strip() or None),
                    toc=bool(options.get("toc", True)),
                    toc_depth=int(options.get("tocDepth") or 6),
                    toc_page_break=bool(options.get("tocPageBreak", True)),
                    h1_page_break=bool(options.get("h1PageBreak", True)),
                    page_size=str(options.get("pageSize") or "A4"),
                    theme=theme,
                    cover=not bool(options.get("noCover", False)),
                    watermark_text=(str(options.get("watermark") or "").strip() or None),
                    watermark_opacity=float(options.get("watermarkOpacity") or 0.065),
                    no_header_footer=bool(options.get("noHeaderFooter", False)),
                    no_mathjax=bool(options.get("noMathjax", False)),
                )
                convert(pdf_options)
                data = pdf_path.read_bytes()

            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:  # pragma: no cover - exercised manually with browser
            self._send_json({"error": str(exc)}, status=500)

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
