from __future__ import annotations

import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from visual_qa import compare_pngs, png_stats  # noqa: E402


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def _write_rgb_png(path: Path, rows: list[list[tuple[int, int, int]]]) -> None:
    height = len(rows)
    width = len(rows[0]) if rows else 0
    raw = b"".join(b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )


def test_visual_qa_png_stats_and_diff_are_dependency_free(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.png"
    candidate = tmp_path / "candidate.png"
    _write_rgb_png(baseline, [[(0, 0, 0), (255, 255, 255)]])
    _write_rgb_png(candidate, [[(0, 0, 0), (250, 250, 250)]])

    stats = png_stats(baseline)
    diff = compare_pngs(baseline, candidate)

    assert stats.width == 2
    assert stats.height == 1
    assert stats.dark_ratio == 0.5
    assert stats.light_ratio == 0.5
    assert diff.changed_ratio > 0
    assert diff.max_delta == 5


@pytest.mark.parametrize(
    "script",
    [
        "audit_appearance_matrix.py",
        "audit_pdf_features.py",
        "compare_visual_snapshots.py",
    ],
)
def test_visual_qa_scripts_have_help(script: str) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--help"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert "--output-dir" in result.stdout


def test_appearance_matrix_supports_filtered_dry_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Smoke\n\nTiny sample.\n", encoding="utf-8")
    output_dir = tmp_path / "audit"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "audit_appearance_matrix.py"),
            "--source",
            str(source),
            "--output-dir",
            str(output_dir),
            "--styles",
            "modern",
            "--palettes",
            "blue",
            "--modes",
            "light",
            "--timeout",
            "60",
        ],
        check=True,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["matrix"]["count"] == 1
    assert manifest["failures"] == []
    assert manifest["records"][0]["name"] == "modern-blue-light"
    assert (output_dir / manifest["records"][0]["pdf"]).is_file()


def test_visual_snapshot_compare_script_writes_summary(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    output = tmp_path / "diff"
    baseline.mkdir()
    candidate.mkdir()
    _write_rgb_png(baseline / "page.png", [[(10, 10, 10), (240, 240, 240)]])
    _write_rgb_png(candidate / "page.png", [[(10, 10, 10), (241, 241, 241)]])

    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "compare_visual_snapshots.py"),
            str(baseline),
            str(candidate),
            "--output-dir",
            str(output),
            "--max-changed-ratio",
            "1",
            "--max-rms-delta",
            "2",
        ],
        check=True,
    )

    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["shared"] == 1
    assert summary["counts"]["failed"] == 0
    assert (output / "SUMMARY.md").is_file()
