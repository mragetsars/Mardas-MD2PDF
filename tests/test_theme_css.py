from pathlib import Path


THEME_DIR = Path(__file__).resolve().parents[1] / "src" / "assets"


def test_toc_can_split_across_pages_without_moving_whole_sections():
    for theme in THEME_DIR.glob("theme-*.css"):
        css = theme.read_text(encoding="utf-8")
        assert ".md2pdf-toc" in css
        assert "page-break-inside: auto" in css
        assert "break-inside: auto" in css
        assert "page-break-inside: avoid" in css
