# PDF Navigation

Mardas MD2PDF uses two navigation layers in generated PDFs:

1. **Visible table of contents links** inside the document body.
2. **PDF viewer outline/bookmarks** exposed by readers such as Chrome, Preview, Okular, and Acrobat.

Both layers are generated from the same Markdown heading IDs.  The renderer now preserves Chromium's named destinations when pypdf writes metadata, merges cover/content PDFs, or adds outline entries. This keeps TOC links active and prevents PDF viewer bookmarks from resolving to matching text inside the table of contents instead of the real heading.

## What to verify

When changing heading, TOC, outline, or PDF metadata behavior, render a document with:

- a cover page;
- a visible TOC;
- duplicated headings;
- Persian and English headings;
- nested headings across several levels.

Then check:

- TOC entries jump to the real content heading;
- viewer bookmarks jump to the real content heading, not the TOC row;
- duplicated headings use stable suffixed IDs;
- non-Latin heading IDs remain usable in both visible links and PDF destinations.

## Debugging

Use `--debug-html` to inspect the generated HTML anchors:

```bash
mrs-md2pdf input.md -o output.pdf --toc --debug-html output.html
```

For PDF-level debugging, inspect named destinations and outline items with `pypdf`:

```python
from pypdf import PdfReader

reader = PdfReader("output.pdf")
print(reader.named_destinations.keys())
print(reader.outline)
```

## Visible TOC link annotations

Visible TOC links are rendered by Chromium as PDF link annotations. After pypdf
copies pages, writes metadata, merges cover/content PDFs, or adds outline items,
those annotations are rewritten from named destinations into explicit destination
arrays. This makes the printed TOC independent of viewer-specific named-destination
resolution while still preserving the named destinations used for diagnostics and
outline fallback behavior.

When debugging a navigation issue, inspect both layers:

- the link annotation on the visible TOC row should contain an explicit `/Dest`
  array pointing at the target page;
- the PDF outline item should point at the same heading coordinate.

