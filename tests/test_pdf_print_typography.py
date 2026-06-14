from pathlib import Path

from mardas_md2pdf.markdown import render_markdown
from mardas_md2pdf.renderer import PdfOptions, _layout_css, build_html


def test_long_code_blocks_get_print_flow_hints():
    code = "\n".join(f"print({i})" for i in range(40))
    result = render_markdown(f'```python title="long.py" linenos\n{code}\n```\n')

    assert 'data-lines="40"' in result.body_html
    assert 'code-block--long' in result.body_html
    assert 'code-block--very-long' not in result.body_html


def test_long_tables_get_print_flow_hints():
    rows = ["| A | B |", "|---|---|"]
    rows.extend(f"| {i} | value {i} |" for i in range(20))
    result = render_markdown("\n".join(rows))

    assert 'table-wrap--long' in result.body_html
    assert 'data-md2pdf-rows="21"' in result.body_html
    assert 'data-md2pdf-columns="2"' in result.body_html


def test_layout_css_contains_print_typography_rules(tmp_path: Path):
    options = PdfOptions(input_path=tmp_path / "input.md", output_path=tmp_path / "out.pdf")
    css, _classes = _layout_css(options, document_direction="ltr")

    assert "orphans: 3" in css
    assert "widows: 3" in css
    assert "h1, h2, h3, h4, h5, h6" in css
    assert "break-after: avoid-page" in css
    assert ".code-block--long, .code-block--very-long" in css
    assert ".table-wrap--long, .table-wrap--wide, .table-wrap--very-wide" in css
    assert "thead" in css and "display: table-header-group" in css


def test_build_html_includes_print_flow_css(tmp_path: Path):
    result = render_markdown("# Heading\n\nParagraph\n")
    options = PdfOptions(input_path=tmp_path / "input.md", output_path=tmp_path / "out.pdf")

    html = build_html(result, options, include_cover=False)

    assert "@media print" in html
    assert "break-before: avoid-page" in html
    assert "code-block--long" in html
