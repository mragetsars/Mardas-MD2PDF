from pathlib import Path

from mardas_md2pdf.appearance import PALETTES_ORDER
from mardas_md2pdf.markdown import render_markdown
from mardas_md2pdf.renderer import PdfOptions, build_html


STYLE_DIR = Path(__file__).resolve().parents[1] / "src" / "assets"


def test_toc_can_split_across_pages_without_moving_whole_sections():
    for style in STYLE_DIR.glob("style-*.css"):
        css = style.read_text(encoding="utf-8")
        assert ".md2pdf-toc" in css
        assert "page-break-inside: auto" in css
        assert "break-inside: auto" in css
        assert "page-break-inside: avoid" in css


def test_dark_style_overrides_details_and_mermaid_for_contrast():
    css = (STYLE_DIR / "style-textbook-dark.css").read_text(encoding="utf-8")
    assert "--md2pdf-details-bg: #101010" in css
    assert "--md2pdf-details-ink: #e5e5e5" in css
    assert "--md2pdf-mermaid-figure-bg: #101010" in css
    assert "--md2pdf-mermaid-node-bg: #151515" in css
    assert "--md2pdf-mermaid-stroke: #d4d4d4" in css
    assert "--md2pdf-mermaid-label-halo: #0b0b0b" in css


def test_academic_style_keeps_accent_colors_palette_driven():
    css = (STYLE_DIR / "style-academic.css").read_text(encoding="utf-8")
    forbidden_legacy_colors = ["#7c2d12", "#c2410c", "#fff7ed", "#fed7aa", "#fffaf5", "124, 45, 18"]
    for color in forbidden_legacy_colors:
        assert color not in css
    assert "--blue: var(--accent" in css
    assert "--md2pdf-mermaid-stroke: var(--accent" in css
    assert "--md2pdf-mermaid-edge-ink: var(--accent" in css


def test_academic_palette_overrides_are_emitted_for_every_palette(tmp_path):
    md = "---\ntitle: Palette QA\ncover_label: Label\n---\n\n# Heading\n\n> [!NOTE]\n> Callout\n"
    input_path = tmp_path / "palette.md"
    input_path.write_text(md, encoding="utf-8")
    for palette in PALETTES_ORDER:
        html = build_html(
            render_markdown(md),
            PdfOptions(
                input_path=input_path,
                output_path=tmp_path / f"{palette}.pdf",
                style="academic",
                palette=palette,
                mode="light",
            ),
        )
        assert f"body.md2pdf-style-academic.md2pdf-palette-{palette} blockquote" in html
        assert "border-inline-start-color: var(--accent)" in html
        assert "background: var(--accent-soft)" in html


def test_all_appearance_combinations_emit_clean_palette_css(tmp_path):
    from mardas_md2pdf.appearance import MODES, PALETTES_ORDER, STYLES
    from mardas_md2pdf.markdown import render_markdown
    from mardas_md2pdf.renderer import PdfOptions, build_html

    md = "---\ntitle: Matrix\ncover_label: Complete Guide\n---\n\n# Heading\n\n`code` and <mark>mark</mark>.\n"
    result = render_markdown(md)
    input_path = tmp_path / "matrix.md"
    input_path.write_text(md, encoding="utf-8")
    for style in STYLES:
        for palette in PALETTES_ORDER:
            for mode in MODES:
                html = build_html(
                    result,
                    PdfOptions(
                        input_path=input_path,
                        output_path=tmp_path / f"{style}-{palette}-{mode}.pdf",
                        style=style,
                        palette=palette,
                        mode=mode,
                    ),
                )
                assert f"md2pdf-style-{style}" in html
                assert f"md2pdf-palette-{palette}" in html
                assert f"md2pdf-mode-{mode}" in html
                assert "background: transparent !important;" in html
                assert "background-color: color-mix(in srgb, var(--accent-soft" in html
