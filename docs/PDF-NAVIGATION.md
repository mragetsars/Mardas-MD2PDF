# PDF Navigation Contract

The guides teach table-of-contents behavior and include live TOC samples. This file records the maintainer QA contract for visible TOC links, PDF outline/bookmarks, destinations, metadata, and page labels.

## User-facing source of truth

- Guide sections: `Table of Contents`, `Security and Trusted Inputs`, and `PDF Preflight Checks`.
- Official visual samples: `examples/GUIDE.en.pdf` and `examples/GUIDE.fa.pdf`.

## What to verify

- The visible table of contents links point to real document headings, not to matching text inside the TOC itself.
- The PDF viewer outline/bookmarks use the same heading hierarchy as Markdown headings.
- Cover/content merging preserves named destinations.
- Metadata writing does not drop internal link annotations.
- Page labels start content numbering after the cover.
- Persian TOC entries keep generated numbers, mixed-script headings, and RTL alignment readable.

## Debugging

Use the focused tests first:

```bash
python -m pytest -q tests/test_pdf_toc_destinations.py
python scripts/check_pdf_preflight.py examples/GUIDE.en.pdf examples/GUIDE.fa.pdf --pages 1,2 --timeout 60
```

For PDF-level failures, inspect annotations and destinations with `pypdf` before changing renderer layout. Link bugs often come from cover/content merge order, named-destination variants, or metadata rewrites rather than TOC HTML itself.

## Visible TOC link annotations

The guides intentionally include visible TOC pages so reviewers can inspect both the printed TOC and the PDF viewer outline. Keep the guide note about Visible TOC links single-source in the guide; this file should remain the QA contract.
