from __future__ import annotations

import html
import re
import unicodedata
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

ARABIC_RANGES = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_RANGES = re.compile(r"[A-Za-z]")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
INLINE_FOOTNOTE_RE = re.compile(r"\[\^([^\]]+)\]")
INLINE_MATH_RE = re.compile(r"(?<!\\)\$(?![\s$])(.+?)(?<!\\)\$(?!\d)")
DISPLAY_MATH_FENCE_RE = re.compile(r"^\s*\$\$\s*$")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
HEADING_RE = re.compile(r"<h([1-6])([^>]*)>(.*?)</h\1>", re.DOTALL | re.IGNORECASE)


@dataclass(slots=True)
class MarkdownRenderResult:
    body_html: str
    metadata: dict[str, Any] = field(default_factory=dict)
    title: str = "Document"
    pygments_css: str = ""
    toc_html: str = ""


class CodeHtmlFormatter(HtmlFormatter):
    """Pygments formatter. The style is selected by the renderer theme."""

    def __init__(self, style: str = "github-dark") -> None:
        super().__init__(
            style=style,
            cssclass="codehilite",
            nowrap=False,
            linenos=False,
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


def highlight_code(
    code: str,
    lang: str | None,
    attrs: str | None = None,
    *,
    code_style: str = "github-dark",
    caption: str | None = None,
    extra_classes: str = "",
) -> str:
    language = (lang or "").strip().split()[0]
    label = language or "text"
    try:
        lexer = get_lexer_by_name(language, stripall=False) if language else TextLexer(stripall=False)
    except ClassNotFound:
        lexer = TextLexer(stripall=False)
        label = language or "text"
    formatter = CodeHtmlFormatter(code_style)
    highlighted = highlight(code, lexer, formatter)
    caption_value = label.upper() if caption is None else caption
    caption_html = f"<figcaption>{html.escape(caption_value)}</figcaption>" if caption_value else ""
    extra_attrs = f" data-lang=\"{html.escape(language)}\"" if language else ""
    classes = "code-block" + (f" {html.escape(extra_classes)}" if extra_classes else "")
    return (
        f'<figure class="{classes}" dir="ltr"{extra_attrs}>'
        f"{caption_html}"
        f"{highlighted}"
        f"</figure>"
    )


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


def protect_and_transform_math(markdown: str) -> str:
    """Transform $...$ and $$...$$ into HTML MathJax wrappers outside code fences."""
    output: list[str] = []
    in_fence = False
    fence_marker = ""
    in_display_math = False
    display_buffer: list[str] = []

    for line in markdown.splitlines(keepends=True):
        fence_match = FENCE_RE.match(line)
        if fence_match and not in_display_math:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker[0]
            elif marker.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            output.append(line)
            continue

        if in_fence:
            output.append(line)
            continue

        if DISPLAY_MATH_FENCE_RE.match(line):
            if in_display_math:
                expr = "".join(display_buffer).strip()
                output.append(f'<div class="math display">\\[{html.escape(expr)}\\]</div>\n')
                display_buffer.clear()
                in_display_math = False
            else:
                in_display_math = True
                display_buffer.clear()
            continue

        if in_display_math:
            display_buffer.append(line)
            continue

        def repl_inline(match: re.Match[str]) -> str:
            expr = match.group(1).strip()
            if not expr:
                return match.group(0)
            return f'<span class="math inline">\\({html.escape(expr)}\\)</span>'

        output.append(INLINE_MATH_RE.sub(repl_inline, line))

    if in_display_math:
        output.append("$$\n")
        output.extend(display_buffer)
    return "".join(output)


def extract_footnotes(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    lines = markdown.splitlines()
    body_lines: list[str] = []
    footnotes: list[tuple[str, str]] = []
    for line in lines:
        match = FOOTNOTE_DEF_RE.match(line)
        if match:
            footnotes.append((match.group(1).strip(), match.group(2).strip()))
        else:
            body_lines.append(line)
    return "\n".join(body_lines), footnotes


def replace_footnote_refs(markdown: str) -> str:
    def repl(match: re.Match[str]) -> str:
        fid = html.escape(match.group(1).strip())
        return (
            f'<sup class="footnote-ref" id="fnref-{fid}">'
            f'<a href="#fn-{fid}" aria-label="Footnote {fid}">{fid}</a></sup>'
        )

    return INLINE_FOOTNOTE_RE.sub(repl, markdown)


def append_footnotes(body_html: str, footnotes: list[tuple[str, str]], md: MarkdownIt) -> str:
    if not footnotes:
        return body_html
    items = []
    for fid, raw in footnotes:
        safe_id = html.escape(fid)
        rendered = md.renderInline(raw)
        items.append(
            f'<li id="fn-{safe_id}" dir="auto">{rendered} '
            f'<a class="footnote-backref" href="#fnref-{safe_id}">↩</a></li>'
        )
    return body_html + '<section class="footnotes" dir="auto"><ol>' + "".join(items) + "</ol></section>"


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


def add_heading_ids(html_text: str) -> tuple[str, list[tuple[int, str, str]]]:
    used: set[str] = set()
    toc: list[tuple[int, str, str]] = []

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
        if level <= 3:
            toc.append((level, plain, heading_id))
        return f"<h{level}{attrs}>{content}</h{level}>"

    return HEADING_RE.sub(repl, html_text), toc


def build_toc(toc: list[tuple[int, str, str]], enabled: bool) -> str:
    if not enabled or not toc:
        return ""
    items = []
    for level, title, heading_id in toc:
        indent_class = f" toc-level-{level}"
        items.append(
            f'<li class="{indent_class.strip()}"><a href="#{html.escape(heading_id)}">'
            f"{html.escape(title)}</a></li>"
        )
    return '<nav class="md2pdf-toc" dir="auto"><h2>فهرست مطالب</h2><ol>' + "".join(items) + "</ol></nav>"


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


def postprocess_html(body_html: str, *, code_style: str = "github-dark") -> str:
    soup = BeautifulSoup(body_html, "html.parser")

    normalize_raw_code_blocks(soup, code_style=code_style)

    # Direction-aware blocks and inline content.
    for tag in soup.find_all(["p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "figcaption"]):
        if tag.get("dir"):
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
    callout_titles = {
        "NOTE": "نکته",
        "TIP": "پیشنهاد",
        "IMPORTANT": "مهم",
        "WARNING": "هشدار",
        "CAUTION": "احتیاط",
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

    return str(soup)


def render_markdown(
    markdown: str, *, toc: bool = False, code_style: str = "github-dark"
) -> MarkdownRenderResult:
    metadata, markdown_body = extract_frontmatter(markdown)
    title = guess_title(markdown_body, metadata)

    markdown_body, footnotes = extract_footnotes(markdown_body)
    markdown_body = replace_footnote_refs(markdown_body)
    markdown_body = protect_and_transform_math(markdown_body)
    markdown_body = markdown_body.replace("\n---page---\n", '\n<div class="md2pdf-page-break"></div>\n')

    md = MarkdownIt(
        "gfm-like",
        {
            "html": True,
            "linkify": False,
            "typographer": True,
            "highlight": lambda code, lang, attrs=None: highlight_code(
                code, lang, attrs, code_style=code_style
            ),
        },
    )
    md.enable(["table", "strikethrough"])

    body_html = md.render(markdown_body)
    body_html = append_footnotes(body_html, footnotes, md)
    body_html, toc_entries = add_heading_ids(body_html)
    toc_html = build_toc(toc_entries, toc)
    body_html = postprocess_html(body_html, code_style=code_style)

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
    path: str | Path, *, toc: bool = False, code_style: str = "github-dark"
) -> MarkdownRenderResult:
    text = Path(path).read_text(encoding="utf-8")
    return render_markdown(text, toc=toc, code_style=code_style)
