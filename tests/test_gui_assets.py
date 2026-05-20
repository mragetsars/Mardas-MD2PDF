from pathlib import Path


GUI_HTML = Path(__file__).resolve().parents[1] / "src" / "assets" / "gui.html"


def test_gui_marks_preview_as_approximate_and_exposes_custom_page_sizes():
    html = GUI_HTML.read_text(encoding="utf-8")

    assert "Approximate preview" in html
    assert "The exported PDF uses the Python renderer" in html
    assert "A4 landscape" in html
    assert "210mm 297mm" in html
