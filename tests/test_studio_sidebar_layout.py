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


def test_studio_light_mode_uses_layered_surface_colors() -> None:
    html = _gui_html()

    light_mode_rule = _css_rule(html, "body.light-mode")
    assert "--bg:#f1f5f9" in light_mode_rule
    assert "--bg-soft:#e2e8f0" in light_mode_rule
    assert "--panel:#ffffff" in light_mode_rule
    assert "--editor:#ffffff" in light_mode_rule
    assert "--preview:#ffffff" in light_mode_rule
    assert "--border-strong:#94a3b8" in light_mode_rule
    assert "--border:#cbd5e1" in light_mode_rule

    light_brand_rule = _css_rule(html, "body.light-mode .brand-mark")
    assert "background:transparent" in light_brand_rule
    assert "border:0" in light_brand_rule
    assert "box-shadow:none" in light_brand_rule


def test_collapsed_settings_restore_button_has_reserved_space() -> None:
    html = _gui_html()

    collapsed_workspace_rule = _css_rule(html, "body.settings-collapsed .workspace")
    assert "padding-left:64px" in collapsed_workspace_rule

    restore_rule = _css_rule(html, ".settings-restore")
    assert "top:76px" in restore_rule
    assert "left:16px" in restore_rule

    assert ".workspace,body.settings-collapsed .workspace{grid-template-columns:1fr;padding:10px}" in html


def test_studio_open_accordion_state_is_minimal_without_side_rails() -> None:
    html = _gui_html()

    closed_rule = _css_rule(html, ".settings-section")
    assert "position:relative" in closed_rule
    assert "border-left" not in closed_rule

    summary_rule = _css_rule(html, ".settings-section>summary")
    assert "position:relative" in summary_rule
    assert "padding:16px 16px 15px" in summary_rule

    assert ".settings-section>summary::before" not in html
    assert ".settings-section[open]>summary::before" not in html

    open_rule = _css_rule(html, ".settings-section[open]")
    assert "border-left" not in open_rule
    assert "box-shadow:" in open_rule
    assert "background:" not in open_rule

    light_open_rule = _css_rule(html, "body.light-mode .settings-section[open]")
    assert "box-shadow:" in light_open_rule
    assert "background:" not in light_open_rule

    open_summary_rule = _css_rule(html, ".settings-section[open]>summary")
    assert "background:color-mix" in open_summary_rule
    assert "border-bottom-color:" in open_summary_rule


def test_studio_footer_and_light_switches_have_clear_boundaries() -> None:
    html = _gui_html()

    footer_rule = _css_rule(html, ".footer")
    assert "padding:0 20px" in footer_rule
    assert "overflow:hidden" in footer_rule

    switch_rule = _css_rule(html, ".switch input")
    for expected in ("width:46px", "height:26px", "cubic-bezier", "box-shadow:"):
        assert expected in switch_rule

    switch_knob_rule = _css_rule(html, ".switch input::after")
    assert "background:#ffffff" in switch_knob_rule
    assert "width:20px" in switch_knob_rule
    assert "height:20px" in switch_knob_rule
    assert "cubic-bezier" in switch_knob_rule

    checked_knob_rule = _css_rule(html, ".switch input:checked::after")
    assert "transform:translateX(20px)" in checked_knob_rule
    assert "background:#ffffff" in checked_knob_rule

    light_switch_rule = _css_rule(html, "body.light-mode .switch input")
    assert "background:#e2e8f0" in light_switch_rule
    assert "border-color:#94a3b8" in light_switch_rule
    assert "box-shadow:" in light_switch_rule

    light_switch_knob_rule = _css_rule(html, "body.light-mode .switch input::after")
    assert "background:#ffffff" in light_switch_knob_rule
    assert "box-shadow:" in light_switch_knob_rule


def test_studio_logo_and_toolbar_icons_are_minimal_and_centered() -> None:
    html = _gui_html()

    brand_rules = [
        _css_rule(html, ".brand-mark"),
        _css_rule(html, "body.light-mode .brand-mark"),
    ]
    for rule in brand_rules:
        assert "background:transparent" in rule
        assert "border:0" in rule
        assert "box-shadow:none" in rule
        assert "linear-gradient" not in rule

    header_title_rule = _css_rule(html, ".sidebar-head strong,.pane-head strong")
    assert "font-size:11px" in header_title_rule
    assert "font-weight:900" in header_title_rule
    assert "letter-spacing:.11em" in header_title_rule

    icon_rule = _css_rule(html, ".icon")
    assert "display:block" in icon_rule
    assert "align-self:center" in icon_rule

    icon_button_rule = _css_rule(html, ".btn-icon")
    assert "display:inline-grid" in icon_button_rule
    assert "place-items:center" in icon_button_rule

    format_button_rule = _css_rule(html, ".format-btn")
    assert "border:0" in format_button_rule
    assert "display:inline-grid" in format_button_rule
    assert "place-items:center" in format_button_rule


def test_studio_uses_monochromatic_accent_controls() -> None:
    html = _gui_html()

    dark_root = _css_rule(html, ":root")
    light_root = _css_rule(html, "body.light-mode")
    assert "--accent-2:#0f766e" in dark_root
    assert "--accent-3:#14b8a6" in dark_root
    assert "--accent-2:#0f766e" in light_root
    assert "--accent-3:#14b8a6" in light_root

    primary_rule = _css_rule(html, ".btn-primary")
    assert "background:var(--accent)" in primary_rule
    assert "linear-gradient" not in primary_rule

    checked_switch_rule = _css_rule(html, ".switch input:checked")
    assert "background:var(--accent)" in checked_switch_rule
    assert "linear-gradient" not in checked_switch_rule

    checked_checkbox_rule = _css_rule(html, ".check input:checked")
    assert "background:var(--accent)" in checked_checkbox_rule
    assert "linear-gradient" not in checked_checkbox_rule

    progress_rule = _css_rule(html, ".progress-bar")
    assert "background:var(--accent)" in progress_rule
    assert "linear-gradient" not in progress_rule


def test_studio_toolbar_controls_use_ghost_button_chrome() -> None:
    html = _gui_html()

    toolbar_button_rule = _css_rule(html, ".tool-group .btn:not(.btn-primary)")
    assert "border-color:transparent" in toolbar_button_rule
    assert "background:transparent" in toolbar_button_rule
    assert "box-shadow:none" in toolbar_button_rule

    toolbar_hover_rule = _css_rule(html, ".tool-group .btn:not(.btn-primary):hover")
    assert "background:color-mix" in toolbar_hover_rule
    assert "border-color:transparent" in toolbar_hover_rule

    quiet_hover_rule = _css_rule(html, ".btn-quiet:hover")
    assert "border-color:transparent" in quiet_hover_rule
    assert "box-shadow:none" in quiet_hover_rule

    format_button_rule = _css_rule(html, ".format-btn")
    assert "border:0" in format_button_rule
    assert "background:transparent" in format_button_rule

    format_hover_rule = _css_rule(html, ".format-btn:hover")
    assert "background:color-mix" in format_hover_rule
    assert "border-color" not in format_hover_rule


def test_studio_settings_panel_has_more_breathing_room() -> None:
    html = _gui_html()

    summary_rule = _css_rule(html, ".settings-section>summary")
    assert "padding:16px 16px 15px" in summary_rule
    assert "gap:14px" in summary_rule

    assert ".settings-body{padding:18px 16px 20px" in html

    kicker_rule = _css_rule(html, ".section-kicker")
    assert "margin:0 0 16px" in kicker_rule
    assert "line-height:1.55" in kicker_rule

    assert ".field{gap:7px;margin-bottom:16px}" in html

    setting_row_rule = _css_rule(html, ".setting-row")
    assert "gap:10px" in setting_row_rule
