from __future__ import annotations

import re
from pathlib import Path

import yaml

from mardas_md2pdf.markdown import render_markdown_file

ROOT = Path(__file__).resolve().parents[1]
GUIDES = [
    ROOT / "docs/guides/GUIDE.en.md",
    ROOT / "docs/guides/GUIDE.fa.md",
]
VERSION_RE = re.compile(r"^## (\d+)\.(\d+)\.(\d+)(?:\b|\s+-)", re.MULTILINE)


def _front_matter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with YAML front matter"
    end = text.find("\n---", 4)
    assert end != -1, f"{path} front matter must have a closing fence"
    raw = text[4:end]
    data = yaml.safe_load(raw)
    assert isinstance(data, dict), f"{path} front matter must parse as a YAML mapping"
    return data


def test_guides_start_with_valid_front_matter():
    for guide in GUIDES:
        metadata = _front_matter(guide)
        assert metadata.get("title")
        assert metadata.get("summary")
        assert metadata.get("version") == "1.9.9"
        assert metadata.get("branding", {}).get("mode") == "full"


def test_guides_do_not_duplicate_toc_navigation_note():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert en.count("Visible TOC links") == 1
    assert fa.count("لینک‌های فهرست مطالب چاپی") == 1
    assert "Visible TOC links" not in en.split("---", 2)[1]
    assert "لینک‌های فهرست مطالب چاپی" not in fa.split("---", 2)[1]


def test_changelog_is_descending_and_has_single_intro():
    changelog = (ROOT / "docs/CHANGELOG.md").read_text(encoding="utf-8")

    assert changelog.startswith("# Changelog\n\nAll notable changes")
    assert changelog.count("All notable changes to Mardas MD2PDF are tracked here.") == 1
    versions = [tuple(map(int, match.groups())) for match in VERSION_RE.finditer(changelog)]
    assert versions == sorted(versions, reverse=True)
    assert len(versions) == len(set(versions))
    assert versions[0] == (1, 9, 9)
    assert (1, 8, 6) in versions
    assert (1, 8, 5) in versions
    assert (1, 5, 0) in versions
    assert (1, 4, 0) in versions
    assert (1, 3, 0) in versions
    assert (1, 2, 0) in versions
    assert (1, 1, 0) in versions
    assert (1, 0, 0) in versions
    assert "## 0.x - 2026-05-26" in changelog
    assert "docs/ROADMAP.md" not in changelog


def test_documentation_map_exists_and_mentions_guides():
    docs = (ROOT / "docs/DOCUMENTATION.md").read_text(encoding="utf-8")

    assert "Documentation map" in docs
    assert "docs/guides/GUIDE.en.md" in docs
    assert "docs/guides/GUIDE.fa.md" in docs
    assert "Changelog policy" in docs
    assert "Historical changelog reconstruction" in docs
    assert "docs/PERSIAN-RTL.md" in docs
    assert "Guide coverage policy" in docs
    assert "live rendering samples" in docs
    assert "docs/ROADMAP.md" not in docs


def test_persian_rtl_reference_document_exists():
    docs = (ROOT / "docs/PERSIAN-RTL.md").read_text(encoding="utf-8")

    assert "Persian and RTL Quality" in docs
    assert "mixed-script" in docs
    assert "mixed-numeral" in docs
    assert "table-wrap--rtl" in docs
    assert "persian-numeral" in docs
    assert "rtl-ascii-punctuation" in docs
    assert "md2pdf-caption--persian" in docs
    assert "Persian navigation and references" in docs
    assert "persian-generated-number" in docs
    assert "footnotes--rtl" in docs
    assert "toc-list--nested" in docs
    assert "border-inline-start" in docs


def test_guides_include_persian_rtl_live_smoke_samples():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert "Persian/RTL visual smoke sample" in en
    assert "نمونه smoke تصویری فارسی/RTL" in fa
    assert "version 1.9.9" in en
    assert "version 1.9.9" in fa
    assert "۱۴۰۵" in en
    assert "۱۴۰۵" in fa
    assert "جدول ۱۲. نمونه جدول فارسی/RTL با عددهای ترکیبی." in en
    assert "جدول ۱۲. نمونه جدول فارسی/RTL با عددهای ترکیبی." in fa
    assert en.count("[^pipeline]") >= 2
    assert fa.count("[^pipeline]") >= 2


def test_guides_render_persian_rtl_samples_as_semantic_audit_html():
    for guide in GUIDES:
        result = render_markdown_file(guide, toc=True)
        html = result.body_html + result.toc_html
        assert "table-wrap--persian-caption" in html
        assert "table-wrap--mixed-number" in html
        assert "md2pdf-caption--persian" in html
        assert "footnote-backrefs" in html
        if guide.name.endswith("fa.md"):
            assert "toc-item--mixed" in html or "toc-item--persian" in html
        else:
            assert "md2pdf-rtl-text" in html or "mixed-script" in html


def test_persian_rtl_reference_mentions_guide_live_sample_policy():
    docs = (ROOT / "docs/PERSIAN-RTL.md").read_text(encoding="utf-8")

    assert "Guide live-sample coverage" in docs
    assert "user manuals" in docs
    assert "live smoke samples" in docs
    assert "docs/guides/GUIDE.en.md" in docs
    assert "docs/guides/GUIDE.fa.md" in docs
