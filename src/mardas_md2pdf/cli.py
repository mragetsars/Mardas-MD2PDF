from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .appearance import (
    MODE_DESCRIPTIONS,
    MODES,
    PALETTE_DESCRIPTIONS,
    PALETTES_ORDER,
    STYLE_DESCRIPTIONS,
    STYLES,
)
from .renderer import BRANDING_MODES, PdfOptions, convert, validate_branding_mode, validate_page_size


class _CliProgressBar:
    def __init__(self, *, stream=None, width: int = 28) -> None:
        self.stream = stream or sys.stderr
        self.width = width
        self._last_line = ""

    def __call__(self, message: str, fraction: float) -> None:
        fraction = max(0.0, min(1.0, float(fraction)))
        filled = round(self.width * fraction)
        bar = "█" * filled + "░" * (self.width - filled)
        line = f"\r[{bar}] {fraction:>6.0%}  {message}"
        padding = " " * max(0, len(self._last_line) - len(line))
        self.stream.write(line + padding)
        if fraction >= 1.0:
            self.stream.write("\n")
        self.stream.flush()
        self._last_line = line


def _progress_callback(mode: str):
    if mode == "off":
        return None
    if mode == "auto" and not sys.stderr.isatty():
        return None
    return _CliProgressBar()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mrs-md2pdf",
        description=(
            "Convert Markdown to polished PDF with Persian RTL/LTR typography, "
            "professional covers, hierarchical TOC, code highlighting, Mermaid flowcharts, tables, watermarking, and MathJax."
        ),
    )
    parser.add_argument("input", nargs="?", type=Path, help="Input Markdown file")
    parser.add_argument("-o", "--output", type=Path, help="Output PDF path")
    parser.add_argument("--title", help="Override document title")
    parser.add_argument("--author", help="Override author metadata")
    parser.add_argument("--description", help="Override summary/description metadata")
    parser.add_argument("--toc", action="store_true", help="Generate a hierarchical table of contents from Markdown headings")
    parser.add_argument("--toc-depth", type=int, default=6, choices=range(1, 7), metavar="1..6", help="Maximum heading level to include in the TOC; default: 6")
    parser.add_argument("--toc-page-break", action="store_true", help="Start the main document body on a new page after the TOC")
    parser.add_argument("--h1-page-break", action="store_true", help="Start every top-level Markdown heading (# / h1) on a new page")
    parser.add_argument("--debug-html", type=Path, help="Write the intermediate HTML for inspection")
    parser.add_argument(
        "--page-size",
        default="A4",
        help='PDF page size, e.g. A4, Letter, "A4 landscape", or "210mm 297mm"',
    )
    parser.add_argument(
        "--dir",
        dest="document_direction",
        choices=["auto", "rtl", "ltr"],
        default=None,
        help="Document shell direction. Defaults to front matter dir/direction, then auto-detection.",
    )
    parser.add_argument("--margin-top", default="18mm", help="Top CSS page margin")
    parser.add_argument("--margin-bottom", default="20mm", help="Bottom CSS page margin")
    parser.add_argument("--margin-x", default="16mm", help="Left/right CSS page margin")
    parser.add_argument("--font-dir", type=Path, help="Directory containing Vazirmatn font files")
    parser.add_argument("--chromium-path", help="Path to Chromium/Chrome executable")
    parser.add_argument(
        "--chromium-sandbox",
        choices=["auto", "on", "off"],
        default="auto",
        help=(
            "Chromium sandbox mode. auto keeps sandboxing on for normal users and disables it only "
            "when running as root; off is intended for trusted containers only."
        ),
    )
    parser.add_argument(
        "--style",
        choices=list(STYLES),
        default="modern",
        help="Document shape and layout style. Controls spacing, cover shape, table density, and code block form.",
    )
    parser.add_argument(
        "--palette",
        choices=list(PALETTES_ORDER),
        default="blue",
        help="Document accent color palette. Controls links, markers, cover accents, callouts, and diagram strokes.",
    )
    parser.add_argument(
        "--mode",
        choices=list(MODES),
        default="light",
        help="Document contrast mode: light or dark.",
    )
    parser.add_argument("--no-cover", action="store_true", help="Do not generate the automatic cover page")
    parser.add_argument(
        "--branding",
        choices=BRANDING_MODES,
        default=None,
        help="Cover branding mode. off hides tool branding, subtle shows a small generated-with note, full shows a cover brand block. Defaults to front matter or off.",
    )
    parser.add_argument("--brand-name", help="Brand or organization name to show on the cover when branding is enabled")
    parser.add_argument("--brand-logo", type=Path, help="Brand logo image for the cover when branding is enabled")
    parser.add_argument("--brand-footer", help="Small brand subtitle/footer shown under the cover brand name")
    parser.add_argument("--cover-logo", type=Path, help="Alias for --brand-logo")
    parser.add_argument("--no-cover-logo", action="store_true", help="Hide any logo on the generated cover brand block")
    parser.add_argument("--watermark", help="Text watermark to repeat on all content pages. The cover is never watermarked")
    parser.add_argument("--watermark-image", type=Path, help="Image watermark to repeat on all content pages. The cover is never watermarked")
    parser.add_argument("--watermark-opacity", type=float, default=0.065, help="Watermark opacity between 0 and 1; default: 0.065")
    parser.add_argument("--watermark-width", default="105mm", help="CSS width for image watermarks, e.g. 90mm or 45%%; default: 105mm")
    parser.add_argument("--no-header-footer", action="store_true", help="Disable page number footer")
    parser.add_argument("--no-mathjax", action="store_true", help="Do not load MathJax")
    parser.add_argument(
        "--unsafe-html",
        action="store_true",
        help="Allow raw HTML without sanitizing it first. Use only for trusted local Markdown.",
    )
    parser.add_argument(
        "--allow-remote-assets",
        action="store_true",
        help="Allow remote http(s) images to be loaded by Chromium. Disabled by default for privacy.",
    )
    parser.add_argument("--timeout-ms", type=int, default=120_000, help="Browser timeout in milliseconds")
    parser.add_argument(
        "--progress",
        choices=["auto", "on", "off"],
        default="auto",
        help="Show a terminal progress bar during PDF generation. Default: auto, only on interactive terminals.",
    )
    parser.add_argument("--list-styles", action="store_true", help="List available appearance styles and exit")
    parser.add_argument("--list-palettes", action="store_true", help="List available color palettes and exit")
    parser.add_argument("--list-modes", action="store_true", help="List available light/dark modes and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _print_named_choices(title: str, descriptions: dict[str, str], order: tuple[str, ...]) -> None:
    print(title)
    for name in order:
        print(f"  {name:<12} {descriptions.get(name, '')}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_styles:
        _print_named_choices("Styles", STYLE_DESCRIPTIONS, STYLES)
        return 0
    if args.list_palettes:
        _print_named_choices("Palettes", PALETTE_DESCRIPTIONS, PALETTES_ORDER)
        return 0
    if args.list_modes:
        _print_named_choices("Modes", MODE_DESCRIPTIONS, MODES)
        return 0
    input_path = args.input
    if input_path is None:
        parser.error("input is required unless you use --list-styles, --list-palettes, or --list-modes")
    if not input_path.exists():
        parser.error(f"Input file not found: {input_path}")
    brand_logo = args.brand_logo or args.cover_logo
    if brand_logo and not brand_logo.exists():
        parser.error(f"Brand logo not found: {brand_logo}")
    if args.watermark_image and not args.watermark_image.exists():
        parser.error(f"Watermark image not found: {args.watermark_image}")
    if not 0 <= args.watermark_opacity <= 1:
        parser.error("--watermark-opacity must be between 0 and 1")
    try:
        branding = validate_branding_mode(args.branding) if args.branding is not None else None
    except ValueError as exc:
        parser.error(f"--branding {exc}")
    try:
        page_size = validate_page_size(args.page_size)
    except ValueError as exc:
        parser.error(f"--page-size {exc}")

    output_path = args.output or input_path.with_suffix(".pdf")
    options = PdfOptions(
        input_path=input_path,
        output_path=output_path,
        title=args.title,
        author=args.author,
        description=args.description,
        toc=args.toc,
        toc_depth=args.toc_depth,
        toc_page_break=args.toc_page_break,
        h1_page_break=args.h1_page_break,
        debug_html=args.debug_html,
        page_size=page_size,
        document_direction=args.document_direction,
        margin_top=args.margin_top,
        margin_bottom=args.margin_bottom,
        margin_x=args.margin_x,
        font_dir=args.font_dir,
        chromium_path=args.chromium_path,
        chromium_sandbox=args.chromium_sandbox,
        no_header_footer=args.no_header_footer,
        no_mathjax=args.no_mathjax,
        timeout_ms=args.timeout_ms,
        style=args.style,
        palette=args.palette,
        mode=args.mode,
        cover=not args.no_cover,
        cover_logo=brand_logo,
        cover_logo_enabled=not args.no_cover_logo,
        branding=branding,
        brand_name=args.brand_name,
        brand_logo=brand_logo,
        brand_footer=args.brand_footer,
        watermark_text=args.watermark,
        watermark_image=args.watermark_image,
        watermark_opacity=args.watermark_opacity,
        watermark_width=args.watermark_width,
        unsafe_html=args.unsafe_html,
        allow_remote_assets=args.allow_remote_assets,
        progress=_progress_callback(args.progress),
    )
    pdf_path = convert(options)
    print(f"PDF created: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
