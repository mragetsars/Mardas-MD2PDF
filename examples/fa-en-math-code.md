---
title: "نمونه حرفه‌ای تبدیل Markdown به PDF"
author: "Mardas"
date: "1404-04-12"
summary: "این فایل برای تست متن فارسی/English mixed، جدول، فرمول ریاضی، بلاک کد، لینک، تصویر و نکته طراحی شده است."
lang: fa
---

# نمونه Markdown فارسی و English mixed

این یک پاراگراف فارسی است که در آن از عبارت‌های English مثل `Markdown`, `PDF`, `Playwright`, و `RTL/LTR` استفاده شده است. هدف این است که متن در PDF خوانا بماند و ترتیب کلمات فارسی و انگلیسی به‌هم نریزد.

> [!NOTE]
> این قالب برای مستندات فنی، گزارش‌های آکادمیک، جزوه آموزشی، proposal، و documentation مناسب است.

## فهرست قابلیت‌ها

- [x] پشتیبانی از فارسی و English در یک جمله
- [x] جدول‌های تمیز و خوانا
- [x] فرمول ریاضی inline مثل $E = mc^2$
- [x] فرمول display با MathJax
- [x] هایلایت کد براساس زبان برنامه‌نویسی
- [ ] افزودن تم‌های بیشتر در نسخه بعدی

## جدول نمونه

| قابلیت | وضعیت | توضیح |
|---|---:|---|
| RTL/LTR | ✅ | تشخیص جهت متن برای پاراگراف، عنوان، سلول جدول و لیست |
| Code Highlight | ✅ | رنگ‌بندی با Pygments و فونت monospace |
| MathJax | ✅ | خروجی SVG دقیق برای فرمول‌ها |
| PDF Print CSS | ✅ | حاشیه، فوتر، رنگ‌بندی و break مناسب |

## فرمول ریاضی

فرمول زیر باید وسط‌چین و خوانا باشد:

$$
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}
$$

و یک رابطه ماتریسی:

$$
A = \begin{bmatrix}
1 & 2 \\
3 & 4
\end{bmatrix},\quad
\det(A) = -2
$$

## بلاک کد Python

```python
from dataclasses import dataclass

@dataclass
class Document:
    title: str
    lang: str = "fa"


def greet(doc: Document) -> str:
    return f"Rendering {doc.title} as a beautiful PDF"

print(greet(Document("راهنمای Mardas MD2PDF")))
```

## بلاک کد JavaScript

```javascript
const items = ["Markdown", "Persian", "MathJax", "PDF"];
const message = items.map((item, index) => `${index + 1}. ${item}`).join("\n");
console.log(message);
```

## نقل‌قول و لینک

> زیبایی خروجی PDF فقط به تبدیل متن نیست؛ تایپوگرافی، فاصله‌ها، کنتراست، فونت، و رفتار صفحه‌بندی هم مهم هستند.

برای ساخت PDF، پروژه از یک HTML میانی استفاده می‌کند و سپس آن را با Chromium به PDF تبدیل می‌کند.[^html]

[^html]: این روش برای استایل‌دهی پیشرفته و کنترل دقیق روی خروجی چاپی بسیار مناسب است.
