from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
import tempfile
from importlib import resources
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any, Callable

from bs4 import BeautifulSoup

from . import __version__
from .appearance import appearance_from_metadata, resolve_appearance
from .config import (
    CONFIG_FILENAME,
    CONFIG_SCHEMA_VERSION,
    LoadedProjectConfig,
    default_config_text,
    load_project_config,
)
from .diagnostics import Diagnostic, format_diagnostic, has_errors, write_diagnostics
from .markdown import MarkdownInputError, render_markdown_file

PROJECT_COMMANDS = ("init", "validate", "doctor", "explain-config")


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--config",
        type=Path,
        help=f"Use an explicit {CONFIG_FILENAME} project configuration file.",
    )
    group.add_argument(
        "--no-config",
        action="store_true",
        help=f"Disable automatic {CONFIG_FILENAME} discovery for this command.",
    )


def _init_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mrs-md2pdf init", description=f"Create a versioned {CONFIG_FILENAME} project file."
    )
    parser.add_argument("directory", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing configuration file atomically"
    )
    return parser


def _init_main(argv: list[str]) -> int:
    parser = _init_parser()
    args = parser.parse_args(argv)
    directory = args.directory.expanduser().resolve()
    if directory.exists() and not directory.is_dir():
        parser.error(f"Project path is not a directory: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / CONFIG_FILENAME
    if target.exists() and not args.force:
        parser.error(f"Configuration already exists: {target}; use --force to replace it")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{CONFIG_FILENAME}.", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(default_config_text())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Created project configuration: {target}")
    return 0


def _analysis_parser(command: str) -> argparse.ArgumentParser:
    descriptions = {
        "validate": "Validate project configuration and Markdown without launching Chromium.",
        "doctor": "Check the local rendering environment and project configuration.",
        "explain-config": "Show effective project settings and their sources.",
    }
    parser = argparse.ArgumentParser(
        prog=f"mrs-md2pdf {command}", description=descriptions[command]
    )
    parser.add_argument(
        "input",
        nargs="?" if command == "doctor" else None,
        type=Path,
        default=Path.cwd() if command == "doctor" else None,
    )
    _add_config_arguments(parser)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def _input_diagnostics(path: Path, *, required_file: bool) -> list[Diagnostic]:
    if not path.exists():
        return [Diagnostic("MARDAS-E201", "error", "Input path does not exist.", path=path)]
    if required_file and not path.is_file():
        return [
            Diagnostic("MARDAS-E202", "error", "Input must be a regular Markdown file.", path=path)
        ]
    return []


def _project_config_diagnostics(config: LoadedProjectConfig) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    path_checks = [
        ("brand_logo", "MARDAS-E113", "Configured branding logo is not a regular file."),
        ("watermark_image", "MARDAS-E114", "Configured watermark image is not a regular file."),
    ]
    for key, code, message in path_checks:
        value = config.values.get(key)
        if value is not None and not Path(value).is_file():
            diagnostics.append(Diagnostic(code, "error", message, path=Path(value)))
    font_dir = config.values.get("font_dir")
    if font_dir is not None and not Path(font_dir).is_dir():
        diagnostics.append(
            Diagnostic(
                "MARDAS-E115",
                "error",
                "Configured font directory does not exist or is not a directory.",
                path=Path(font_dir),
            )
        )
    if config.values.get("unsafe_html") is True:
        diagnostics.append(
            Diagnostic(
                "MARDAS-W301",
                "warning",
                "Project configuration enables unsanitized raw HTML.",
                path=config.path,
                hint="Keep security.unsafe_html=false for untrusted Markdown.",
            )
        )
    if config.values.get("allow_remote_assets") is True:
        diagnostics.append(
            Diagnostic(
                "MARDAS-W302",
                "warning",
                "Project configuration permits remote network assets.",
                path=config.path,
                hint="Remote assets can disclose network metadata and make builds non-reproducible.",
            )
        )
    return diagnostics


def _load_analysis_config(
    args: argparse.Namespace, path: Path
) -> tuple[LoadedProjectConfig, list[Diagnostic]]:
    result = load_project_config(start=path, explicit_path=args.config, disabled=args.no_config)
    diagnostics = list(result.diagnostics)
    if not has_errors(diagnostics):
        diagnostics.extend(_project_config_diagnostics(result.config))
    return result.config, diagnostics


def _validate_document(
    path: Path, config: LoadedProjectConfig
) -> tuple[list[Diagnostic], dict[str, Any]]:
    diagnostics: list[Diagnostic] = []
    values = config.values
    try:
        result = render_markdown_file(
            path,
            toc=bool(values.get("toc", False)),
            toc_depth=int(values.get("toc_depth", 6)),
            unsafe_html=bool(values.get("unsafe_html", False)),
            allow_remote_images=bool(values.get("allow_remote_assets", False)),
        )
    except (MarkdownInputError, OSError, UnicodeError, ValueError) as exc:
        diagnostics.append(
            Diagnostic(
                "MARDAS-E203",
                "error",
                str(exc),
                path=path,
                hint="Fix the Markdown/front matter error and run validation again.",
            )
        )
        return diagnostics, {}

    if not values.get("title") and not result.metadata.get("title") and result.title == "Document":
        diagnostics.append(
            Diagnostic(
                "MARDAS-W201",
                "warning",
                "Document has no explicit title or level-one heading.",
                path=path,
                hint="Add `title` to front matter or add a `# Heading`.",
            )
        )
    soup = BeautifulSoup(result.body_html, "html.parser")
    for placeholder in soup.select(".md2pdf-image-placeholder[data-md2pdf-blocked-src]"):
        source = str(placeholder.get("data-md2pdf-blocked-src") or "").strip()
        reason = str(placeholder.get("data-md2pdf-blocked-reason") or "").strip()
        code = "MARDAS-W203" if reason == "local" else "MARDAS-W204"
        message = (
            f"Local image could not be embedded: {source}"
            if reason == "local"
            else f"Remote image is blocked by project policy: {source}"
        )
        diagnostics.append(
            Diagnostic(
                code,
                "warning",
                message,
                path=path,
                hint=(
                    "Keep the image inside the document directory and verify its path."
                    if reason == "local"
                    else "Use a local image or explicitly enable security.allow_remote_assets for trusted projects."
                ),
            )
        )

    previous_level: int | None = None
    for level, title, _heading_id, _number in result.toc_entries:
        if previous_level is not None and level > previous_level + 1:
            diagnostics.append(
                Diagnostic(
                    "MARDAS-W202",
                    "warning",
                    f"Heading hierarchy jumps from level {previous_level} to level {level}: {title}",
                    path=path,
                    hint="Use consecutive heading levels for a clearer document outline.",
                )
            )
        previous_level = level
    return diagnostics, {
        "title": values.get("title") or result.metadata.get("title") or result.title,
        "headings": len(result.toc_entries),
        "metadata_keys": sorted(result.metadata),
    }


def _validate_main(argv: list[str]) -> int:
    parser = _analysis_parser("validate")
    args = parser.parse_args(argv)
    input_path = args.input.expanduser().resolve()
    diagnostics = _input_diagnostics(input_path, required_file=True)
    config, config_diagnostics = _load_analysis_config(args, input_path)
    diagnostics.extend(config_diagnostics)
    document_context: dict[str, Any] = {}
    if not has_errors(diagnostics):
        document_diagnostics, document_context = _validate_document(input_path, config)
        diagnostics.extend(document_diagnostics)
    context = {
        "command": "validate",
        "input": str(input_path),
        "config": str(config.path) if config.path else None,
        "schema_version": CONFIG_SCHEMA_VERSION,
        "document": document_context,
    }
    write_diagnostics(diagnostics, output_format=args.format, stream=sys.stdout, context=context)
    return 1 if has_errors(diagnostics) else 0


def _doctor_main(argv: list[str]) -> int:
    parser = _analysis_parser("doctor")
    args = parser.parse_args(argv)
    target = args.input.expanduser().resolve()
    diagnostics = _input_diagnostics(target, required_file=False)
    config, config_diagnostics = _load_analysis_config(args, target)
    diagnostics.extend(config_diagnostics)

    if sys.version_info < (3, 10):
        diagnostics.append(
            Diagnostic(
                "MARDAS-E403",
                "error",
                "Python 3.10 or newer is required.",
                hint="Install a supported Python runtime before rendering documents.",
            )
        )

    chromium = shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
    if not chromium:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                managed_browser = Path(playwright.chromium.executable_path)
            if managed_browser.is_file():
                chromium = str(managed_browser)
        except Exception:
            chromium = None
    configured_chromium = config.values.get("chromium_path")
    if configured_chromium:
        configured_path = Path(configured_chromium)
        if configured_path.is_file():
            chromium = str(configured_path)
        else:
            diagnostics.append(
                Diagnostic(
                    "MARDAS-E401",
                    "error",
                    "Configured Chromium executable does not exist.",
                    path=configured_path,
                )
            )
    if not chromium:
        diagnostics.append(
            Diagnostic(
                "MARDAS-W401",
                "warning",
                "No system Chromium/Chrome executable was found on PATH.",
                hint="Run `playwright install chromium` or configure browser.chromium_path.",
            )
        )

    mathjax_path = resources.files("mardas_md2pdf") / "assets" / "mathjax" / "tex-svg-full.js"
    if not mathjax_path.is_file():
        diagnostics.append(
            Diagnostic(
                "MARDAS-E402",
                "error",
                "Vendored MathJax asset is missing from the installed package.",
            )
        )

    if target.is_file() and not has_errors(diagnostics):
        document_diagnostics, _ = _validate_document(target, config)
        diagnostics.extend(document_diagnostics)

    dependency_versions: dict[str, str] = {}
    for distribution in ("playwright", "pypdf", "markdown-it-py", "beautifulsoup4", "PyYAML"):
        try:
            dependency_versions[distribution] = package_version(distribution)
        except PackageNotFoundError:
            diagnostics.append(
                Diagnostic(
                    "MARDAS-E404",
                    "error",
                    f"Required dependency is not installed: {distribution}",
                )
            )

    context = {
        "command": "doctor",
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "input": str(target),
        "config": str(config.path) if config.path else None,
        "chromium": chromium,
        "mathjax": str(mathjax_path),
        "dependencies": dependency_versions,
    }
    write_diagnostics(diagnostics, output_format=args.format, stream=sys.stdout, context=context)
    return 1 if has_errors(diagnostics) else 0


def _metadata_value(metadata: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return value
    return None


def _effective_config(input_path: Path, config: LoadedProjectConfig) -> dict[str, dict[str, Any]]:
    result = render_markdown_file(
        input_path,
        toc=bool(config.values.get("toc", False)),
        toc_depth=int(config.values.get("toc_depth", 6)),
        unsafe_html=bool(config.values.get("unsafe_html", False)),
        allow_remote_images=bool(config.values.get("allow_remote_assets", False)),
    )
    metadata = result.metadata
    metadata_appearance = appearance_from_metadata(metadata)
    raw_appearance = (
        metadata.get("appearance") if isinstance(metadata.get("appearance"), dict) else {}
    )
    appearance = resolve_appearance(
        style=config.values.get("style") or metadata_appearance.style,
        palette=config.values.get("palette") or metadata_appearance.palette,
        mode=config.values.get("mode") or metadata_appearance.mode,
    )
    metadata_branding = (
        metadata.get("branding") if isinstance(metadata.get("branding"), dict) else {}
    )
    metadata_direction = _metadata_value(
        metadata, "dir", "direction", "text_direction", "document_direction"
    )

    defaults: dict[str, Any] = {
        "toc": False,
        "toc_depth": 6,
        "toc_page_break": False,
        "h1_page_break": False,
        "page_size": "A4",
        "margin_top": "18mm",
        "margin_bottom": "20mm",
        "margin_x": "16mm",
        "cover": True,
        "header_footer": True,
        "mathjax": True,
        "unsafe_html": False,
        "allow_remote_assets": False,
        "timeout_ms": 120_000,
        "chromium_sandbox": "auto",
        "show_logo": True,
        "watermark": None,
        "watermark_opacity": 0.065,
        "watermark_width": "105mm",
        "font_dir": None,
        "chromium_path": None,
    }
    effective: dict[str, dict[str, Any]] = {}

    def add(name: str, value: Any, source: str) -> None:
        effective[name] = {
            "value": str(value) if isinstance(value, Path) else value,
            "source": source,
        }

    for key, default in defaults.items():
        internal_key = {
            "cover": "no_cover",
            "header_footer": "no_header_footer",
            "mathjax": "no_mathjax",
        }.get(key, key)
        if internal_key in config.values:
            raw = config.values[internal_key]
            value = not raw if internal_key.startswith("no_") else raw
            add(key, value, str(config.path))
        else:
            add(key, default, "built-in default")

    metadata_fields = {
        "title": _metadata_value(metadata, "title"),
        "author": _metadata_value(metadata, "authors", "author"),
        "description": _metadata_value(metadata, "description", "summary", "subject"),
        "direction": metadata_direction or "auto",
    }
    config_destinations = {
        "title": "title",
        "author": "author",
        "description": "description",
        "direction": "document_direction",
    }
    for name, metadata_value in metadata_fields.items():
        dest = config_destinations[name]
        if dest in config.values:
            add(name, config.values[dest], str(config.path))
        elif metadata_value not in (None, ""):
            add(name, metadata_value, "front matter")
        else:
            add(name, None if name != "direction" else "auto", "built-in default")

    for name, value in (
        ("style", appearance.style),
        ("palette", appearance.palette),
        ("mode", appearance.mode),
    ):
        metadata_explicit = name in raw_appearance or name in metadata
        source = (
            str(config.path)
            if name in config.values
            else "front matter"
            if metadata_explicit
            else "built-in default"
        )
        add(name, value, source)

    branding_value = config.values.get("branding")
    if branding_value is not None:
        add("branding", branding_value, str(config.path))
    elif metadata_branding.get("mode") or metadata.get("branding"):
        add("branding", metadata_branding.get("mode") or metadata.get("branding"), "front matter")
    else:
        add("branding", "off", "built-in default")

    for dest, value in sorted(config.values.items()):
        public_name = {
            "document_direction": "direction",
            "no_cover": "cover",
            "no_header_footer": "header_footer",
            "no_mathjax": "mathjax",
            "no_cover_logo": "show_logo",
        }.get(dest, dest)
        if public_name in effective:
            continue
        add(public_name, not value if dest.startswith("no_") else value, str(config.path))
    return dict(sorted(effective.items()))


def _explain_config_main(argv: list[str]) -> int:
    parser = _analysis_parser("explain-config")
    args = parser.parse_args(argv)
    input_path = args.input.expanduser().resolve()
    diagnostics = _input_diagnostics(input_path, required_file=True)
    config, config_diagnostics = _load_analysis_config(args, input_path)
    diagnostics.extend(config_diagnostics)
    effective: dict[str, dict[str, Any]] = {}
    if not has_errors(diagnostics):
        try:
            effective = _effective_config(input_path, config)
        except (MarkdownInputError, OSError, UnicodeError, ValueError) as exc:
            diagnostics.append(Diagnostic("MARDAS-E203", "error", str(exc), path=input_path))

    if args.format == "json":
        write_diagnostics(
            diagnostics,
            output_format="json",
            stream=sys.stdout,
            context={
                "command": "explain-config",
                "input": str(input_path),
                "config": str(config.path) if config.path else None,
                "schema_version": CONFIG_SCHEMA_VERSION,
                "effective": effective,
            },
        )
    else:
        print(f"Input: {input_path}")
        print(f"Config: {config.path or 'none discovered'}")
        print(f"Schema version: {CONFIG_SCHEMA_VERSION}")
        if diagnostics:
            print()
            for item in diagnostics:
                print(format_diagnostic(item))
        if effective:
            print("\nEffective settings:")
            for name, item in effective.items():
                print(f"  {name:<24} {item['value']!s:<20} [{item['source']}]")
    return 1 if has_errors(diagnostics) else 0


def run_project_command(command: str, argv: list[str]) -> int:
    handlers: dict[str, Callable[[list[str]], int]] = {
        "init": _init_main,
        "validate": _validate_main,
        "doctor": _doctor_main,
        "explain-config": _explain_config_main,
    }
    try:
        handler = handlers[command]
    except KeyError as exc:  # pragma: no cover - protected by CLI dispatch
        raise ValueError(f"Unknown project command: {command}") from exc
    return handler(argv)
