from __future__ import annotations

import mimetypes
from importlib import resources
from pathlib import Path

PRODUCT_LOGO = "mardas-md2pdf-logo.png"
PRODUCT_LOGO_WHITE = "mardas-md2pdf-logo-white.png"
PRODUCT_MARK_SVG = "mardas-md2pdf-mark.svg"
PRODUCT_MARK_WHITE_SVG = "mardas-md2pdf-mark-white.svg"
PRODUCT_APP_ICON_SVG = "mardas-md2pdf-app-icon.svg"

DEFAULT_LOGO_CANDIDATES = (PRODUCT_LOGO, PRODUCT_MARK_SVG)
COVER_LABEL_LOGO_CANDIDATES = (PRODUCT_LOGO_WHITE, PRODUCT_MARK_WHITE_SVG)

GUI_BRAND_ASSET_ROUTES = {
    f"/assets/{PRODUCT_LOGO}": PRODUCT_LOGO,
    f"/assets/{PRODUCT_LOGO_WHITE}": PRODUCT_LOGO_WHITE,
    f"/assets/{PRODUCT_MARK_SVG}": PRODUCT_MARK_SVG,
    f"/assets/{PRODUCT_MARK_WHITE_SVG}": PRODUCT_MARK_WHITE_SVG,
    f"/assets/{PRODUCT_APP_ICON_SVG}": PRODUCT_APP_ICON_SVG,
}


def packaged_asset_path(filename: str) -> Path:
    return Path(str(resources.files("mardas_md2pdf") / "assets" / filename))


def product_logo_path(*, variant: str = "default") -> Path | None:
    candidates = COVER_LABEL_LOGO_CANDIDATES if variant == "cover-label" else DEFAULT_LOGO_CANDIDATES
    for filename in candidates:
        path = packaged_asset_path(filename)
        if path.exists():
            return path
    return None


def gui_brand_asset_filename(route: str) -> str | None:
    return GUI_BRAND_ASSET_ROUTES.get(route)


def asset_content_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"
