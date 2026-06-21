#!/usr/bin/env python3
"""Capture a Studio browser screenshot for visual QA artifacts."""

from __future__ import annotations

import argparse
import base64
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from visual_qa import ensure_clean_dir, write_json

URL_RE = re.compile(r"https?://[^\s]+")


def _read_server_url(process: subprocess.Popen[str], timeout: float) -> str:
    deadline = time.monotonic() + timeout
    lines: list[str] = []
    assert process.stdout is not None
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if line:
            lines.append(line.rstrip())
            match = URL_RE.search(line)
            if match:
                return match.group(0)
        if process.poll() is not None:
            break
    raise RuntimeError("Studio server did not report a URL. Output:\n" + "\n".join(lines))


def _chromium_executable() -> str | None:
    configured = os.environ.get("MARDAS_CHROMIUM_PATH")
    if configured:
        return configured
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _capture_studio(html_text: str, screenshot_path: Path, timeout_ms: int) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised by users without dev/browser deps.
        raise RuntimeError("Playwright is required for Studio visual QA") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=_chromium_executable())
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page.set_content(html_text, wait_until="domcontentloaded", timeout=timeout_ms)
            page.screenshot(path=str(screenshot_path), full_page=True)
            checks = {
                "title": page.title(),
                "export_button_visible": page.locator("#exportPdfBtn").is_visible(),
                "document_section_visible": page.locator("#titleInput").is_visible(),
                "appearance_section_visible": page.locator('[data-choice-group="style"]').count() > 0,
                "branding_section_visible": page.locator('[data-choice-group="branding"]').count() > 0,
                "settings_badge": page.locator("#appearanceName").inner_text(),
            }
        finally:
            browser.close()
    return checks


def _fetch_studio_html(url: str, timeout: float) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 - local Studio URL only.
        html_text = response.read().decode("utf-8")
    asset_url = url.rstrip("/") + "/assets/mardas-md2pdf-logo.png"
    try:
        with urllib.request.urlopen(asset_url, timeout=timeout) as response:  # noqa: S310 - local Studio URL only.
            logo_data = base64.b64encode(response.read()).decode("ascii")
        html_text = html_text.replace('/assets/mardas-md2pdf-logo.png', f'data:image/png;base64,{logo_data}')
    except Exception:
        pass
    return html_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("build/visual-qa/studio"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=30, help="Seconds to wait for the Studio server")
    parser.add_argument("--browser-timeout-ms", type=int, default=60_000)
    parser.add_argument("--clean", action="store_true", help="Delete output directory before capturing")
    args = parser.parse_args(argv)

    if args.clean:
        ensure_clean_dir(args.output_dir)
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "mardas_md2pdf.gui",
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--no-open",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        url = _read_server_url(process, timeout=args.timeout)
        screenshot_path = args.output_dir / "studio-default.png"
        html_text = _fetch_studio_html(url, timeout=args.timeout)
        checks = _capture_studio(html_text, screenshot_path, timeout_ms=args.browser_timeout_ms)
        payload = {
            "url": url,
            "screenshot": screenshot_path.name,
            "checks": checks,
        }
        write_json(args.output_dir / "manifest.json", payload)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    if checks.get("title") != "Mardas MD2PDF Studio":
        raise SystemExit("unexpected Studio page title")
    for key in ["export_button_visible", "document_section_visible", "appearance_section_visible", "branding_section_visible"]:
        if not checks.get(key):
            raise SystemExit(f"Studio visual check failed: {key}")
    print(f"Studio screenshot written to {screenshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
