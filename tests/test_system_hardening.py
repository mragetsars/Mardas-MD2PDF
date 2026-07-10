from __future__ import annotations

import json
import time
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Barrier, Event, Lock, Thread

import pytest

from mardas_md2pdf import gui
from mardas_md2pdf.markdown import MarkdownInputError, extract_frontmatter, render_markdown
from mardas_md2pdf.renderer import PdfOptions, _stringify_metadata_value, build_html


def _start_studio_server() -> tuple[ThreadingHTTPServer, Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), gui.GuiRequestHandler)
    server.studio_bind_host = "127.0.0.1"  # type: ignore[attr-defined]
    server.studio_csrf_token = "secret"  # type: ignore[attr-defined]
    server.studio_preview_state_lock = Lock()  # type: ignore[attr-defined]
    server.studio_preview_render_lock = Lock()  # type: ignore[attr-defined]
    server.studio_latest_preview_ids = {}  # type: ignore[attr-defined]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post_json(
    server: ThreadingHTTPServer,
    endpoint: str,
    payload: dict[str, object],
    *,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=20)
    try:
        headers = {
            "Content-Type": "application/json",
            "Origin": f"http://127.0.0.1:{server.server_port}",
            "X-Mardas-Studio-Token": "secret",
        }
        headers.update(extra_headers or {})
        connection.request("POST", endpoint, body=json.dumps(payload), headers=headers)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_recursive_and_excessively_deep_yaml_are_rejected() -> None:
    with pytest.raises(MarkdownInputError, match="recursive YAML alias"):
        extract_frontmatter("---\nroot: &root\n  self: *root\n---\n# Body\n")

    nested = "value"
    for index in range(20):
        nested = {f"level-{index}": nested}
    with pytest.raises(MarkdownInputError, match="nesting depth"):
        from yaml import safe_dump

        extract_frontmatter(f"---\n{safe_dump(nested)}---\n# Body\n")


def test_metadata_stringifier_rejects_recursive_values() -> None:
    recursive: dict[str, object] = {}
    recursive["self"] = recursive

    with pytest.raises(ValueError, match="recursive alias"):
        _stringify_metadata_value(recursive)


def test_studio_returns_controlled_error_for_invalid_frontmatter() -> None:
    server, thread = _start_studio_server()
    try:
        status, body = _post_json(
            server,
            "/api/render-html",
            {"markdown": "---\ntitle: [broken\n---\n# Body\n"},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)

    payload = json.loads(body.decode("utf-8"))
    assert status == 400
    assert payload["code"] == "invalid_markdown"
    assert "Invalid YAML front matter" in payload["error"]


def test_studio_export_concurrency_is_bounded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    active = 0
    maximum = 0
    state_lock = Lock()
    entered = Barrier(gui.MAX_STUDIO_CONCURRENT_EXPORTS + 1)
    release = Event()

    def fake_convert(options: PdfOptions) -> Path:
        nonlocal active, maximum
        with state_lock:
            active += 1
            maximum = max(maximum, active)
        entered.wait(timeout=10)
        assert release.wait(timeout=10)
        options.output_path.write_bytes(b"%PDF-1.7\n%%EOF\n")
        with state_lock:
            active -= 1
        return options.output_path

    monkeypatch.setattr(gui, "convert", fake_convert)
    server, thread = _start_studio_server()
    results: list[int] = []

    def export() -> None:
        status, _body = _post_json(server, "/api/render", {"markdown": "# Report"})
        results.append(status)

    workers = [Thread(target=export, daemon=True) for _ in range(3)]
    try:
        workers[0].start()
        workers[1].start()
        entered.wait(timeout=10)
        workers[2].start()
        deadline = time.monotonic() + 10
        while len(results) < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        release.set()
        for worker in workers:
            worker.join(timeout=20)
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)

    assert maximum == gui.MAX_STUDIO_CONCURRENT_EXPORTS
    assert sorted(results) == [200, 200, 429]


def test_preview_freshness_is_isolated_per_client(monkeypatch: pytest.MonkeyPatch) -> None:
    entered_a = Event()
    release_a = Event()

    def fake_render(payload: dict[str, object]) -> str:
        if payload.get("markdown") == "# Client A":
            entered_a.set()
            assert release_a.wait(timeout=10)
        return f"<html><body>{payload.get('markdown')}</body></html>"

    monkeypatch.setattr(gui, "_render_studio_html_payload", fake_render)
    server, thread = _start_studio_server()
    responses: dict[str, int] = {}

    def post(name: str, client_id: str, preview_id: str, markdown: str) -> None:
        status, _body = _post_json(
            server,
            "/api/render-html",
            {"markdown": markdown},
            extra_headers={
                "X-Mardas-Studio-Client-Id": client_id,
                "X-Mardas-Studio-Preview-Id": preview_id,
            },
        )
        responses[name] = status

    thread_a = Thread(target=post, args=("a", "client-a", "preview-a", "# Client A"), daemon=True)
    thread_b = Thread(target=post, args=("b", "client-b", "preview-b", "# Client B"), daemon=True)
    try:
        thread_a.start()
        assert entered_a.wait(timeout=10)
        thread_b.start()
        time.sleep(0.05)
        release_a.set()
        thread_a.join(timeout=20)
        thread_b.join(timeout=20)
    finally:
        release_a.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)

    assert responses == {"a": 200, "b": 200}


def test_heading_ids_are_unique_across_raw_html_and_markdown() -> None:
    result = render_markdown('<h2 id="dup">Raw</h2>\n\n## Markdown {#ignored}\n\n<h3 id="dup">Again</h3>')

    assert result.body_html.count('id="dup"') == 1
    assert 'id="dup-2"' in result.body_html
    assert len({entry[2] for entry in result.toc_entries}) == len(result.toc_entries)


def test_relative_file_links_are_inert_and_html_has_no_local_base_path(tmp_path: Path) -> None:
    input_path = tmp_path / "document" / "report.md"
    input_path.parent.mkdir()
    result = render_markdown("[Sibling](secret.txt) [Parent](../outside.txt) [Web](https://example.com) [Section](#part)")
    html = build_html(result, PdfOptions(input_path=input_path, output_path=tmp_path / "out.pdf"))

    assert "<base " not in html
    assert "file://" not in html
    assert html.count("md2pdf-local-link-blocked") == 2
    assert 'href="https://example.com"' in html
    assert 'href="#part"' in html
