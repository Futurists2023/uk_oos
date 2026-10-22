"""WooCommerce reader using the public Store API (/wp-json/wc/store/v1/products).

Brand detection order:
  1. WooCommerce native "brands" field
  2. Product tags named "Brand_<name>" (convention used by gloworganic.co.uk)
"""
import html
import time

import config
from oos import net

PAGE_SIZE = 100
BRAND_TAG_PREFIX = "brand_"


def _brand(p: dict) -> str:
    if p.get("brands"):
        return html.unescape(p["brands"][0].get("name", "")).strip()
    for tag in p.get("tags", []):
        name = html.unescape(tag.get("name", ""))
        if name.lower().startswith(BRAND_TAG_PREFIX):
            return name[len(BRAND_TAG_PREFIX):].strip()
    return ""


def _product(p: dict) -> dict:
    variants = [
        {"id": v.get("id"), "title": ", ".join(a.get("value", "") for a in v.get("attributes", [])),
         "sku": None, "available": None, "price": None}
        for v in p.get("variations", [])
    ] or [{"id": p.get("id"), "title": "Default", "sku": p.get("sku"),
           "available": p.get("is_in_stock"), "price": None}]
    return {
        "id": p.get("id"),
        "title": html.unescape(p.get("name") or ""),
        "url": p.get("permalink"),
        "brand": _brand(p),
        "product_type": "",
        "tags": [html.unescape(t.get("name", "")) for t in p.get("tags", [])],
        "in_stock": p.get("is_in_stock"),  # product-level only; variant stock needs a per-product call
        "variants": variants,
    }


def fetch(domain: str) -> dict:
    base = f"https://{domain}"
    products = []
    page, total_pages = 1, 1
    while page <= total_pages:
        resp = net.get(f"{base}/wp-json/wc/store/v1/products",
                       params={"per_page": PAGE_SIZE, "page": page})
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code} on page {page}")
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        batch = resp.json()
        products.extend(_product(p) for p in batch)
        print(f"    page {page}/{total_pages}: +{len(batch)} (total {len(products)})")
        page += 1
        time.sleep(config.DELAY_BETWEEN_REQUESTS)
    return {"base_url": resp.url.split("/wp-json")[0], "products": products}
