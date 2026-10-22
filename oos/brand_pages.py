"""Brand-list readers for stores without a public product feed.

These return brand names only (no products), read from the store's
brand A-Z page.
"""
import html
import re

from oos import net


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def bigcommerce_brands(domain: str) -> dict:
    """BigCommerce: brand slugs from the brands sitemap, names from the /brands/ page."""
    base = f"https://{domain}"
    sm = net.get(f"{base}/xmlsitemap.php", params={"type": "brands", "page": 1})
    sm.raise_for_status()
    slugs = {
        loc.rstrip("/").rsplit("/", 1)[-1]
        for loc in re.findall(r"<loc>([^<]+)</loc>", sm.text)
    }
    slugs.discard("brands")

    page = net.get(f"{base}/brands/")
    page.raise_for_status()
    body = page.content.decode("utf-8", errors="replace")
    names = {}
    for slug, inner in re.findall(
            rf'<a[^>]+href="{re.escape(base)}/([^"/]+)/"[^>]*>(.*?)</a>', body, re.S):
        if slug in slugs and slug not in names:
            name = _clean(inner)
            if name:
                names[slug] = name
    # Any sitemap brand not linked on the page: fall back to a readable slug.
    unmatched = sorted(slugs - names.keys())
    for slug in unmatched:
        names[slug] = slug.replace("-", " ").title()
    return {"base_url": base, "brands": sorted(names.values(), key=str.casefold),
            "unmatched_slugs": unmatched}


def ziracle_brands(domain: str) -> dict:
    """Ziracle (Next.js storefront): brands linked as /brands/<slug>/."""
    base = "https://www.ziracle.com"
    page = net.get(f"{base}/brands/")
    page.raise_for_status()
    body = page.content.decode("utf-8", errors="replace")
    names = {}
    for slug, inner in re.findall(r'<a[^>]+href="/brands/([a-z0-9\-]+)/?"[^>]*>(.*?)</a>', body, re.S):
        if slug in names:
            continue
        name = _clean(inner)
        if not name:
            alt = re.search(r'alt="([^"]+)"', inner)
            name = html.unescape(alt.group(1)).strip() if alt else ""
        names[slug] = name or slug.replace("-", " ").title()
    return {"base_url": base, "brands": sorted(set(names.values()), key=str.casefold)}
