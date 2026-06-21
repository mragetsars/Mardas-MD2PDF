from __future__ import annotations

from mardas_md2pdf import brand_assets
from mardas_md2pdf.renderer import _default_logo_path


def test_product_logo_candidates_prefer_canonical_png_assets():
    assert brand_assets.DEFAULT_LOGO_CANDIDATES[0] == brand_assets.PRODUCT_LOGO
    assert brand_assets.COVER_LABEL_LOGO_CANDIDATES[0] == brand_assets.PRODUCT_LOGO_WHITE
    assert _default_logo_path().name == brand_assets.PRODUCT_LOGO
    assert _default_logo_path(variant="cover-label").name == brand_assets.PRODUCT_LOGO_WHITE


def test_studio_brand_asset_routes_expose_only_current_application_logos():
    routes = brand_assets.GUI_BRAND_ASSET_ROUTES

    assert routes["/assets/mardas-md2pdf-logo.png"] == brand_assets.PRODUCT_LOGO
    assert routes["/assets/mardas-md2pdf-logo-white.png"] == brand_assets.PRODUCT_LOGO_WHITE
    assert routes["/assets/mardas-md2pdf-mark.svg"] == brand_assets.PRODUCT_MARK_SVG
    assert brand_assets.gui_brand_asset_filename("/assets/" + "Mardas" + ".png") is None
    assert brand_assets.asset_content_type(brand_assets.PRODUCT_LOGO) == "image/png"
