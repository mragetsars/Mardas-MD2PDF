from mardas_md2pdf.renderer import _css_page_size, _playwright_page_size_kwargs


def test_css_page_size_accepts_named_orientation_and_dimensions():
    assert _css_page_size("A4 landscape") == "A4 landscape"
    assert _css_page_size("210mm 297mm") == "210mm 297mm"
    assert _css_page_size("bad; value") == "A4"


def test_playwright_page_size_uses_format_only_for_named_formats():
    assert _playwright_page_size_kwargs("Letter") == {"format": "Letter"}
    assert _playwright_page_size_kwargs("210mm 297mm") == {"width": "210mm", "height": "297mm"}
    assert _playwright_page_size_kwargs("A4 landscape") == {}


def test_font_faces_warns_for_missing_font_directory(tmp_path):
    import pytest

    from mardas_md2pdf.renderer import _font_faces

    with pytest.warns(RuntimeWarning, match="Font directory not found"):
        assert _font_faces(tmp_path / "missing-fonts") == ""


def test_render_pdf_warns_when_mathjax_evaluation_fails(tmp_path):
    import pytest

    from mardas_md2pdf.renderer import PdfOptions, _render_pdf

    class FakePage:
        def __init__(self):
            self.evaluate_calls = 0
            self.pdf_kwargs = None

        def set_content(self, html_text, wait_until):
            self.html_text = html_text
            self.wait_until = wait_until

        def evaluate(self, expression):
            self.evaluate_calls += 1
            if self.evaluate_calls == 2:
                raise RuntimeError("boom")
            return None

        def emulate_media(self, media):
            self.media = media

        def pdf(self, **kwargs):
            self.pdf_kwargs = kwargs

    page = FakePage()
    options = PdfOptions(input_path=tmp_path / "in.md", output_path=tmp_path / "out.pdf")
    with pytest.warns(RuntimeWarning, match="MathJax rendering failed"):
        _render_pdf(page, "<html></html>", options, tmp_path / "out.pdf", display_footer=False, title="T")
    assert page.pdf_kwargs["format"] == "A4"
