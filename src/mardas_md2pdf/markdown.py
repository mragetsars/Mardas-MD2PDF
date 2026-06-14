from __future__ import annotations

import base64
import html
import mimetypes
import re
import unicodedata
import warnings
from urllib.parse import unquote, urlparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - PyYAML is declared as dependency
    yaml = None

from bs4 import BeautifulSoup, NavigableString, Tag
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

from .mermaid import render_mermaid_to_svg

ARABIC_RANGES = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_RANGES = re.compile(r"[A-Za-z]")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
INLINE_FOOTNOTE_RE = re.compile(r"\[\^([^\]]+)\]")
INLINE_MATH_RE = re.compile(r"(?<!\\)\$(?![\s$])(.+?)(?<!\\)\$(?!\d)")
DISPLAY_MATH_FENCE_RE = re.compile(r"^\s*\$\$\s*$")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
HEADING_RE = re.compile(r"<h([1-6])([^>]*)>(.*?)</h\1>", re.DOTALL | re.IGNORECASE)
BLOCKED_RAW_HTML_TAGS = {"script", "style", "iframe", "object", "embed", "form", "meta", "link", "base"}
SAFE_RAW_HTML_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "caption",
    "cite",
    "code",
    "col",
    "colgroup",
    "dd",
    "del",
    "details",
    "div",
    "dl",
    "dt",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "ins",
    "kbd",
    "li",
    "mark",
    "ol",
    "p",
    "pre",
    "s",
    "section",
    "small",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}
GLOBAL_SAFE_ATTRS = {
    "class",
    "id",
    "dir",
    "lang",
    "title",
    "role",
    "aria-label",
    "data-lang",
    "data-line-start",
    "data-lines",
    "data-md2pdf-columns",
    "data-md2pdf-rows",
}
TAG_SAFE_ATTRS = {
    "a": {"href", "name", "target", "rel"},
    "img": {"src", "alt", "width", "height"},
    "th": {"align", "colspan", "rowspan", "scope"},
    "td": {"align", "colspan", "rowspan"},
    "ol": {"start", "type"},
    "ul": {"type"},
    "code": {"class"},
}
SAFE_URL_SCHEMES = {"", "http", "https", "mailto", "data"}
SAFE_DATA_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp", "image/avif"}
MAX_EMBED_IMAGE_BYTES = 20 * 1024 * 1024
TRANSPARENT_IMAGE_DATA_URI = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
RTL_LANG_PREFIXES = ("ar", "fa", "he", "iw", "ku", "ps", "sd", "ug", "ur", "yi")


def normalize_language(value: Any, fallback: str = "auto") -> str:
    """Return a compact BCP-47-ish language code used for UI labels.

    The converter only needs the primary subtag for built-in labels such as the
    table-of-contents title and callout captions. Unknown or empty values are
    kept as ``fallback`` so direction detection can still infer a sensible
    default from the actual Markdown body.
    """
    text = str(value or "").strip().replace("_", "-").lower()
    return text or fallback


def is_rtl_language(lang: str | None) -> bool:
    return normalize_language(lang, "").startswith(RTL_LANG_PREFIXES)


def language_family(lang: str | None, text_hint: str = "") -> str:
    """Choose ``fa`` or ``en`` for bundled UI strings.

    Persian is used for RTL languages and Persian-dominant documents. English is
    used for explicit English metadata and for LTR/Latin-dominant documents.
    """
    normalized = normalize_language(lang, "auto")
    if normalized.startswith("en"):
        return "en"
    if is_rtl_language(normalized):
        return "fa"
    if normalized not in {"", "auto", "und"}:
        return "en"
    return "fa" if dominant_direction(text_hint) == "rtl" else "en"


def ui_label(key: str, *, lang: str | None = None, text_hint: str = "") -> str:
    labels = {
        "fa": {
            "toc_title": "فهرست مطالب",
            "toc_aria": "فهرست مطالب",
            "callout_note": "نکته",
            "callout_tip": "پیشنهاد",
            "callout_important": "مهم",
            "callout_warning": "هشدار",
            "callout_caution": "احتیاط",
            "callout_info": "اطلاعات",
            "callout_success": "موفقیت",
            "callout_question": "پرسش",
            "callout_failure": "خطا",
            "callout_danger": "خطر",
            "callout_bug": "اشکال",
            "callout_example": "نمونه",
            "callout_quote": "نقل‌قول",
            "callout_abstract": "خلاصه",
            "footnote": "پانویس",
        },
        "en": {
            "toc_title": "Table of Contents",
            "toc_aria": "Table of contents",
            "callout_note": "Note",
            "callout_tip": "Tip",
            "callout_important": "Important",
            "callout_warning": "Warning",
            "callout_caution": "Caution",
            "callout_info": "Info",
            "callout_success": "Success",
            "callout_question": "Question",
            "callout_failure": "Failure",
            "callout_danger": "Danger",
            "callout_bug": "Bug",
            "callout_example": "Example",
            "callout_quote": "Quote",
            "callout_abstract": "Abstract",
            "footnote": "Footnote",
        },
    }
    family = language_family(lang, text_hint)
    return labels[family].get(key, labels["en"].get(key, key))


@dataclass(slots=True)
class MarkdownRenderResult:
    body_html: str
    metadata: dict[str, Any] = field(default_factory=dict)
    title: str = "Document"
    pygments_css: str = ""
    toc_html: str = ""
    toc_entries: list[tuple[int, str, str, str]] = field(default_factory=list)


@dataclass(slots=True)
class TocItem:
    level: int
    title: str
    heading_id: str
    number: str
    title_html: str = ""
    children: list["TocItem"] = field(default_factory=list)


class CodeHtmlFormatter(HtmlFormatter):
    """Pygments formatter. The Pygments style is selected by the resolved appearance."""

    def __init__(
        self,
        style: str = "github-dark",
        *,
        linenos: bool = False,
        hl_lines: list[int] | None = None,
        line_start: int = 1,
    ) -> None:
        super().__init__(
            style=style,
            cssclass="codehilite",
            nowrap=False,
            linenos="table" if linenos else False,
            linenostart=max(1, int(line_start or 1)),
            hl_lines=hl_lines or [],
        )


def extract_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end() :]
    if yaml is None:
        return {}, body
    try:
        data = yaml.safe_load(raw) or {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data, body


def guess_title(markdown: str, metadata: dict[str, Any]) -> str:
    meta_title = metadata.get("title")
    if meta_title:
        return str(meta_title)
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip(" #\t") or "Document"
    return "Document"


def has_persian(text: str) -> bool:
    return bool(ARABIC_RANGES.search(text or ""))


def has_latin(text: str) -> bool:
    return bool(LATIN_RANGES.search(text or ""))


def dominant_direction(text: str) -> str:
    """Return rtl/ltr/auto by scanning the first strong directional character."""
    for char in text:
        direction = unicodedata.bidirectional(char)
        if direction in {"R", "AL"}:
            return "rtl"
        if direction == "L":
            return "ltr"
    return "auto"



CODE_FENCE_TITLE_RE = re.compile(r"(?:^|\s)(?:title|filename|file)=(?P<quote>[\"\'])(?P<value>.*?)(?P=quote)")
CODE_FENCE_BRACE_RE = re.compile(r"\{(?P<spec>[^}]*)\}")
CODE_FENCE_KV_RE = re.compile(
    r"(?P<key>[A-Za-z][\w-]*)\s*=\s*"
    r"(?:(?P<quote>[\"'])(?P<quoted>.*?)(?P=quote)|(?P<bare>[^\s}]+))"
)
CODE_FENCE_ATTR_CLASS_RE = re.compile(r"(?<!\S)\.(?P<class>[A-Za-z_][\w.-]*)")
CODE_FENCE_TITLE_KEYS = {"title", "filename", "file", "caption", "name"}
CODE_FENCE_HIGHLIGHT_KEYS = {
    "hl_lines",
    "hl-lines",
    "highlight",
    "line-highlight",
    "lines",
    "emphasize-lines",
}
CODE_FENCE_LINE_NUMBER_KEYS = {
    "linenos",
    "line-numbers",
    "linenumbers",
    "numbered",
    "numberlines",
    "lineNumbers",
}
CODE_FENCE_LINE_START_KEYS = {
    "start",
    "startline",
    "start-line",
    "line-start",
    "linenostart",
    "lineno-start",
    "first-line",
}
CODE_FENCE_LINE_NUMBER_CLASSES = {
    "linenos",
    "line-numbers",
    "linenumbers",
    "numbered",
    "numberlines",
    "numberLines",
}
CODE_FENCE_LINE_NUMBER_KEY_SET = {item.lower() for item in CODE_FENCE_LINE_NUMBER_KEYS}
CODE_FENCE_LINE_START_KEY_SET = {item.lower() for item in CODE_FENCE_LINE_START_KEYS}
CODE_FENCE_LANGUAGE_ALIASES = {
    "mmd": "mermaid",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "md": "markdown",
    "yml": "yaml",
}


def _parse_line_highlights(spec: str | None) -> list[int]:
    if not spec:
        return []
    values: set[int] = set()
    cleaned = str(spec).strip().strip("{}[]()\"'").replace(";", ",")
    for part in re.split(r"[,\s]+", cleaned):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            start_text, end_text = [chunk.strip() for chunk in part.split('-', 1)]
            if start_text.isdigit() and end_text.isdigit():
                start, end = int(start_text), int(end_text)
                if start > 0 and end >= start:
                    values.update(range(start, end + 1))
            continue
        if part.isdigit() and int(part) > 0:
            values.add(int(part))
    return sorted(values)


def _normalize_code_language(value: str | None) -> str:
    language = (value or "").strip().strip(".").lower()
    return CODE_FENCE_LANGUAGE_ALIASES.get(language, language)


def _parse_code_fence_key_values(attrs: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in CODE_FENCE_KV_RE.finditer(attrs or ""):
        key = match.group("key").strip()
        value = match.group("quoted") if match.group("quote") else match.group("bare")
        values[key] = (value or "").strip()
    return values


def _truthy_attr_value(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() not in {"", "0", "false", "no", "off", "none"}


def _positive_int_attr(value: str | None, *, fallback: int = 1) -> int:
    try:
        parsed = int(str(value or "").strip())
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _first_language_class(attrs: str) -> str:
    for match in CODE_FENCE_ATTR_CLASS_RE.finditer(attrs or ""):
        name = match.group("class")
        if name in CODE_FENCE_LINE_NUMBER_CLASSES:
            continue
        if name.startswith("language-"):
            return _normalize_code_language(name.removeprefix("language-"))
        return _normalize_code_language(name)
    return ""


def parse_code_fence_info(info: str | None) -> dict[str, Any]:
    """Parse documentation-style fenced code metadata.

    The parser accepts the common variants used by GitHub, MkDocs, Pandoc,
    Quarto, and documentation generators, for example::

        ```python title="renderer.py" {2,5-6} linenos
        ```{.python .numberLines hl_lines="2 5-6" title=renderer.py}

    Unknown attributes are intentionally preserved in ``attrs`` but ignored by
    the renderer so future syntax can be added without breaking existing input.
    """
    text = (info or "").strip()
    language = ""
    attrs = ""

    if text.startswith("{"):
        match = CODE_FENCE_BRACE_RE.match(text)
        if match:
            attrs = match.group("spec").strip()
            remainder = text[match.end() :].strip()
            if remainder:
                attrs = f"{attrs} {remainder}".strip()
            language = _first_language_class(attrs)
        else:
            attrs = text
    else:
        parts = text.split(maxsplit=1)
        if parts:
            language = _normalize_code_language(parts[0])
        attrs = parts[1] if len(parts) > 1 else ""
        brace_language = _first_language_class(attrs)
        if not language and brace_language:
            language = brace_language

    kv = _parse_code_fence_key_values(attrs)

    title = ""
    for key, value in kv.items():
        if key.lower() in CODE_FENCE_TITLE_KEYS:
            title = value
            break

    highlight_values: list[int] = []
    for brace_match in CODE_FENCE_BRACE_RE.finditer(attrs):
        spec = brace_match.group("spec")
        if re.fullmatch(r"[0-9,;\-\s]+", spec.strip()):
            highlight_values.extend(_parse_line_highlights(spec))
    for key, value in kv.items():
        if key.lower() in CODE_FENCE_HIGHLIGHT_KEYS:
            highlight_values.extend(_parse_line_highlights(value))

    attrs_lower = attrs.lower()
    linenos = bool(
        re.search(
            r"(?:^|\s)(?:linenos|line-numbers|numbered|numberlines|lineNumbers)(?:\s|$)",
            attrs,
            re.I,
        )
        or any(f".{name.lower()}" in attrs_lower for name in CODE_FENCE_LINE_NUMBER_CLASSES)
        or any(
            key.lower() in CODE_FENCE_LINE_NUMBER_KEY_SET and _truthy_attr_value(value)
            for key, value in kv.items()
        )
    )

    line_start = 1
    for key, value in kv.items():
        if key.lower() in CODE_FENCE_LINE_START_KEY_SET:
            line_start = _positive_int_attr(value, fallback=1)
            break

    return {
        "language": language,
        "title": title,
        "linenos": linenos,
        "highlight_lines": sorted(set(highlight_values)),
        "line_start": line_start,
        "attrs": attrs,
    }


def highlight_code(
    code: str,
    lang: str | None,
    attrs: str | None = None,
    *,
    code_style: str = "github-dark",
    caption: str | None = None,
    extra_classes: str = "",
    linenos: bool = False,
    highlight_lines: list[int] | None = None,
    line_start: int = 1,
) -> str:
    parts = (lang or "").strip().split()
    language = parts[0] if parts else ""
    label = language or "text"
    try:
        lexer = get_lexer_by_name(language, stripall=False) if language else TextLexer(stripall=False)
    except ClassNotFound:
        lexer = TextLexer(stripall=False)
        label = language or "text"
    normalized_highlight_lines = highlight_lines or []
    if line_start > 1 and normalized_highlight_lines and all(
        line >= line_start for line in normalized_highlight_lines
    ):
        normalized_highlight_lines = [line - line_start + 1 for line in normalized_highlight_lines]
    formatter = CodeHtmlFormatter(
        code_style,
        linenos=linenos,
        hl_lines=normalized_highlight_lines,
        line_start=line_start,
    )
    highlighted = highlight(code, lexer, formatter)
    caption_value = caption if caption not in (None, "") else label.upper()
    caption_html = (
        f'<figcaption dir="auto">{html.escape(caption_value)}</figcaption>'
        if caption_value
        else ""
    )
    line_count = max(1, len(code.rstrip("\n").splitlines()))
    extra_attrs = f" data-lang=\"{html.escape(language)}\"" if language else ""
    extra_attrs += f" data-lines=\"{line_count}\""
    if linenos and line_start > 1:
        extra_attrs += f" data-line-start=\"{line_start}\""
    classes = "code-block" + (f" {html.escape(extra_classes)}" if extra_classes else "")
    if linenos:
        classes += " code-block--numbered"
    if highlight_lines:
        classes += " code-block--highlighted"
    if line_count >= 36:
        classes += " code-block--long"
    if line_count >= 90:
        classes += " code-block--very-long"
    return (
        f'<figure class="{classes}" dir="ltr"{extra_attrs}>'
        f"{caption_html}"
        f"{highlighted}"
        f"</figure>"
    )



def mermaid_placeholder(code: str, caption: str | None = None) -> str:
    """Keep Mermaid source safe until post-processing renders it as SVG."""
    escaped = html.escape(code.rstrip("\n"))
    caption_text = html.escape((caption or "MERMAID").strip() or "MERMAID")
    return (
        '<figure class="mermaid-diagram mermaid-diagram--pending" dir="ltr">'
        f'<figcaption>{caption_text}</figcaption>'
        '<pre><code class="language-mermaid">'
        f"{escaped}"
        '</code></pre>'
        '</figure>'
    )


def is_mermaid_language(value: str | None) -> bool:
    parts = (value or "").strip().split(maxsplit=1)
    language = parts[0].lower() if parts else ""
    return language in {"mermaid", "mmd"}


def _svg_viewbox_size(svg_tag) -> tuple[float, float] | None:
    """Return SVG viewBox dimensions when they are available."""
    viewbox = svg_tag.get("viewBox") or svg_tag.get("viewbox") or ""
    parts = str(viewbox).replace(",", " ").split()
    if len(parts) != 4:
        return None
    try:
        width = float(parts[2])
        height = float(parts[3])
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def _classify_mermaid_svg(svg_tag) -> list[str]:
    """Classify generated Mermaid diagrams for print-friendly scaling."""
    size = _svg_viewbox_size(svg_tag)
    if size is None:
        return []
    width, height = size
    aspect = width / height
    classes: list[str] = []
    if aspect < 0.72 or height >= 900:
        classes.append("mermaid-diagram--tall")
    if aspect > 2.4 or width >= 1200:
        classes.append("mermaid-diagram--wide")
    return classes


def render_mermaid_placeholders(soup: BeautifulSoup) -> None:
    """Replace Mermaid placeholder code blocks with generated SVG diagrams."""
    for figure in soup.find_all("figure", class_=lambda c: c and "mermaid-diagram" in c):
        code_tag = figure.find("code", class_=lambda c: c and "language-mermaid" in c)
        if code_tag is None:
            continue
        source = code_tag.get_text()
        svg = render_mermaid_to_svg(source)
        if not svg:
            figure["class"] = list(set(figure.get("class", []) + ["mermaid-diagram--fallback"]))
            continue
        # Parse the generated SVG with the built-in HTML parser instead of
        # BeautifulSoup's ``xml`` feature. The ``xml`` feature requires lxml,
        # but lxml is intentionally not a runtime dependency for Mardas MD2PDF.
        # ``html.parser`` is enough here because the SVG is generated by our
        # own offline Mermaid renderer, and keeping this dependency-free path
        # prevents fresh editable installs from crashing on Mermaid blocks.
        fragment = BeautifulSoup(svg, "html.parser")
        svg_tag = fragment.find("svg")
        if svg_tag is None:
            continue
        for layout_class in _classify_mermaid_svg(svg_tag):
            existing = set(figure.get("class", []))
            existing.add(layout_class)
            figure["class"] = sorted(existing)
        svg_tag["preserveAspectRatio"] = "xMidYMid meet"
        pre = figure.find("pre")
        if pre is not None:
            pre.replace_with(svg_tag)
        else:
            figure.append(svg_tag)
        classes = set(figure.get("class", []))
        classes.discard("mermaid-diagram--pending")
        classes.add("mermaid-diagram--rendered")
        figure["class"] = sorted(classes)

def guess_code_language(code: str) -> tuple[str, str]:
    """Best-effort language guess for indented Markdown code blocks.

    Fenced blocks already carry their language, but many reports use 4-space
    indented blocks. markdown-it emits those as plain ``<pre><code>`` nodes,
    so we infer a readable highlighter and caption here. The heuristic is
    deliberately conservative: when unsure, it returns plain text.
    """
    stripped = code.strip("\n")
    lowered = stripped.lower()
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    first = lines[0] if lines else ""

    if not stripped:
        return "text", ""
    if "#include" in stripped or re.search(r"\bpid_t\b|\bint\s+main\s*\(", stripped):
        return "c", "C"
    if re.search(r"^\s*#\s*define\s+SYS_", stripped, re.M) or "SYSCALL(" in stripped:
        return "c", "C"
    if re.search(r"\bdef\s+\w+\s*\(|\bimport\s+\w+|\bfrom\s+\w+\s+import\b", stripped):
        return "python", "PYTHON"
    if re.search(r"\bconst\s+\w+\s*=|\blet\s+\w+\s*=|console\.log\s*\(", stripped):
        return "javascript", "JAVASCRIPT"
    if re.search(r"^\s*</?[-a-zA-Z][^>]*>\s*$", stripped, re.M):
        return "html", "HTML"
    if re.search(r"^\s*(make|gdb|qemu|cat|dice|ksort|usort|pidtest|ptest|makenums)(\s|$)", stripped, re.M):
        return "bash", "BASH"
    if re.search(r"^\s*\(gdb\)\s+", stripped, re.M):
        return "bash", "GDB"
    if first.startswith("# terminal") or "inside xv6" in lowered:
        return "bash", "BASH"
    if re.search(r"^\s*#\d+\s+\w+", stripped, re.M):
        return "text", "TRACE"
    if re.fullmatch(r"[-+*/=()0-9A-Za-z_\s.]+", stripped) and any(ch.isdigit() for ch in stripped):
        return "text", ""
    return "text", ""


def _replace_outside_inline_code(
    text: str,
    pattern: re.Pattern[str],
    repl: Any,
) -> str:
    """Apply a regex replacement only outside Markdown inline code spans.

    The Markdown parser will later turn backtick-delimited spans into ``<code>``.
    Pre-processing steps such as math and footnote expansion must therefore leave
    literal examples like ``$x$`` and ``[^note]`` untouched. This lightweight
    scanner follows the common Markdown rule that a code span opens with one or
    more backticks and closes with the same run length on the same line.
    """
    output: list[str] = []
    index = 0
    while index < len(text):
        marker_match = re.search(r"`+", text[index:])
        if not marker_match:
            output.append(pattern.sub(repl, text[index:]))
            break

        start = index + marker_match.start()
        marker = marker_match.group(0)
        output.append(pattern.sub(repl, text[index:start]))

        content_start = start + len(marker)
        close = text.find(marker, content_start)
        if close == -1:
            output.append(pattern.sub(repl, text[start:]))
            break

        output.append(text[start : close + len(marker)])
        index = close + len(marker)
    return "".join(output)


def _fence_transition(
    line: str, in_fence: bool, fence_char: str, fence_len: int
) -> tuple[bool, str, int]:
    match = FENCE_RE.match(line)
    if not match:
        return in_fence, fence_char, fence_len

    marker = match.group(1)
    marker_char = marker[0]
    marker_len = len(marker)
    if not in_fence:
        return True, marker_char, marker_len
    if marker_char == fence_char and marker_len >= fence_len:
        return False, "", 0
    return in_fence, fence_char, fence_len


def protect_and_transform_math(markdown: str) -> str:
    """Transform $...$ and $$...$$ into HTML MathJax wrappers outside code."""
    output: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    in_display_math = False
    display_buffer: list[str] = []

    def repl_inline(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        if not expr:
            return match.group(0)
        return f'<span class="math inline">\\\\({html.escape(expr)}\\\\)</span>'

    for line in markdown.splitlines(keepends=True):
        next_in_fence, next_fence_char, next_fence_len = _fence_transition(
            line, in_fence, fence_char, fence_len
        )
        fence_changed = (next_in_fence, next_fence_char, next_fence_len) != (
            in_fence,
            fence_char,
            fence_len,
        )
        if fence_changed and not in_display_math:
            in_fence, fence_char, fence_len = next_in_fence, next_fence_char, next_fence_len
            output.append(line)
            continue

        if in_fence:
            output.append(line)
            continue

        if DISPLAY_MATH_FENCE_RE.match(line):
            if in_display_math:
                expr = "".join(display_buffer).strip()
                output.append(f'<div class="math display">$${html.escape(expr)}$$</div>\n')
                display_buffer.clear()
                in_display_math = False
            else:
                in_display_math = True
                display_buffer.clear()
            continue

        if in_display_math:
            display_buffer.append(line)
            continue

        output.append(_replace_outside_inline_code(line, INLINE_MATH_RE, repl_inline))

    if in_display_math:
        output.append("$$\n")
        output.extend(display_buffer)
    return "".join(output)


def _dedent_footnote_line(line: str) -> str:
    if line.startswith("    "):
        return line[4:]
    if line.startswith("\t"):
        return line[1:]
    return line


def extract_footnotes(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """Extract Markdown footnotes, including indented multi-line bodies.

    The previous implementation only supported single-line definitions such as
    ``[^id]: text``. Standard Markdown footnotes often continue with four-space
    indented paragraphs, lists, or code. This parser keeps those continuation
    blocks together and removes them from the main document body before normal
    rendering.
    """
    lines = markdown.splitlines()
    body_lines: list[str] = []
    footnotes: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        match = FOOTNOTE_DEF_RE.match(line)
        if not match:
            body_lines.append(line)
            index += 1
            continue

        fid = match.group(1).strip()
        raw_lines = [match.group(2).strip()]
        index += 1
        while index < len(lines):
            current = lines[index]
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if FOOTNOTE_DEF_RE.match(current):
                break
            if current.startswith(("    ", "\t")):
                raw_lines.append(_dedent_footnote_line(current))
                index += 1
                continue
            if not current.strip() and (next_line.startswith(("    ", "\t")) or not next_line.strip()):
                raw_lines.append("")
                index += 1
                continue
            break
        footnote_text = "\n".join(raw_lines).strip()
        if footnote_text:
            footnotes.append((fid, footnote_text))
    return "\n".join(body_lines), footnotes


def replace_footnote_refs(markdown: str, *, lang: str | None = None, text_hint: str = "") -> str:
    label = ui_label("footnote", lang=lang, text_hint=text_hint)

    def repl(match: re.Match[str]) -> str:
        fid = html.escape(match.group(1).strip())
        return (
            f'<sup class="footnote-ref" id="fnref-{fid}">'
            f'<a href="#fn-{fid}" aria-label="{html.escape(label)} {fid}">{fid}</a></sup>'
        )

    output: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    for line in markdown.splitlines(keepends=True):
        next_in_fence, next_fence_char, next_fence_len = _fence_transition(
            line, in_fence, fence_char, fence_len
        )
        fence_changed = (next_in_fence, next_fence_char, next_fence_len) != (
            in_fence,
            fence_char,
            fence_len,
        )
        if fence_changed:
            in_fence, fence_char, fence_len = next_in_fence, next_fence_char, next_fence_len
            output.append(line)
            continue
        if in_fence:
            output.append(line)
            continue
        output.append(_replace_outside_inline_code(line, INLINE_FOOTNOTE_RE, repl))
    return "".join(output)


def append_footnotes(body_html: str, footnotes: list[tuple[str, str]], md: MarkdownIt) -> str:
    if not footnotes:
        return body_html
    items = []
    for index, (fid, raw) in enumerate(footnotes, start=1):
        safe_id = html.escape(fid)
        rendered = md.render(raw).strip()
        items.append(
            f'<li class="footnote-item" id="fn-{safe_id}">'
            f'<span class="footnote-marker" aria-hidden="true">{index}.</span>'
            f'<div class="footnote-body" dir="auto">{rendered}</div> '
            f'<a class="footnote-backref" href="#fnref-{safe_id}">↩</a></li>'
        )
    return body_html + '<section class="footnotes"><ol>' + "".join(items) + "</ol></section>"


def slugify(value: str, used: set[str]) -> str:
    value = re.sub(r"<.*?>", "", value)
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = re.sub(r"[^\w\u0600-\u06FF\-]+", "", value, flags=re.UNICODE)
    value = value.strip("-") or "section"
    base = value
    index = 2
    while value in used:
        value = f"{base}-{index}"
        index += 1
    used.add(value)
    return value


def add_heading_ids(html_text: str, *, toc_depth: int = 6) -> tuple[str, list[tuple[int, str, str, str]]]:
    used: set[str] = set()
    toc: list[tuple[int, str, str, str]] = []
    max_depth = max(1, min(int(toc_depth or 6), 6))

    def repl(match: re.Match[str]) -> str:
        level = int(match.group(1))
        attrs = match.group(2)
        content = match.group(3)
        if " id=" in attrs:
            id_match = re.search(r'id=["\']([^"\']+)["\']', attrs)
            heading_id = id_match.group(1) if id_match else slugify(content, used)
        else:
            heading_id = slugify(content, used)
            attrs += f' id="{heading_id}"'
        plain = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
        if level <= max_depth and plain:
            toc.append((level, plain, heading_id, content))
        anchor = (
            f'<a class="heading-anchor" href="#{html.escape(heading_id)}" '
            f'aria-label="Permalink to {html.escape(plain)}">#</a>'
        )
        return f"<h{level}{attrs}>{content}{anchor}</h{level}>"

    return HEADING_RE.sub(repl, html_text), toc


def _toc_tree(entries: list[tuple[int, str, str, str]]) -> list[TocItem]:
    """Build a proper nested TOC tree based on Markdown heading levels.

    The stack uses the original HTML heading level, so a skipped level such as
    h1 -> h3 is still treated as a child of the nearest previous parent. The
    displayed section number is based on the actual nesting depth in the tree,
    producing values such as 2, 2-1, 2-2 and 2-2-3.
    """
    roots: list[TocItem] = []
    stack: list[tuple[int, TocItem]] = []
    counters: list[int] = []

    for entry in entries:
        if len(entry) == 3:
            source_level, title, heading_id = entry
            title_html = html.escape(title)
        else:
            source_level, title, heading_id, title_html = entry
        while stack and stack[-1][0] >= source_level:
            stack.pop()
        depth = len(stack) + 1
        counters = counters[:depth]
        while len(counters) < depth:
            counters.append(0)
        counters[depth - 1] += 1
        number = "-".join(str(value) for value in counters)
        item = TocItem(source_level, title, heading_id, number, title_html)
        if stack:
            stack[-1][1].children.append(item)
        else:
            roots.append(item)
        stack.append((source_level, item))
    return roots


def _render_toc_items(items: list[TocItem], *, depth: int = 1) -> str:
    if not items:
        return ""
    parts = [f'<ol class="toc-list toc-depth-{depth}">']
    for item in items:
        parts.append(
            f'<li class="toc-level-{item.level}" data-level="{item.level}">' 
            f'<a href="#{html.escape(item.heading_id)}">'
            f'<span class="toc-number">{html.escape(item.number)}</span>'
            f'<span class="toc-title">{item.title_html or html.escape(item.title)}</span>'
            f'</a>'
        )
        parts.append(_render_toc_items(item.children, depth=depth + 1))
        parts.append('</li>')
    parts.append('</ol>')
    return "".join(parts)


def build_toc(
    toc: list[tuple[int, str, str, str]],
    enabled: bool,
    *,
    lang: str | None = None,
    text_hint: str = "",
) -> str:
    if not enabled or not toc:
        return ""
    tree = _toc_tree(toc)
    title = ui_label("toc_title", lang=lang, text_hint=text_hint)
    aria = ui_label("toc_aria", lang=lang, text_hint=text_hint)
    return (
        f'<nav class="md2pdf-toc" dir="auto" aria-label="{html.escape(aria)}">'
        f'<h2>{html.escape(title)}</h2>'
        f'{_render_toc_items(tree)}'
        '</nav>'
    )


def normalize_raw_code_blocks(soup: BeautifulSoup, *, code_style: str) -> None:
    """Wrap and highlight raw indented code blocks.

    markdown-it applies the custom highlighter to fenced code, but not to every
    4-space indented block. Without this pass, those blocks inherit light code
    text without the dark/bright container, which makes them nearly invisible in
    Chromium PDFs.
    """
    skip_parent_classes = {"code-block", "codehilite", "highlight"}
    for pre in list(soup.find_all("pre")):
        parents = list(pre.parents)
        if any(skip_parent_classes.intersection(set(parent.get("class", []))) for parent in parents if isinstance(parent, Tag)):
            continue
        code_tag = pre.find("code")
        code = code_tag.get_text() if code_tag else pre.get_text()
        lang, caption = guess_code_language(code)
        fragment = BeautifulSoup(
            highlight_code(
                code.rstrip("\n"),
                lang,
                code_style=code_style,
                caption=caption,
                extra_classes="raw-code-block",
            ),
            "html.parser",
        )
        figure = fragment.find("figure")
        if figure is not None:
            pre.replace_with(figure)


def _is_path_inside(path: Path, root: Path) -> bool:
    """Return whether a possibly symlinked path stays under the document root."""
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _local_image_candidates(src: str, base_dir: Path) -> list[Path]:
    """Return safe local filesystem candidates for an image src.

    Markdown image paths are treated as document-local assets. Remote URLs and
    existing data URIs are intentionally left untouched, while absolute paths,
    ``file:`` URLs, and parent-directory escapes are ignored so a Markdown file
    cannot silently embed arbitrary files from the host machine.
    """
    parsed = urlparse(src.strip())
    if parsed.scheme in {"http", "https", "data", "mailto"}:
        return []
    if parsed.scheme:
        return []

    clean_src = unquote(src.split("#", 1)[0].split("?", 1)[0]).strip()
    if not clean_src:
        return []

    raw_path = Path(clean_src)
    if raw_path.is_absolute():
        return []

    base_dir = base_dir.resolve(strict=False)
    candidates = [base_dir / raw_path]

    # A common authoring mistake is to keep the Markdown reference as
    # images/foo.png while exporting or copying foo.png beside the Markdown file.
    # Falling back to the basename keeps the converter forgiving while still
    # limiting all lookups to the Markdown document directory.
    if len(raw_path.parts) > 1:
        candidates.append(base_dir / raw_path.name)

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not _is_path_inside(candidate, base_dir):
            continue
        key = str(candidate.resolve(strict=False))
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _image_file_to_data_uri(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    mime_type = mimetypes.guess_type(str(path))[0] or "image/png"
    if not mime_type.startswith("image/"):
        return None
    size = path.stat().st_size
    if size > MAX_EMBED_IMAGE_BYTES:
        warnings.warn(
            f"Skipping image larger than {MAX_EMBED_IMAGE_BYTES} bytes: {path}",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _has_url_control_chars(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _is_safe_data_image_url(value: str) -> bool:
    if not value.lower().startswith("data:") or "," not in value:
        return False
    header = value[5:].split(",", 1)[0].strip().lower()
    media_type = header.split(";", 1)[0].strip()
    return media_type in SAFE_DATA_IMAGE_MIME_TYPES


def _is_safe_url(value: str) -> bool:
    raw_value = str(value or "").strip()
    if _has_url_control_chars(raw_value):
        return False
    parsed = urlparse(raw_value)
    scheme = parsed.scheme.lower()
    if scheme not in SAFE_URL_SCHEMES:
        return False
    if scheme == "data":
        return _is_safe_data_image_url(raw_value)
    return True


def sanitize_html(body_html: str) -> str:
    """Keep a safe, document-oriented subset of raw HTML.

    Markdown authors can still use useful HTML such as ``<img>`` and explicit
    page-break ``<div>`` markers. Active content and event handlers are removed
    before the HTML is handed to Chromium.
    """
    soup = BeautifulSoup(body_html, "html.parser")
    for tag in list(soup.find_all(True)):
        name = (tag.name or "").lower()
        if name in BLOCKED_RAW_HTML_TAGS:
            tag.decompose()
            continue
        if name not in SAFE_RAW_HTML_TAGS:
            tag.unwrap()
            continue

        allowed = GLOBAL_SAFE_ATTRS | TAG_SAFE_ATTRS.get(name, set())
        for attr in list(tag.attrs):
            lower_attr = attr.lower()
            if lower_attr.startswith("on") or lower_attr == "style" or lower_attr not in allowed:
                del tag.attrs[attr]
                continue
            value = tag.attrs.get(attr)
            if lower_attr in {"href", "src"}:
                values = value if isinstance(value, list) else [str(value)]
                if not values or any(not _is_safe_url(str(item)) for item in values):
                    del tag.attrs[attr]
            elif lower_attr in {"target", "rel"}:
                if name != "a":
                    del tag.attrs[attr]
        if name == "a" and tag.get("target") == "_blank":
            rel = set(str(tag.get("rel") or "").split())
            rel.update({"noopener", "noreferrer"})
            tag["rel"] = " ".join(sorted(rel))
    return str(soup)


def _is_local_image_reference(src: str) -> bool:
    """Return whether an image source would ask Chromium to read local files."""
    parsed = urlparse(src.strip())
    if parsed.scheme.lower() in {"http", "https", "data", "mailto"}:
        return False
    return True


def _is_remote_image_reference(src: str) -> bool:
    return urlparse(src.strip()).scheme.lower() in {"http", "https"}


def _short_blocked_image_source(src: str, *, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(src or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _block_image_reference(soup: BeautifulSoup, img: Tag, src: str, *, reason: str) -> None:
    """Prevent Chromium from resolving an image source outside the asset boundary."""
    label = "Remote image blocked" if reason == "remote" else "Image blocked or missing"
    detail = _short_blocked_image_source(src)

    placeholder = soup.new_tag("span")
    placeholder["class"] = "md2pdf-image-placeholder md2pdf-image--blocked"
    placeholder["role"] = "note"
    placeholder["data-md2pdf-blocked-src"] = src
    placeholder["data-md2pdf-blocked-reason"] = reason

    title = soup.new_tag("strong")
    title.string = label
    placeholder.append(title)
    if detail:
        body = soup.new_tag("span")
        body.string = detail
        placeholder.append(body)

    img.replace_with(placeholder)


def embed_local_images(body_html: str, base_dir: str | Path, *, allow_remote_images: bool = False) -> str:
    """Inline document-local images and block unsafe unresolved image reads.

    Chromium can render relative image paths when every asset is present beside
    the Markdown file. In practice, reports are often copied without their
    ``images/`` directory, or generated from a temporary working directory. This
    pass resolves local ``<img src=...>`` values against the Markdown location and
    embeds the image bytes directly into the HTML, so the PDF no longer depends
    on external files during the print step.

    If a local image source cannot be embedded safely, it is replaced with a
    transparent placeholder. This keeps the renderer from falling back to the
    document ``<base>`` URL and reading parent-directory or absolute paths during
    Chromium's print step. Remote URLs are blocked by default for privacy and can
    be allowed explicitly by trusted callers. Existing data URIs are left unchanged.
    """
    soup = BeautifulSoup(body_html, "html.parser")
    root = Path(base_dir)
    for img in soup.find_all("img"):
        src = str(img.get("src") or "").strip()
        if not src:
            continue
        embedded = False
        for candidate in _local_image_candidates(src, root):
            data_uri = _image_file_to_data_uri(candidate)
            if not data_uri:
                continue
            img["src"] = data_uri
            img["data-md2pdf-source"] = src
            img["class"] = list(set(img.get("class", []) + ["md2pdf-image"]))
            embedded = True
            break
        if not embedded and _is_local_image_reference(src):
            _block_image_reference(soup, img, src, reason="local")
        elif not allow_remote_images and _is_remote_image_reference(src):
            _block_image_reference(soup, img, src, reason="remote")
    return str(soup)


AUTOLINK_RE = re.compile(
    r"(?P<url>https?://[^\s<]+|www\.[^\s<]+)|(?P<email>[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})"
)
AUTOLINK_SKIP_PARENTS = {"a", "code", "pre", "script", "style", "kbd"}


def apply_literal_autolinks(soup: BeautifulSoup) -> None:
    """Link bare URLs, www-prefixed domains, and email addresses outside code."""
    for node in list(soup.find_all(string=True)):
        text = str(node)
        if not text or not AUTOLINK_RE.search(text):
            continue
        if any(parent.name in AUTOLINK_SKIP_PARENTS for parent in node.parents if isinstance(parent, Tag)):
            continue
        fragment = soup.new_tag("span")
        pos = 0
        for match in AUTOLINK_RE.finditer(text):
            if match.start() > pos:
                fragment.append(NavigableString(text[pos : match.start()]))
            label = match.group(0).rstrip('.,);:!?')
            trailing = match.group(0)[len(label):]
            href = label
            if match.group("email"):
                href = f"mailto:{label}"
            elif label.startswith("www."):
                href = f"https://{label}"
            link = soup.new_tag("a", href=href)
            link.string = label
            fragment.append(link)
            if trailing:
                fragment.append(NavigableString(trailing))
            pos = match.end()
        if pos < len(text):
            fragment.append(NavigableString(text[pos:]))
        node.replace_with(fragment)
        fragment.unwrap()


def promote_image_caption_pairs(soup: BeautifulSoup) -> None:
    """Turn common Markdown image-caption pairs into semantic figures.

    Markdown has no official caption syntax, but documentation often uses::

        ![Architecture](arch.png)
        *Figure 1. Architecture overview.*

    This pass preserves normal paragraphs while giving the PDF renderer a proper
    ``<figure>`` / ``<figcaption>`` structure when the pattern is unambiguous.
    """
    for paragraph in list(soup.find_all("p")):
        images = paragraph.find_all("img", recursive=False)
        if len(images) != 1:
            continue
        meaningful_text = paragraph.get_text("", strip=True)
        if meaningful_text:
            continue
        next_sibling = paragraph.find_next_sibling()
        caption_html = ""
        if (
            isinstance(next_sibling, Tag)
            and next_sibling.name == "p"
            and len(next_sibling.contents) == 1
            and isinstance(next_sibling.contents[0], Tag)
            and next_sibling.contents[0].name in {"em", "strong"}
        ):
            caption_text = next_sibling.get_text(" ", strip=True)
            if re.match(r"^(figure|fig\.|شکل|تصویر)\b", caption_text, re.I):
                caption_html = str(next_sibling.contents[0])
                next_sibling.decompose()
        figure = soup.new_tag("figure")
        figure["class"] = "md2pdf-figure"
        figure["dir"] = "auto"
        paragraph.replace_with(figure)
        figure.append(images[0].extract())
        if caption_html:
            caption = soup.new_tag("figcaption")
            caption.append(BeautifulSoup(caption_html, "html.parser"))
            figure.append(caption)




def _table_column_count(table: Tag) -> int:
    """Return the widest row width, honoring simple colspan values."""
    max_columns = 0
    for row in table.find_all("tr"):
        columns = 0
        for cell in row.find_all(["th", "td"], recursive=False):
            try:
                colspan = int(str(cell.get("colspan") or "1"))
            except ValueError:
                colspan = 1
            columns += max(1, colspan)
        max_columns = max(max_columns, columns)
    return max_columns


def _table_row_count(table: Tag) -> int:
    """Return the number of rendered rows for print-flow hints."""
    return len(table.find_all("tr"))

def postprocess_html(body_html: str, *, code_style: str = "github-dark", lang: str | None = None) -> str:
    soup = BeautifulSoup(body_html, "html.parser")

    promote_image_caption_pairs(soup)
    render_mermaid_placeholders(soup)
    apply_literal_autolinks(soup)
    normalize_raw_code_blocks(soup, code_style=code_style)

    # Direction-aware blocks and inline content.
    for tag in soup.find_all(["p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "figcaption"]):
        if tag.get("dir"):
            continue
        if "footnote-item" in tag.get("class", []):
            continue
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        tag["dir"] = "auto"
        if has_persian(text) and has_latin(text):
            tag["class"] = list(set(tag.get("class", []) + ["mixed-script"]))

    # Make code and pre blocks strictly LTR.
    for tag in soup.find_all(["pre", "code"]):
        tag["dir"] = "ltr"

    # Wrap tables for visual polish and safe overflow.
    for table in soup.find_all("table"):
        if table.parent and getattr(table.parent, "name", None) == "div" and "table-wrap" in table.parent.get("class", []):
            continue
        columns = _table_column_count(table)
        rows = _table_row_count(table)
        classes = ["table-wrap"]
        if columns >= 8:
            classes.append("table-wrap--wide")
        if columns >= 12:
            classes.append("table-wrap--very-wide")
        if rows >= 18:
            classes.append("table-wrap--long")
        wrapper = soup.new_tag("div")
        wrapper["class"] = classes
        wrapper["dir"] = "auto"
        if columns:
            wrapper["data-md2pdf-columns"] = str(columns)
        if rows:
            wrapper["data-md2pdf-rows"] = str(rows)
        table.wrap(wrapper)

    # GitHub-style task lists.
    for li in soup.find_all("li"):
        first_text = None
        for child in li.children:
            if isinstance(child, NavigableString) and child.strip():
                first_text = child
                break
        if first_text is None:
            continue
        text = str(first_text)
        match = re.match(r"^(\s*)\[( |x|X)\]\s+", text)
        if not match:
            continue
        checked = match.group(2).lower() == "x"
        checkbox = soup.new_tag("input", type="checkbox")
        if checked:
            checkbox["checked"] = "checked"
        checkbox["disabled"] = "disabled"
        li.insert(0, checkbox)
        first_text.replace_with(text[match.end() :])
        li["class"] = list(set(li.get("class", []) + ["task-list-item"]))
        if li.parent and li.parent.name in {"ul", "ol"}:
            li.parent["class"] = list(set(li.parent.get("class", []) + ["task-list"]))

    # Obsidian/GitHub flavored callouts: > [!NOTE], > [!TIP] Title, > [!NOTE]-
    text_hint = soup.get_text(" ", strip=True)
    callout_kind_aliases = {
        "NOTE": "note",
        "INFO": "info",
        "TODO": "info",
        "TIP": "tip",
        "HINT": "tip",
        "IMPORTANT": "important",
        "WARNING": "warning",
        "WARN": "warning",
        "CAUTION": "caution",
        "ATTENTION": "caution",
        "SUCCESS": "success",
        "CHECK": "success",
        "DONE": "success",
        "QUESTION": "question",
        "HELP": "question",
        "FAQ": "question",
        "FAILURE": "failure",
        "FAIL": "failure",
        "MISSING": "failure",
        "DANGER": "danger",
        "ERROR": "danger",
        "BUG": "bug",
        "EXAMPLE": "example",
        "QUOTE": "quote",
        "CITE": "quote",
        "ABSTRACT": "abstract",
        "SUMMARY": "abstract",
        "TLDR": "abstract",
    }
    callout_titles = {
        canonical: ui_label(f"callout_{canonical}", lang=lang, text_hint=text_hint)
        for canonical in sorted(set(callout_kind_aliases.values()))
    }
    callout_re = re.compile(
        r"^\[!(?P<kind>[A-Z][A-Z0-9_-]*)\](?P<fold>[+-])?\s*(?P<title>.*)$",
        re.I,
    )
    for blockquote in soup.find_all("blockquote"):
        first_p = blockquote.find("p")
        if not first_p:
            continue
        text = first_p.get_text("\n", strip=True)
        first_line, _, remainder = text.partition("\n")
        match = callout_re.match(first_line.strip())
        if not match:
            continue
        raw_kind = match.group("kind").upper().replace("-", "_")
        canonical = callout_kind_aliases.get(raw_kind)
        if not canonical:
            continue
        custom_title = match.group("title").strip()
        classes = set(blockquote.get("class", []))
        classes.update({"callout", f"callout-{canonical}"})
        if match.group("fold"):
            classes.add("callout-foldable")
        blockquote["class"] = sorted(classes)
        title_tag = soup.new_tag("strong")
        title_tag["class"] = "callout-title"
        title_tag.string = custom_title or callout_titles.get(canonical, canonical.title())
        first_p.clear()
        first_p.append(title_tag)
        if remainder.strip():
            first_p.append("\n" + remainder.strip())

    # Explicit page break marker: <div class="page-break"></div> or ---page---
    for div in soup.find_all("div", class_=lambda c: c and "page-break" in c):
        div["class"] = list(set(div.get("class", []) + ["md2pdf-page-break"]))

    # Render HTML details/summary as expanded PDF-friendly disclosure blocks.
    for details in soup.find_all("details"):
        details["open"] = "open"
        details["class"] = list(set(details.get("class", []) + ["md2pdf-details"]))
        summary = details.find("summary")
        if summary is not None:
            summary["class"] = list(set(summary.get("class", []) + ["md2pdf-summary"]))

    return str(soup)


PAGEBREAK_COMMENT_RE = re.compile(r"<!--\s*(?:pagebreak|page-break|newpage)\s*-->", re.I)
PAGEBREAK_CONTAINER_LINE_RE = re.compile(r"^:::\s*(?:pagebreak|page-break|newpage)\s*$", re.I)
PAGEBREAK_CONTAINER_CLOSE_RE = re.compile(r"^:::\s*$")
PAGEBREAK_MARKER_LINE_RE = re.compile(r"^---page---$", re.I)


def _line_ending(line: str) -> str:
    return "\n" if line.endswith("\n") else ""


def preprocess_pdf_directives(markdown: str) -> str:
    """Normalize lightweight PDF layout directives outside Markdown code fences.

    Documentation often needs to show the directive syntax inside fenced code
    blocks. A line-aware pass keeps those examples literal while still allowing
    authors to place page breaks in the real document body.
    """
    output: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    lines = markdown.splitlines(keepends=True)
    i = 0

    while i < len(lines):
        line = lines[i]
        next_in_fence, next_fence_char, next_fence_len = _fence_transition(
            line, in_fence, fence_char, fence_len
        )
        fence_changed = (next_in_fence, next_fence_char, next_fence_len) != (
            in_fence,
            fence_char,
            fence_len,
        )

        if fence_changed:
            in_fence, fence_char, fence_len = next_in_fence, next_fence_char, next_fence_len
            output.append(line)
            i += 1
            continue

        if in_fence:
            output.append(line)
            i += 1
            continue

        stripped = line.strip()
        ending = _line_ending(line)

        if PAGEBREAK_MARKER_LINE_RE.match(stripped):
            output.append(f'<div class="md2pdf-page-break"></div>{ending}')
            i += 1
            continue

        if PAGEBREAK_COMMENT_RE.fullmatch(stripped):
            output.append(f'<div class="md2pdf-page-break"></div>{ending}')
            i += 1
            continue

        if PAGEBREAK_CONTAINER_LINE_RE.match(stripped):
            if i + 1 < len(lines) and PAGEBREAK_CONTAINER_CLOSE_RE.match(lines[i + 1].strip()):
                output.append(f'<div class="md2pdf-page-break"></div>{ending}')
                i += 2
                continue

        output.append(PAGEBREAK_COMMENT_RE.sub('<div class="md2pdf-page-break"></div>', line))
        i += 1

    return "".join(output)


def render_markdown(
    markdown: str,
    *,
    toc: bool = False,
    toc_depth: int = 6,
    code_style: str = "github-dark",
    unsafe_html: bool = False,
    allow_remote_images: bool = False,
) -> MarkdownRenderResult:
    metadata, markdown_body = extract_frontmatter(markdown)
    title = guess_title(markdown_body, metadata)
    lang = normalize_language(metadata.get("lang"), "auto")

    markdown_body = preprocess_pdf_directives(markdown_body)
    markdown_body, footnotes = extract_footnotes(markdown_body)
    markdown_body = replace_footnote_refs(markdown_body, lang=lang, text_hint=markdown_body)
    markdown_body = protect_and_transform_math(markdown_body)

    md = MarkdownIt(
        "gfm-like",
        {
            "html": True,
            "linkify": False,
            "typographer": True,
        },
    )
    md.enable(["table", "strikethrough"])

    def render_fence(tokens: list[Any], idx: int, options: dict[str, Any], env: dict[str, Any]) -> str:
        """Render fenced code blocks as complete figures, not nested inside <pre><code>.

        markdown-it wraps custom highlighter output unless it starts with <pre>. Our
        highlighter returns a semantic <figure> with a separate language caption, so
        using a renderer rule prevents invalid <pre><code><figure> nesting. That
        nesting used to be normalized later as raw text and could turn ```c into
        a literal leading "C" inside the code content.
        """
        token = tokens[idx]
        fence_info = parse_code_fence_info(token.info)
        lang = fence_info["language"]
        if is_mermaid_language(lang):
            return mermaid_placeholder(token.content, fence_info["title"] or None) + "\n"
        return highlight_code(
            token.content,
            lang,
            fence_info["attrs"],
            code_style=code_style,
            caption=fence_info["title"] or None,
            linenos=bool(fence_info["linenos"]),
            highlight_lines=fence_info["highlight_lines"],
            line_start=int(fence_info.get("line_start") or 1),
        ) + "\n"

    md.renderer.rules["fence"] = render_fence

    body_html = md.render(markdown_body)
    body_html = append_footnotes(body_html, footnotes, md)
    if not unsafe_html:
        body_html = sanitize_html(body_html)
    body_html, toc_entries = add_heading_ids(body_html, toc_depth=toc_depth)
    text_hint = BeautifulSoup(body_html, "html.parser").get_text(" ", strip=True)
    toc_html = build_toc(toc_entries, toc, lang=lang, text_hint=text_hint)
    body_html = postprocess_html(body_html, code_style=code_style, lang=lang)

    formatter = CodeHtmlFormatter(code_style)
    pygments_css = formatter.get_style_defs(".codehilite")
    return MarkdownRenderResult(
        body_html=body_html,
        metadata=metadata,
        title=title,
        pygments_css=pygments_css,
        toc_html=toc_html,
        toc_entries=toc_entries,
    )


def render_markdown_file(
    path: str | Path,
    *,
    toc: bool = False,
    toc_depth: int = 6,
    code_style: str = "github-dark",
    unsafe_html: bool = False,
    allow_remote_images: bool = False,
) -> MarkdownRenderResult:
    input_path = Path(path)
    text = input_path.read_text(encoding="utf-8")
    result = render_markdown(
        text,
        toc=toc,
        toc_depth=toc_depth,
        code_style=code_style,
        unsafe_html=unsafe_html,
    )
    result.body_html = embed_local_images(
        result.body_html,
        input_path.resolve().parent,
        allow_remote_images=allow_remote_images,
    )
    return result
