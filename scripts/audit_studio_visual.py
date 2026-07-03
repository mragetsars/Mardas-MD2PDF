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


def _fetch_studio_html(url: str, timeout: float) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 - local Studio URL only.
        html_text = response.read().decode("utf-8")
    base_href = url.rstrip("/") + "/"
    html_text = html_text.replace("<head>", f'<head>\n<base href="{base_href}">', 1)
    asset_url = base_href + "assets/mardas-md2pdf-logo.png"
    try:
        with urllib.request.urlopen(asset_url, timeout=timeout) as response:  # noqa: S310 - local Studio URL only.
            logo_data = base64.b64encode(response.read()).decode("ascii")
        html_text = html_text.replace("/assets/mardas-md2pdf-logo.png", f"data:image/png;base64,{logo_data}")
    except Exception:
        pass
    return html_text


def _proxy_local_studio_api(url: str, path: str, *, body: bytes | None, content_type: str, timeout: float) -> tuple[int, bytes, str]:
    request = urllib.request.Request(
        url.rstrip("/") + path,
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - local Studio URL only.
            return response.status, response.read(), response.headers.get_content_type()
    except Exception as exc:
        return 502, str(exc).encode("utf-8", errors="replace"), "text/plain"


def _capture_studio(html_text: str, url: str, screenshot_path: Path, timeout_ms: int) -> dict[str, Any]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised by users without dev/browser deps.
        raise RuntimeError("Playwright is required for Studio visual QA") from exc

    preview_ready_script = """
        () => {
          const status = document.querySelector('#previewStatus')?.textContent || '';
          return /preview (updated|failed)/i.test(status);
        }
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=_chromium_executable())
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)

            def proxy_render_html(route: Any, request: Any) -> None:
                status, body, content_type = _proxy_local_studio_api(
                    url,
                    "/api/render-html",
                    body=request.post_data_buffer,
                    content_type=request.headers.get("content-type", "application/json"),
                    timeout=max(timeout_ms / 1000, 1),
                )
                route.fulfill(status=status, body=body, content_type=content_type)

            page.route("**/api/render-html", proxy_render_html)
            page.set_content(html_text, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_function(preview_ready_script, timeout=timeout_ms)
            except PlaywrightTimeoutError:
                pass
            preview_status = page.locator("#previewStatus").inner_text(timeout=timeout_ms)
            preview_mode = page.locator("#previewModeInput").input_value(timeout=timeout_ms)
            preview_frame_visible = page.locator("#accuratePreviewFrame").is_visible()
            page_marker_ready_script = """
                () => {
                  const frame = document.querySelector('#accuratePreviewFrame');
                  const doc = frame && frame.contentDocument;
                  return Boolean(doc && doc.querySelector('.md2pdf-preview-page-markers'));
                }
            """
            try:
                page.wait_for_function(page_marker_ready_script, timeout=timeout_ms)
            except PlaywrightTimeoutError:
                pass
            page_markers = page.evaluate(page_marker_ready_script)
            page.screenshot(path=str(screenshot_path), full_page=True)
            line_number_check = page.evaluate(
                """
                () => {
                  const editor = document.querySelector('#editor');
                  const content = document.querySelector('#lineNumberContent') || document.querySelector('#lineNumbers');
                  if (!editor || !content || typeof syncLineNumbers !== 'function') {
                    return { ok: false, visibleTail: '', renderedLineNumbers: 0 };
                  }
                  editor.value = Array.from({ length: 3005 }, (_, index) => 'line ' + (index + 1)).join('\\n');
                  editor.dispatchEvent(new Event('input', { bubbles: true }));
                  editor.scrollTop = editor.scrollHeight;
                  editor.dispatchEvent(new Event('scroll'));
                  syncLineNumbers();
                  const visibleTail = content.textContent.split('\\n').slice(-12).join(' ');
                  return {
                    ok: content.textContent.includes('3005'),
                    visibleTail,
                    renderedLineNumbers: content.textContent.split('\\n').filter(Boolean).length,
                    editorScrollTop: editor.scrollTop,
                  };
                }
                """
            )
            checks = {
                "title": page.title(),
                "export_button_visible": page.locator("#exportPdfBtn").is_visible(),
                "document_section_visible": page.locator("#titleInput").is_visible(),
                "appearance_section_visible": page.locator('[data-choice-group="style"]').count() > 0,
                "branding_section_visible": page.locator('[data-choice-group="branding"]').count() > 0,
                "settings_badge": page.locator("#appearanceName").inner_text(),
                "preview_status": preview_status,
                "preview_mode": preview_mode,
                "preview_failed": "failed" in preview_status.lower(),
                "preview_frame_visible": preview_frame_visible,
                "pdf_like_preview_loaded": "pdf-like preview updated" in preview_status.lower(),
                "pdf_like_page_markers": page_markers,
                "long_editor_line_numbers_ok": bool(line_number_check.get("ok")),
                "long_editor_line_number_tail": line_number_check.get("visibleTail"),
                "long_editor_rendered_line_numbers": line_number_check.get("renderedLineNumbers"),
            }
        finally:
            browser.close()
    return checks


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
        checks = _capture_studio(html_text, url, screenshot_path, timeout_ms=args.browser_timeout_ms)
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
    if checks.get("preview_mode") != "accurate":
        raise SystemExit("unexpected Studio preview mode")
    if checks.get("preview_failed"):
        raise SystemExit(f"Studio preview check failed: {checks.get('preview_status')}")
    if not checks.get("preview_frame_visible"):
        raise SystemExit("Studio preview frame is not visible")
    if not checks.get("pdf_like_page_markers"):
        raise SystemExit("Studio PDF-like preview page markers were not attached")
    if not checks.get("long_editor_line_numbers_ok"):
        raise SystemExit("Studio editor line-number virtualization failed for long documents")
    print(f"Studio screenshot written to {screenshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
