from pathlib import Path


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


def test_academic_style_aligns_mermaid_arrows_with_node_borders():
    css = (STYLE_DIR / "style-academic.css").read_text(encoding="utf-8")
    assert "--md2pdf-mermaid-stroke: #7c2d12" in css
    assert "--md2pdf-mermaid-edge-ink: #7c2d12" in css
