from mardas_md2pdf.markdown import render_markdown


def test_mixed_direction_and_code_highlight():
    result = render_markdown("# سلام English\n\nمتن mixed با `code`.\n\n```python\nprint('hi')\n```")
    assert "dir=\"auto\"" in result.body_html
    assert "code-block" in result.body_html
    assert "PYTHON" in result.body_html


def test_fenced_code_language_caption_is_not_merged_into_code():
    result = render_markdown("```c\nint setSeed(void);\n```\n")
    assert '<figure class="code-block"' in result.body_html
    assert '>C</figcaption>' in result.body_html
    assert 'Cint setSeed' not in result.body_html
    assert '<pre><code class="language-c"><figure' not in result.body_html


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


def test_local_markdown_images_are_embedded_as_data_uris(tmp_path):
    from mardas_md2pdf.markdown import render_markdown_file

    png = tmp_path / "chart.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xe2\x08\x9b\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    md = tmp_path / "report.md"
    md.write_text("![Chart](chart.png)\n", encoding="utf-8")

    result = render_markdown_file(md)

    assert 'src="data:image/png;base64,' in result.body_html
    assert 'data-md2pdf-source="chart.png"' in result.body_html


def test_local_image_lookup_falls_back_to_markdown_directory_basename(tmp_path):
    from mardas_md2pdf.markdown import render_markdown_file

    png = tmp_path / "executive_overview.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xe2\x08\x9b\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    md = tmp_path / "report.md"
    md.write_text('<img src="./images/executive_overview.png" alt="Overview">\n', encoding="utf-8")

    result = render_markdown_file(md)

    assert 'src="data:image/png;base64,' in result.body_html
    assert 'data-md2pdf-source="./images/executive_overview.png"' in result.body_html


def test_cover_supports_multiline_summary_and_multiple_authors(tmp_path):
    from mardas_md2pdf.renderer import PdfOptions, build_html

    md = """---
title: "گزارش نمونه"
subtitle: "نمونه metadata پیشرفته"
authors:
  - name: "Meraj Rastegar"
    email: "mragetsars@gmail.com"
  - "Mardas Team"
summary: |
  خط اول خلاصه برای جلد PDF.
  خط دوم خلاصه باید در همان پاراگراف با شکست خط بماند.

  این پاراگراف دوم خلاصه است.
cover_label: "گزارش آزمایشی"
institution: "Tehran University"
course: "Data Science"
keywords:
  - RTL
  - PDF
lang: fa
---

# بدنه
"""
    result = render_markdown(md)
    input_path = tmp_path / "sample.md"
    input_path.write_text(md, encoding="utf-8")

    html = build_html(result, PdfOptions(input_path=input_path, output_path=tmp_path / "sample.pdf"))

    assert "نویسندگان" in html
    assert "Meraj Rastegar (mragetsars@gmail.com)" in html
    assert "Mardas Team" in html
    assert "خط اول خلاصه برای جلد PDF.<br>خط دوم خلاصه" in html
    assert "این پاراگراف دوم خلاصه است." in html
    assert "Tehran University" in html
    assert "Data Science" in html
    assert "RTL" in html
    assert "PDF" in html
    assert "گزارش آزمایشی" in html
    assert "گزارش PDF" not in html
    assert '<section class="md2pdf-cover__top" dir="ltr">' in html


def test_inline_math_keeps_mathjax_delimiters_after_markdown_parsing():
    result = render_markdown("متن فارسی با $T=500$ و $\\epsilon=0.05$ وسط جمله.")
    assert '<span class="math inline">\\(T=500\\)</span>' in result.body_html
    assert '<span class="math inline">\\(\\epsilon=0.05\\)</span>' in result.body_html
    assert '<span class="math inline">(T=500)</span>' not in result.body_html
    assert '<span class="math inline">(\\epsilon=0.05)</span>' not in result.body_html


def test_toc_preserves_inline_math_for_mathjax_rendering():
    result = render_markdown("## استنتاج\n\n### اثر $T$ و $\\epsilon$ روی دقت\n", toc=True)
    assert '<span class="toc-title">اثر <span class="math inline">\\(T\\)</span> و <span class="math inline">\\(\\epsilon\\)</span> روی دقت</span>' in result.toc_html
    assert '(\\epsilon)' not in result.toc_html


def test_multiline_footnotes_render_as_markdown_blocks():
    result = render_markdown(
        "متن دارای ارجاع[^n].\n\n"
        "[^n]: خط اول پانویس.\n"
        "    خط دوم همان پانویس با **تاکید**.\n\n"
        "    - مورد اول\n"
        "    - مورد دوم\n"
    )
    assert 'class="footnote-body"' in result.body_html
    assert "خط دوم همان پانویس" in result.body_html
    assert "<strong>تاکید</strong>" in result.body_html
    assert '<li dir="auto">مورد اول</li>' in result.body_html
    assert '<section class="footnotes"><ol><li class="footnote-item" id="fn-n"><span class="footnote-marker"' in result.body_html


def test_raw_html_is_sanitized_by_default():
    result = render_markdown('<img src="chart.png" onerror="alert(1)"><script>alert(1)</script>')
    assert "<script" not in result.body_html
    assert "onerror" not in result.body_html
    assert '<img src="chart.png"' in result.body_html


def test_renderer_page_size_and_direction_are_late_css_overrides(tmp_path):
    from mardas_md2pdf.renderer import PdfOptions, build_html

    md = """---
title: English report
lang: en
dir: ltr
---

# English report

Only English text.
"""
    result = render_markdown(md)
    input_path = tmp_path / "english.md"
    input_path.write_text(md, encoding="utf-8")
    html = build_html(
        result,
        PdfOptions(input_path=input_path, output_path=tmp_path / "english.pdf", page_size="Letter"),
    )
    assert "size: Letter;" in html
    assert '<html lang="en" dir="ltr">' in html
    assert "md2pdf-dir-ltr" in html


def test_lang_en_localizes_toc_callouts_and_cover_direction(tmp_path):
    from mardas_md2pdf.renderer import PdfOptions, build_html

    md = """---
title: English report
lang: en
---

# English report

> [!NOTE]
> This is a localized callout.

## Analysis
"""
    result = render_markdown(md, toc=True)
    input_path = tmp_path / "english.md"
    input_path.write_text(md, encoding="utf-8")
    html = build_html(result, PdfOptions(input_path=input_path, output_path=tmp_path / "english.pdf"))

    assert "Table of Contents" in result.toc_html
    assert "فهرست مطالب" not in result.toc_html
    assert "Note" in result.body_html
    assert '<html lang="en" dir="ltr">' in html
    assert 'class="md2pdf-cover" lang="en" dir="ltr"' in html
    assert "Generated Document" in html
    assert "PDF Report" not in html
    assert '<section class="md2pdf-cover__top" dir="ltr">' in html


def test_lang_en_drives_ltr_shell_even_when_body_contains_persian(tmp_path):
    from mardas_md2pdf.renderer import PdfOptions, build_html

    md = """---
title: Mixed language notes
lang: en
dir: auto
---

# English title

این پاراگراف فارسی است اما پوسته سند باید با lang انگلیسی LTR شود.
"""
    result = render_markdown(md, toc=True)
    input_path = tmp_path / "mixed.md"
    input_path.write_text(md, encoding="utf-8")
    html = build_html(result, PdfOptions(input_path=input_path, output_path=tmp_path / "mixed.pdf"))

    assert '<html lang="en" dir="ltr">' in html
    assert "Table of Contents" in result.toc_html


def test_math_scaling_rules_distinguish_inline_and_display_math(tmp_path):
    from mardas_md2pdf.renderer import PdfOptions, build_html

    md = "متن با $E=mc^2$ و سپس:\n\n$$\nE=mc^2\n$$\n"
    result = render_markdown(md)
    input_path = tmp_path / "math.md"
    input_path.write_text(md, encoding="utf-8")
    html = build_html(result, PdfOptions(input_path=input_path, output_path=tmp_path / "math.pdf"))

    assert "--md2pdf-inline-math-scale: 100%;" in html
    assert "--md2pdf-display-math-scale: 130%;" in html
    assert "mjx-container:not([display=\"true\"])" in html
    assert "mjx-container[display=\"true\"]" in html


def test_cover_label_aliases_and_ltr_cover_alignment(tmp_path):
    from mardas_md2pdf.renderer import PdfOptions, build_html

    md = """---
title: English report
subtitle: Left aligned subtitle
summary: |
  The summary should start on the left side of the English cover.
cover_label: Custom Cover Label
lang: en
---

# Body
"""
    result = render_markdown(md)
    input_path = tmp_path / "english.md"
    input_path.write_text(md, encoding="utf-8")
    html = build_html(result, PdfOptions(input_path=input_path, output_path=tmp_path / "english.pdf"))

    assert "Custom Cover Label" in html
    assert "Generated Document" not in html
    assert "body.md2pdf-dir-ltr .md2pdf-cover__content" in html
    assert "margin-left: 0;" in html
    assert "body.md2pdf-dir-ltr .md2pdf-cover__summary { margin: 5mm auto 0 0; }" in html
    assert "body.md2pdf-dir-rtl .md2pdf-cover__detail > span" in html
    assert "font-family: var(--font-fa), var(--font-en);" in html
