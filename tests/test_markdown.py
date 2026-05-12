from mardas_md2pdf.markdown import render_markdown


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


def test_hierarchical_toc_numbers_and_nesting():
    markdown = "# فصل اول\n\n## بخش اول\n\n## بخش دوم\n\n### زیر بخش\n\n# فصل دوم\n"
    result = render_markdown(markdown, toc=True)
    assert "md2pdf-toc" in result.toc_html
    assert '<span class="toc-number">1</span>' in result.toc_html
    assert '<span class="toc-number">1-1</span>' in result.toc_html
    assert '<span class="toc-number">1-2</span>' in result.toc_html
    assert '<span class="toc-number">1-2-1</span>' in result.toc_html
    assert '<span class="toc-number">2</span>' in result.toc_html
    assert 'toc-depth-2' in result.toc_html


def test_public_theme_choices_are_explicit_light_or_dark():
    from mardas_md2pdf.cli import build_parser

    parser = build_parser()
    theme_action = next(action for action in parser._actions if "--theme" in action.option_strings)
    assert "textbook-light" in theme_action.choices
    assert "textbook-dark" in theme_action.choices
    assert "textbook" not in theme_action.choices


def test_hidden_unbranded_cover_option_is_not_in_help():
    from mardas_md2pdf.cli import build_parser

    parser = build_parser()
    help_text = parser.format_help()
    assert "--no-cover-brand" not in help_text
    assert any("--no-cover-brand" in action.option_strings for action in parser._actions)


def test_gui_entrypoint_module_exists():
    import mardas_md2pdf.gui as gui

    assert gui.build_parser().prog == "mrs-md2pdf-gui"
