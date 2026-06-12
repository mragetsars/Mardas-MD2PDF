from __future__ import annotations

from pathlib import Path


GUI_HTML = Path(__file__).resolve().parents[1] / "src" / "mardas_md2pdf" / "assets" / "gui.html"


def _gui_html() -> str:
    return GUI_HTML.read_text(encoding="utf-8")


def _css_rule(html: str, selector: str) -> str:
    start = html.index(selector + "{")
    end = html.index("}", start)
    return html[start:end]


def test_studio_headers_are_pixel_aligned() -> None:
    html = _gui_html()
    header_rule = _css_rule(html, ".sidebar-head,.pane-head")

    assert "height:46px" in header_rule
    assert "min-height:46px" in header_rule
    assert "flex:0 0 46px" in header_rule

    sidebar_head_rule = _css_rule(html, ".sidebar-head")
    assert "flex-wrap:nowrap" in sidebar_head_rule
    assert "height:auto" not in sidebar_head_rule
    assert "min-height:52px" not in sidebar_head_rule


def test_studio_appearance_badge_truncates_without_reflow() -> None:
    html = _gui_html()
    badge_rule = _css_rule(html, ".sidebar-head #appearanceName")

    assert "white-space:nowrap" in badge_rule
    assert "overflow:hidden" in badge_rule
    assert "text-overflow:ellipsis" in badge_rule
    assert "overflow-wrap:anywhere" not in badge_rule
    assert "white-space:normal" not in badge_rule


def test_studio_sidebar_uses_block_scroller_without_flex_leakage() -> None:
    html = _gui_html()
    assert html.count(".sidebar-body{") == 1

    sidebar_rule = _css_rule(html, ".sidebar")
    for expected in ("height:100%", "overflow:hidden", "display:flex", "flex-direction:column"):
        assert expected in sidebar_rule

    body_rule = _css_rule(html, ".sidebar-body")
    for expected in (
        "display:block",
        "overflow-y:auto",
        "overflow-x:hidden",
        "flex:1 1 auto",
        "min-height:0",
        "padding:16px",
    ):
        assert expected in body_rule
    assert "display:flex" not in body_rule
    assert "gap:" not in body_rule

    assert ".sidebar-body>.card,.sidebar-body>.settings-section{margin-bottom:16px}" in html
    assert ".sidebar-body>.card:last-child,.sidebar-body>.settings-section:last-child{margin-bottom:0}" in html


def test_studio_light_mode_and_open_accordion_contrast_are_explicit() -> None:
    html = _gui_html()

    light_mode_rule = _css_rule(html, "body.light-mode")
    assert "--border-strong:#aeb8c5" in light_mode_rule
    assert "--border:#d9dee7" in light_mode_rule

    light_brand_rule = _css_rule(html, "body.light-mode .brand-mark")
    assert "background:linear-gradient" in light_brand_rule
    assert "border-color:" in light_brand_rule

    open_rule = _css_rule(html, ".settings-section[open]")
    assert "border-color:" in open_rule
    assert "background:" in open_rule
    assert "box-shadow:" in open_rule

    open_summary_rule = _css_rule(html, ".settings-section[open]>summary")
    assert "background:" in open_summary_rule
    assert "border-bottom-color:" in open_summary_rule
