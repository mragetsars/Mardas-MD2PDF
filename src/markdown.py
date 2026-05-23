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
GLOBAL_SAFE_ATTRS = {"class", "id", "dir", "lang", "title", "role", "aria-label"}
TAG_SAFE_ATTRS = {
    "a": {"href", "name", "target", "rel"},
    "img": {"src", "alt", "width", "height"},
    "th": {"align", "colspan", "rowspan", "scope"},
    "td": {"align", "colspan", "rowspan"},
    "ol": {"start", "type"},
    "ul": {"type"},
    "code": {"class"},
}
SAFE_URL_SCHEMES = {"", "http", "https", "mailto", "file", "data"}
MAX_EMBED_IMAGE_BYTES = 20 * 1024 * 1024
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


@dataclass(slots=True)
class TocItem:
    level: int
    title: str
    heading_id: str
    number: str
    title_html: str = ""
    children: list["TocItem"] = field(default_factory=list)


class CodeHtmlFormatter(HtmlFormatter):
    """Pygments formatter. The style is selected by the renderer theme."""

    def __init__(
        self,
        style: str = "github-dark",
        *,
        linenos: bool = False,
        hl_lines: list[int] | None = None,
    ) -> None:
        super().__init__(
            style=style,
            cssclass="codehilite",
            nowrap=False,
            linenos="table" if linenos else False,
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
CODE_FENCE_BRACE_RE = re.compile(r"\{(?P<spec>[0-9,\-\s]+)\}")


def _parse_line_highlights(spec: str | None) -> list[int]:
    if not spec:
        return []
    values: set[int] = set()
    for part in spec.split(','):
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


def parse_code_fence_info(info: str | None) -> dict[str, Any]:
    """Parse GitHub/documentation-style fenced code metadata."""
    text = (info or "").strip()
    parts = text.split(maxsplit=1)
    language = parts[0] if parts else ""
    attrs = parts[1] if len(parts) > 1 else ""

    title_match = CODE_FENCE_TITLE_RE.search(attrs)
    title = title_match.group('value').strip() if title_match else ""

    brace_match = CODE_FENCE_BRACE_RE.search(attrs)
    highlight_lines = _parse_line_highlights(brace_match.group('spec') if brace_match else None)
    linenos = bool(re.search(r"(?:^|\s)(?:linenos|line-numbers|numbered)(?:\s|$)", attrs, re.I))
    return {
        "language": language,
        "title": title,
        "linenos": linenos,
        "highlight_lines": highlight_lines,
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
) -> str:
    parts = (lang or "").strip().split()
    language = parts[0] if parts else ""
    label = language or "text"
    try:
        lexer = get_lexer_by_name(language, stripall=False) if language else TextLexer(stripall=False)
    except ClassNotFound:
        lexer = TextLexer(stripall=False)
        label = language or "text"
    formatter = CodeHtmlFormatter(code_style, linenos=linenos, hl_lines=highlight_lines)
    highlighted = highlight(code, lexer, formatter)
    caption_value = caption if caption not in (None, "") else label.upper()
    caption_html = (
        f'<figcaption dir="auto">{html.escape(caption_value)}</figcaption>'
        if caption_value
        else ""
    )
    extra_attrs = f" data-lang=\"{html.escape(language)}\"" if language else ""
    classes = "code-block" + (f" {html.escape(extra_classes)}" if extra_classes else "")
    if linenos:
        classes += " code-block--numbered"
    if highlight_lines:
        classes += " code-block--highlighted"
    return (
        f'<figure class="{classes}" dir="ltr"{extra_attrs}>'
        f"{caption_html}"
        f"{highlighted}"
        f"</figure>"
    )



def mermaid_placeholder(code: str) -> str:
    """Keep Mermaid source safe until post-processing renders it as SVG."""
    escaped = html.escape(code.rstrip("\n"))
    return (
        '<figure class="mermaid-diagram mermaid-diagram--pending" dir="ltr">'
        '<figcaption>MERMAID</figcaption>'
        '<pre><code class="language-mermaid">'
        f"{escaped}"
        '</code></pre>'
        '</figure>'
    )


def is_mermaid_language(value: str | None) -> bool:
    parts = (value or "").strip().split(maxsplit=1)
    language = parts[0].lower() if parts else ""
    return language in {"mermaid", "mmd"}


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
        fragment = BeautifulSoup(svg, "xml")
        svg_tag = fragment.find("svg")
        if svg_tag is None:
            continue
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
                output.append(f'<div class="math display">\\\\[{html.escape(expr)}\\\\]</div>\n')
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


def _local_image_candidates(src: str, base_dir: Path) -> list[Path]:
    """Return likely local filesystem candidates for an image src."""
    parsed = urlparse(src)
    if parsed.scheme in {"http", "https", "data", "mailto"}:
        return []
    if parsed.scheme == "file":
        return [Path(unquote(parsed.path))]
    if parsed.scheme:
        return []

    clean_src = unquote(src.split("#", 1)[0].split("?", 1)[0]).strip()
    if not clean_src:
        return []

    raw_path = Path(clean_src)
    if raw_path.is_absolute():
        return [raw_path]

    base_dir = base_dir.resolve()
    candidates = [base_dir / raw_path]

    # A common authoring mistake is to keep the Markdown reference as
    # images/foo.png while exporting or copying foo.png beside the Markdown file.
    # Falling back to the basename makes the converter forgiving without changing
    # valid paths that already exist.
    if len(raw_path.parts) > 1:
        candidates.append(base_dir / raw_path.name)

    # If the current working directory contains the referenced asset, keep that
    # as a final fallback for scripts that launch the CLI from the project root.
    candidates.append(Path.cwd() / raw_path)
    if len(raw_path.parts) > 1:
        candidates.append(Path.cwd() / raw_path.name)

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
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


def _is_safe_url(value: str) -> bool:
    parsed = urlparse((value or "").strip())
    if parsed.scheme.lower() not in SAFE_URL_SCHEMES:
        return False
    if parsed.scheme.lower() == "data":
        return value.lower().startswith("data:image/")
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


def embed_local_images(body_html: str, base_dir: str | Path) -> str:
    """Inline local images as data URIs for reliable Chromium PDF rendering.

    Chromium can render relative image paths when every asset is present beside
    the Markdown file. In practice, reports are often copied without their
    ``images/`` directory, or generated from a temporary working directory. This
    pass resolves local ``<img src=...>`` values against the Markdown location and
    embeds the image bytes directly into the HTML, so the PDF no longer depends
    on external files during the print step. Remote URLs and existing data URIs
    are left unchanged.
    """
    soup = BeautifulSoup(body_html, "html.parser")
    root = Path(base_dir)
    for img in soup.find_all("img"):
        src = str(img.get("src") or "").strip()
        if not src:
            continue
        for candidate in _local_image_candidates(src, root):
            data_uri = _image_file_to_data_uri(candidate)
            if not data_uri:
                continue
            img["src"] = data_uri
            img["data-md2pdf-source"] = src
            img["class"] = list(set(img.get("class", []) + ["md2pdf-image"]))
            break
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
        wrapper = soup.new_tag("div")
        wrapper["class"] = "table-wrap"
        wrapper["dir"] = "auto"
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

    # Obsidian/GitHub flavored callouts: > [!NOTE]
    text_hint = soup.get_text(" ", strip=True)
    callout_titles = {
        "NOTE": ui_label("callout_note", lang=lang, text_hint=text_hint),
        "TIP": ui_label("callout_tip", lang=lang, text_hint=text_hint),
        "IMPORTANT": ui_label("callout_important", lang=lang, text_hint=text_hint),
        "WARNING": ui_label("callout_warning", lang=lang, text_hint=text_hint),
        "CAUTION": ui_label("callout_caution", lang=lang, text_hint=text_hint),
    }
    for blockquote in soup.find_all("blockquote"):
        first_p = blockquote.find("p")
        if not first_p:
            continue
        text = first_p.get_text(" ", strip=True)
        match = re.match(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$", text, re.I)
        if not match:
            continue
        kind = match.group(1).upper()
        rest = match.group(2).strip()
        blockquote["class"] = list(set(blockquote.get("class", []) + ["callout", f"callout-{kind.lower()}"]))
        title_tag = soup.new_tag("strong")
        title_tag["class"] = "callout-title"
        title_tag.string = callout_titles.get(kind, kind)
        first_p.clear()
        first_p.append(title_tag)
        if rest:
            first_p.append(" " + rest)

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
PAGEBREAK_CONTAINER_RE = re.compile(r"^:::\s*(?:pagebreak|page-break|newpage)\s*\n:::\s*$", re.I | re.M)


def preprocess_pdf_directives(markdown: str) -> str:
    """Normalize lightweight PDF layout directives before Markdown parsing."""
    markdown = PAGEBREAK_COMMENT_RE.sub('<div class="md2pdf-page-break"></div>', markdown)
    markdown = PAGEBREAK_CONTAINER_RE.sub('<div class="md2pdf-page-break"></div>', markdown)
    markdown = markdown.replace("\n---page---\n", '\n<div class="md2pdf-page-break"></div>\n')
    return markdown


def render_markdown(
    markdown: str,
    *,
    toc: bool = False,
    toc_depth: int = 6,
    code_style: str = "github-dark",
    unsafe_html: bool = False,
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
            return mermaid_placeholder(token.content) + "\n"
        return highlight_code(
            token.content,
            lang,
            fence_info["attrs"],
            code_style=code_style,
            caption=fence_info["title"] or None,
            linenos=bool(fence_info["linenos"]),
            highlight_lines=fence_info["highlight_lines"],
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
    )


def render_markdown_file(
    path: str | Path,
    *,
    toc: bool = False,
    toc_depth: int = 6,
    code_style: str = "github-dark",
    unsafe_html: bool = False,
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
    result.body_html = embed_local_images(result.body_html, input_path.resolve().parent)
    return result
