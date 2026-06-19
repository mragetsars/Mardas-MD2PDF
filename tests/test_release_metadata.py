from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_project_version_metadata_matches() -> None:
    project = tomllib.loads(_read("pyproject.toml"))["project"]
    version = project["version"]

    assert f'__version__ = "{version}"' in _read("src/mardas_md2pdf/__init__.py")
    assert f"Version-v{version}-success" in _read("README.md")
    assert f'version: "{version}"' in _read("docs/guides/GUIDE.en.md")
    assert f'version: "{version}"' in _read("docs/guides/GUIDE.fa.md")
    assert re.search(rf"^## {re.escape(version)} - \d{{4}}-\d{{2}}-\d{{2}}", _read("docs/CHANGELOG.md"), re.MULTILINE)


def test_maintenance_scripts_are_executable() -> None:
    for relative_path in [
        "scripts/install_playwright.sh",
        "scripts/check.sh",
        "scripts/build_examples.sh",
        "scripts/build_dist.sh",
        "scripts/clean_workspace.sh",
    ]:
        path = ROOT / relative_path
        assert path.is_file()
        assert os.access(path, os.X_OK)


def test_release_docs_reference_maintenance_scripts() -> None:
    release_doc = _read("docs/RELEASE.md")
    maintenance_doc = _read("docs/MAINTENANCE.md")
    readme = _read("README.md")

    for command in [
        "./scripts/check.sh",
        "./scripts/build_examples.sh",
        "./scripts/build_dist.sh",
        "./scripts/clean_workspace.sh",
    ]:
        assert command in release_doc
        assert command in maintenance_doc

    assert "docs/MAINTENANCE.md" in readme
    assert "Release Artifacts" in release_doc



def test_example_builds_set_deterministic_pdf_dates() -> None:
    script = ROOT.joinpath("scripts", "build_examples.sh").read_text(encoding="utf-8")

    assert "SOURCE_DATE_EPOCH" in script
    assert "1735689600" in script


def test_build_dist_supports_no_isolation_mode() -> None:
    script = ROOT.joinpath("scripts", "build_dist.sh").read_text(encoding="utf-8")

    assert "MARDAS_BUILD_NO_ISOLATION" in script
    assert "python -m build --no-isolation" in script
