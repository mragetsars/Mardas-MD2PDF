from pathlib import Path


GUI_HTML = Path(__file__).resolve().parents[1] / "src" / "mardas_md2pdf" / "assets" / "gui.html"


def test_gui_marks_preview_as_approximate_and_exposes_custom_page_sizes():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "Approximate preview" in html
    assert "The exported PDF uses the Python renderer" in html
    assert "A4 landscape" in html
    assert "210mm 297mm" in html


def test_gui_asset_writer_enforces_size_limits(tmp_path, monkeypatch):
    import base64

    from mardas_md2pdf import gui

    def asset(path: str, size: int) -> dict[str, str]:
        payload = base64.b64encode(b"x" * size).decode("ascii")
        return {"path": path, "data": f"data:image/png;base64,{payload}"}

    monkeypatch.setattr(gui, "MAX_GUI_ASSET_BYTES", 10)
    monkeypatch.setattr(gui, "MAX_GUI_TOTAL_ASSET_BYTES", 15)

    gui._write_gui_assets(tmp_path, [asset("a.png", 10), asset("b.png", 6), asset("c.png", 11)])

    assert (tmp_path / "a.png").exists()
    assert not (tmp_path / "b.png").exists()
    assert not (tmp_path / "c.png").exists()




def test_studio_brand_logo_path_uses_attached_assets(tmp_path):
    from mardas_md2pdf import gui

    gui._write_gui_assets(
        tmp_path,
        [
            {
                "path": "images/logo.png",
                "data": "data:image/png;base64,eA==",
            }
        ],
    )

    logo = tmp_path / gui._safe_asset_relative_path("images/logo.png", fallback="brand-logo")
    assert logo.is_file()
    assert logo.read_bytes() == b"x"


def test_gui_documents_asset_limits():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "Up to 250 assets" in html
    assert "12 MB per asset" in html
    assert "32 MB total" in html
    assert "MAX_GUI_ASSETS" in html


def test_studio_json_decode_errors_are_client_facing():
    import pytest

    from mardas_md2pdf import gui

    with pytest.raises(gui.StudioRequestError) as exc_info:
        gui._decode_json_payload(b'{bad json')

    assert exc_info.value.status == 400
    assert exc_info.value.code == "invalid_json"
    assert "valid JSON" in str(exc_info.value)


def test_studio_error_payload_includes_code_and_status():
    from mardas_md2pdf import gui

    assert gui._error_payload("Nope", status=413, code="too_large") == {
        "error": "Nope",
        "status": 413,
        "code": "too_large",
    }


def test_studio_bind_warning_only_for_non_local_hosts():
    from mardas_md2pdf import gui

    assert gui._studio_bind_warning("127.0.0.1") is None
    assert gui._studio_bind_warning("localhost") is None
    assert gui._studio_bind_warning("::1") is None

    warning = gui._studio_bind_warning("0.0.0.0")
    assert warning is not None
    assert "non-local host" in warning
    assert "trusted networks" in warning


def test_gui_persists_studio_workspace_state():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "MARDAS_STUDIO_STATE_KEY" in html
    assert "mardas-md2pdf-studio-state-v1" in html
    assert "function loadStudioState" in html
    assert "function saveStudioState" in html
    assert "Reset State" in html
    assert "MAX_STORED_MARKDOWN_CHARS" in html


def test_gui_exposes_keyboard_shortcuts_for_local_workflow():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "event.ctrlKey || event.metaKey" in html
    assert "downloadMarkdown();" in html
    assert "renderPDF();" in html


def test_gui_displays_structured_render_error_codes():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "async function readRenderError" in html
    assert "payload.code" in html
    assert "Export failed (" in html



def test_studio_validates_render_options():
    import pytest

    from mardas_md2pdf import gui

    options = gui._validated_render_options(
        {
            "tocDepth": "4",
            "watermarkOpacity": "0.35",
            "pageSize": "A4 landscape",
            "toc": "false",
            "noCover": "true",
        }
    )

    assert options["toc_depth"] == 4
    assert options["watermark_opacity"] == 0.35
    assert options["page_size"] == "A4 landscape"
    assert options["style"] == "modern"
    assert options["palette"] == "blue"
    assert options["mode"] == "light"
    assert options["branding"] == "off"
    assert options["toc"] is False
    assert options["cover"] is False

    custom = gui._validated_render_options({"style": "textbook", "palette": "emerald", "mode": "dark", "branding": "full"})
    assert custom["style"] == "textbook"
    assert custom["palette"] == "emerald"
    assert custom["mode"] == "dark"
    assert custom["branding"] == "full"

    for bad_options, code in [
        ({"tocDepth": "bad"}, "invalid_toc_depth"),
        ({"tocDepth": 9}, "invalid_toc_depth"),
        ({"watermarkOpacity": "bad"}, "invalid_watermark_opacity"),
        ({"watermarkOpacity": 1.9}, "invalid_watermark_opacity"),
        ({"pageSize": "not-a-size"}, "invalid_page_size"),
        ({"direction": "sideways"}, "invalid_direction"),
        ({"style": "textbook-dark"}, "invalid_style"),
        ({"palette": "neon"}, "invalid_palette"),
        ({"mode": "auto"}, "invalid_mode"),
        ({"branding": "loud"}, "invalid_branding"),
    ]:
        with pytest.raises(gui.StudioRequestError) as exc_info:
            gui._validated_render_options(bad_options)
        assert exc_info.value.status == 400
        assert exc_info.value.code == code


def test_gui_uses_appearance_controls_instead_of_theme_profile_controls():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "styleInput" in html
    assert "paletteInput" in html
    assert "modeInput" in html
    assert "brandingInput" in html
    assert "brandNameInput" in html
    assert "brandLogoInput" in html
    assert "brandFooterInput" in html
    assert "appearanceName" in html
    assert "pdfThemeInput" not in html
    assert "profileName" not in html
    assert "--theme" not in html
    assert "--style" in html
    assert "--palette" in html
    assert "--mode" in html


def test_gui_groups_export_settings_into_user_facing_sections():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "Document<small>Basic identity and page setup</small>" in html
    assert "Appearance<small>Shape, color, and light/dark output</small>" in html
    assert "Branding<small>Keep output owned by the document</small>" in html
    assert "Layout<small>TOC, cover, and page flow</small>" in html
    assert 'class="choice-title"' in html
    assert "#icon-settings" in html


def test_gui_uses_visual_choice_cards_for_appearance_workflow():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'data-choice-group="style"' in html
    assert 'data-choice-value="modern"' in html
    assert 'data-choice-value="academic"' in html
    assert 'data-choice-group="palette"' in html
    assert 'class="palette-dot"' in html
    assert 'data-choice-group="mode"' in html
    assert 'data-choice-group="branding"' in html
    assert "function attachChoiceCards" in html
    assert "function syncChoiceCards" in html


def test_gui_copy_command_includes_branding_options():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "--branding " in html
    assert "--brand-name" in html
    assert "--brand-logo" in html
    assert "--brand-footer" in html


def test_gui_replaces_static_view_modes_with_resizable_panes():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'id="settingsGutter"' in html
    assert 'id="previewGutter"' in html
    assert 'id="settingsRestoreBtn"' in html
    assert 'function resizeSettingsPane' in html
    assert 'function resizePreviewPane' in html
    assert 'function collapseSettingsPane' in html
    assert 'function expandSettingsPane' in html
    assert 'SETTINGS_COLLAPSE_THRESHOLD' in html
    assert 'settingsCollapsed' in html
    assert 'layoutSplit' not in html
    assert 'layoutEditor' not in html
    assert 'layoutPreview' not in html
    assert 'layoutZen' not in html
    assert 'zenToolbar' not in html


def test_gui_topbar_uses_grouped_toolbar_and_icon_buttons():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'role="toolbar" aria-label="Studio toolbar"' in html
    assert 'class="tool-group" aria-label="File actions"' in html
    assert 'class="tool-group" aria-label="Resources"' in html
    assert 'class="tool-group" aria-label="Export"' in html
    assert 'class="tool-group" aria-label="View mode"' not in html
    assert 'class="tool-divider"' in html
    assert 'class="btn btn-icon btn-quiet" onclick="copyCommand()"' in html
    assert 'id="interfaceBtn" title="Switch to light Studio UI"' in html




def test_gui_uses_inline_svg_icons_and_project_logo():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'class="icon-sprite"' in html
    assert 'href="#icon-folder-open"' in html
    assert 'href="#icon-save"' in html
    assert 'href="#icon-file-down"' in html
    assert 'href="#icon-bold"' in html
    assert 'href="#icon-table"' in html
    assert '<span class="brand-mark"><img src="/assets/Mardas.png" alt="" /></span>' in html
    assert 'stroke-width:1.8' in html


def test_gui_has_no_emoji_icon_glyphs():
    html = GUI_HTML.read_text(encoding="utf-8")
    emoji_codepoints = [
        0x1F4C2, 0x1F4BE, 0x1F5BC, 0x2600, 0x1F319, 0x1F4CC, 0x1F3A8,
        0x1F3F7, 0x1F9ED, 0x2699, 0x1F4C4, 0x1F517, 0x2705,
    ]
    for codepoint in emoji_codepoints:
        assert chr(codepoint) not in html


def test_gui_microinteractions_use_stable_numeric_and_soft_cards():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'font-variant-numeric:tabular-nums' in html
    assert '.choice-copy{color:color-mix' in html
    assert 'body:not(.light-mode) .choice-copy{color:#d0d0d0}' in html
    assert '.format-btn{height:30px' in html
    assert '--muted:#b3b3b3' in html
    assert '--faint:#9a9a9a' in html
    assert '.editor-formatbar{gap:6px' in html
    assert 'border-color:transparent;background:transparent' in html

def test_gui_uses_chatgpt_like_scrollbars_and_pure_interface_surfaces():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert '*::-webkit-scrollbar' in html
    assert '--scroll-thumb:#4a4a4a' in html
    assert '--scroll-thumb:#cbd5e1' in html
    assert '--bg:#000000' in html
    assert '--panel-2:#212121' in html
    assert '--panel:#ffffff' in html
    assert '--preview:#ffffff' in html


def test_gui_export_button_keeps_contrast_on_hover_and_active():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert '.btn-primary:hover{color:#ffffff' in html
    assert '.btn-primary:active{color:#ffffff' in html
    assert '.btn-primary:focus-visible' in html


def test_gui_settings_are_accordion_sections_with_switches():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'class="card settings-section" open' in html
    assert '#icon-palette' in html
    assert '#icon-badge' in html
    assert '#icon-compass' in html
    assert '<details class="card settings-section" open><summary>' in html
    assert 'interpolate-size:allow-keywords' in html
    assert 'class="switch"><span>Generate table of contents</span>' in html
    assert 'class="switch"><span>Hide footer/page number</span>' in html


def test_gui_editor_has_formatting_toolbar_line_numbers_and_sync_scroll():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'class="editor-formatbar" aria-label="Markdown formatting toolbar"' in html
    assert "onclick=\"insertMarkdown('bold')\"" in html
    assert "onclick=\"insertMarkdown('table')\"" in html
    assert 'id="lineNumbers" class="line-numbers"' in html
    assert 'function insertMarkdown' in html
    assert 'function syncLineNumbers' in html
    assert 'function syncPreviewScroll' in html
    assert "editor.addEventListener('scroll'" in html


def test_gui_preview_exposes_render_status_and_footer_save_state():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'id="previewStatus" class="preview-status"' in html
    assert 'function setPreviewStatus' in html
    assert "setPreviewStatus('Updating preview...', true)" in html
    assert '<span id="savedState">Live preview</span>' in html
    assert 'Markdown source' in html


def test_gui_sidebar_scrolls_and_palette_uses_compact_swatches():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert '.sidebar{height:100%;display:flex;flex-direction:column;overflow:hidden' in html
    assert '.sidebar-body{display:block;flex:1 1 auto;min-height:0;padding:16px;overflow-y:auto;overflow-x:hidden' in html
    assert '.palette-grid{display:flex;align-items:center;gap:8px;flex-wrap:wrap' in html
    assert '.palette-card{position:relative;display:inline-grid;place-items:center;width:34px;height:34px' in html
    assert 'title="Blue palette" aria-label="Blue palette"' in html
    assert '.palette-card > span:not(.palette-dot)' in html


def test_gui_logo_uses_contain_fit_with_breathing_room():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert '.brand-mark{overflow:visible;background:transparent' in html
    assert '.brand-mark img{width:100%;height:100%;object-fit:contain;display:block}' in html
    assert 'body.light-mode .brand-mark img{filter:invert(1)' in html
