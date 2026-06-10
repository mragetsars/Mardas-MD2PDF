#!/usr/bin/env python3
"""Render every appearance combination for visual review.

This script is intentionally kept outside the normal CI path because it launches
Chromium once per combination.  Use it after changing appearance CSS, styles, or
palettes to create a complete matrix of smoke PDFs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from mardas_md2pdf.appearance import MODES, PALETTES_ORDER, STYLES

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
version: "1.6.1"
status: "Audit"
keywords:
  - appearance
  - style
  - palette
  - mode
lang: en
dir: ltr
cover_label: "Appearance Audit"
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


def _write_sample(path: Path) -> None:
    path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")


def _render_png(pdf: Path, output_dir: Path, page: int, label: str, dpi: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{pdf.stem}.png"
    if target.exists():
        return
    prefix = output_dir / pdf.stem
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-singlefile", str(pdf), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    generated = output_dir / f"{pdf.stem}.png"
    if not generated.exists():
        raise RuntimeError(f"pdftoppm did not create {label} render for {pdf.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("appearance-audit"))
    parser.add_argument("--source", type=Path, help="Use an existing Markdown smoke document")
    parser.add_argument("--render-png", action="store_true", help="Render cover/content PNGs with pdftoppm")
    parser.add_argument("--png-dpi", type=int, default=64)
    parser.add_argument("--timeout", type=int, default=60, help="Seconds per PDF render")
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = args.source or args.output_dir / "appearance_matrix.md"
    if args.source is None:
        _write_sample(source)

    pdf_dir = args.output_dir / "pdf"
    pdf_dir.mkdir(exist_ok=True)
    failures: list[str] = []
    for style in STYLES:
        for palette in PALETTES_ORDER:
            for mode in MODES:
                name = f"{style}-{palette}-{mode}"
                output_pdf = pdf_dir / f"{name}.pdf"
                command = [
                    sys.executable,
                    "-m",
                    "mardas_md2pdf.cli",
                    str(source),
                    "-o",
                    str(output_pdf),
                    "--style",
                    style,
                    "--palette",
                    palette,
                    "--mode",
                    mode,
                    "--toc",
                    "--toc-depth",
                    "3",
                    "--progress",
                    "off",
                ]
                print(f"render {name}")
                try:
                    subprocess.run(command, check=True, timeout=args.timeout)
                    if args.render_png:
                        _render_png(output_pdf, args.output_dir / "cover", 1, "cover", args.png_dpi)
                        _render_png(output_pdf, args.output_dir / "content", 2, "content", args.png_dpi)
                except Exception as exc:  # noqa: BLE001 - audit script should keep collecting failures.
                    failures.append(f"{name}: {exc}")

    if failures:
        failure_text = "\n".join(failures)
        (args.output_dir / "failures.txt").write_text(failure_text + "\n", encoding="utf-8")
        print(failure_text, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
