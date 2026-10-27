"""Multi-Brand Stateful 24/7 Cloud & Local Monitor for UK Independent Stockists.

Supports all 24 UK SME Beauty & Wellness brands defined in `sme_brands.py`.

Usage:
    python monitor_brand.py --list-brands
    python monitor_brand.py --brand "Balmonds"
    python monitor_brand.py --brands balmonds bare-biology upcircle
    python monitor_brand.py --all
    python monitor_brand.py --brand balmonds --only mypure.co.uk
    python monitor_brand.py --brand balmonds --report-only
"""
import argparse
import asyncio
import html
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import urllib.request

from playwright.async_api import async_playwright

import db
import discover_uk_stockists
import sme_brands

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
STOCKISTS_DIR = HERE / "stockists"
REPORTS_DIR = HERE / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def parse_gbp_price(text: str | float | int | None) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return round(float(text), 2)
    m = re.search(r"(\d+\.\d{2})", str(text))
    return round(float(m.group(1)), 2) if m else None


async def human_pause(min_s: float = 2.2, max_s: float = 4.2, label: str = "") -> None:
    delay = random.uniform(min_s, max_s)
    if label:
        print(f"    [human pause {delay:.1f}s] {label}")
    await asyncio.sleep(delay)


async def smooth_scroll(page, steps: int = 3) -> None:
    """Mimic natural human mouse movement across the viewport, variable wheel scrolling, and reading pauses."""
    try:
        await page.mouse.move(
            random.randint(240, 1180),
            random.randint(180, 720),
            steps=random.randint(12, 25),
        )
    except Exception:
        pass
    for i in range(steps):
        await page.mouse.wheel(0, random.randint(240, 490))
        await asyncio.sleep(random.uniform(0.8, 1.5))
        if i == steps - 1 and random.random() < 0.35:
            # Occasional slight scroll back up like a shopper re-reading a product card
            await page.mouse.wheel(0, -random.randint(80, 160))
            await asyncio.sleep(random.uniform(0.5, 1.0))


async def scrape_shopify_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Visit Shopify store at human pace and extract variant-level price & availability for `brand_cfg`."""
    domain = store["domain"]
    brand_url = store["brand_url"]
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]

    await page.goto(brand_url, wait_until="domcontentloaded", timeout=30000)
    await human_pause(2.0, 3.6, f"Viewing {domain} ({brand_name})")
    await smooth_scroll(page, steps=2)

    origin = f"{urlparse(page.url).scheme}://{urlparse(page.url).netloc}"

    raw_products = await page.evaluate(
        """async ({ slug, brandName }) => {
            if (location.pathname.includes('/products/')) {
                try {
                    const r = await fetch(location.pathname + '.js');
                    if (r.ok) {
                        const p = await r.json();
                        return { mode: 'product_js', products: [p] };
                    }
                } catch (e) {}
            }

            const candidatePaths = [
                `/collections/${slug}/products.json?limit=250`,
                `/collections/${slug}-skincare/products.json?limit=250`,
                `/collections/${slug.replace(/-/g, '')}/products.json?limit=250`,
                `/products.json?limit=250`,
            ];
            for (const path of candidatePaths) {
                try {
                    await new Promise(res => setTimeout(res, 350 + Math.random() * 450));
                    const r = await fetch(path);
                    if (r.ok) {
                        const data = await r.json();
                        if (data && Array.isArray(data.products) && data.products.length > 0) {
                            return { mode: 'products_json', products: data.products };
                        }
                    }
                } catch (e) {}
            }

            try {
                await new Promise(res => setTimeout(res, 450 + Math.random() * 550));
                const r = await fetch(`/search/suggest.json?q=${encodeURIComponent(brandName)}&resources[type]=product&resources[limit]=25`);
                if (r.ok) {
                    const data = await r.json();
                    const candidates = (((data || {}).resources || {}).results || {}).products || [];
                    const full = [];
                    for (const c of candidates) {
                        const cleanPath = (c.url || '').split('?')[0];
                        try {
                            await new Promise(res => setTimeout(res, 400 + Math.random() * 500));
                            const pr = await fetch(cleanPath + '.js');
                            if (pr.ok) {
                                full.push(await pr.json());
                                continue;
                            }
                        } catch (e) {}
                        full.push(c);
                    }
                    if (full.length > 0) return { mode: 'suggest_js', products: full };
                }
            } catch (e) {}
            return { mode: 'none', products: [] };
        }""",
        {"slug": slug, "brandName": brand_name},
    )

    if not raw_products.get("products"):
        for cand_path in [
            f"/collections/{slug}/products.json?limit=250",
            f"/collections/{slug}-skincare/products.json?limit=250",
            f"/collections/{slug.replace('-', '')}/products.json?limit=250",
            "/products.json?limit=250",
        ]:
            try:
                req = urllib.request.Request(
                    f"{origin}{cand_path}",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                body = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
                prods = json.loads(body).get("products") or []
                if prods:
                    raw_products = {"mode": "products_json", "products": prods}
                    break
            except Exception:
                pass

    skus = []
    mode = raw_products.get("mode")
    is_dtc = domain in {d.lower().removeprefix("www.") for d in brand_cfg.get("dtc_domains", [])}
    for p in raw_products.get("products", []):
        title = (p.get("title") or "").strip()
        vendor = (p.get("vendor") or "").strip()
        if not is_dtc and not sme_brands.matches_brand(brand_cfg, vendor, title):
            continue
        # On DTC stores, skip £0 free samples, gift cards, or empty-Bag placeholders
        if re.search(r"\b(?:gift\s+card|e-gift|voucher|sample\s+sachet)\b", title, re.I):
            continue

        handle = p.get("handle") or (p.get("url") or "").split("/products/")[-1].split("?")[0]
        prod_url = f"{origin}/products/{handle}" if handle else brand_url
        variants = p.get("variants") or []

        if variants:
            for v in variants:
                v_title = (v.get("title") or "Default").strip()
                if re.search(r"\b(?:5\s*litre|5\s*l|salon\s*size|professional\s*only|tester)\b", v_title, re.I):
                    continue
                if v_title.lower() == "default title":
                    m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets|sachets))\b", title, re.I)
                    v_title = m_size.group(1) if m_size else "Standard"
                raw_price = v.get("price")
                if isinstance(raw_price, int) or (mode in ("product_js", "suggest_js") and isinstance(raw_price, (int, float)) and raw_price > 100):
                    price_val = round(float(raw_price) / 100.0, 2)
                else:
                    price_val = parse_gbp_price(raw_price)

                if is_dtc and (price_val is None or price_val <= 0.0):
                    continue

                raw_comp = v.get("compare_at_price")
                if isinstance(raw_comp, int) and raw_comp > 100:
                    comp_val = round(float(raw_comp) / 100.0, 2)
                else:
                    comp_val = parse_gbp_price(raw_comp)

                v_id = v.get("id") or v_title
                sku_key = f"{domain}::{slug}::{handle}::{v_id}"
                skus.append({
                    "sku_key": sku_key,
                    "product_title": title,
                    "variant_title": v_title,
                    "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title, v_title),
                    "product_url": prod_url,
                    "sku_code": v.get("sku") or "",
                    "price": price_val,
                    "compare_at_price": comp_val,
                    "currency": "GBP",
                    "available": bool(v.get("available")),
                })
        else:
            price_val = parse_gbp_price(p.get("price"))
            if is_dtc and (price_val is None or price_val <= 0.0):
                continue
            sku_key = f"{domain}::{slug}::{handle}::default"
            skus.append({
                "sku_key": sku_key,
                "product_title": title,
                "variant_title": "Standard",
                "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
                "product_url": prod_url,
                "sku_code": "",
                "price": price_val,
                "compare_at_price": None,
                "currency": "GBP",
                "available": bool(p.get("available", True)),
            })

    return skus


async def accept_cookies(page) -> None:
    """Politely accept UK cookie consent banners like a real human shopper."""
    try:
        for sel in [
            "button#onetrust-accept-btn-handler",
            "button:has-text('Accept All')",
            "button:has-text('Accept all')",
            "button:has-text('Allow all')",
            "button:has-text('Accept Cookies')",
        ]:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.hover()
                await asyncio.sleep(random.uniform(0.3, 0.7))
                await loc.click()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                break
    except Exception:
        pass


async def scrape_spacenk_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Calibrated Space NK Engine: scrolls & clicks 'Show More' across all pages and extracts deduplicated SKUs."""
    domain = store["domain"]
    brand_url = store["brand_url"]
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]

    await page.goto(brand_url, wait_until="domcontentloaded", timeout=35000)
    await human_pause(2.5, 4.2, f"Browsing {domain} ({brand_name})")
    await accept_cookies(page)

    for cycle in range(8):
        await smooth_scroll(page, steps=4)
        btn = page.locator(
            "button[data-url*='Search-UpdateGrid'], .show-more button, button.more, button:has-text('Show More'), button:has-text('Load More')"
        ).first
        if await btn.count() > 0:
            try:
                await btn.scroll_into_view_if_needed(timeout=5000)
                await asyncio.sleep(random.uniform(0.8, 1.5))
                if await btn.is_visible():
                    await btn.hover()
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    await btn.click()
                    await human_pause(3.0, 4.8, f"Space NK page {cycle + 2}")
                    continue
            except Exception:
                pass
        break

    raw = await page.evaluate(
        """(brandName) => {
            const out = [];
            const seenUrls = new Set();
            const tiles = document.querySelectorAll('.product-tile, [data-pid], article');
            for (const tile of tiles) {
                if (tile.parentElement && tile.parentElement.closest('.product-tile')) continue;
                const links = Array.from(tile.querySelectorAll('a[href*="/uk/"]'));
                const prodLink = links.find(a => /\\.html$/i.test((a.href || '').split('?')[0])) || links[0];
                if (!prodLink) continue;
                const url = (prodLink.href || '').split('?')[0].split('#')[0];
                if (!url || seenUrls.has(url)) continue;

                const fullText = (tile.innerText || '').replace(/\\s+/g, ' ').trim();
                const bEsc = brandName.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
                if (!new RegExp(bEsc, 'i').test(fullText)) continue;
                seenUrls.add(url);

                let title = '';
                const hEl = tile.querySelector('h2, h3, h4, .pdp-link, .product-tile__name');
                if (hEl && hEl.innerText.trim().length > 2) {
                    title = hEl.innerText.replace(/\\s+/g, ' ').trim();
                }
                if (!title || /^worth\\s+£/i.test(title)) {
                    const m = fullText.match(new RegExp(bEsc + '\\\\s+(.+?)(?:\\\\s+PRICE REDUCED|\\\\s+£\\\\d+|\\\\s+N/A|\\\\s+\\\\(\\\\d+\\\\)\\\\s*Reviews)', 'i'));
                    if (m && m[1]) {
                        title = m[1].trim();
                    } else {
                        const slugPart = url.split('/').slice(-1)[0].replace(/\\.html$/i, '').replace(/^MUK\\d+-?/i, '');
                        title = slugPart.replace(/-/g, ' ');
                    }
                }

                const hasPriceRange = /£\\d+\\.\\d{2}\\s*-\\s*£\\d+\\.\\d{2}/.test(fullText);
                const priceMatches = fullText.match(/£(\\d+\\.\\d{2})/g) || [];
                const prices = priceMatches.map(p => parseFloat(p.replace('£', '')));
                const price = prices.length > 0 ? prices[prices.length - 1] : null;
                const compareAt = (!hasPriceRange && prices.length > 1 && prices[0] > price) ? prices[0] : null;
                const isOos = /\\bout of stock\\b|\\bsold out\\b|\\bnotify me\\b|\\bwaitlist\\b|\\bunavailable\\b/i.test(fullText);

                out.push({ title, url, price, compareAt, available: !isOos, hasPriceRange });
            }
            return out;
        }""",
        brand_name,
    )

    skus = []
    for item in raw:
        if item.get("hasPriceRange"):
            try:
                await human_pause(1.8, 3.0, f"Expanding multi-size variants on {domain}: {item['title']}")
                await page.goto(item["url"], wait_until="domcontentloaded", timeout=30000)
                variants_ld = await page.evaluate(
                    """() => {
                        const out = [];
                        for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
                            try {
                                const d = JSON.parse(s.innerText);
                                if (Array.isArray(d.hasVariant)) {
                                    for (const v of d.hasVariant) {
                                        const offer = v.offers || {};
                                        out.push({
                                            name: v.name || '',
                                            size: v.size || '',
                                            sku: v.sku || offer.sku || '',
                                            url: v.url || offer.url || location.href,
                                            price: offer.price ? parseFloat(offer.price) : null,
                                            avail: /InStock/i.test(offer.availability || ''),
                                        });
                                    }
                                }
                            } catch (e) {}
                        }
                        return out;
                    }"""
                )
                if variants_ld:
                    for v in variants_ld:
                        v_name = v["name"] or item["title"]
                        v_size = v["size"] or "Standard"
                        v_code = v["sku"] or v_size
                        skus.append({
                            "sku_key": f"{domain}::{slug}::{v_code}",
                            "product_title": v_name,
                            "variant_title": v_size,
                            "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, v_name),
                            "product_url": v["url"],
                            "sku_code": v_code,
                            "price": v["price"],
                            "compare_at_price": None,
                            "currency": "GBP",
                            "available": bool(v["avail"]),
                        })
                    continue
            except Exception:
                pass

        title = item["title"]
        m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets|sachets))\b", title, re.I)
        v_title = m_size.group(1) if m_size else "Standard"
        path_slug = item["url"].split("/")[-1].replace(".html", "")
        skus.append({
            "sku_key": f"{domain}::{slug}::{path_slug}",
            "product_title": title,
            "variant_title": v_title,
            "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
            "product_url": item["url"],
            "sku_code": path_slug,
            "price": item["price"],
            "compare_at_price": item["compareAt"],
            "currency": "GBP",
            "available": bool(item["available"]),
        })
    return skus


async def scrape_thg_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Calibrated THG Engine (Cult Beauty & Lookfantastic): follows Brand Hub -> 'Shop All / View All' and extracts SKUs."""
    domain = store["domain"]
    brand_url = store["brand_url"]
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]

    await page.goto(brand_url, wait_until="domcontentloaded", timeout=35000)
    await human_pause(2.5, 4.5, f"Browsing {domain} ({brand_name})")
    await accept_cookies(page)

    view_all_href = await page.evaluate(
        """(slug) => {
            for (const a of document.querySelectorAll('a[href]')) {
                const href = (a.href || '').toLowerCase();
                const txt = (a.innerText || '').replace(/\\s+/g, ' ').trim();
                if (href.includes(slug) && (/^(?:shop all|view all|view all products|shop all products)$/i.test(txt) || /view-all|shop-all/i.test(href))) {
                    return a.href;
                }
            }
            return null;
        }""",
        slug,
    )
    if view_all_href and view_all_href != page.url:
        await page.goto(view_all_href, wait_until="domcontentloaded", timeout=35000)
        await human_pause(2.8, 4.5, f"Viewing full {brand_name} grid on {domain}")

    await smooth_scroll(page, steps=5)

    raw = await page.evaluate(
        """({ brandName, slug }) => {
            const out = [];
            const seen = new Set();
            const bEsc = brandName.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
            const cards = document.querySelectorAll('product-card-wrapper, .product-card, article, [data-testid*="product"], .productListProducts_product');
            for (const card of cards) {
                const titleLink = card.querySelector('a.product-item-title, a[data-testid*="title"], h2 a, h3 a') || card.querySelector('a[href*="/p/"], a[href*=".html"]');
                if (!titleLink) continue;
                const href = (titleLink.href || '').split('?')[0];
                if (!href || seen.has(href)) continue;
                if (!new RegExp(slug, 'i').test(href) && !new RegExp(bEsc, 'i').test(titleLink.innerText || '')) continue;

                const fullText = (card.innerText || '').replace(/\\s+/g, ' ').trim();
                seen.add(href);

                const h = card.querySelector('a.product-item-title, h2, h3, h4, [class*="title"], [class*="name"], [data-testid*="title"]');
                let title = h ? h.innerText.replace(/\\s+/g, ' ').trim() : (titleLink.innerText || '').replace(/\\s+/g, ' ').trim();
                if (!title || title.length < 4) continue;

                const cleanPriceText = fullText.replace(/(?:FREE GOODY BAG WITH|SPEND|WORTH|SAVE UP TO)\\s*£\\d+(?:\\.\\d{2})?/gi, '');
                const priceMatches = cleanPriceText.match(/£(\\d+\\.\\d{2})/g) || [];
                const prices = priceMatches.map(p => parseFloat(p.replace('£', '')));
                const price = prices.length > 0 ? prices[prices.length - 1] : null;
                const compareAt = prices.length > 1 && prices[0] > price ? prices[0] : null;
                const isOos = /\\bout of stock\\b|\\bsold out\\b|\\bnotify me\\b|\\bemail me\\b|\\bunavailable\\b/i.test(fullText);

                out.push({ title, url: href, price, compareAt, available: !isOos });
            }
            return out;
        }""",
        {"brandName": brand_name, "slug": slug},
    )

    skus = []
    for item in raw:
        title = item["title"]
        m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets|sachets))\b", title, re.I)
        v_title = m_size.group(1) if m_size else "Standard"
        path_slug = urlparse(item["url"]).path.strip("/").replace("/", "_")
        skus.append({
            "sku_key": f"{domain}::{slug}::{path_slug}",
            "product_title": title,
            "variant_title": v_title,
            "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
            "product_url": item["url"],
            "sku_code": path_slug,
            "price": item["price"],
            "compare_at_price": item["compareAt"],
            "currency": "GBP",
            "available": bool(item["available"]),
        })
    return skus


async def scrape_hb_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Calibrated Holland & Barrett Engine: extracts /shop/product/ cards and OOS badges."""
    domain = store["domain"]
    brand_url = store["brand_url"]
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]

    await page.goto(brand_url, wait_until="domcontentloaded", timeout=35000)
    await human_pause(2.8, 4.5, f"Browsing {domain} ({brand_name})")
    await accept_cookies(page)
    await smooth_scroll(page, steps=5)

    raw = await page.evaluate(
        """() => {
            const out = [];
            const seen = new Set();
            for (const a of document.querySelectorAll('a[href*="/shop/product/"]')) {
                const url = (a.href || '').split('?')[0];
                if (!url || seen.has(url)) continue;
                seen.add(url);

                let card = a.parentElement;
                for (let i = 0; i < 5 && card; i++) {
                    if (/£\\d+/.test(card.innerText || '')) break;
                    card = card.parentElement;
                }
                const fullText = card ? (card.innerText || '').replace(/\\s+/g, ' ').trim() : (a.innerText || '').replace(/\\s+/g, ' ').trim();
                const aText = (a.innerText || '').replace(/\\s+/g, ' ').trim();
                const title = aText.split(/\\(\\d+\\)|£\\d+/)[0].replace(/Sold by Face The Future/i, '').trim();
                if (!title || title.length < 4) continue;

                const priceMatches = fullText.match(/£(\\d+\\.\\d{2})(?!\\s*\\/)/g) || [];
                const prices = priceMatches.map(p => parseFloat(p.replace('£', '')));
                const price = prices.length > 0 ? prices[0] : null;
                const compareAt = prices.length > 1 && prices[1] > price ? prices[1] : null;
                const isOos = /\\bout of stock\\b|\\bsold out\\b|\\bnotify me\\b|\\bsee alternatives\\b/i.test(fullText);

                out.push({ title, url, price, compareAt, available: !isOos });
            }
            return out;
        }"""
    )

    skus = []
    for item in raw:
        title = item["title"]
        m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets|sachets))\b", title, re.I)
        v_title = m_size.group(1) if m_size else "Standard"
        path_slug = item["url"].split("/")[-1]
        skus.append({
            "sku_key": f"{domain}::{slug}::{path_slug}",
            "product_title": title,
            "variant_title": v_title,
            "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
            "product_url": item["url"],
            "sku_code": path_slug,
            "price": item["price"],
            "compare_at_price": item["compareAt"],
            "currency": "GBP",
            "available": bool(item["available"]),
        })
    return skus


async def scrape_boots_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Calibrated Boots Engine: single-pass human browse capturing Boots' passive search/v2 JSON hits."""
    domain = store["domain"]
    brand_url = store["brand_url"]
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]

    captured_hits = []

    async def handle_boots_response(resp):
        u = resp.url.lower()
        if "online/api/search/v2/multiple-query" in u:
            try:
                data = await resp.json()
                hits = (data.get("products") or {}).get("hits") or []
                if hits:
                    captured_hits.extend(hits)
            except Exception:
                pass

    page.on("response", handle_boots_response)
    try:
        await page.goto(brand_url, wait_until="domcontentloaded", timeout=40000)
        await human_pause(3.2, 5.0, f"Browsing {domain} ({brand_name})")
        await accept_cookies(page)
        await smooth_scroll(page, steps=4)

        shop_all = page.locator(f"a[href*='{slug}-shop-all'], a:has-text('Shop all')").first
        if await shop_all.count() > 0:
            try:
                await shop_all.scroll_into_view_if_needed(timeout=5000)
                await asyncio.sleep(random.uniform(0.8, 1.4))
                await shop_all.click()
                await human_pause(4.0, 6.0, f"Viewing Boots 'Shop all' grid for {brand_name}")
            except Exception:
                pass

        for cycle in range(3):
            await smooth_scroll(page, steps=4)
            vm = page.locator("button:has-text('View more'), a:has-text('View more')").first
            if await vm.count() > 0 and await vm.is_visible():
                try:
                    await vm.scroll_into_view_if_needed(timeout=4000)
                    await asyncio.sleep(random.uniform(0.7, 1.3))
                    await vm.click()
                    await human_pause(3.5, 5.2, f"Boots page {cycle + 2}")
                except Exception:
                    break
            else:
                break
    finally:
        page.remove_listener("response", handle_boots_response)

    skus = []
    seen_ids = set()
    for h in captured_hits:
        obj_id = str(h.get("objectId") or h.get("objectID") or "")
        if not obj_id or obj_id in seen_ids:
            continue
        seen_ids.add(obj_id)

        title = (h.get("title") or h.get("name") or (h.get("attributes") or {}).get("name") or f"{brand_name} {obj_id}").strip()
        pricing = h.get("pricing") or {}
        curr_p = (pricing.get("current") or {}).get("value")
        reg_p = (pricing.get("regular") or {}).get("value")
        price_val = round(float(curr_p), 2) if curr_p is not None else None
        comp_val = round(float(reg_p), 2) if (reg_p is not None and price_val is not None and float(reg_p) > price_val) else None

        attrs = h.get("attributes") or {}
        stock_msg = str(attrs.get("StockOverrideMessage") or h.get("stockDescription") or "").upper()
        in_stock_flag = h.get("inStock", True)
        is_avail = bool(in_stock_flag) and ("OUT_OF_STOCK" not in stock_msg and "COMING_SOON" not in stock_msg)

        prod_url = (h.get("urls") or {}).get("product") or h.get("actionURL") or f"https://www.boots.com/{slug}-{obj_id}"
        if prod_url.startswith("/"):
            prod_url = f"https://www.boots.com{prod_url}"

        v_title = str(h.get("ppuQuantity") or "Standard")
        skus.append({
            "sku_key": f"{domain}::{slug}::{obj_id}",
            "product_title": title,
            "variant_title": v_title,
            "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
            "product_url": prod_url,
            "sku_code": obj_id,
            "price": price_val,
            "compare_at_price": comp_val,
            "currency": "GBP",
            "available": is_avail,
        })
    return skus


async def scrape_frasers_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Calibrated Frasers Group Engine (Harvey Nichols, Flannels, House of Fraser): extracts `[class*='productCard']` tiles."""
    domain = store["domain"]
    brand_url = store["brand_url"]
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]

    await page.goto(brand_url, wait_until="domcontentloaded", timeout=35000)
    await human_pause(3.0, 4.8, f"Browsing {domain} ({brand_name})")
    await accept_cookies(page)
    await smooth_scroll(page, steps=6)

    raw = await page.evaluate(
        """({ slug, brandName }) => {
            const out = [];
            const seen = new Set();
            const bEsc = brandName.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
            const anchors = Array.from(document.querySelectorAll('a[href]'));
            for (const a of anchors) {
                const rawHref = a.getAttribute('href') || '';
                if (!new RegExp(slug, 'i').test(rawHref)) continue;
                const fullUrl = a.href.split('?')[0];
                const basePath = fullUrl.split('#')[0];
                if (basePath.endsWith('/' + slug) || seen.has(basePath)) continue;

                const card = a.closest('[class*="productCard"], [data-testid*="product"], li, article') || a.parentElement;
                if (!card) continue;
                const fullText = (card.innerText || '').replace(/\\s+/g, ' ').trim();
                if (!/£\\d+/.test(fullText)) continue;
                seen.add(basePath);

                // Extract clean product title starting from brandName up to the first £ price
                let title = '';
                const m = fullText.match(new RegExp('(' + bEsc + '\\\\s+.+?)(?:\\\\s+£\\\\d+)', 'i'));
                if (m && m[1]) {
                    title = m[1].trim();
                } else {
                    title = fullText.split(/£\\d+/)[0].replace(/^.*?CODE:\\s*\\S+\\s*/i, '').trim();
                }
                if (!title || title.length < 4) continue;

                const priceMatches = fullText.match(/£(\\d+(?:\\.\\d{2})?)/g) || [];
                const prices = priceMatches.map(p => parseFloat(p.replace('£', '')));
                const price = prices.length > 0 ? prices[0] : null;
                const compareAt = prices.length > 1 && prices[1] > price ? prices[1] : null;
                const isOos = /\\bout of stock\\b|\\bsold out\\b|\\bunavailable\\b/i.test(fullText);

                out.push({ title, url: fullUrl, basePath, price, compareAt, available: !isOos });
            }
            return out;
        }""",
        {"slug": slug, "brandName": brand_name},
    )

    skus = []
    for item in raw:
        title = item["title"]
        m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets|sachets))\b", title, re.I)
        v_title = m_size.group(1) if m_size else "Standard"
        path_slug = item["basePath"].split("/")[-1]
        skus.append({
            "sku_key": f"{domain}::{slug}::{path_slug}",
            "product_title": title,
            "variant_title": v_title,
            "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
            "product_url": item["url"],
            "sku_code": path_slug,
            "price": item["price"],
            "compare_at_price": item["compareAt"],
            "currency": "GBP",
            "available": bool(item["available"]),
        })
    return skus


async def scrape_bathandunwind_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Calibrated Bath & Unwind Engine: extracts `.card.category-processed` tiles and stock/pre-order states."""
    domain = store["domain"]
    brand_url = store["brand_url"]
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]

    await page.goto(brand_url, wait_until="domcontentloaded", timeout=35000)
    await human_pause(2.5, 4.2, f"Browsing {domain} ({brand_name})")
    await accept_cookies(page)
    await smooth_scroll(page, steps=5)

    raw = await page.evaluate(
        """(brandName) => {
            const out = [];
            const seen = new Set();
            const cards = document.querySelectorAll('.card.category-processed, article.card, .productGrid .product');
            for (const card of cards) {
                const a = card.querySelector('a[href]');
                if (!a) continue;
                const url = (a.href || '').split('?')[0].split('#')[0];
                if (!url || url.includes('/brands/') || seen.has(url)) continue;
                seen.add(url);

                const fullText = (card.innerText || '').replace(/\\s+/g, ' ').trim();
                const h = card.querySelector('.card-title, h2, h3, h4');
                let title = h ? h.innerText.replace(/\\s+/g, ' ').trim() : (a.innerText || '').replace(/\\s+/g, ' ').trim();
                if (!title || title.length < 4) {
                    const slugPart = url.replace(/\\/$/, '').split('/').slice(-1)[0];
                    title = slugPart.replace(/-/g, ' ');
                }

                // Exclude "Worth: £XX.XX" when picking shelf price
                const cleanedPriceText = fullText.replace(/Worth:\\s*£\\d+(?:\\.\\d{2})?/gi, '');
                const hasPriceRange = /£\\d+\\.\\d{2}\\s*-\\s*£\\d+\\.\\d{2}/.test(cleanedPriceText);
                const priceMatches = cleanedPriceText.match(/£(\\d+\\.\\d{2})/g) || [];
                const prices = priceMatches.map(p => parseFloat(p.replace('£', '')));
                const price = prices.length > 0 ? prices[prices.length - 1] : null;
                const compareAt = (!hasPriceRange && prices.length > 1 && prices[0] > price) ? prices[0] : null;
                const isOos = /\\bout of stock\\b|\\bsold out\\b|\\bpre-order\\b|\\bunavailable\\b/i.test(fullText);

                out.push({ title, url, price, compareAt, available: !isOos, hasPriceRange, prices });
            }
            return out;
        }""",
        brand_name,
    )

    skus = []
    for item in raw:
        path_slug = item["url"].rstrip("/").split("/")[-1]
        if item.get("hasPriceRange"):
            try:
                await human_pause(1.8, 3.0, f"Expanding multi-size options on {domain}: {item['title']}")
                await page.goto(item["url"], wait_until="domcontentloaded", timeout=30000)
                opts = await page.evaluate(
                    """() => Array.from(document.querySelectorAll('.form-option-variant')).map(el => el.innerText.replace(/\\s+/g, ' ').trim()).filter(Boolean)"""
                )
                if opts:
                    prices_list = item.get("prices") or [item["price"]]
                    for idx_o, opt_txt in enumerate(opts):
                        opt_price = prices_list[idx_o] if idx_o < len(prices_list) else prices_list[-1]
                        opt_slug = re.sub(r"[^a-z0-9]+", "-", opt_txt.lower()).strip("-")
                        skus.append({
                            "sku_key": f"{domain}::{slug}::{path_slug}::{opt_slug}",
                            "product_title": f"{item['title']} ({opt_txt})",
                            "variant_title": opt_txt,
                            "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, item["title"]),
                            "product_url": item["url"],
                            "sku_code": f"{path_slug}-{opt_slug}",
                            "price": opt_price,
                            "compare_at_price": None,
                            "currency": "GBP",
                            "available": bool(item["available"]),
                        })
                    continue
            except Exception:
                pass

        title = item["title"]
        m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets|sachets))\b", title, re.I)
        v_title = m_size.group(1) if m_size else "Standard"
        skus.append({
            "sku_key": f"{domain}::{slug}::{path_slug}",
            "product_title": title,
            "variant_title": v_title,
            "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
            "product_url": item["url"],
            "sku_code": path_slug,
            "price": item["price"],
            "compare_at_price": item["compareAt"],
            "currency": "GBP",
            "available": bool(item["available"]),
        })
    return skus


async def scrape_custom_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Dispatch to calibrated Major UK Retailer engine or generic custom UK store scraper."""
    domain = store["domain"].lower().removeprefix("www.")
    if domain == "spacenk.com":
        return await scrape_spacenk_store(page, store, brand_cfg)
    if domain in ("cultbeauty.co.uk", "cultbeauty.com", "lookfantastic.com"):
        return await scrape_thg_store(page, store, brand_cfg)
    if domain == "hollandandbarrett.com":
        return await scrape_hb_store(page, store, brand_cfg)
    if domain == "boots.com":
        return await scrape_boots_store(page, store, brand_cfg)
    if domain in ("harveynichols.com", "flannels.com", "houseoffraser.co.uk"):
        return await scrape_frasers_store(page, store, brand_cfg)
    if domain == "bathandunwind.com":
        return await scrape_bathandunwind_store(page, store, brand_cfg)

    brand_url = store["brand_url"]
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]

    await page.goto(brand_url, wait_until="domcontentloaded", timeout=30000)
    await human_pause(2.4, 4.0, f"Browsing {domain} ({brand_name})")
    await smooth_scroll(page, steps=3)

    if store.get("platform") == "WooCommerce":
        woo_items = await page.evaluate(
            """async (brandName) => {
                try {
                    const r = await fetch(`/wp-json/wc/store/v1/products?search=${encodeURIComponent(brandName)}&per_page=50`);
                    if (r.ok) {
                        const data = await r.json();
                        if (Array.isArray(data)) return data;
                    }
                } catch (e) {}
                return [];
            }""",
            brand_name,
        )
        if woo_items:
            skus = []
            for p in woo_items:
                title = html.unescape(p.get("name") or "").strip()
                b_tag = (p.get("brands") or [{}])[0].get("name", "") if p.get("brands") else ""
                if not sme_brands.matches_brand(brand_cfg, b_tag, title):
                    continue
                prices_obj = p.get("prices") or {}
                minor = int(prices_obj.get("currency_minor_unit", 2))
                raw_p = prices_obj.get("price")
                price_val = round(float(raw_p) / (10 ** minor), 2) if raw_p and str(raw_p).isdigit() else None
                raw_reg = prices_obj.get("regular_price")
                reg_val = round(float(raw_reg) / (10 ** minor), 2) if raw_reg and str(raw_reg).isdigit() else None
                comp_val = reg_val if (reg_val and price_val and reg_val > price_val) else None
                m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets))\b", title, re.I)
                v_title = m_size.group(1) if m_size else "Standard"
                sku_key = f"{domain}::{slug}::{p.get('id') or title.lower()}"
                skus.append({
                    "sku_key": sku_key,
                    "product_title": title,
                    "variant_title": v_title,
                    "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
                    "product_url": p.get("permalink") or brand_url,
                    "sku_code": p.get("sku") or "",
                    "price": price_val,
                    "compare_at_price": comp_val,
                    "currency": prices_obj.get("currency_code") or "GBP",
                    "available": bool(p.get("is_in_stock", True)),
                })
            if skus:
                return skus

    if domain == "bodykind.com":
        items = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.product')).map(el => {
                const a = el.querySelector('a[href*="-p"]');
                const title = a ? (a.getAttribute('title') || a.innerText || '').trim() : '';
                const url = a ? a.href : '';
                const text = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                const outOfStock = /out of stock|sold out|unavailable/i.test(text);
                return { title, url, text, available: !outOfStock };
            }).filter(x => x.title);
        }""")
    elif domain == "biggreensmile.com":
        items = await page.evaluate(
            """(slug) => {
                const seen = new Set();
                const out = [];
                for (const a of document.querySelectorAll('a[href*="/products/"]')) {
                    const url = a.href.split('#')[0];
                    const title = (a.innerText || a.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
                    if (!title || title.toLowerCase().includes('find out more') || seen.has(url)) continue;
                    seen.add(url);
                    const card = a.closest('li, .product, .item, div[class*="product"], div[class*="item"]') || a.parentElement;
                    const text = card ? card.innerText.replace(/\\s+/g, ' ').trim() : title;
                    const outOfStock = /out of stock|sold out|unavailable|email me when/i.test(text) || !/\\bbuy\\b|\\badd\\b/i.test(text);
                    out.push({ title, url, text, available: !outOfStock });
                }
                return out;
            }""",
            slug,
        )
    else:
        items = await page.evaluate("""() => {
            const seen = new Set();
            const out = [];
            for (const a of document.querySelectorAll('a[href]')) {
                const url = a.href.split('?')[0].split('#')[0];
                if (!url.startsWith(location.origin)) continue;
                const text = (a.innerText || a.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
                if (!text || seen.has(url)) continue;
                seen.add(url);
                const card = a.closest('td, li, .product, article, div') || a.parentElement;
                const cardText = card ? card.innerText.replace(/\\s+/g, ' ').trim() : text;
                const outOfStock = /out of stock|sold out|unavailable|discontinued/i.test(cardText);
                out.push({ title: text, url, text: cardText.slice(0, 300), available: !outOfStock });
            }
            return out;
        }""")

    skus = []
    for item in items:
        raw_title = html.unescape(re.sub(r"^£\d+\.\d{2}\s*\(incl VAT\)\s*", "", item["title"])).strip()
        if not sme_brands.matches_brand(brand_cfg, "", f"{raw_title} {item['url']}"):
            continue
        # Reject brand collection pages, pagination links, or generic navigation links
        if re.search(r"/(?:brands|collections|category|categories)/", item["url"], re.I):
            continue
        if re.search(
            r"^(?:next|prev|previous|next\s+product|previous\s+product|view\s+all|read\s+more|back\s+to)\b",
            raw_title,
            re.I,
        ):
            continue
        if raw_title.lower() in (
            brand_name.lower(),
            f"› {brand_name.lower()}",
            f"see all {brand_name.lower()} products",
        ):
            continue
        # If raw_title is a filename/slug like 'balmonds-gentle-face-wash.html', humanize it
        if re.search(r"\.(?:html?|aspx|php)$", raw_title, re.I) or ("-" in raw_title and " " not in raw_title):
            raw_title = re.sub(r"\.(?:html?|aspx|php)$", "", raw_title, flags=re.I).replace("-", " ").title()

        norm_key = sme_brands.normalize_product_family_key(brand_cfg, raw_title)
        if not norm_key or norm_key in (f"{slug}_sku", f"other_{slug}_sku", "next_product", "previous_product"):
            continue

        m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets))\b", raw_title, re.I)
        v_title = m_size.group(1) if m_size else "Standard"
        prices = [float(x) for x in re.findall(r"[£$](\d+\.\d{2})", item["text"])]
        price_val = prices[0] if prices else None
        comp_val = prices[1] if len(prices) > 1 and prices[1] > prices[0] else None
        currency = "GBP" if ("£" in item["text"] or price_val is None) else "USD"
        path_slug = urlparse(item["url"]).path.strip("/").replace("/", "_") or raw_title.lower()
        sku_key = f"{domain}::{slug}::{path_slug}"
        skus.append({
            "sku_key": sku_key,
            "product_title": raw_title,
            "variant_title": v_title,
            "normalized_product_key": norm_key,
            "product_url": item["url"],
            "sku_code": "",
            "price": price_val,
            "compare_at_price": comp_val,
            "currency": currency,
            "available": bool(item["available"]),
        })

    return skus


def format_duration_since(iso_ts: str | None, now: datetime) -> tuple[str, float]:
    if not iso_ts:
        return "-", 0.0
    dt = datetime.fromisoformat(iso_ts)
    delta_hours = max(0.0, (now - dt).total_seconds() / 3600.0)
    days = int(delta_hours // 24)
    hours = int(delta_hours % 24)
    if days > 0:
        return f"{days}d {hours}h (since {dt.strftime('%Y-%m-%d %H:%M UTC')})", round(delta_hours / 24.0, 1)
    return f"{hours}h (first detected {dt.strftime('%Y-%m-%d %H:%M UTC')})", round(delta_hours / 24.0, 2)


def generate_intelligence_report_for_brand(conn, brand_cfg: dict) -> dict:
    brand_name = brand_cfg["name"]
    slug = brand_cfg["slug"]
    now = datetime.now(timezone.utc)

    stores = [dict(r) for r in conn.execute("SELECT * FROM stores WHERE brand = ? ORDER BY domain", (brand_name,)).fetchall()]
    skus = [dict(r) for r in conn.execute("SELECT * FROM skus WHERE brand = ? ORDER BY domain, product_title", (brand_name,)).fetchall()]
    events = [dict(r) for r in conn.execute("SELECT * FROM stock_events WHERE brand = ? ORDER BY id DESC LIMIT 50", (brand_name,)).fetchall()]

    active_skus = [s for s in skus if s["is_listed"] == 1]
    oos_skus = [s for s in active_skus if s["is_available"] == 0]
    silent_removed = [s for s in skus if s["is_listed"] == 0]

    dtc_set = {d.lower().removeprefix("www.") for d in brand_cfg.get("dtc_domains", [])}
    retail_stores = [st for st in stores if st["domain"].lower().removeprefix("www.") not in dtc_set]
    total_retail_stores = max(1, len(retail_stores))

    # Refresh canonical normalized_product_key across all SKUs and build DTC + Retailer lookup maps
    dtc_by_norm: dict[str, list[dict]] = defaultdict(list)
    retail_in_stock_by_norm: dict[str, set[str]] = defaultdict(set)
    retail_oos_by_norm: dict[str, set[str]] = defaultdict(set)
    retail_stores_by_norm: dict[str, set[str]] = defaultdict(set)
    labels_by_norm_key: dict[str, Counter] = defaultdict(Counter)
    retail_prices_by_norm: dict[str, dict[str, float]] = defaultdict(dict)

    for s in active_skus:
        combined_title = f"{s['product_title']} {s.get('variant_title') or ''}"
        nk = sme_brands.normalize_product_family_key(brand_cfg, combined_title)
        if nk == "renaissance_cleansing_gel_100ml" and s.get("current_price") and s["current_price"] < 25.0:
            nk = "renaissance_cleansing_gel_35ml"
            if s.get("variant_title") == "Standard":
                s["variant_title"] = "35ml (Travel)"
        if nk != s.get("normalized_product_key"):
            s["normalized_product_key"] = nk
            conn.execute("UPDATE skus SET normalized_product_key = ? WHERE sku_key = ?", (nk, s["sku_key"]))
        if not nk or len(nk) < 3:
            continue
        dom = s["domain"]
        is_dtc_dom = dom.lower().removeprefix("www.") in dtc_set
        clean_lbl = s["product_title"].split("|")[0].strip()
        if nk == "renaissance_cleansing_gel_200ml":
            clean_lbl = "Renaissance Cleansing Gel (200ml Supersize)"
        elif nk == "renaissance_cleansing_gel_35ml":
            clean_lbl = "Renaissance Cleansing Gel (35ml Travel)"
        elif nk == "renaissance_cleansing_gel_100ml":
            clean_lbl = "Renaissance Cleansing Gel (100ml)"
        labels_by_norm_key[nk][clean_lbl] += (3 if is_dtc_dom else 1)

        if is_dtc_dom:
            dtc_by_norm[nk].append(s)
        else:
            retail_stores_by_norm[nk].add(dom)
            if s["is_available"] == 1:
                retail_in_stock_by_norm[nk].add(dom)
            else:
                retail_oos_by_norm[nk].add(dom)
            if s.get("current_price"):
                prev_p = retail_prices_by_norm[nk].get(dom)
                if prev_p is None or s["current_price"] > prev_p:
                    retail_prices_by_norm[nk][dom] = s["current_price"]
    conn.commit()

    def get_dtc_reference(norm_key: str, variant_hint: str = "") -> tuple[str, float | None]:
        """Return (dtc_status_code, dtc_rrp) for a normalized product key."""
        dtc_matches = dtc_by_norm.get(norm_key, [])
        if not dtc_matches:
            return ("NOT_ON_DTC", None)
        vh = (variant_hint or "").lower().replace(" ", "")
        sized = [m for m in dtc_matches if vh and vh != "standard" and vh in (m.get("variant_title") or "").lower().replace(" ", "")]
        if sized:
            pool = sized
        else:
            # Prefer full-size standard retail variants over travel minis, refills, or 5L spa trade sizes
            std_pool = [
                m for m in dtc_matches
                if not re.search(r"\b(?:travel|refill|5\s*litre|10\s*ml|7\s*ml|5\.5\s*ml|14\s*ml|15\s*ml|7\s*capsules|14\s*capsules)\b", (m.get("variant_title") or ""), re.I)
            ]
            pool = std_pool if std_pool else dtc_matches
        any_in_stock = any(m["is_available"] == 1 for m in pool)
        prices = [m["current_price"] for m in pool if m.get("current_price")]
        rrp = max(prices) if prices else None
        return ("IN_STOCK_ON_DTC" if any_in_stock else "OOS_ON_DTC", rrp)

    hero_benchmarks = []
    all_retail_doms = {st["domain"] for st in retail_stores}
    for norm_key, dom_set in sorted(retail_stores_by_norm.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        pct = round(100.0 * len(dom_set) / total_retail_stores)
        best_label = labels_by_norm_key[norm_key].most_common(1)[0][0] if labels_by_norm_key[norm_key] else norm_key.replace("_", " ").title()
        dtc_state, dtc_rrp = get_dtc_reference(norm_key)
        undercut_notes = []
        if dtc_rrp:
            for r_dom, r_price in sorted(retail_prices_by_norm[norm_key].items()):
                if r_price < dtc_rrp * 0.92:
                    diff_pct = round(100 * (1 - r_price / dtc_rrp))
                    undercut_notes.append(f"`{r_dom}` £{r_price:.2f} (-{diff_pct}% vs RRP)")
        hero_benchmarks.append({
            "normalized_key": norm_key,
            "product_family": best_label,
            "dtc_status": dtc_state,
            "dtc_rrp": dtc_rrp,
            "stores_carrying": len(dom_set),
            "total_stores": total_retail_stores,
            "penetration_pct": pct,
            "is_hero": len(dom_set) >= 2,
            "in_stock_in": sorted(retail_in_stock_by_norm.get(norm_key, set())),
            "oos_in": sorted(retail_oos_by_norm.get(norm_key, set()) - retail_in_stock_by_norm.get(norm_key, set())),
            "missing_in": sorted(all_retail_doms - dom_set),
            "undercut_alerts": undercut_notes,
        })

    oos_enriched = []
    retail_oos_enriched = []
    dtc_oos_enriched = []
    for s in oos_skus:
        dur_str, days_float = format_duration_since(s["first_seen_oos_at"], now)
        nk = s["normalized_product_key"]
        dtc_state, dtc_rrp = get_dtc_reference(nk, s.get("variant_title") or "")
        is_dtc_dom = s["domain"].lower().removeprefix("www.") in dtc_set

        price_note = "Full Price"
        if s["compare_at_price"] and s["current_price"] and s["compare_at_price"] > s["current_price"]:
            disc_pct = round(100 * (1 - s["current_price"] / s["compare_at_price"]))
            price_note = f"Discounted -{disc_pct}% (was £{s['compare_at_price']:.2f})"
        elif dtc_rrp and s["current_price"] and s["current_price"] < dtc_rrp * 0.92:
            disc_pct = round(100 * (1 - s["current_price"] / dtc_rrp))
            price_note = f"Below DTC RRP -{disc_pct}% (DTC £{dtc_rrp:.2f})"

        competing_in_stock = sorted(d for d in retail_in_stock_by_norm.get(nk, set()) if d != s["domain"])
        if is_dtc_dom:
            diagnosis = "Brand DTC Warehouse OOS"
        elif dtc_state == "IN_STOCK_ON_DTC":
            diagnosis = "🚨 UNFORCED RETAIL OUTAGE (In Stock on DTC)"
        elif dtc_state == "OOS_ON_DTC":
            diagnosis = "⚠️ FACTORY SHORTAGE (Also OOS on DTC)"
        else:
            diagnosis = f"🚨 RETAIL OUTAGE (In Stock at {len(competing_in_stock)} other retailers)" if competing_in_stock else "Retail Exclusive OOS"

        enriched_item = {
            **s,
            "duration_label": dur_str,
            "days_oos": days_float,
            "price_note": price_note,
            "dtc_status": dtc_state,
            "dtc_rrp": dtc_rrp,
            "diagnosis": diagnosis,
            "in_stock_elsewhere": competing_in_stock,
        }
        oos_enriched.append(enriched_item)
        if is_dtc_dom:
            dtc_oos_enriched.append(enriched_item)
        else:
            retail_oos_enriched.append(enriched_item)

    report_payload = {
        "brand": brand_name,
        "brand_slug": slug,
        "generated_at": now.isoformat(timespec="seconds"),
        "summary": {
            "monitored_uk_stores": len(stores),
            "monitored_retail_stockists": len(retail_stores),
            "total_listed_skus_variants": len(active_skus),
            "in_stock_skus_variants": len(active_skus) - len(oos_enriched),
            "out_of_stock_skus_variants": len(oos_enriched),
            "retail_out_of_stock_variants": len(retail_oos_enriched),
            "unforced_retail_outages": sum(1 for x in retail_oos_enriched if "UNFORCED" in x["diagnosis"] or "RETAIL OUTAGE" in x["diagnosis"]),
            "factory_shortages_on_dtc": sum(1 for x in retail_oos_enriched if "FACTORY SHORTAGE" in x["diagnosis"]),
            "silent_removed_skus": len(silent_removed),
        },
        "out_of_stock_alerts": oos_enriched,
        "retail_out_of_stock_alerts": retail_oos_enriched,
        "dtc_out_of_stock": dtc_oos_enriched,
        "hero_benchmarks": [h for h in hero_benchmarks if h["is_hero"]],
        "silent_removals": silent_removed,
        "recent_events": events,
    }

    report_json_path = REPORTS_DIR / f"{slug}_intelligence_report.json"
    report_md_path = REPORTS_DIR / f"{slug}_intelligence_report.md"
    report_json_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# UK Stockist Out-of-Stock (OOS) Intelligence Report: {brand_name}",
        "",
        f"- **Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **Monitored Storefronts:** {len(stores)} (1 Official DTC Master Catalog + {len(retail_stores)} Major UK Stockists)",
        f"- **Total Tracked Variants:** {len(active_skus)} ({len(active_skus) - len(oos_enriched)} In Stock | **{len(oos_enriched)} OOS**)",
        f"- **Retailer Out-of-Stock Alerts:** **{len(retail_oos_enriched)}** (**{report_payload['summary']['unforced_retail_outages']} Unforced Retail Outages** vs. **{report_payload['summary']['factory_shortages_on_dtc']} Brand Warehouse Shortages**)",
        f"- **Removed / Delisted Variants:** **{len(silent_removed)}**",
        "",
        "---",
        "",
        "## 1A. Major UK Retailer Out-of-Stock Alerts (Cross-Checked Against Official DTC)",
        "",
    ]
    if retail_oos_enriched:
        lines += [
            "| Retailer | Product | Size / Variant | Shelf Price | DTC RRP | Diagnosis (Step 1A DTC Cross-Check) | Competing Retailers Currently In Stock | Time OOS |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for item in retail_oos_enriched:
            p_str = f"£{item['current_price']:.2f}" if item["current_price"] else "-"
            rrp_str = f"£{item['dtc_rrp']:.2f}" if item.get("dtc_rrp") else "-"
            safe_title = item["product_title"].replace("|", "—")
            elsewhere = ", ".join(f"`{d}`" for d in item["in_stock_elsewhere"][:5]) if item["in_stock_elsewhere"] else "_None_"
            lines.append(
                f"| `{item['domain']}` | {safe_title} | {item['variant_title']} | {p_str} ({item['price_note']}) | {rrp_str} | "
                f"**{item['diagnosis']}** | {elsewhere} | **{item['duration_label']}** |"
            )
    else:
        lines.append("_All tracked variants across monitored UK retail stockists are currently In Stock._")

    lines += [
        "",
        "### 1B. Official Brand DTC Master Catalog Out-of-Stock Items (Reference Baseline)",
        "",
    ]
    if dtc_oos_enriched:
        lines += [
            "| Official DTC Store | Product | Size / Variant | DTC RRP | First Seen OOS |",
            "|---|---|---|---|---|",
        ]
        for item in dtc_oos_enriched:
            p_str = f"£{item['current_price']:.2f}" if item["current_price"] else "-"
            lines.append(
                f"| `{item['domain']}` | {item['product_title'].replace('|', '—')} | {item['variant_title']} | {p_str} | {item['first_seen_oos_at'] or '-'} |"
            )
    else:
        lines.append("_100% of active products on the official Brand DTC storefront are currently In Stock._")

    lines += [
        "",
        "---",
        "",
        "## 2. Cross-Retailer Hero Assortment & RRP Price Comparison Matrix",
        "",
        "| Core Product Family | DTC Status & RRP | UK Stockists Carrying | Stockists In Stock | Stockists OOS | Price Undercutting / RRP Alerts | Missing From Stockists (Assortment Gap) |",
        "|---|---|---|---|---|---|---|",
    ]
    for h in hero_benchmarks:
        if not h["is_hero"]:
            continue
        dtc_lbl = f"✅ £{h['dtc_rrp']:.2f}" if (h["dtc_status"] == "IN_STOCK_ON_DTC" and h["dtc_rrp"]) else (
            f"⚠️ OOS (£{h['dtc_rrp']:.2f})" if (h["dtc_status"] == "OOS_ON_DTC" and h["dtc_rrp"]) else "Retail Only"
        )
        in_str = ", ".join(f"`{d}`" for d in h["in_stock_in"]) or "-"
        oos_str = ", ".join(f"**`{d}`**" for d in h["oos_in"]) or "-"
        undercut_str = "; ".join(h["undercut_alerts"]) if h["undercut_alerts"] else "At RRP"
        miss_str = ", ".join(f"`{d}`" for d in h["missing_in"][:5]) + (f" (+{len(h['missing_in'])-5} more)" if len(h["missing_in"]) > 5 else "")
        lines.append(
            f"| **{h['product_family']}** | {dtc_lbl} | **{h['stores_carrying']}/{h['total_stores']}** ({h['penetration_pct']}%) | {in_str} | {oos_str} | {undercut_str} | {miss_str or '_All Stockists_'} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Removed / Delisted Variants (Diffed Against Previous Scans)",
        "",
    ]
    if silent_removed:
        lines += [
            "| Store | Product | Variant | Last Seen Price | Removed At |",
            "|---|---|---|---|---|",
        ]
        for sr in silent_removed:
            p_str = f"£{sr['current_price']:.2f}" if sr["current_price"] else "-"
            lines.append(
                f"| `{sr['domain']}` | {sr['product_title'].replace('|', '—')} | {sr['variant_title']} | {p_str} | {sr['silent_removed_at']} |"
            )
    else:
        lines.append(
            "_No removed variants detected yet._"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Stockist Summary",
        "",
        "| Store | Tier | Platform | Total Variants | In Stock | Out of Stock | Storefront URL |",
        "|---|---|---|---|---|---|---|",
    ]
    for st in stores:
        dom = st["domain"]
        tier_lbl = sme_brands.stockist_tier(dom)
        st_skus = [s for s in active_skus if s["domain"] == dom]
        st_oos = [s for s in oos_enriched if s["domain"] == dom]
        st_in = len(st_skus) - len(st_oos)
        lines.append(
            f"| `{dom}` | {tier_lbl} | {st['platform']} | {len(st_skus)} | {st_in} | **{len(st_oos)}** | {st['brand_url']} |"
        )

    content = "\n".join(lines) + "\n"
    report_md_path.write_text(content, encoding="utf-8")
    if slug == "balmonds":
        (HERE / "balmonds_intelligence_report.md").write_text(content, encoding="utf-8")
        (HERE / "balmonds_intelligence_report.json").write_text(
            json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(f"Generated {brand_name} Intelligence Report:\n  - {report_md_path}\n  - {report_json_path}")
    return report_payload


async def audit_single_brand(
    context, conn, brand_cfg: dict, only_domains: set[str] | None, report_only: bool, discover_if_missing: bool
) -> dict:
    slug = brand_cfg["slug"]
    brand_name = brand_cfg["name"]
    stockist_file = STOCKISTS_DIR / f"{slug}_uk_stockists.json"

    if not report_only:
        stockists = []
        if stockist_file.exists():
            data = json.loads(stockist_file.read_text(encoding="utf-8"))
            stockists = data.get("verified_stockists", [])
        else:
            # Check if stores already exist in SQLite/Supabase for this brand
            db_stores = conn.execute(
                "SELECT domain, platform, brand_url FROM stores WHERE brand = ? ORDER BY domain",
                (brand_name,),
            ).fetchall()
            if db_stores:
                stockists = [dict(r) for r in db_stores]
            elif discover_if_missing:
                print(f"No stockist file yet for {brand_name} — running UK stockist discovery first...")
                disc_data = await discover_uk_stockists.discover_for_brand(context, brand_cfg, skip_search=False)
                stockists = disc_data.get("verified_stockists", [])
            else:
                print(f"Skipping live scrape for {brand_name}: no stockists found (pass --discover to find UK stockists).")
                return generate_intelligence_report_for_brand(conn, brand_cfg)

        dtc_set = {d.lower().removeprefix("www.") for d in brand_cfg.get("dtc_domains", [])}
        targets = [s for s in stockists if not only_domains or s["domain"] in only_domains]
        # Enforce Step 1A (DTC Master Catalog First) -> Step 1B (Major UK Retailers)
        targets.sort(key=lambda s: (0 if s["domain"].lower().removeprefix("www.") in dtc_set else 1, s["domain"]))

        page = await context.new_page()
        for idx, store in enumerate(targets, 1):
            dom = store["domain"]
            step_lbl = "Step 1A: DTC Master Catalog" if dom.lower().removeprefix("www.") in dtc_set else "Step 1B: Major Retailer"
            print(f"[{brand_name} {idx}/{len(targets)} — {step_lbl}] Auditing {dom} ({store.get('platform', 'unknown')})...")
            try:
                if (store.get("platform") or "").lower() == "shopify":
                    scraped = await scrape_shopify_store(page, store, brand_cfg)
                else:
                    scraped = await scrape_custom_store(page, store, brand_cfg)
                stats = db.record_store_snapshot(
                    conn, dom, brand_name, store.get("platform", "unknown"), store["brand_url"], scraped
                )
                in_cnt = sum(1 for x in scraped if x["available"])
                oos_cnt = sum(1 for x in scraped if not x["available"])
                print(f"    -> Recorded {stats['seen']} SKU/variants ({in_cnt} in stock, {oos_cnt} OOS)")
            except Exception as exc:
                print(f"    -> Error auditing {dom} for {brand_name}: {exc}")
            if idx < len(targets):
                await human_pause(3.0, 5.5, f"Natural pause before next retailer")
        await page.close()

    return generate_intelligence_report_for_brand(conn, brand_cfg)


def select_next_batch_brands(conn, batch_size: int) -> list[dict]:
    """Select the next `batch_size` brands ordered by oldest last_checked_at (never-checked brands first)."""
    rows = conn.execute(
        "SELECT brand, MAX(last_checked_at) AS last_ts FROM stores GROUP BY brand"
    ).fetchall()
    last_checked_by_brand = {r["brand"]: r["last_ts"] for r in rows}

    scored = []
    for idx, b in enumerate(sme_brands.SME_BRANDS):
        ts = last_checked_by_brand.get(b["name"], "")
        # Never checked brands have ts == "" so they sort first, then oldest timestamp
        scored.append((0 if not ts else 1, ts, idx, b))

    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    selected = [item[3] for item in scored[:batch_size]]
    print(
        f"Auto-batch ({batch_size}): selected {', '.join(b['name'] for b in selected)}"
    )
    return selected


async def run_cli(args) -> None:
    conn = db.get_conn()
    pulled = db.pull_supabase_to_sqlite(conn)
    if pulled["stores"] or pulled["skus"]:
        print(f"Synced state from Supabase: {pulled['stores']} stores, {pulled['skus']} SKUs")

    if args.list_brands:
        print(f"Configured {len(sme_brands.SME_BRANDS)} UK SME Brands:")
        rows = conn.execute("SELECT brand, COUNT(*) AS cnt, MAX(last_checked_at) AS ts FROM stores GROUP BY brand").fetchall()
        db_info = {r["brand"]: (r["cnt"], r["ts"]) for r in rows}
        for i, b in enumerate(sme_brands.SME_BRANDS, 1):
            st_file = STOCKISTS_DIR / f"{b['slug']}_uk_stockists.json"
            if b["name"] in db_info:
                cnt, ts = db_info[b["name"]]
                status = f"{cnt} stores in DB (last checked {ts})"
            elif st_file.exists():
                status = "stockists ready"
            else:
                status = "pending discovery"
            print(f"  {i:2d}. {b['name']:<24} (slug: {b['slug']:<18} | {status})")
        conn.close()
        return

    if args.auto_batch:
        target_brands = select_next_batch_brands(conn, args.auto_batch)
    elif args.all:
        target_brands = sme_brands.SME_BRANDS
    elif args.brands:
        target_brands = [sme_brands.get_brand(b) for b in args.brands]
    elif args.brand:
        target_brands = [sme_brands.get_brand(args.brand)]
    else:
        target_brands = [sme_brands.get_brand("balmonds")]

    only_set = set(args.only) if args.only else None

    if args.report_only:
        for b in target_brands:
            generate_intelligence_report_for_brand(conn, b)
        conn.close()
        return

    async with async_playwright() as p:
        launch_args = [
            "--headless=new",
            "--disable-blink-features=AutomationControlled",
            "--window-size=1440,900",
        ]
        try:
            browser = await p.chromium.launch(channel="chrome", headless=True, args=launch_args)
        except Exception:
            browser = await p.chromium.launch(headless=True, args=launch_args)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="en-GB",
            timezone_id="Europe/London",
            extra_http_headers={
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            },
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-GB', 'en']});
            window.chrome = window.chrome || { runtime: {} };
            """
        )

        for idx, b in enumerate(target_brands, 1):
            await audit_single_brand(
                context, conn, b, only_set, args.report_only, args.discover
            )
            if idx < len(target_brands):
                await human_pause(4.0, 7.5, "Natural breather before next brand")

        await browser.close()

    conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-brands", action="store_true", help="List all 24 configured UK SME brands")
    ap.add_argument("--brand", help="Single brand name or slug to audit")
    ap.add_argument("--brands", nargs="+", help="Multiple brand names or slugs to audit")
    ap.add_argument("--all", action="store_true", help="Audit all 24 UK SME brands")
    ap.add_argument("--auto-batch", type=int, metavar="N", help="Automatically select the next N brands (oldest/unchecked first) for 24/7 rotation")
    ap.add_argument("--discover", action="store_true", help="Auto-discover UK stockists if stockist file does not exist yet")
    ap.add_argument("--only", nargs="+", help="Audit only specified store domains")
    ap.add_argument("--report-only", action="store_true", help="Regenerate report from SQLite without scraping")
    args = ap.parse_args()
    asyncio.run(run_cli(args))


if __name__ == "__main__":
    main()
