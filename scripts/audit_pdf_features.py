#!/usr/bin/env python3
"""Render feature-heavy PDF smoke documents for visual QA artifacts."""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

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

FEATURE_SMOKE_MARKDOWN = """---
title: "PDF Feature Smoke"
subtitle: "Tables, code, Mermaid, math, captions, footnotes, and RTL/LTR prose"
authors:
  - name: "Mardas MD2PDF QA"
    role: "Visual smoke"
summary: |
  A compact smoke document that exercises renderer features that have historically
  needed visual inspection, especially after typography and RTL/Persian changes.
version: "1.11.0"
lang: en
dir: ltr
cover_label: "Feature Smoke"
branding:
  mode: full
---

# Feature overview

This sample mixes Persian متن فارسی, English identifiers such as `renderer.pipeline`,
inline math $a^2 + b^2 = c^2$, a footnote reference[^feature], and a link to
<https://example.com/path?q=PDF>.

> [!SUCCESS]
> Callouts should keep their icon, accent, border, and text contrast in every rendered appearance.

## Numbered code block

```python title="qa_matrix.py" linenos linenostart=24 {26,31-32}
def build_visual_matrix(styles, palettes, modes):
    for style in styles:
        for palette in palettes:
            for mode in modes:
                yield f"{style}-{palette}-{mode}"

for item in build_visual_matrix(["modern"], ["blue"], ["light"]):
    print(item)
```

## Captioned table

Table 13. Feature smoke table with mixed Persian and Latin cells.

| Feature | English expectation | یادداشت فارسی | Status |
| :--- | :--- | :--- | :---: |
| Code | line numbers stay aligned | شماره خط‌ها باید هم‌راستا باشند | OK |
| Tables | borders remain visible | جدول نباید clip شود | OK |
| Math | baseline and display math remain readable | فرمول باید خوانا باشد | OK |
| Mermaid | node labels and arrows remain visible | نمودار باید کنتراست کافی داشته باشد | OK |
| RTL text | renderer.[^feature] stays grouped | نشانه‌گذاری نباید جابه‌جا شود | OK |

## Display math

$$
\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}
$$

## Mermaid flow

```mermaid title="Render pipeline"
flowchart LR
  MD[Markdown] --> HTML[Structured HTML]
  HTML --> CSS[Appearance CSS]
  CSS --> PDF[(PDF)]
  PDF --> QA{{Visual QA}}
```

## RTL paragraph

در این پاراگراف فارسی عبارت‌هایی مثل renderer. و GitHub Actions. و PDF navigation? باید با نشانه‌های پایانی خود کنار هم بمانند و در خروجی PDF از خط جدا نشوند.

[^feature]: A repeated footnote reference should keep back-links and visual grouping stable.
"""


@dataclasses.dataclass(frozen=True, slots=True)
class AppearanceCase:
    style: str
    palette: str
    mode: str

    @property
    def name(self) -> str:
        return f"{self.style}-{self.palette}-{self.mode}"


def _parse_appearance(value: str) -> AppearanceCase:
    parts = tuple(part.strip() for part in value.split(":"))
    if len(parts) != 3:
        raise SystemExit(f"invalid appearance {value!r}; expected style:palette:mode")
    style, palette, mode = parts
    if style not in STYLES:
        raise SystemExit(f"invalid style {style!r}; expected one of: {', '.join(STYLES)}")
    if palette not in PALETTES_ORDER:
        raise SystemExit(f"invalid palette {palette!r}; expected one of: {', '.join(PALETTES_ORDER)}")
    if mode not in MODES:
        raise SystemExit(f"invalid mode {mode!r}; expected one of: {', '.join(MODES)}")
    return AppearanceCase(style=style, palette=palette, mode=mode)


def _parse_appearances(value: str | None) -> tuple[AppearanceCase, ...]:
    if not value:
        return (
            AppearanceCase("modern", "blue", "light"),
            AppearanceCase("modern", "blue", "dark"),
            AppearanceCase("github", "slate", "dark"),
            AppearanceCase("academic", "amber", "dark"),
        )
    return tuple(_parse_appearance(part) for part in value.split(",") if part.strip())


def _write_sample(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(FEATURE_SMOKE_MARKDOWN, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("build/visual-qa/features"))
    parser.add_argument("--source", type=Path, help="Use an existing feature smoke Markdown document")
    parser.add_argument(
        "--appearances",
        help="Comma-separated appearance triples: style:palette:mode,style:palette:mode",
    )
    parser.add_argument("--clean", action="store_true", help="Delete output directory before rendering")
    parser.add_argument("--render-png", action="store_true", help="Render representative PNG pages")
    parser.add_argument("--png-dpi", type=int, default=72)
    parser.add_argument("--pages", default="1,2,3", help="Comma-separated 1-based PDF pages to rasterize")
    parser.add_argument("--timeout", type=int, default=90, help="Seconds per PDF render")
    parser.add_argument("--timeout-ms", type=int, default=180_000, help="Chromium timeout in milliseconds")
    args = parser.parse_args(argv)

    if args.clean:
        ensure_clean_dir(args.output_dir)
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    appearances = _parse_appearances(args.appearances)
    pages = tuple(int(part.strip()) for part in args.pages.split(",") if part.strip())
    source = args.source or args.output_dir / "feature-smoke.md"
    if args.source is None:
        _write_sample(source)

    pdf_dir = args.output_dir / "pdf"
    png_dir = args.output_dir / "png"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    records: list[dict[str, object]] = []

    for appearance in appearances:
        output_pdf = pdf_dir / f"{appearance.name}.pdf"
        record: dict[str, object] = {
            "name": appearance.name,
            "style": appearance.style,
            "palette": appearance.palette,
            "mode": appearance.mode,
            "pdf": relative_to(output_pdf, args.output_dir),
        }
        print(f"render {appearance.name}")
        try:
            run_mardas_cli(
                source,
                output_pdf,
                style=appearance.style,
                palette=appearance.palette,
                mode=appearance.mode,
                command_timeout=args.timeout,
                timeout_ms=args.timeout_ms,
            )
            if args.render_png:
                rendered_pages = render_pdf_pages(
                    output_pdf,
                    png_dir,
                    pages=pages,
                    dpi=args.png_dpi,
                    prefix=appearance.name,
                )
                record["png"] = [relative_to(path, args.output_dir) for path in rendered_pages]
                record["png_stats"] = [dataclasses.asdict(png_stats(path)) for path in rendered_pages]
            records.append(record)
        except Exception as exc:  # noqa: BLE001 - audit should keep collecting failures.
            failures.append(f"{appearance.name}: {exc}")

    write_json(
        args.output_dir / "manifest.json",
        {
            "source": relative_to(source, args.output_dir),
            "appearances": [dataclasses.asdict(case) for case in appearances],
            "pages": pages,
            "records": records,
            "failures": failures,
        },
    )

    if args.render_png:
        gallery_items = []
        for record in records:
            for image in record.get("png", []):
                gallery_items.append(
                    {
                        "label": str(record["name"]),
                        "image": str(image),
                        "meta": Path(str(image)).stem,
                    }
                )
        write_html_gallery(args.output_dir / "gallery.html", title="PDF feature smoke", items=gallery_items)

    if failures:
        (args.output_dir / "failures.txt").write_text("\n".join(failures) + "\n", encoding="utf-8")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
