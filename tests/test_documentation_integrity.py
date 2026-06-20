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
        assert metadata.get("version") == "1.13.9"
        assert metadata.get("branding", {}).get("mode") == "full"


def test_guides_share_mardas_appearance_contract():
    expected = {"style": "modern", "palette": "emerald", "mode": "light"}

    for guide in GUIDES:
        metadata = _front_matter(guide)
        assert metadata.get("appearance") == expected
        assert metadata.get("brand") is None

    assert not (ROOT / "docs/guides/images/brand-mark.svg").exists()




def test_project_logo_assets_are_packaged_and_documented():
    mark = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-mark.svg"
    mark_white = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-mark-white.svg"
    app_icon = ROOT / "src/mardas_md2pdf/assets/mardas-md2pdf-app-icon.svg"
    guide_logo = ROOT / "docs/guides/images/logo.svg"
    branding_docs = (ROOT / "docs/BRANDING.md").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for asset in (mark, mark_white, app_icon, guide_logo):
        assert asset.exists(), f"missing logo asset: {asset}"
        text = asset.read_text(encoding="utf-8")
        assert text.startswith("<svg")
        if asset != mark_white:
            assert "#088981" in text
            assert "#123563" in text

    mark_white_text = mark_white.read_text(encoding="utf-8")
    assert "mask" in mark_white_text
    assert "#FFFFFF" in mark_white_text
    assert guide_logo.read_text(encoding="utf-8") == mark.read_text(encoding="utf-8")
    architecture = (ROOT / "docs/guides/images/architecture.svg").read_text(encoding="utf-8")
    assert "architecture-project-mark" in architecture
    assert "M18 52V22" not in architecture
    assert "#088981" in architecture
    assert "#123563" in architecture
    assert '"assets/*.svg"' in pyproject
    assert "mardas-md2pdf-mark.svg" in branding_docs
    assert "mardas-md2pdf-mark-white.svg" in branding_docs
    assert "mardas-md2pdf-app-icon.svg" in branding_docs
    assert "should use `brand.logo` only for their own organization or lab logo" in branding_docs


def test_guides_reuse_architecture_banner_for_safe_html_examples():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert '<img src="images/architecture.svg" width="760" alt="Architecture diagram rendered from safe HTML with explicit width">' in en
    assert '<img src="images/architecture.svg" width="760" alt="نمودار معماری با اندازه مشخص در HTML امن">' in fa
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
    assert versions[0] == (1, 13, 9)
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


def test_docs_readme_lists_persian_rtl_reference():
    docs = (ROOT / "docs/README.md").read_text(encoding="utf-8")

    assert "[Persian and RTL quality](./PERSIAN-RTL.md)" in docs
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
    assert "Persian/RTL release contract" in docs
    assert "author text remains unchanged" in docs
    assert "MARDAS_RENDER_SMOKE=1 bash scripts/check.sh" in docs


def test_guides_include_persian_rtl_live_smoke_samples():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert "Persian/RTL visual smoke sample" in en
    assert "نمونه smoke تصویری فارسی/RTL" in fa
    assert "version 1.13.9" in en
    assert "version 1.13.9" in fa
    assert "۱۴۰۵" in en
    assert "۱۴۰۵" in fa
    assert "جدول ۱۲. نمونه جدول فارسی/RTL با عددهای ترکیبی." in en
    assert "جدول ۱۲. نمونه جدول فارسی/RTL با عددهای ترکیبی." in fa
    assert en.count("[^pipeline]") >= 2
    assert fa.count("[^pipeline]") >= 2




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


def test_persian_rtl_reference_mentions_guide_live_sample_policy():
    docs = (ROOT / "docs/PERSIAN-RTL.md").read_text(encoding="utf-8")

    assert "Guide live-sample coverage" in docs
    assert "user manuals" in docs
    assert "live smoke samples" in docs
    assert "docs/guides/GUIDE.en.md" in docs
    assert "docs/guides/GUIDE.fa.md" in docs


def test_persian_rtl_reference_closeout_contract_stays_release_facing():
    docs = (ROOT / "docs/PERSIAN-RTL.md").read_text(encoding="utf-8")

    assert "The 1.10.x baseline closes the focused Persian/RTL quality pass" in docs
    assert "heading IDs, footnote anchors, PDF destinations, and back-links remain deterministic" in docs
    assert "official guide samples stay compact and readable" in docs
    assert "Phase 13" not in docs
    assert "docs/ROADMAP.md" not in docs


def test_visual_qa_reference_document_exists_and_stays_artifact_based():
    docs = (ROOT / "docs/VISUAL-QA.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Visual QA System" in docs
    assert "scripts/audit_appearance_matrix.py" in docs
    assert "scripts/audit_pdf_features.py" in docs
    assert "scripts/compare_visual_snapshots.py" in docs
    assert "scripts/audit_studio_visual.py" in docs
    assert "scripts/run_visual_qa_matrix.py" in docs
    assert "scripts/check_pdf_preflight.py" in docs
    assert "build/visual-qa/" in docs
    assert "must not be committed" in docs
    assert "[Visual QA system](./VISUAL-QA.md)" in docs_index
    assert "[Visual QA system](./docs/VISUAL-QA.md)" in readme
    assert "docs/ROADMAP.md" not in docs


def test_ci_uploads_visual_qa_artifacts():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Visual QA artifacts" in workflow
    assert "scripts/audit_appearance_matrix.py" in workflow
    assert "scripts/audit_pdf_features.py" in workflow
    assert "scripts/audit_studio_visual.py" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "build/visual-qa/" in workflow


def test_studio_reference_documents_professional_workflow_features():
    docs = (ROOT / "docs/STUDIO.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert ".mardas.json" in docs
    assert "Project files" in docs
    assert "Save Project" in docs
    assert "Open Project" in docs
    assert "command palette" in docs
    assert "Ctrl/Cmd+K" in docs
    assert "Accurate" in docs
    assert "Export debug HTML" in docs
    assert "drag-and-drop asset" in readme or "drag-and-drop asset management" in readme


def test_guides_document_pdf_preflight_smoke_checks():
    en = (ROOT / "docs/guides/GUIDE.en.md").read_text(encoding="utf-8")
    fa = (ROOT / "docs/guides/GUIDE.fa.md").read_text(encoding="utf-8")

    assert "PDF Preflight Checks" in en
    assert "بررسی Preflight فایل PDF" in fa
    assert "scripts/check_pdf_preflight.py" in en
    assert "scripts/check_pdf_preflight.py" in fa
    assert "build/pdf-preflight.json" in en
    assert "build/pdf-preflight.json" in fa
