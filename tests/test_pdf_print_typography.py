from pathlib import Path

from pypdf import PdfWriter

from mardas_md2pdf.markdown import render_markdown, render_markdown_file
from mardas_md2pdf.renderer import (
    FooterContext,
    PdfOptions,
    _add_pdf_page_labels,
    _footer_context,
    _footer_template,
    _layout_css,
    build_html,
)


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


def test_image_caption_pair_becomes_semantic_figure_caption():
    result = render_markdown('![Architecture](diagram.png)\n\n*Figure 1. Architecture overview.*\n')

    assert 'class="md2pdf-figure"' in result.body_html
    assert 'md2pdf-caption--figure' in result.body_html
    assert 'Figure 1. Architecture overview.' in result.body_html


def test_table_caption_pair_becomes_semantic_table_caption():
    result = render_markdown(
        '| Component | Role |\n'
        '|---|---|\n'
        '| Renderer | PDF output |\n\n'
        'Table 1. Rendering pipeline components.\n'
    )

    assert '<caption class="md2pdf-caption md2pdf-caption--table" dir="auto">' in result.body_html
    assert 'Table 1. Rendering pipeline components.' in result.body_html
    assert 'class="table-wrap"' in result.body_html


def test_code_and_mermaid_captions_get_semantic_caption_classes():
    result = render_markdown(
        '```python title="renderer.py"\nprint("hi")\n```\n\n'
        '```mermaid title="Pipeline"\nflowchart LR\n  A --> B\n```\n'
    )

    assert 'md2pdf-caption--code' in result.body_html
    assert 'md2pdf-caption--diagram' in result.body_html
    assert 'renderer.py' in result.body_html
    assert 'Pipeline' in result.body_html


def test_layout_css_contains_semantic_caption_rules(tmp_path: Path):
    options = PdfOptions(input_path=tmp_path / "input.md", output_path=tmp_path / "out.pdf")
    css, _classes = _layout_css(options, document_direction="ltr")

    assert ".md2pdf-caption" in css
    assert "caption-side: top" in css
    assert "md2pdf-caption--table" in css
    assert "table > caption.md2pdf-caption--table" in css



def test_guide_image_references_use_document_local_assets():
    guide_dir = Path("docs/guides")
    en = (guide_dir / "GUIDE.en.md").read_text(encoding="utf-8")
    fa = (guide_dir / "GUIDE.fa.md").read_text(encoding="utf-8")

    assert "README.png" not in en
    assert "README.png" not in fa
    assert (guide_dir / "images/architecture.svg").exists()
    assert (guide_dir / "images/logo.svg").exists()
    assert "images/architecture.svg" in en
    assert "images/logo.svg" in en
    assert "images/architecture.svg" in fa
    assert "images/logo.svg" in fa


def test_local_svg_images_embed_and_keep_semantic_captions(tmp_path: Path):
    images = tmp_path / "images"
    images.mkdir()
    (images / "architecture.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40"><text x="8" y="24">OK</text></svg>',
        encoding="utf-8",
    )
    markdown = tmp_path / "sample.md"
    markdown.write_text(
        '![Architecture](images/architecture.svg)\n\n*Figure 1. Architecture overview.*\n',
        encoding="utf-8",
    )

    result = render_markdown_file(markdown)

    assert 'src="data:image/svg+xml;base64,' in result.body_html
    assert 'md2pdf-caption--figure' in result.body_html
    assert 'Image blocked or missing' not in result.body_html

def test_footer_context_collects_running_metadata(tmp_path: Path):
    result = render_markdown(
        '---\n'
        'title: "Quarterly Report"\n'
        'course: "Research Lab"\n'
        'version: "1.8.4"\n'
        'status: "Draft"\n'
        'date: "2026-06-14"\n'
        'lang: en\n'
        '---\n\n'
        '# Body\n'
    )
    options = PdfOptions(input_path=tmp_path / "input.md", output_path=tmp_path / "out.pdf")

    context = _footer_context(result, options, "Quarterly Report")

    assert context.title == "Quarterly Report"
    assert context.lang == "en"
    assert context.document_direction == "ltr"
    assert "Research Lab" in context.metadata
    assert "1.8.4" in context.metadata
    assert "Draft" in context.metadata


def test_footer_template_is_bidi_safe_and_contains_running_metadata():
    template = _footer_template(
        FooterContext(
            title="گزارش Mardas MD2PDF",
            metadata="Mardas Lab · 1.8.4 · Stable",
            lang="fa",
            document_direction="rtl",
        ),
        "modern",
        "light",
    )

    assert "گزارش Mardas MD2PDF" in template
    assert "Mardas Lab · 1.8.4 · Stable" in template
    assert "صفحه" in template
    assert "unicode-bidi:plaintext" in template
    assert "grid-template-columns" in template


def test_pdf_page_labels_restart_after_cover_page():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)

    _add_pdf_page_labels(writer, content_start_page=1)

    labels = writer._root_object["/PageLabels"]["/Nums"]
    assert labels[0] == 0
    assert labels[1]["/P"] == "Cover "
    assert labels[2] == 1
    assert labels[3]["/St"] == 1


def test_footnote_references_use_stable_numeric_markers():
    result = render_markdown(
        'First reference[^long-note] and the same note again[^long-note].\n\n'
        '[^long-note]: A detailed note with **Markdown** content.\n'
    )

    assert 'id="fnref-long-note"' in result.body_html
    assert 'id="fnref-long-note-2"' in result.body_html
    assert 'href="#fn-long-note"' in result.body_html
    assert '>1</a></sup>' in result.body_html
    assert (
        '<section class="footnotes"><ol><li class="footnote-item" id="fn-long-note">'
        in result.body_html
    )
    assert 'class="footnote-backrefs"' in result.body_html
    assert 'href="#fnref-long-note-2"' in result.body_html


def test_unresolved_footnote_references_stay_visible_without_broken_links():
    result = render_markdown('Missing note stays readable[^missing].\n')

    assert '[^missing]' in result.body_html
    assert 'href="#fn-missing"' not in result.body_html
    assert 'class="footnotes"' not in result.body_html


def test_build_html_contains_footnote_print_polish(tmp_path: Path):
    result = render_markdown('Reference[^note].\n\n[^note]: Body.\n')
    options = PdfOptions(input_path=tmp_path / "input.md", output_path=tmp_path / "out.pdf")

    html = build_html(result, options, include_cover=False)

    assert '.footnotes' in html
    assert 'break-inside: avoid-page' in html
    assert 'grid-template-columns: max-content minmax(0, 1fr) max-content' in html
    assert '.footnote-backrefs' in html
    assert '<section class="footnotes"><ol><li class="footnote-item"' in html
