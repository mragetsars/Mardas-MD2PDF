#!/usr/bin/env python3
"""Compare two PNG visual QA snapshots with configurable thresholds."""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from visual_qa import compare_pngs, relative_to, write_json


def _collect_pngs(root: Path) -> dict[str, Path]:
    return {path.relative_to(root).as_posix(): path for path in sorted(root.rglob("*.png"))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="Directory containing baseline PNG files")
    parser.add_argument("candidate", type=Path, help="Directory containing candidate PNG files")
    parser.add_argument("--output-dir", type=Path, default=Path("build/visual-qa/diff"))
    parser.add_argument("--max-changed-ratio", type=float, default=0.015)
    parser.add_argument("--max-rms-delta", type=float, default=4.0)
    parser.add_argument("--fail-on-missing", action="store_true")
    args = parser.parse_args(argv)

    if not args.baseline.is_dir():
        raise SystemExit(f"baseline directory not found: {args.baseline}")
    if not args.candidate.is_dir():
        raise SystemExit(f"candidate directory not found: {args.candidate}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    baseline = _collect_pngs(args.baseline)
    candidate = _collect_pngs(args.candidate)
    shared_names = sorted(set(baseline) & set(candidate))
    missing = sorted(set(baseline) - set(candidate))
    added = sorted(set(candidate) - set(baseline))

    failures: list[str] = []
    comparisons: list[dict[str, object]] = []
    for name in shared_names:
        diff = compare_pngs(baseline[name], candidate[name])
        record = dataclasses.asdict(diff)
        record["name"] = name
        record["baseline"] = relative_to(baseline[name], args.baseline)
        record["candidate"] = relative_to(candidate[name], args.candidate)
        record["passed"] = (
            diff.changed_ratio <= args.max_changed_ratio and diff.rms_delta <= args.max_rms_delta
        )
        comparisons.append(record)
        if not record["passed"]:
            failures.append(
                f"{name}: changed_ratio={diff.changed_ratio} rms_delta={diff.rms_delta} max_delta={diff.max_delta}"
            )

    if args.fail_on_missing:
        failures.extend(f"missing: {name}" for name in missing)
        failures.extend(f"added: {name}" for name in added)

    summary = {
        "baseline": str(args.baseline),
        "candidate": str(args.candidate),
        "thresholds": {
            "max_changed_ratio": args.max_changed_ratio,
            "max_rms_delta": args.max_rms_delta,
            "fail_on_missing": args.fail_on_missing,
        },
        "counts": {
            "baseline": len(baseline),
            "candidate": len(candidate),
            "shared": len(shared_names),
            "missing": len(missing),
            "added": len(added),
            "failed": len(failures),
        },
        "missing": missing,
        "added": added,
        "comparisons": comparisons,
        "failures": failures,
    }
    write_json(args.output_dir / "summary.json", summary)
    lines = [
        "# Visual Snapshot Comparison",
        "",
        f"Baseline: `{args.baseline}`",
        f"Candidate: `{args.candidate}`",
        "",
        "## Counts",
        "",
        f"- Shared PNGs: {len(shared_names)}",
        f"- Missing PNGs: {len(missing)}",
        f"- Added PNGs: {len(added)}",
        f"- Failed comparisons: {len(failures)}",
        "",
        "## Thresholds",
        "",
        f"- Maximum changed ratio: {args.max_changed_ratio}",
        f"- Maximum RMS delta: {args.max_rms_delta}",
    ]
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in failures)
    (args.output_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
