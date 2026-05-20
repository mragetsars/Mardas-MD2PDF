---
title: "English Markdown to PDF Demo"
subtitle: "Language-aware cover, TOC, callouts, and MathJax sizing"
authors:
  - "Mardas MD2PDF Team"
date: "2026-05-20"
summary: |
  This short document verifies that lang: en produces an English, LTR PDF shell while still allowing Persian text inside the body.

  It also compares inline math with display math.
institution: "Mardas Lab"
version: "1.3"
keywords:
  - English
  - LTR
  - MathJax
  - Table of Contents
lang: en
dir: auto
---

# English Document Shell

> [!NOTE]
> This callout title should be English because the document language is English.

This paragraph contains inline math such as $E=mc^2$, $T=500$, and $\epsilon=0.05$. The formulas should stay visually aligned with the surrounding text.

این جمله فارسی است و باید داخل سند انگلیسی همچنان خوانا بماند، بدون اینکه پوسته‌ی کلی PDF راست‌به‌چپ شود.

## Display Formula

The display formula below should be centered and larger than inline formulas:

$$
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}
$$

## Code Block

```python
print("Language-aware Markdown to PDF")
```
