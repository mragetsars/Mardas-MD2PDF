# Appearance Maintenance Notes

The complete user tutorial for `style`, `palette`, and `mode` lives in the guide sections `Appearance`, `First PDF`, and `Front Matter`. This file is the maintainer contract for keeping that guide coverage and the implementation synchronized.

## User-facing source of truth

- `docs/guides/GUIDE.en.md` and `docs/guides/GUIDE.fa.md` must teach appearance selection and show runnable CLI/front-matter examples.
- `examples/GUIDE.en.pdf` and `examples/GUIDE.fa.pdf` are the official visual samples for `modern + emerald + light`.
- Studio must expose the same style, palette, and mode choices as the CLI.

## CLI

```bash
mrs-md2pdf input.md -o output.pdf --style modern --palette emerald --mode light
mrs-md2pdf --list-styles
mrs-md2pdf --list-palettes
mrs-md2pdf --list-modes
```

## Front matter

```yaml
appearance:
  style: modern
  palette: emerald
  mode: light
```

If a document omits appearance settings, the renderer falls back to its defaults. The guides use `modern`, `emerald`, and `light` intentionally so the official examples have a stable visual baseline.

## Built-in styles

| Style | Contract |
| :--- | :--- |
| `modern` | Product/report style with rounded blocks and strong visual hierarchy. |
| `github` | Markdown-project style close to GitHub-style documents. |
| `textbook` | Longer teaching material with book-like rhythm. |
| `academic` | Formal report, thesis, and structured article output. |

## Built-in palettes

| Palette | Contract |
| :--- | :--- |
| `blue` | Professional default blue. |
| `emerald` | Calm green used by the official guide PDFs. |
| `violet` | Creative/product documents. |
| `amber` | Review and educational material. |
| `rose` | Editorial reports. |
| `slate` | Formal technical documents. |
| `neutral` | Minimal grayscale output. |

## Modes

- `light` is the default print-oriented mode.
- `dark` is supported for screen-like PDFs and must keep code blocks, Mermaid labels, TOC links, callouts, and table surfaces readable.

## Studio

Studio appearance cards must map to the same values as the CLI and front matter. A Studio change that adds or removes an appearance choice must update the guide, this contract, and the GUI tests.

## Palette purity rules

Palette changes must not introduce unrelated layout changes. A palette should change color tokens only. Layout shape belongs to style CSS, and light/dark surface contrast belongs to mode-specific tokens.

## Visual audit workflow

For appearance changes, run representative guide builds and at least one visual matrix pass:

```bash
python scripts/audit_appearance_matrix.py --output-dir build/appearance-audit --render-png --resume
python scripts/run_visual_qa_matrix.py --output-dir build/visual-qa/matrix --max-cases 1 --render-png --clean
```

Artifacts under `build/` are temporary and must not be committed.
