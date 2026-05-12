from md2pdf_pro.markdown import render_markdown


def test_mixed_direction_and_code_highlight():
    result = render_markdown("# سلام English\n\nمتن mixed با `code`.\n\n```python\nprint('hi')\n```")
    assert "dir=\"auto\"" in result.body_html
    assert "code-block" in result.body_html
    assert "PYTHON" in result.body_html


def test_table_and_math():
    result = render_markdown("|a|b|\n|-|-|\n|1|2|\n\n$$\nx^2\n$$")
    assert "table-wrap" in result.body_html
    assert "math display" in result.body_html


def test_indented_code_blocks_are_wrapped_and_visible():
    result = render_markdown("برنامه تست:\n\n    #include \"user.h\"\n    int main(void) { return 0; }\n")
    assert "raw-code-block" in result.body_html
    assert "<pre" in result.body_html
    assert "C</figcaption>" in result.body_html
    assert "#include" in result.body_html
