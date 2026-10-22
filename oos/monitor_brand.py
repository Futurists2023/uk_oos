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

    skus = []
    mode = raw_products.get("mode")
    for p in raw_products.get("products", []):
        title = (p.get("title") or "").strip()
        vendor = (p.get("vendor") or "").strip()
        if not sme_brands.matches_brand(brand_cfg, vendor, title):
            continue

        handle = p.get("handle") or (p.get("url") or "").split("/products/")[-1].split("?")[0]
        prod_url = f"{origin}/products/{handle}" if handle else brand_url
        variants = p.get("variants") or []

        if variants:
            for v in variants:
                v_title = (v.get("title") or "Default").strip()
                if v_title.lower() == "default title":
                    m_size = re.search(r"(\d+\s*(?:ml|g|caps|capsules|tablets|sachets))\b", title, re.I)
                    v_title = m_size.group(1) if m_size else "Standard"
                raw_price = v.get("price")
                if isinstance(raw_price, int) or (mode in ("product_js", "suggest_js") and isinstance(raw_price, (int, float)) and raw_price > 100):
                    price_val = round(float(raw_price) / 100.0, 2)
                else:
                    price_val = parse_gbp_price(raw_price)

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
                    "normalized_product_key": sme_brands.normalize_product_family_key(brand_cfg, title),
                    "product_url": prod_url,
                    "sku_code": v.get("sku") or "",
                    "price": price_val,
                    "compare_at_price": comp_val,
                    "currency": "GBP",
                    "available": bool(v.get("available")),
                })
        else:
            price_val = parse_gbp_price(p.get("price"))
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


async def scrape_custom_store(page, store: dict, brand_cfg: dict) -> list[dict]:
    """Visit custom/Magento/WooCommerce/ASPX UK store at human pace and extract products for `brand_cfg`."""
    domain = store["domain"]
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

    # Group products across stores by normalized product family key to find Hero SKUs
    total_stores = max(1, len(stores))
    stores_by_norm_key: dict[str, set[str]] = defaultdict(set)
    labels_by_norm_key: dict[str, Counter] = defaultdict(Counter)

    for s in active_skus:
        nk = sme_brands.normalize_product_family_key(brand_cfg, s["product_title"])
        if not nk or len(nk) < 3:
            continue
        stores_by_norm_key[nk].add(s["domain"])
        clean_lbl = s["product_title"].split("|")[0].strip()
        labels_by_norm_key[nk][clean_lbl] += 1

    hero_benchmarks = []
    for norm_key, dom_set in sorted(stores_by_norm_key.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        pct = round(100.0 * len(dom_set) / total_stores)
        best_label = labels_by_norm_key[norm_key].most_common(1)[0][0] if labels_by_norm_key[norm_key] else norm_key.replace("_", " ").title()
        hero_benchmarks.append({
            "normalized_key": norm_key,
            "product_family": best_label,
            "stores_carrying": len(dom_set),
            "total_stores": total_stores,
            "penetration_pct": pct,
            "is_hero": pct >= 50 and len(dom_set) >= 2,
            "missing_in": sorted(set(st["domain"] for st in stores) - dom_set),
        })

    hero_map = {h["normalized_key"]: h["product_family"] for h in hero_benchmarks if h["is_hero"]}

    oos_enriched = []
    for s in oos_skus:
        dur_str, days_float = format_duration_since(s["first_seen_oos_at"], now)
        price_note = "Full Price"
        if s["compare_at_price"] and s["current_price"] and s["compare_at_price"] > s["current_price"]:
            disc_pct = round(100 * (1 - s["current_price"] / s["compare_at_price"]))
            price_note = f"Discounted -{disc_pct}% (was £{s['compare_at_price']:.2f})"

        oos_enriched.append({
            **s,
            "duration_label": dur_str,
            "days_oos": days_float,
            "price_note": price_note,
        })

    report_payload = {
        "brand": brand_name,
        "brand_slug": slug,
        "generated_at": now.isoformat(timespec="seconds"),
        "summary": {
            "monitored_uk_stores": len(stores),
            "total_listed_skus_variants": len(active_skus),
            "in_stock_skus_variants": len(active_skus) - len(oos_enriched),
            "out_of_stock_skus_variants": len(oos_enriched),
            "silent_removed_skus": len(silent_removed),
        },
        "out_of_stock_alerts": oos_enriched,
        "silent_removals": silent_removed,
        "recent_events": events,
    }

    report_json_path = REPORTS_DIR / f"{slug}_intelligence_report.json"
    report_md_path = REPORTS_DIR / f"{slug}_intelligence_report.md"
    report_json_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# UK Stockist Out-of-Stock (OOS) Report: {brand_name}",
        "",
        f"- **Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **Monitored UK Stockists:** {len(stores)}",
        f"- **Total Tracked Variants:** {len(active_skus)}",
        f"- **In Stock Variants:** {len(active_skus) - len(oos_enriched)}",
        f"- **Out-of-Stock (OOS) Variants:** **{len(oos_enriched)}**",
        f"- **Removed / Unlisted Variants:** **{len(silent_removed)}**",
        "",
        "---",
        "",
        "## 1. Out-of-Stock (OOS) Variants",
        "",
    ]
    if oos_enriched:
        lines += [
            "| Store | Tier | Product | Size / Variant | Shelf Price | First Seen OOS | Time OOS | Price Note |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for item in oos_enriched:
            p_str = f"£{item['current_price']:.2f}" if item["current_price"] else "-"
            safe_title = item["product_title"].replace("|", "—")
            tier_lbl = sme_brands.stockist_tier(item["domain"])
            lines.append(
                f"| `{item['domain']}` | {tier_lbl} | {safe_title} | {item['variant_title']} | {p_str} | "
                f"{item['first_seen_oos_at'] or '-'} | **{item['duration_label']}** | {item['price_note']} |"
            )
    else:
        lines.append("_All tracked variants across monitored UK stockists are currently In Stock._")

    lines += [
        "",
        "---",
        "",
        "## 2. Removed / Delisted Variants (Diffed Against Previous Scans)",
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

        targets = [s for s in stockists if not only_domains or s["domain"] in only_domains]

        page = await context.new_page()
        for idx, store in enumerate(targets, 1):
            dom = store["domain"]
            print(f"[{brand_name} {idx}/{len(targets)}] Auditing {dom} ({store.get('platform', 'unknown')})...")
            try:
                if store.get("platform") == "Shopify":
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
                await human_pause(2.5, 4.8, f"Natural pause before next retailer")
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
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
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
