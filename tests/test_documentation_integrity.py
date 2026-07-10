from __future__ import annotations

import re
import struct
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
        assert metadata.get("version") == "1.13.40"
        assert metadata.get("branding", {}).get("mode") == "full"


def test_guides_share_mardas_appearance_contract():
    expected = {"style": "modern", "palette": "emerald", "mode": "light"}

    for guide in GUIDES:
        metadata = _front_matter(guide)
        assert metadata.get("appearance") == expected
        assert metadata.get("brand") is None

    assert not (ROOT / "docs/guides/images/brand-mark.svg").exists()




def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", data[16:24])


def test_project_logo_assets_are_packaged_and_documented():
    logo = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-logo.png"
    logo_white = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-logo-white.png"
    mark = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-mark.svg"
    mark_white = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-mark-white.svg"
    app_icon = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-app-icon.svg"
    gui_mark_mask = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-mark-gui-mask.svg"
    guide_logo_png = ROOT / "docs/guides/images/logo.png"
    readme_png = ROOT / "README.png"
    documentation_docs = (ROOT / "docs/DOCUMENTATION.md").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for asset in (logo, logo_white, guide_logo_png):
        assert asset.exists(), f"missing canonical logo asset: {asset}"
        assert _png_dimensions(asset) == (768, 768)

    assert readme_png.exists()
    assert _png_dimensions(readme_png) == (1916, 821)

    for asset in (mark, mark_white, app_icon, gui_mark_mask):
        assert asset.exists(), f"missing logo asset: {asset}"
        svg_text = asset.read_text(encoding="utf-8")
        assert svg_text.startswith("<svg")
        if asset in (mark, app_icon):
            assert "#088A83" in svg_text
            assert "#123664" in svg_text
        if asset == gui_mark_mask:
            assert "mask" in svg_text
            assert "#000000" in svg_text

    mark_white_text = mark_white.read_text(encoding="utf-8")
    assert "mask" in mark_white_text
    assert "#FFFFFF" in mark_white_text
    assert not (ROOT / "docs/guides/images/logo.svg").exists()
    architecture = ROOT / "docs/guides/images/architecture.png"
    assert architecture.exists()
    assert _png_dimensions(architecture) == (1200, 600)
    assert architecture.stat().st_size < 450_000
    assert not (ROOT / "docs/guides/images/architecture.svg").exists()
    assert not (ROOT / "src/mardas_md2pdf/assets" / ("Mardas" + ".png")).exists()
    assert '"assets/*.png"' in pyproject
    assert '"assets/*.svg"' in pyproject
    assert "mardas-md2pdf-logo.png" in documentation_docs
    assert "mardas-md2pdf-logo-white.png" in documentation_docs
    assert "mardas-md2pdf-mark.svg" in documentation_docs
    assert "mardas-md2pdf-mark-white.svg" in documentation_docs
    assert "mardas-md2pdf-app-icon.svg" in documentation_docs
    assert "mardas-md2pdf-mark-gui-mask.svg" in documentation_docs
    assert "should use `brand.logo` only for their own organization or lab logo" in documentation_docs
    assert "Asset layout policy" in documentation_docs
    assert "`src/mardas_md2pdf/assets/`" in documentation_docs
    assert "`docs/guides/images/`" in documentation_docs
    assert "`README.png`" in documentation_docs


def test_guides_reuse_architecture_banner_for_safe_html_examples():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert '<img src="images/architecture.png" width="760" alt="Architecture diagram rendered from safe HTML with explicit width">' in en
    assert '<img src="images/architecture.png" width="760" alt="نمودار معماری با اندازه مشخص در HTML امن">' in fa
    assert '<img src="images/logo.svg"' not in en
    assert '<img src="images/logo.svg"' not in fa


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
    assert versions[0] == (1, 13, 40)
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
    assert "Retired feature-reference pages" in docs
    assert "Guide coverage policy" in docs
    assert "live rendering samples" in docs
    assert "docs/ROADMAP.md" not in docs


def test_docs_readme_is_lean_and_guide_first():
    docs = (ROOT / "docs/README.md").read_text(encoding="utf-8")

    assert "guide-first documentation model" in docs
    assert "Feature documentation is intentionally" in docs
    assert "./guides/GUIDE.en.md" in docs
    assert "./guides/GUIDE.fa.md" in docs
    assert "./RELEASE.md" in docs
    assert "./MAINTENANCE.md" in docs
    assert "./SECURITY.md" in docs
    assert "docs/ROADMAP.md" not in docs


def test_advanced_code_samples_keep_highlight_ranges_visible():
    files = [
        ROOT / "docs/guides/GUIDE.en.md",
        ROOT / "docs/guides/GUIDE.fa.md",
        ROOT / "src/mardas_md2pdf/assets/gui.html",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert '```python title="renderer.py" {2,5-6} linenos' in text
        assert "metadata = inspect_pdf(pdf)" in text
        assert "log_export(metadata)" in text
        assert "return pdf" in text




def test_obsolete_feature_reference_docs_are_removed():
    removed_docs = [
        "APPEARANCE.md",
        "BRANDING.md",
        "MARKDOWN-FIDELITY.md",
        "PDF-NAVIGATION.md",
        "PDF-TYPOGRAPHY.md",
        "PERSIAN-RTL.md",
        "STUDIO.md",
        "VISUAL-QA.md",
    ]
    for filename in removed_docs:
        assert not (ROOT / "docs" / filename).exists(), filename

    docs_index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    documentation_policy = (ROOT / "docs/DOCUMENTATION.md").read_text(encoding="utf-8")
    for filename in removed_docs:
        assert f"./{filename}" not in docs_index
        assert f"docs/{filename}" not in documentation_policy
    assert "Retired feature-reference pages" in documentation_policy


def test_guides_state_that_feature_docs_were_retired():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert "complete user manual" in en
    assert "instead of maintaining parallel feature-reference pages" in en
    assert "مرجع کامل کاربر" in fa
    assert "صفحه‌های feature/reference موازی حذف شده‌اند" in fa


def test_guides_include_persian_rtl_live_smoke_samples():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert "Persian/RTL visual smoke sample" in en
    assert "نمونه smoke تصویری فارسی/RTL" in fa
    assert "version 1.13.40" in en
    assert "version 1.13.40" in fa
    assert "۱۴۰۵" in en
    assert "۱۴۰۵" in fa
    assert "جدول ۱۲. نمونه جدول فارسی/RTL با عددهای ترکیبی." in en
    assert "جدول ۱۲. نمونه جدول فارسی/RTL با عددهای ترکیبی." in fa
    assert "[^rtl-smoke]" in en
    assert "[^footnote-demo]" in en
    assert "[^rtl-smoke]" in fa
    assert "[^footnote-demo]" in fa




def test_guides_render_callouts_without_raw_alert_markers():
    for guide in GUIDES:
        result = render_markdown_file(guide, toc=True)
        html = result.body_html
        assert "[!NOTE]" not in html
        assert "[!TIP]" not in html
        assert "[!IMPORTANT]" not in html
        assert "[!WARNING]" not in html
        assert "callout-note" in html
        assert "callout-tip" in html
        assert "callout-warning" in html
        if guide.name.endswith("fa.md"):
            assert '<strong class="callout-title">نکته</strong>' in html
            assert '<strong class="callout-title">مهم</strong>' in html
        else:
            assert '<strong class="callout-title">Note</strong>' in html
            assert '<strong class="callout-title">Important</strong>' in html

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


def test_ci_uploads_visual_qa_artifacts():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Visual QA artifacts" in workflow
    assert "scripts/audit_appearance_matrix.py" in workflow
    assert "scripts/audit_pdf_features.py" in workflow
    assert "scripts/audit_studio_visual.py" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "build/visual-qa/" in workflow


def test_guides_cover_retired_feature_reference_topics():
    combined = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8") + "\n" + (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    required = [
        "Appearance",
        "Cover Branding",
        "Enhanced code fences",
        "PDF navigation",
        "Persian/RTL visual smoke sample",
        "GUI Workflow",
        "PDF Preflight Checks",
        "Mermaid Flowcharts",
    ]
    for marker in required:
        assert marker in combined


def test_readme_has_no_stale_feature_reference_links():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    combined = readme + "\n" + docs_index
    for stale in [
        "docs/APPEARANCE.md",
        "docs/BRANDING.md",
        "docs/MARKDOWN-FIDELITY.md",
        "docs/PDF-NAVIGATION.md",
        "docs/PDF-TYPOGRAPHY.md",
        "docs/PERSIAN-RTL.md",
        "docs/STUDIO.md",
        "docs/VISUAL-QA.md",
    ]:
        assert stale not in combined


def test_guides_document_pdf_preflight_smoke_checks():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert "PDF Preflight Checks" in en
    assert "بررسی Preflight فایل PDF" in fa
    assert "scripts/check_pdf_preflight.py" in en
    assert "scripts/check_pdf_preflight.py" in fa
    assert "build/pdf-preflight.json" in en
    assert "build/pdf-preflight.json" in fa
