from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_STYLE = "modern"
DEFAULT_PALETTE = "blue"
DEFAULT_MODE = "light"

STYLE_FILES = {
    "modern": {"light": "style-modern.css", "dark": "style-modern.css"},
    "github": {"light": "style-github.css", "dark": "style-github.css"},
    "textbook": {"light": "style-textbook-light.css", "dark": "style-textbook-dark.css"},
    "academic": {"light": "style-academic.css", "dark": "style-academic.css"},
}
STYLES = tuple(STYLE_FILES)
STYLE_DESCRIPTIONS = {
    "modern": "Clean rounded document layout for reports and guides.",
    "github": "README-friendly layout for technical documentation.",
    "textbook": "Compact print-first layout for course notes and long documents.",
    "academic": "Formal serif-leaning layout for papers and academic reports.",
}
MODES = ("light", "dark")
MODE_DESCRIPTIONS = {
    "light": "Light paper-like output for ordinary print and sharing.",
    "dark": "Dark output for screen-first documents and high-contrast previews.",
}

PALETTES: dict[str, dict[str, str]] = {
    "blue": {
        "accent": "#2563eb",
        "accent_2": "#7c3aed",
        "accent_soft": "#eef4ff",
        "accent_line": "#5aa6e8",
        "quote": "#eff6ff",
    },
    "emerald": {
        "accent": "#059669",
        "accent_2": "#0d9488",
        "accent_soft": "#ecfdf5",
        "accent_line": "#34d399",
        "quote": "#ecfdf5",
    },
    "violet": {
        "accent": "#7c3aed",
        "accent_2": "#db2777",
        "accent_soft": "#f5f3ff",
        "accent_line": "#a78bfa",
        "quote": "#f5f3ff",
    },
    "amber": {
        "accent": "#d97706",
        "accent_2": "#b45309",
        "accent_soft": "#fffbeb",
        "accent_line": "#f59e0b",
        "quote": "#fffbeb",
    },
    "rose": {
        "accent": "#e11d48",
        "accent_2": "#be123c",
        "accent_soft": "#fff1f2",
        "accent_line": "#fb7185",
        "quote": "#fff1f2",
    },
    "slate": {
        "accent": "#475569",
        "accent_2": "#0f172a",
        "accent_soft": "#f1f5f9",
        "accent_line": "#94a3b8",
        "quote": "#f8fafc",
    },
    "neutral": {
        "accent": "#404040",
        "accent_2": "#171717",
        "accent_soft": "#f5f5f5",
        "accent_line": "#a3a3a3",
        "quote": "#fafafa",
    },
}
PALETTES_ORDER = tuple(PALETTES)
PALETTE_DESCRIPTIONS = {
    "blue": "Default professional blue accents.",
    "emerald": "Green accents for calm reports and dashboards.",
    "violet": "Purple accents for creative and product documents.",
    "amber": "Warm amber accents for teaching and review documents.",
    "rose": "Rose accents for editorial or highlighted reports.",
    "slate": "Cool neutral accents for understated technical documents.",
    "neutral": "Minimal grayscale accents for formal output.",
}


@dataclass(frozen=True, slots=True)
class Appearance:
    """Resolved visual system for a PDF output.

    ``style`` controls layout/shape choices, ``palette`` controls accent colors,
    and ``mode`` controls light/dark contrast.  These are intentionally separate
    so users can reason about document shape, color, and contrast independently.
    """

    style: str = DEFAULT_STYLE
    palette: str = DEFAULT_PALETTE
    mode: str = DEFAULT_MODE


def _clean(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_style_name(value: Any) -> str:
    candidate = _clean(value) or DEFAULT_STYLE
    return candidate if candidate in STYLES else DEFAULT_STYLE


def normalize_palette_name(value: Any) -> str:
    candidate = _clean(value) or DEFAULT_PALETTE
    return candidate if candidate in PALETTES else DEFAULT_PALETTE


def normalize_mode_name(value: Any) -> str:
    candidate = _clean(value) or DEFAULT_MODE
    return candidate if candidate in MODES else DEFAULT_MODE


def validate_style_name(value: Any) -> str:
    candidate = _clean(value) or DEFAULT_STYLE
    if candidate not in STYLES:
        choices = ", ".join(STYLES)
        raise ValueError(f"style must be one of: {choices}")
    return candidate


def validate_palette_name(value: Any) -> str:
    candidate = _clean(value) or DEFAULT_PALETTE
    if candidate not in PALETTES:
        choices = ", ".join(PALETTES_ORDER)
        raise ValueError(f"palette must be one of: {choices}")
    return candidate


def validate_mode_name(value: Any) -> str:
    candidate = _clean(value) or DEFAULT_MODE
    if candidate not in MODES:
        choices = ", ".join(MODES)
        raise ValueError(f"mode must be one of: {choices}")
    return candidate


def resolve_appearance(*, style: Any = None, palette: Any = None, mode: Any = None) -> Appearance:
    return Appearance(
        style=normalize_style_name(style),
        palette=normalize_palette_name(palette),
        mode=normalize_mode_name(mode),
    )


def appearance_from_metadata(metadata: dict[str, Any]) -> Appearance:
    raw = metadata.get("appearance")
    if isinstance(raw, dict):
        return resolve_appearance(
            style=raw.get("style"),
            palette=raw.get("palette"),
            mode=raw.get("mode"),
        )
    return resolve_appearance(
        style=metadata.get("style"),
        palette=metadata.get("palette"),
        mode=metadata.get("mode"),
    )


def style_css_file(style: str, mode: str) -> str:
    resolved = resolve_appearance(style=style, mode=mode)
    return STYLE_FILES[resolved.style][resolved.mode]


def code_style_for_appearance(style: str, mode: str) -> str:
    appearance = resolve_appearance(style=style, mode=mode)
    if appearance.mode == "dark":
        return "bw"
    if appearance.style in {"github", "textbook", "academic"}:
        return "friendly"
    return "github-dark"


def math_scale_vars(style: str) -> tuple[str, str]:
    resolved_style = normalize_style_name(style)
    if resolved_style == "academic":
        return "70%", "105%"
    if resolved_style == "textbook":
        return "78%", "115%"
    return "100%", "130%"


def footer_kind(style: str, mode: str) -> str:
    appearance = resolve_appearance(style=style, mode=mode)
    if appearance.style == "textbook":
        return "textbook-dark" if appearance.mode == "dark" else "textbook-light"
    return appearance.style


def appearance_body_classes(appearance: Appearance) -> str:
    return " ".join(
        [
            f"md2pdf-style-{appearance.style}",
            f"md2pdf-palette-{appearance.palette}",
            f"md2pdf-mode-{appearance.mode}",
        ]
    )


def palette_css(palette_name: str, mode_name: str) -> str:
    appearance = resolve_appearance(palette=palette_name, mode=mode_name)
    colors = PALETTES[appearance.palette]
    dark_css = ""
    if appearance.mode == "dark":
        dark_css = """
@page { background: #0b1020; }
html {
  background: #0b1020 !important;
  color: #e5e7eb !important;
}
body.md2pdf-mode-dark {
  --ink: #e5e7eb;
  --muted: #a1a1aa;
  --soft: #111827;
  --softer: #0f172a;
  --line: #334155;
  --line-strong: #475569;
  --accent-soft: color-mix(in srgb, var(--accent) 18%, #020617);
  --quote: #111827;
  --code-bg: #020617;
  --code-ink: #e5e7eb;
  background: #0b1020 !important;
  color: var(--ink) !important;
}
body.md2pdf-mode-dark .md2pdf-document,
body.md2pdf-mode-dark .md2pdf-article {
  background: transparent !important;
  color: var(--ink) !important;
}
body.md2pdf-mode-dark h1,
body.md2pdf-mode-dark h2,
body.md2pdf-mode-dark h3,
body.md2pdf-mode-dark h4,
body.md2pdf-mode-dark h5,
body.md2pdf-mode-dark h6,
body.md2pdf-mode-dark .md2pdf-cover h1,
body.md2pdf-mode-dark strong { color: #f8fafc !important; }
body.md2pdf-mode-dark p,
body.md2pdf-mode-dark li,
body.md2pdf-mode-dark td { color: var(--ink) !important; }
body.md2pdf-mode-dark table { background: #0f172a !important; color: var(--ink) !important; }
body.md2pdf-mode-dark th { background: #111827 !important; color: #f8fafc !important; }
body.md2pdf-mode-dark td,
body.md2pdf-mode-dark th { border-bottom-color: var(--line) !important; }
body.md2pdf-mode-dark tbody tr:nth-child(even) td { background: #111827 !important; }
body.md2pdf-mode-dark blockquote,
body.md2pdf-mode-dark .callout,
body.md2pdf-mode-dark .md2pdf-details,
body.md2pdf-mode-dark .mermaid-diagram {
  background: #111827 !important;
  border-color: var(--line) !important;
  color: var(--ink) !important;
}
body.md2pdf-mode-dark .md2pdf-cover__summary,
body.md2pdf-mode-dark em,
body.md2pdf-mode-dark small,
body.md2pdf-mode-dark .footnotes,
body.md2pdf-mode-dark .footnote-backref { color: var(--muted) !important; }
body.md2pdf-mode-dark :not(pre) > code {
  background: #111827 !important;
  border-color: var(--line) !important;
  color: #f8fafc !important;
}
body.md2pdf-mode-dark .code-block,
body.md2pdf-mode-dark .codehilite,
body.md2pdf-mode-dark .highlight,
body.md2pdf-mode-dark pre {
  background: #020617 !important;
  color: #f8fafc !important;
  border-color: var(--line) !important;
}
body.md2pdf-mode-dark .code-block figcaption {
  background: #111827 !important;
  color: #e5e7eb !important;
  border-bottom-color: var(--line) !important;
}
body.md2pdf-mode-dark .md2pdf-toc,
body.md2pdf-mode-dark .md2pdf-toc h2 { color: #f8fafc !important; }
body.md2pdf-mode-dark .md2pdf-toc a {
  background: transparent !important;
  color: var(--accent) !important;
}
body.md2pdf-mode-dark .md2pdf-toc li > ol { border-inline-start-color: var(--line) !important; }
body.md2pdf-mode-dark .md2pdf-toc .toc-number { color: #e5e7eb !important; }
body.md2pdf-mode-dark .md2pdf-watermark { mix-blend-mode: screen; }
body.md2pdf-mode-dark .md2pdf-watermark--text { color: #f8fafc; }
body.md2pdf-mode-dark .md2pdf-watermark--image img { filter: invert(1) grayscale(1); }
"""
    return f"""
:root {{
  --accent: {colors['accent']};
  --accent-2: {colors['accent_2']};
  --accent-soft: {colors['accent_soft']};
  --quote: {colors['quote']};
  --blue: {colors['accent']};
  --blue-soft: {colors['accent_soft']};
  --blue-line: {colors['accent_line']};
  --md2pdf-mermaid-stroke: {colors['accent']};
  --md2pdf-mermaid-edge-ink: {colors['accent']};
}}
body.md2pdf-palette-{appearance.palette} a {{ color: var(--accent); }}
body.md2pdf-palette-{appearance.palette} li::marker {{ color: var(--accent); }}
body.md2pdf-palette-{appearance.palette} .md2pdf-cover__eyebrow,
body.md2pdf-palette-{appearance.palette} .md2pdf-summary,
body.md2pdf-palette-{appearance.palette} .footnote-marker {{ color: var(--accent); }}
{dark_css}
"""
