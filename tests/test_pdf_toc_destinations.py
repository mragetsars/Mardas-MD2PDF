from pathlib import Path

from pypdf import PdfReader, PdfWriter

from mardas_md2pdf.markdown import render_markdown
from mardas_md2pdf.renderer import (
    _copy_pdf_with_metadata,
    _heading_destination_names,
)


def test_toc_links_and_headings_share_stable_ids() -> None:
    result = render_markdown(
        """# Intro\n\n## Duplicate\n\n## Duplicate\n\n# فارسی عنوان\n""",
        toc=True,
    )

    assert 'href="#intro"' in result.toc_html
    assert 'id="intro"' in result.body_html
    assert 'href="#duplicate"' in result.toc_html
    assert 'id="duplicate"' in result.body_html
    assert 'href="#duplicate-2"' in result.toc_html
    assert 'id="duplicate-2"' in result.body_html
    assert 'href="#فارسی-عنوان"' in result.toc_html
    assert 'id="فارسی-عنوان"' in result.body_html


def test_heading_destination_names_cover_chromium_encoded_ids() -> None:
    names = _heading_destination_names("فارسی-عنوان")

    assert "/فارسی-عنوان" in names
    assert "/%D9%81%D8%A7%D8%B1%D8%B3%DB%8C-%D8%B9%D9%86%D9%88%D8%A7%D9%86" in names


def test_metadata_copy_preserves_named_destinations_for_toc_links(tmp_path: Path) -> None:
    source_pdf = tmp_path / "source.pdf"
    output_pdf = tmp_path / "output.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_named_destination("/intro", 0)
    with source_pdf.open("wb") as handle:
        writer.write(handle)

    _copy_pdf_with_metadata(
        source_pdf,
        output_pdf,
        {"/Title": "TOC destination test"},
        outline_source_entries=[(1, "Intro", "intro")],
    )

    reader = PdfReader(str(output_pdf))
    assert "/intro" in reader.named_destinations
    assert reader.outline[0]["/Title"] == "Intro"
    assert reader.get_destination_page_number(reader.outline[0]) == 0
