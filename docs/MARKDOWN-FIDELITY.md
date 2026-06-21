# Markdown Fidelity Contract

The guides are the canonical user tutorial for Markdown features. This file records the parser/renderer contract that maintainers must preserve.

## User-facing source of truth

- `docs/guides/GUIDE.en.md` and `docs/guides/GUIDE.fa.md` teach paragraphs, emphasis, lists, task lists, tables, blockquotes, callouts, GitHub-style alerts, details, autolinks, heading anchors, page breaks, formulas, code blocks, Mermaid, images, safe HTML, and footnotes.
- The guide PDFs under `examples/` are the official visual samples.

## Fenced code blocks

The advanced fence grammar supports language, title, line highlights, line numbers, and line-start metadata.

```markdown
```python title="renderer.py" {2,5-6} linenos
def convert(markdown: str) -> bytes:
    html = render_markdown(markdown)
    pdf = render_pdf(html)
    metadata = inspect_pdf(pdf)
    log_export(metadata)
    return pdf
```
```

Contract:

- `python` selects the lexer.
- `title="renderer.py"` becomes the code caption.
- `{2,5-6}` highlights line 2 and the inclusive range 5 through 6.
- `linenos` enables line numbers.
- `linenostart=10` or equivalent metadata shifts displayed line numbers but must not corrupt highlight selection.
- Highlight wrappers must preserve indentation, line rhythm, and newline boundaries.

## Language aliases

The parser recognizes practical aliases such as:

| Alias | Normalized language |
| :--- | :--- |
| `py` | `python` |
| `js` | `javascript` |
| `ts` | `typescript` |
| `sh` / `shell` | `bash` |
| `mmd` | `mermaid` |

## Mermaid diagrams

The offline Mermaid renderer covers the common flowchart subset used by the guides and project reports:

- `flowchart` / `graph` declarations;
- `TD`, `TB`, `LR`, `RL`, `BT` directions;
- rectangle, rounded, circle, diamond, database, hexagon, subroutine, stadium, and parallelogram nodes;
- solid, dotted, thick, and labelled edges, including pipe-labelled edges such as `A -.->|no| B`;
- semantic captions through the same caption pipeline as figures and code listings.

When syntax falls outside the supported subset, the renderer should fail visibly and safely rather than silently deleting user content.

## Callouts

GitHub-style alert blocks are normalized into semantic callouts. Raw markers such as `[!NOTE]` must not remain visible in rendered guide HTML/PDF output. Persian guide output must use localized callout titles.

## Page breaks, math, footnotes, and images

These features are taught in the guides. Maintainers should preserve the following invariants:

- manual page breaks become print-safe markers;
- MathJax source is protected until browser rendering;
- footnotes keep references and backlinks readable;
- local images are embedded or replaced with blocked placeholders;
- safe HTML image sizing stays deterministic;
- captions remain attached to figures, code listings, tables, and diagrams.
