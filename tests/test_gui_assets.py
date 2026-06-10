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
