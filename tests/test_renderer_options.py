from mardas_md2pdf.renderer import _css_page_size, _playwright_page_size_kwargs


def test_css_page_size_accepts_named_orientation_and_dimensions():
    assert _css_page_size("A4 landscape") == "A4 landscape"
    assert _css_page_size("210mm 297mm") == "210mm 297mm"
    assert _css_page_size("bad; value") == "A4"


def test_playwright_page_size_uses_format_only_for_named_formats():
    assert _playwright_page_size_kwargs("Letter") == {"format": "Letter"}
    assert _playwright_page_size_kwargs("210mm 297mm") == {"width": "210mm", "height": "297mm"}
    assert _playwright_page_size_kwargs("A4 landscape") == {}
