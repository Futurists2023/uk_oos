"""Shopify storefront reader using the public /products.json endpoint.

Only *published* products appear in this feed. Products a store has
unpublished (e.g. auto-hidden when sold out) will not be returned.
"""
import html
import time

import config
from oos import net

PAGE_SIZE = 250
MAX_PAGES = 200  # safety cap = 50,000 products


def _product(p: dict, base: str) -> dict:
    return {
        "id": p.get("id"),
        "title": html.unescape(p.get("title") or ""),
        "url": f"{base}/products/{p.get('handle')}",
        "brand": html.unescape((p.get("vendor") or "").strip()),
        "product_type": (p.get("product_type") or "").strip(),
        "tags": p.get("tags", []),
        "variants": [
            {
                "id": v.get("id"),
                "title": v.get("title"),
                "sku": v.get("sku"),
                "available": v.get("available"),
                "price": v.get("price"),
            }
            for v in p.get("variants", [])
        ],
    }


def resolve_base_url(domain: str) -> str | None:
    """Return the working storefront base URL (after redirects) or None."""
    for candidate in (f"https://{domain}", f"https://www.{domain}"):
        try:
            resp = net.get(f"{candidate}/products.json?limit=1")
        except Exception:
            continue
        if resp.ok and resp.headers.get("content-type", "").startswith("application/json"):
            return resp.url.split("/products.json")[0]
    return None


def fetch(domain: str) -> dict:
    """Fetch every published product. Returns {"base_url", "products"}."""
    base = resolve_base_url(domain)
    if not base:
        raise RuntimeError("No public /products.json feed")

    products, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        resp = net.get(f"{base}/products.json", params={"limit": PAGE_SIZE, "page": page})
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code} on page {page}")
        batch = resp.json().get("products", [])
        new = [p for p in batch if p.get("id") not in seen]
        if not new:
            break
        for p in new:
            seen.add(p["id"])
            products.append(_product(p, base))
        print(f"    page {page}: +{len(new)} (total {len(products)})")
        if len(batch) < PAGE_SIZE:
            break
        time.sleep(config.DELAY_BETWEEN_REQUESTS)

    return {"base_url": base, "products": products}
