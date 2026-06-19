#!/usr/bin/env python3
"""Render appearance combinations for visual regression review.

The default matrix covers every registered style, palette, and mode.  For CI or
fast local checks, pass comma-separated filters such as ``--styles modern,github``
and ``--palettes blue,slate``.
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path
from typing import Iterable

from mardas_md2pdf.appearance import MODES, PALETTES_ORDER, STYLES
from visual_qa import (
    ensure_clean_dir,
    png_stats,
    relative_to,
    render_pdf_pages,
    run_mardas_cli,
    write_html_gallery,
    write_json,
)

SAMPLE_MARKDOWN = """---
title: "Appearance Matrix Smoke"
subtitle: "Style, palette and mode verification"
authors:
  - name: "Mardas MD2PDF QA"
    role: "Appearance audit"
date: "1405-03-20"
summary: |
  This document intentionally mixes Persian and English content, code, tables,
  callouts, formulas, Mermaid diagrams, footnotes, and wide rows so every
  appearance combination can be checked visually.
institution: "Mardas Lab"
course: "Appearance QA"
version: "1.11.0"
status: "Audit"
keywords:
  - appearance
  - style
  - palette
  - mode
lang: en
dir: ltr
cover_label: "Appearance Audit"
branding:
  mode: full
---

# Overview

This PDF is a compact visual benchmark for **Mardas MD2PDF** appearance combinations.
It includes Persian text مثل این جمله فارسی کنار English identifiers such as `RenderOptions` and `appearance.mode`.

> [!NOTE]
> A callout should follow the selected palette, keep readable contrast in dark mode, and avoid looking detached from the cover.

The inline formula $E = mc^2$ should remain readable. The display formula should align with surrounding text:

$$
\\int_0^1 x^2 dx = \\frac{1}{3}
$$

## Code and table

```python title="appearance.py" {2,5} linenos
def resolve_appearance(style, palette, mode):
    style = style or "modern"
    palette = palette or "blue"
    mode = mode or "light"
    return style, palette, mode
```

| Area | Expected behavior | Persian note |
| :--- | :--- | :--- |
| Cover | Background and accent should match style + palette | جلد باید با صفحات داخلی هماهنگ باشد |
| Code | Blocks should be readable in light and dark modes | کد نباید کنتراست کم داشته باشد |
| Tables | Borders and zebra rows should remain visible | جدول باید خوانا بماند |
| Callouts | Accent should follow palette | رنگ تاکید باید از پالت بیاید |

## Mermaid

```mermaid
flowchart TD
  A[Markdown] --> B[HTML]
  B --> C[CSS appearance]
  C --> D[PDF]
```

## Longer paragraph

A screen-first dark output may use deep surfaces, but it should not make every style look identical. A textbook dark style can be almost black, while modern or GitHub can stay slightly tinted if the accent palette still feels intentional.

متن فارسی برای بررسی حالت راست‌به‌چپ و ترکیب کلمات English در کنار شناسه‌هایی مثل `md2pdf-mode-dark` استفاده می‌شود تا خوانایی در همه حالت‌ها مشخص شود.[^note]

[^note]: Footnote text should keep enough contrast and should not disappear in dark mode.
"""


@dataclasses.dataclass(frozen=True, slots=True)
class RenderItem:
    style: str
    palette: str
    mode: str

    @property
    def name(self) -> str:
        return f"{self.style}-{self.palette}-{self.mode}"


def _parse_filter(value: str | None, allowed: Iterable[str], *, label: str) -> tuple[str, ...]:
    allowed_tuple = tuple(allowed)
    if not value:
        return allowed_tuple
    requested = tuple(part.strip() for part in value.split(",") if part.strip())
    invalid = [part for part in requested if part not in allowed_tuple]
    if invalid:
        choices = ", ".join(allowed_tuple)
        raise SystemExit(f"invalid {label}: {', '.join(invalid)}; expected one of: {choices}")
    return requested


def _write_sample(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("build/visual-qa/appearance"))
    parser.add_argument("--source", type=Path, help="Use an existing Markdown smoke document")
    parser.add_argument("--styles", help="Comma-separated style filter")
    parser.add_argument("--palettes", help="Comma-separated palette filter")
    parser.add_argument("--modes", help="Comma-separated mode filter")
    parser.add_argument("--clean", action="store_true", help="Delete output directory before rendering")
    parser.add_argument("--render-png", action="store_true", help="Render cover/content PNGs with pdftoppm")
    parser.add_argument("--png-dpi", type=int, default=72)
    parser.add_argument("--timeout", type=int, default=90, help="Seconds per PDF render")
    parser.add_argument("--timeout-ms", type=int, default=180_000, help="Chromium timeout in milliseconds")
    args = parser.parse_args(argv)

    if args.clean:
        ensure_clean_dir(args.output_dir)
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    styles = _parse_filter(args.styles, STYLES, label="style")
    palettes = _parse_filter(args.palettes, PALETTES_ORDER, label="palette")
    modes = _parse_filter(args.modes, MODES, label="mode")
    source = args.source or args.output_dir / "appearance-matrix.md"
    if args.source is None:
        _write_sample(source)

    pdf_dir = args.output_dir / "pdf"
    cover_dir = args.output_dir / "cover_png"
    content_dir = args.output_dir / "content_png"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    records: list[dict[str, object]] = []
    for style in styles:
        for palette in palettes:
            for mode in modes:
                item = RenderItem(style=style, palette=palette, mode=mode)
                output_pdf = pdf_dir / f"{item.name}.pdf"
                record: dict[str, object] = {
                    "name": item.name,
                    "style": style,
                    "palette": palette,
                    "mode": mode,
                    "pdf": relative_to(output_pdf, args.output_dir),
                }
                print(f"render {item.name}")
                try:
                    run_mardas_cli(
                        source,
                        output_pdf,
                        style=style,
                        palette=palette,
                        mode=mode,
                        command_timeout=args.timeout,
                        timeout_ms=args.timeout_ms,
                    )
                    if args.render_png:
                        cover_png = render_pdf_pages(
                            output_pdf,
                            cover_dir,
                            pages=(1,),
                            dpi=args.png_dpi,
                            prefix=item.name,
                        )[0]
                        content_png = render_pdf_pages(
                            output_pdf,
                            content_dir,
                            pages=(2,),
                            dpi=args.png_dpi,
                            prefix=item.name,
                        )[0]
                        record["cover_png"] = relative_to(cover_png, args.output_dir)
                        record["content_png"] = relative_to(content_png, args.output_dir)
                        record["cover_stats"] = dataclasses.asdict(png_stats(cover_png))
                        record["content_stats"] = dataclasses.asdict(png_stats(content_png))
                    records.append(record)
                except Exception as exc:  # noqa: BLE001 - audit should keep collecting failures.
                    failures.append(f"{item.name}: {exc}")

    payload = {
        "matrix": {
            "styles": styles,
            "palettes": palettes,
            "modes": modes,
            "count": len(styles) * len(palettes) * len(modes),
        },
        "source": relative_to(source, args.output_dir),
        "records": records,
        "failures": failures,
    }
    write_json(args.output_dir / "manifest.json", payload)

    if args.render_png:
        cover_items = [
            {"label": str(record["name"]), "image": str(record["cover_png"]), "meta": "cover"}
            for record in records
            if "cover_png" in record
        ]
        content_items = [
            {"label": str(record["name"]), "image": str(record["content_png"]), "meta": "content"}
            for record in records
            if "content_png" in record
        ]
        write_html_gallery(args.output_dir / "cover-gallery.html", title="Appearance cover matrix", items=cover_items)
        write_html_gallery(args.output_dir / "content-gallery.html", title="Appearance content matrix", items=content_items)

    if failures:
        (args.output_dir / "failures.txt").write_text("\n".join(failures) + "\n", encoding="utf-8")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
