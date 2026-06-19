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
        "audit_studio_visual.py",
    ],
)
def test_visual_qa_scripts_define_helpful_cli_entrypoints(script: str) -> None:
    source = (SCRIPTS / script).read_text(encoding="utf-8")

    assert "argparse.ArgumentParser" in source
    assert "--output-dir" in source
    assert 'if __name__ == "__main__"' in source


def test_appearance_matrix_filter_contract_is_bounded_without_rendering() -> None:
    from audit_appearance_matrix import RenderItem, _parse_filter

    assert _parse_filter("modern", ["modern", "github"], label="style") == ("modern",)
    assert RenderItem("modern", "blue", "light").name == "modern-blue-light"



def test_visual_snapshot_compare_script_writes_summary(tmp_path: Path) -> None:
    from compare_visual_snapshots import main as compare_main

    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    output = tmp_path / "diff"
    baseline.mkdir()
    candidate.mkdir()
    _write_rgb_png(baseline / "page.png", [[(10, 10, 10), (240, 240, 240)]])
    _write_rgb_png(candidate / "page.png", [[(10, 10, 10), (241, 241, 241)]])

    assert compare_main([
        str(baseline),
        str(candidate),
        "--output-dir",
        str(output),
        "--max-changed-ratio",
        "1",
        "--max-rms-delta",
        "2",
    ]) == 0

    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["shared"] == 1
    assert summary["counts"]["failed"] == 0
    assert (output / "SUMMARY.md").is_file()



def test_visual_qa_commands_are_process_tree_timeout_safe() -> None:
    source = (SCRIPTS / "visual_qa.py").read_text(encoding="utf-8")

    assert "start_new_session" in source or "CREATE_NEW_PROCESS_GROUP" in source
    assert "os.killpg" in source
    assert "SIGKILL" in source
    assert "timed out after" in source


def test_visual_qa_scripts_expose_reliable_batch_controls() -> None:
    appearance_help = subprocess.run(
        [sys.executable, str(SCRIPTS / "audit_appearance_matrix.py"), "--help"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        timeout=30,
    ).stdout
    feature_help = subprocess.run(
        [sys.executable, str(SCRIPTS / "audit_pdf_features.py"), "--help"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        timeout=30,
    ).stdout

    for flag in ["--resume", "--fail-fast", "--max-cases", "--raster-timeout"]:
        assert flag in appearance_help
        assert flag in feature_help
    assert "--all-appearances" in feature_help



def test_feature_audit_all_appearances_can_be_bounded_without_rendering() -> None:
    from audit_pdf_features import _parse_appearances
    from mardas_md2pdf.appearance import MODES, PALETTES_ORDER, STYLES

    appearances = _parse_appearances(None, all_appearances=True)

    assert len(appearances) == len(STYLES) * len(PALETTES_ORDER) * len(MODES)
    assert appearances[0].name == f"{STYLES[0]}-{PALETTES_ORDER[0]}-{MODES[0]}"
