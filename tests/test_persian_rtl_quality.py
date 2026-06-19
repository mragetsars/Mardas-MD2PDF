from pathlib import Path

from mardas_md2pdf.markdown import render_markdown
from mardas_md2pdf.renderer import PdfOptions, _layout_css


def test_persian_blocks_get_explicit_rtl_direction_classes():
    result = render_markdown('---\nlang: fa\n---\n\nاین یک پاراگراف فارسی برای بررسی جهت متن است.\n')

    assert 'dir="rtl"' in result.body_html
    assert 'md2pdf-rtl-text' in result.body_html


def test_mixed_persian_latin_text_gets_bidi_and_numeric_classes():
    result = render_markdown(
        "---\nlang: fa\n---\n\n"
        "در خروجی PDF مقدار version 1.8.9 و شماره ۱۲۳ باید خوانا بماند.\n"
    )

    assert 'dir="auto"' in result.body_html
    assert 'mixed-script' in result.body_html
    assert 'mixed-numeral' in result.body_html


def test_rtl_tables_get_direction_and_cell_profiles():
    result = render_markdown(
        "---\nlang: fa\n---\n\n"
        "| ستون | مقدار | شناسه |\n"
        "|---|---|---|\n"
        "| نسخه | version 1.8.9 و ۱.۸.۹ | PDF |\n"
        "| وضعیت | پایدار | stable |\n"
    )

    assert 'table-wrap--rtl' in result.body_html
    assert 'table-wrap--mixed-direction' in result.body_html
    assert 'table-wrap--mixed-numerals' in result.body_html
    assert 'table-cell--rtl' in result.body_html
    assert 'table-cell--ltr' in result.body_html
    assert 'table-cell--mixed' in result.body_html


def test_layout_css_contains_persian_rtl_quality_rules(tmp_path: Path):
    options = PdfOptions(input_path=tmp_path / "input.md", output_path=tmp_path / "out.pdf")
    css, _classes = _layout_css(options, document_direction="rtl")

    assert ".md2pdf-rtl-text" in css
    assert ".mixed-script" in css
    assert ".mixed-numeral" in css
    assert ".table-wrap--rtl table" in css
    assert ".table-cell--mixed" in css
    assert "unicode-bidi: plaintext" in css
