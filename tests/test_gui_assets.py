from pathlib import Path


GUI_HTML = Path(__file__).resolve().parents[1] / "src" / "assets" / "gui.html"


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
    assert options["toc"] is False
    assert options["cover"] is False

    for bad_options, code in [
        ({"tocDepth": "bad"}, "invalid_toc_depth"),
        ({"tocDepth": 9}, "invalid_toc_depth"),
        ({"watermarkOpacity": "bad"}, "invalid_watermark_opacity"),
        ({"watermarkOpacity": 1.9}, "invalid_watermark_opacity"),
        ({"pageSize": "not-a-size"}, "invalid_page_size"),
        ({"direction": "sideways"}, "invalid_direction"),
    ]:
        with pytest.raises(gui.StudioRequestError) as exc_info:
            gui._validated_render_options(bad_options)
        assert exc_info.value.status == 400
        assert exc_info.value.code == code
