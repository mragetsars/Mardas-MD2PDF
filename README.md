# MD2PDF Pro

یک ابزار حرفه‌ای برای تبدیل فایل‌های Markdown به PDF زیبا، تمیز و مناسب متن‌های فارسی/انگلیسی.

این پروژه عمداً از مسیر زیر استفاده می‌کند:

```text
Markdown → HTML تایپوگرافی‌شده → Chromium PDF
```

دلیل این انتخاب این است که مرورگر مدرن در شکل‌دهی متن فارسی، ترکیب RTL/LTR، SVGهای MathJax، CSS چاپی، جدول‌های پیچیده و فونت‌ها عملکرد بسیار قابل‌اعتمادی دارد.

## قابلیت‌ها

- پشتیبانی از متن فارسی، انگلیسی و جملات mixed مثل: «این پروژه از Markdown و PDF استفاده می‌کند»
- تنظیم `dir="auto"` برای پاراگراف‌ها، عنوان‌ها، آیتم‌های لیست و سلول‌های جدول
- خروجی PDF با دو تم: `modern` بدون سایه‌های مشکل‌ساز و `textbook` شبیه جزوه/کتاب فارسی
- هایلایت سینتکس کد با Pygments
- فونت فارسی با اولویت Vazirmatn و fallback برای Noto Sans Arabic
- فونت کدنویسی monospace برای code block و inline code
- پشتیبانی از جدول‌های GFM، strikethrough، task list، لینک، تصویر، footnote ساده و page break
- پشتیبانی آفلاین از MathJax برای فرمول‌های `$...$` و `$$...$$`
- تولید فهرست مطالب از headingهای سطح ۱ تا ۳
- امکان حذف cover با `--no-cover` برای خروجی‌های آموزشی و جزوه‌ای
- قابلیت خروجی گرفتن HTML میانی برای debug و سفارشی‌سازی

## نصب سریع

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m playwright install chromium
```

در سیستم‌هایی که Chromium نصب است، ابزار معمولاً همان Chromium سیستم را پیدا می‌کند. در غیر این صورت دستور بالا مرورگر مورد نیاز Playwright را نصب می‌کند.

## نصب فونت Vazirmatn

فایل فونت داخل پروژه بسته‌بندی نشده است. برای بهترین کیفیت فارسی، فونت Vazirmatn را روی سیستم نصب کنید یا فایل‌های آن را در یک پوشه قرار دهید و مسیر آن را با `--font-dir` بدهید.

نام فایل‌های پشتیبانی‌شده در `--font-dir`:

```text
Vazirmatn-Regular.woff2
Vazirmatn[wght].woff2
Vazirmatn-Regular.ttf
Vazirmatn.ttf
Vazirmatn-Bold.woff2
Vazirmatn-Bold.ttf
```

بدون این فونت هم خروجی ساخته می‌شود، اما کیفیت فارسی به فونت‌های نصب‌شده روی سیستم وابسته خواهد بود.

## استفاده

```bash
md2pdf-pro examples/fa-en-math-code.md -o output.pdf --toc
```

با فونت محلی:

```bash
md2pdf-pro examples/fa-en-math-code.md \
  -o output.pdf \
  --toc \
  --font-dir ./fonts
```

خروجی HTML برای بررسی:

```bash
md2pdf-pro examples/fa-en-math-code.md \
  -o output.pdf \
  --debug-html output.html
```

تنظیم حاشیه و سایز صفحه:

```bash
md2pdf-pro input.md -o output.pdf \
  --page-size A4 \
  --margin-top 20mm \
  --margin-bottom 22mm \
  --margin-x 18mm
```


### خروجی شبیه جزوه/نمونه دانشگاهی

برای خروجی نزدیک‌تر به نمونه‌های آموزشی فارسی، از تم `textbook` استفاده کنید. این تم سایه‌ها را حذف می‌کند، code block روشن و تخت می‌سازد، callout آبیِ ساده دارد و فوتر را فقط به شماره صفحه محدود می‌کند:

```bash
md2pdf-pro input.md -o output.pdf --toc --theme textbook --no-cover
```

### حذف سایه‌ها

در نسخه 0.2.0 سایه‌ی اطراف code block، جدول، blockquote، callout و تصویر حذف شده است تا در خروجی Chromium PDF لبه‌ها تمیز و بدون artifact چاپ شوند. تم `modern` همچنان ظاهر قبلی را نگه می‌دارد، اما به شکل flat و بدون shadow.

## Front matter

در ابتدای فایل Markdown می‌توانید metadata بنویسید:

```yaml
---
title: "عنوان سند"
author: "نام نویسنده"
date: "2026-05-12"
summary: "خلاصه کوتاه سند"
lang: fa
---
```

این اطلاعات در cover و عنوان PDF استفاده می‌شود.

## فرمول ریاضی

Inline:

```markdown
انرژی برابر است با $E = mc^2$.
```

Display:

```markdown
$$
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}
$$
```

MathJax به صورت vendored داخل پروژه قرار داده شده تا خروجی فرمول‌ها حتی بدون CDN ساخته شود.

## Page break

برای رفتن به صفحه بعد:

```markdown
---page---
```

یا:

```html
<div class="page-break"></div>
```

## ساختار پروژه

```text
md2pdf-pro/
├── pyproject.toml
├── README.md
├── examples/
│   └── fa-en-math-code.md
├── scripts/
│   └── install_playwright.sh
├── src/md2pdf_pro/
│   ├── __init__.py
│   ├── cli.py
│   ├── markdown.py
│   ├── renderer.py
│   └── assets/
│       ├── theme.css
│       └── mathjax/tex-svg-full.js
└── tests/
    └── test_markdown.py
```

## نکته‌های طراحی

- بدنه سند `rtl` است، اما هر بلوک متنی `dir="auto"` می‌گیرد تا ترکیب فارسی و انگلیسی درست خوانده شود.
- `pre`, `code`, MathJax و عبارت‌های کدنویسی همیشه LTR هستند.
- جدول‌ها داخل wrapper قرار می‌گیرند تا border-radius و صفحه‌بندی بهتری داشته باشند؛ سایه‌ها عمداً حذف شده‌اند.
- در PDF از `print_background=True` استفاده می‌شود تا رنگ‌های جدول، code block و callout حفظ شوند.
- اگر فرمول TeX خطا داشته باشد، تبدیل PDF متوقف نمی‌شود و سند همچنان ساخته می‌شود.

## توسعه آینده

- تم‌های بیشتر برای حالت مقاله، کتاب و گزارش
- پشتیبانی اختیاری Mermaid
- heading number خودکار
- caption خودکار برای تصاویر
- خروجی EPUB/HTML مستقل
