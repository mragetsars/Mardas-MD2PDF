from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark_large_documents.py"


def _benchmark_module():
    spec = importlib.util.spec_from_file_location("benchmark_large_documents", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_large_document_benchmark_inputs_are_deterministic() -> None:
    module = _benchmark_module()
    first = module._document_text(module.PROFILES["pages50"])
    second = module._document_text(module.PROFILES["pages50"])

    assert first == second
    assert first.count('<div class="page-break"></div>') == 49
    assert "Mixed فارسی English ۱۴۰۵" in first
    assert module._selected_profiles("small,pages500") == [
        module.PROFILES["small"],
        module.PROFILES["pages500"],
    ]


def test_large_document_benchmark_help_is_executable() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0
    assert "pages500" in completed.stdout
    assert "--mode" in completed.stdout
    assert "--repeats" in completed.stdout
