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
    assert "<summary><span>⚙️ Advanced</span>" in html


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


def test_gui_zen_mode_has_escape_route_and_is_not_restored():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert 'id="zenToolbar"' in html
    assert 'id="zenExitBtn"' in html
    assert 'function exitZen()' in html
    assert "event.key === 'Escape' && currentLayout === 'zen'" in html
    assert "lastNonZenLayout" in html
    assert "layout: currentLayout === 'zen' ? lastNonZenLayout : currentLayout" in html
    assert "['split','editor','preview'].includes(state.layout)" in html
    assert "body.zen .zen-toolbar{display:flex}" in html
    assert "Ctrl/Cmd+4" in Path(__file__).resolve().parents[1].joinpath("docs", "STUDIO.md").read_text(encoding="utf-8")
