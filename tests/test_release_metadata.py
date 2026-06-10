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

    assert f'__version__ = "{version}"' in _read("src/__init__.py")
    assert f"Version-v{version}-success" in _read("README.md")
    assert f'version: "{version}"' in _read("GUIDE.en.md")
    assert f'version: "{version}"' in _read("GUIDE.fa.md")
    assert re.search(rf"^## {re.escape(version)} - \d{{4}}-\d{{2}}-\d{{2}}", _read("CHANGELOG.md"), re.MULTILINE)


def test_maintenance_scripts_are_executable() -> None:
    for relative_path in [
        "scripts/install_playwright.sh",
        "scripts/check.sh",
        "scripts/build_examples.sh",
        "scripts/build_dist.sh",
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
    ]:
        assert command in release_doc
        assert command in maintenance_doc

    assert "docs/MAINTENANCE.md" in readme
    assert "Release Artifacts" in release_doc
