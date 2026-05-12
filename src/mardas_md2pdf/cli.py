from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .renderer import PdfOptions, convert


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mrs-md2pdf",
        description="Convert Markdown to polished PDF with Persian RTL/LTR typography, hierarchical TOC, code highlighting, tables, and MathJax.",
    )
    parser.add_argument("input", type=Path, help="Input Markdown file")
    parser.add_argument("-o", "--output", type=Path, help="Output PDF path")
    parser.add_argument("--title", help="Override document title")
    parser.add_argument("--author", help="Override author metadata")
    parser.add_argument("--description", help="Override summary/description metadata")
    parser.add_argument("--toc", action="store_true", help="Generate a hierarchical table of contents from Markdown headings")
    parser.add_argument("--toc-depth", type=int, default=6, choices=range(1, 7), metavar="1..6", help="Maximum heading level to include in the TOC; default: 6")
    parser.add_argument("--debug-html", type=Path, help="Write the intermediate HTML for inspection")
    parser.add_argument("--page-size", default="A4", help="PDF page size, e.g. A4, Letter")
    parser.add_argument("--margin-top", default="18mm", help="Top CSS page margin")
    parser.add_argument("--margin-bottom", default="20mm", help="Bottom CSS page margin")
    parser.add_argument("--margin-x", default="16mm", help="Left/right CSS page margin")
    parser.add_argument("--font-dir", type=Path, help="Directory containing Vazirmatn font files")
    parser.add_argument("--chromium-path", help="Path to Chromium/Chrome executable")
    parser.add_argument("--theme", choices=["modern", "textbook"], default="modern", help="Visual theme. modern is the polished flat theme; textbook is closer to academic Persian course notes.")
    parser.add_argument("--no-cover", action="store_true", help="Do not generate the automatic cover page")
    parser.add_argument("--no-header-footer", action="store_true", help="Disable page number footer")
    parser.add_argument("--no-mathjax", action="store_true", help="Do not load MathJax")
    parser.add_argument("--timeout-ms", type=int, default=120_000, help="Browser timeout in milliseconds")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    input_path = args.input
    if not input_path.exists():
        parser.error(f"Input file not found: {input_path}")
    output_path = args.output or input_path.with_suffix(".pdf")
    options = PdfOptions(
        input_path=input_path,
        output_path=output_path,
        title=args.title,
        author=args.author,
        description=args.description,
        toc=args.toc,
        toc_depth=args.toc_depth,
        debug_html=args.debug_html,
        page_size=args.page_size,
        margin_top=args.margin_top,
        margin_bottom=args.margin_bottom,
        margin_x=args.margin_x,
        font_dir=args.font_dir,
        chromium_path=args.chromium_path,
        no_header_footer=args.no_header_footer,
        no_mathjax=args.no_mathjax,
        timeout_ms=args.timeout_ms,
        theme=args.theme,
        cover=not args.no_cover,
    )
    pdf_path = convert(options)
    print(f"PDF created: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
