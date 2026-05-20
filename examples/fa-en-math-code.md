---
title: "نمونه حرفه‌ای تبدیل Markdown به PDF"
subtitle: "نمونه کامل قابلیت‌های متن، جدول، فرمول، کد، تصویر و جلد"
authors:
  - name: "Mardas"
    email: "mragetsars@yahoo.com"
  - "Mardas MD2PDF Team"
date: "1404-04-12"
summary: |
  این فایل برای تست متن فارسی/English mixed، جدول، فرمول ریاضی، بلاک کد، لینک، تصویر، فهرست مطالب و نکته طراحی شده است. خط دوم summary نشان می‌دهد متن چندخطی YAML روی جلد PDF با شکست خط تمیز حفظ می‌شود.

  این پاراگراف دوم summary است و جدا از پاراگراف اول روی جلد چاپ می‌شود.
institution: "Mardas Lab"
course: "Markdown Publishing"
version: "1.3"
keywords:
  - RTL/LTR
  - MathJax
  - Local Images
  - Safe HTML
  - PDF Metadata
  - Language-Aware UI
  - Math Scaling
lang: fa
dir: auto
---

# نمونه Markdown فارسی و English mixed

این یک پاراگراف فارسی است که در آن از عبارت‌های English مثل `Markdown`, `PDF`, `Playwright`, و `RTL/LTR` استفاده شده است. هدف این است که متن در PDF خوانا بماند و ترتیب کلمات فارسی و انگلیسی به‌هم نریزد.

> [!NOTE]
> این قالب برای مستندات فنی، گزارش‌های آکادمیک، جزوه آموزشی، proposal، و documentation مناسب است.

## فهرست قابلیت‌ها

- [x] پشتیبانی از فارسی و English در یک جمله
- [x] جدول‌های تمیز و خوانا
- [x] فرمول ریاضی inline مثل $E = mc^2$ و نمادهای $T$، $\epsilon$ و $\Sigma$
- [x] فرمول display با MathJax
- [x] هایلایت کد براساس زبان برنامه‌نویسی
- [x] نمایش تصویرهای محلی Markdown و HTML در PDF
- [x] پشتیبانی از summary چندخطی و چند author در YAML
- [x] ثبت metadata در PDF نهایی
- [x] sanitization برای HTML خام قابل اعتمادتر
- [x] پانویس چندخطی با Markdown داخلی
- [ ] افزودن تم‌های بیشتر در نسخه بعدی

## جدول نمونه

| قابلیت | وضعیت | توضیح |
|---|---:|---|
| RTL/LTR | ✅ | تشخیص جهت متن برای پاراگراف، عنوان، سلول جدول و لیست |
| Code Highlight | ✅ | رنگ‌بندی با Pygments و فونت monospace |
| MathJax | ✅ | خروجی SVG دقیق برای فرمول‌ها |
| Local Images | ✅ | تبدیل تصویرهای محلی به data URI برای نمایش پایدار در PDF |
| Safe Raw HTML | ✅ | حذف script، event handler، iframe و URLهای ناامن قبل از چاپ |
| PDF Metadata | ✅ | ثبت Title، Author، Subject و Keywords از YAML یا CLI |
| PDF Print CSS | ✅ | حاشیه، فوتر، رنگ‌بندی و break مناسب |

## تصویر محلی Markdown

تصویر زیر از مسیر نسبی `examples/images/md2pdf-sample-chart.png` خوانده می‌شود و قبل از چاپ PDF داخل HTML جاسازی می‌شود؛ بنابراین خروجی PDF وابسته به مسیر فایل تصویر در زمان باز شدن PDF نیست.

![نمونه نمودار محلی](images/md2pdf-sample-chart.png)

## تصویر محلی با HTML

همان تصویر را می‌توان با تگ HTML و اندازه‌ی دلخواه هم نوشت:

<p align="center">
  <img src="./images/md2pdf-sample-chart.png" alt="HTML local image example" width="75%"/>
</p>

## فرمول ریاضی

### فرمول درون‌خطی در متن فارسی

عبارت‌های ریاضی درون‌خطی مثل $T=500$، $\epsilon=0.05$، $\Sigma=I$ و $E=mc^2$ باید وسط متن فارسی به‌درستی با MathJax رندر شوند، هم‌اندازه‌ی نوشته‌های اطراف خود باشند، و نباید به شکل خامی مثل `\epsilon` یا پرانتزهای نامرتب چاپ شوند. این حالت مخصوصاً در عنوان‌ها و فهرست مطالب هم مهم است.

#### اثر $T$ و $\epsilon$ روی دقت

این عنوان برای تست فهرست مطالب است؛ در TOC هم باید نمادهای $T$ و $\epsilon$ به‌صورت ریاضی دیده شوند، نه متن خام TeX.

### فرمول‌های نمایشی

فرمول زیر باید وسط‌چین، خوانا و کمی بزرگ‌تر از فرمول‌های درون‌خطی باشد:

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

## بلاک کد C

در این بلاک، برچسب زبان `C` باید بالای کد نمایش داده شود و نباید وارد متن کد شود:

```c
int setSeed(void);
int getRandomNumber(int n, int *buf);
int process_information(int pid);
int sort_numbers(const char *src_file);
```

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

    ادامه‌ی همین پانویس به‌صورت چندخطی نوشته شده است تا parser جدید بتواند indentation استاندارد Markdown را حفظ کند.

    - خروجی HTML پانویس می‌تواند لیست داشته باشد.
    - تاکید مثل **print CSS** و inline code مثل `@page` هم باید درست رندر شود.
