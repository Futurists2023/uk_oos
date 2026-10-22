"""Multi-Brand UK Independent E-Commerce Stockist Discovery Engine.

Supports all 24 UK SME Beauty & Wellness brands defined in `sme_brands.py`.

Usage:
    python discover_uk_stockists.py --list-brands
    python discover_uk_stockists.py --brand "Bare Biology"
    python discover_uk_stockists.py --brands bare-biology evolve georganics
    python discover_uk_stockists.py --all
    python discover_uk_stockists.py --brand upcircle --skip-search
"""
import argparse
import asyncio
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote, quote_plus

from playwright.async_api import async_playwright

import sme_brands

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
STOCKISTS_DIR = HERE / "stockists"
STOCKISTS_DIR.mkdir(parents=True, exist_ok=True)

# 1. Exclusion lists: Large chains, marketplaces, supermarkets, department stores, and all 24 brands' DTC sites
ALL_DTC_DOMAINS = {
    dom for b in sme_brands.SME_BRANDS for dom in b.get("dtc_domains", [])
}

EXCLUDED_CHAINS_AND_MARKETPLACES = ALL_DTC_DOMAINS | {
    # Marketplaces
    "amazon.co.uk", "amazon.com", "ebay.co.uk", "ebay.com", "etsy.com",
    "onbuy.com", "fruugo.co.uk", "fruugo.com", "aliexpress.com", "temu.com",
    "notonthehighstreet.com", "ebay.ie", "ubuy.co.uk", "desertcart.co.uk",
    # High-street chains & major pharmacy chains
    "boots.com", "hollandandbarrett.com", "superdrug.com", "lloydspharmacy.com",
    "well.co.uk", "rowlandspharmacy.co.uk", "daylewis.co.uk", "numarknet.com",
    # Supermarkets
    "tesco.com", "sainsburys.co.uk", "asda.com", "morrisons.com",
    "waitrose.com", "ocado.com", "aldi.co.uk", "lidl.co.uk", "iceland.co.uk",
    # Department stores & major beauty conglomerates
    "johnlewis.com", "selfridges.com", "harrods.com", "libertylondon.com",
    "marksandspencer.com", "next.co.uk", "debenhams.com", "houseoffraser.co.uk",
    "fenwick.co.uk", "harveynichols.com",
    "lookfantastic.com", "cultbeauty.co.uk", "cultbeauty.com", "feelunique.com",
    "sephora.co.uk", "sephora.com", "spacenk.com", "notino.co.uk", "beautybay.com",
    "escentual.com", "asos.com", "very.co.uk", "argos.co.uk", "tkmaxx.com",
}

EXCLUDED_NON_RETAIL = {
    "google.com", "google.co.uk", "bing.com", "duckduckgo.com", "yahoo.com",
    "uservoice.com", "facebook.com", "instagram.com", "tiktok.com", "youtube.com",
    "pinterest.co.uk", "pinterest.com", "twitter.com", "x.com", "linkedin.com",
    "reddit.com", "trustpilot.com", "feefo.com", "reviews.io", "yell.com",
    "thomsonlocal.com", "checkatrade.com", "wikipedia.org", "incidecoder.com",
    "skinsafeproducts.com", "hotukdeals.com", "vouchercodes.co.uk",
    "myvouchercodes.co.uk", "topcashback.co.uk", "quidco.com", "klarna.com",
    "clearpay.co.uk", "paypal.com", "shopify.com", "companieshouse.gov.uk",
    "gov.uk", "nhs.uk", "eczema.org", "psoriasis-association.org.uk",
    "mumsnet.com", "netmums.com", "beautypedia.com", "makeupalley.com",
    "cosmopolitan.com", "vogue.co.uk", "glamourmagazine.co.uk", "elle.com",
    "theguardian.com", "independent.co.uk", "telegraph.co.uk", "dailymail.co.uk",
    "mirror.co.uk", "thesun.co.uk", "marieclaire.co.uk", "goodhousekeeping.com",
    "whowhatwear.com", "womanandhome.com", "getthegloss.com", "sheerluxe.com",
    "faire.com", "ankorstore.com", "creoate.com", "orderchamp.com", "claires.co.uk",
    "pricecheck.co.uk", "pricespy.co.uk", "idealo.co.uk", "kelkoo.co.uk",
    "skinshare.co.uk", "offspring.co.uk", "latestdeals.co.uk", "lovethesales.com",
    "britishbeautycouncil.com", "cewuk.co.uk", "diarydirectory.com",
}

# Master pool of known UK independent clean beauty, apothecary, eco & health retailers
UK_INDEPENDENT_RETAILER_POOL = [
    "contentbeautywellbeing.com",
    "bodykind.com",
    "mypure.co.uk",
    "biggreensmile.com",
    "onlynaturals.co.uk",
    "expresschemist.co.uk",
    "planetorganic.com",
    "quickvit.co.uk",
    "baldwins.co.uk",
    "dulwichhealth.co.uk",
    "johnandginger.co.uk",
    "naturisimo.com",
    "gloworganic.co.uk",
    "plasticfreedom.co.uk",
    "allnaturalme.co.uk",
    "ohmycream.co.uk",
    "liveinthelight.co.uk",
    "blommabeauty.com",
    "victoriahealth.com",
    "ziracle.com",
    "justbeyoutiful.co.uk",
    "ethicalhouse.co.uk",
    "peacewiththewild.co.uk",
    "ethicalsuperstore.com",
    "babipur.co.uk",
    "ecco-verde.co.uk",
    "regn.co.uk",
    "riverandpark.co.uk",
    "therapyorganics.co.uk",
    "citysurvivor.co.uk",
    "naturedoc.shop",
    "thelighttechnique.com",
    "elysiantheory.co.uk",
    "supplementhub.co.uk",
    "shop.zenhealthcare.co.uk",
    "yourhealthbasket.co.uk",
]


def clean_domain(url_or_domain: str) -> str:
    if not url_or_domain.startswith("http"):
        url_or_domain = "https://" + url_or_domain
    try:
        host = urlparse(url_or_domain).netloc.lower()
    except Exception:
        return ""
    host = re.sub(r"^www\.", "", host)
    return host.split(":")[0]


def is_excluded_domain(domain: str) -> tuple[bool, str]:
    if not domain or "." not in domain:
        return True, "Invalid domain"
    for ex in EXCLUDED_CHAINS_AND_MARKETPLACES:
        if domain == ex or domain.endswith("." + ex):
            return True, f"Excluded chain/marketplace/DTC ({ex})"
    for ex in EXCLUDED_NON_RETAIL:
        if domain == ex or domain.endswith("." + ex):
            return True, f"Excluded non-retail/directory ({ex})"
    non_uk_tlds = (
        ".com.au", ".co.nz", ".co.za", ".ca", ".de", ".fr", ".es", ".it",
        ".nl", ".pl", ".se", ".dk", ".no", ".fi", ".ie", ".ch", ".at", ".be",
        ".pt", ".cz", ".hu", ".ro", ".bg", ".gr", ".sg", ".hk", ".jp", ".in",
        ".ae", ".sa", ".my", ".ph", ".us", ".gov", ".edu", ".ac.uk", ".nhs.uk",
    )
    if any(domain.endswith(tld) for tld in non_uk_tlds):
        return True, f"Non-UK TLD ({domain})"
    return False, ""


async def human_pause(min_s: float = 1.8, max_s: float = 3.5, label: str = "") -> None:
    delay = random.uniform(min_s, max_s)
    if label:
        print(f"    [pause {delay:.1f}s] {label}")
    await asyncio.sleep(delay)


async def smooth_scroll(page, steps: int = 2) -> None:
    for _ in range(steps):
        await page.mouse.wheel(0, random.randint(250, 480))
        await asyncio.sleep(random.uniform(0.6, 1.2))


def extract_organic_yahoo(hrefs: list[str]) -> list[str]:
    out = []
    for h in hrefs:
        u = h
        if "RU=http" in h:
            m = re.search(r"RU=([^/&]+)", h)
            if m:
                u = unquote(m.group(1))
        if not u.startswith("http"):
            continue
        if any(x in u for x in ("yahoo.com", "bing.com", "msclkid=")):
            continue
        if u not in out:
            out.append(u)
    return out


def build_search_queries_for_brand(brand: dict) -> list[str]:
    name = brand["name"]
    hint = brand.get("search_hint", f'"{name}"')
    return [
        f'"{name}" {hint} site:.co.uk',
        f'"{name}" "add to basket" OR "add to cart" site:.co.uk',
        f'inurl:collections/{brand["slug"]} OR inurl:brands/{brand["slug"]} site:.co.uk',
    ]


async def discover_from_search(page, brand: dict) -> dict[str, list[str]]:
    """Run human-paced Yahoo UK search queries for `brand`."""
    discovered: dict[str, list[str]] = {}
    queries = build_search_queries_for_brand(brand)
    print(f"\n=== STEP 1 ({brand['name']}): Human-Paced Yahoo UK Search Discovery ===")

    for idx, query in enumerate(queries, 1):
        print(f"  [{idx}/{len(queries)}] Searching: {query}")
        try:
            await page.goto(
                f"https://uk.search.yahoo.com/search?p={quote_plus(query)}",
                wait_until="domcontentloaded",
                timeout=22000,
            )
            await human_pause(2.0, 3.4, "Reading search results")
            if idx == 1:
                try:
                    btn = page.locator("button[name='agree'], button:has-text('Accept all')").first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await human_pause(1.5, 2.5, "Accepted Yahoo UK cookie banner")
                except Exception:
                    pass

            await smooth_scroll(page, steps=2)
            hrefs = await page.evaluate(
                "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
            )
            urls = extract_organic_yahoo(hrefs)
            new_domains = 0
            for actual_url in urls:
                dom = clean_domain(actual_url)
                excluded, _ = is_excluded_domain(dom)
                if not excluded:
                    if dom not in discovered:
                        discovered[dom] = []
                        new_domains += 1
                    if actual_url not in discovered[dom]:
                        discovered[dom].append(actual_url)
            print(f"    -> Found {len(urls)} organic links (+{new_domains} new UK domains)")
        except Exception as e:
            print(f"    -> Search query note: {e}")

    return discovered


def build_store_hint_urls(domain: str, brand: dict, search_hints: list[str]) -> list[str]:
    """Generate brand-specific candidate URLs on a given UK retailer domain."""
    slug = brand["slug"]
    name_q = quote_plus(brand["name"])
    urls = list(search_hints)
    if domain == "biggreensmile.com":
        urls.append(f"https://www.biggreensmile.com/brands/{slug}.aspx?brand={name_q}")
    elif domain == "expresschemist.co.uk":
        urls.append(f"https://www.expresschemist.co.uk/{slug}.html")
    elif domain == "bodykind.com":
        urls.append(f"https://www.bodykind.com/search/?q={name_q}")
    return urls


async def check_storefront_for_brand(
    context, domain: str, brand: dict, hint_urls: list[str], source: str
) -> dict:
    """Visit a candidate UK store at a human pace and check if it stocks `brand`."""
    page = await context.new_page()
    slug = brand["slug"]
    aliases_lower = [a.lower() for a in brand["aliases"]]

    result = {
        "domain": domain,
        "brand": brand["name"],
        "brand_slug": slug,
        "source": source,
        "is_uk": False,
        "uk_signals": [],
        "is_ecommerce": False,
        "stocks_brand": False,
        "brand_url": None,
        "product_count": 0,
        "in_stock_count": None,
        "out_of_stock_count": None,
        "sample_products": [],
        "platform": "unknown",
        "notes": "",
    }

    try:
        candidates = build_store_hint_urls(domain, brand, hint_urls) + [
            f"https://www.{domain}",
            f"https://{domain}",
        ]
        loaded_resp = None
        for u_cand in candidates:
            try:
                resp = await page.goto(u_cand, wait_until="domcontentloaded", timeout=20000)
                if resp and resp.status < 400 and page.url.startswith("http"):
                    # Avoid staying on a generic brands redirect if it didn't match
                    if "brands/brands.aspx" in page.url.lower():
                        continue
                    loaded_resp = resp
                    break
            except Exception:
                continue

        if not loaded_resp or not page.url.startswith("http"):
            result["notes"] = "Unreachable or HTTP error"
            await page.close()
            return result

        final_domain = clean_domain(page.url)
        excluded, ex_reason = is_excluded_domain(final_domain)
        if excluded:
            result["notes"] = f"Redirected to excluded domain {final_domain} ({ex_reason})"
            await page.close()
            return result

        await human_pause(1.8, 3.2, f"Browsing {domain} for {brand['name']}")
        await smooth_scroll(page, steps=2)

        meta = await page.evaluate("""() => {
            const html = document.documentElement.outerHTML;
            const text = (document.body ? document.body.innerText : '');
            const hasPound = text.includes('£') || html.includes('&pound;') || html.includes('GBP');
            const hasUkText = /\\b(united kingdom|uk delivery|royal mail|uk mainland|england|scotland|wales|london|derbyshire|sussex|yorkshire|vat no|company no|registered in england|\\+44|0800)\\b/i.test(text)
                || /\\b(en-gb|en_gb|gbp|\\.co\\.uk)\\b/i.test(html);
            const isShopify = html.includes('Shopify.shop') || html.includes('cdn.shopify.com');
            const isWoo = html.includes('woocommerce') || html.includes('wp-content/plugins/woocommerce');
            const isBigCommerce = html.includes('bigcommerce') || html.includes('stencil');
            const isMagento = html.includes('Mage.Cookies') || html.includes('magento') || html.includes('mage/');
            const hasCart = /\\b(add to basket|add to bag|add to cart|checkout|my basket|shopping bag|shopping cart|buy now|view basket|in stock|out of stock)\\b/i.test(text)
                || !!document.querySelector('[href*="cart"], [href*="basket"], [href*="checkout"], form[action*="cart"], [class*="basket"], [class*="cart"]');
            return { hasPound, hasUkText, isShopify, isWoo, isBigCommerce, isMagento, hasCart };
        }""")

        if domain.endswith(".co.uk") or domain.endswith(".org.uk") or domain.endswith(".uk"):
            result["uk_signals"].append(".co.uk/.uk TLD")
        if meta["hasPound"]:
            result["uk_signals"].append("£ GBP currency")
        if meta["hasUkText"]:
            result["uk_signals"].append("UK address/shipping/VAT/locale")

        result["is_uk"] = bool(
            domain.endswith(".co.uk")
            or domain.endswith(".uk")
            or meta["hasPound"]
            or meta["hasUkText"]
        )

        if meta["isShopify"]:
            result["platform"] = "Shopify"
        elif meta["isWoo"]:
            result["platform"] = "WooCommerce"
        elif meta["isBigCommerce"]:
            result["platform"] = "BigCommerce"
        elif meta["isMagento"]:
            result["platform"] = "Magento"

        result["is_ecommerce"] = bool(meta["hasCart"] or result["platform"] != "unknown")
        origin = f"{urlparse(page.url).scheme}://{urlparse(page.url).netloc}"

        # Strategy A: Shopify store check
        if meta["isShopify"]:
            shopify_raw = await page.evaluate(
                """async ({ slug, brandName, aliases }) => {
                    const candidatePaths = [
                        `/collections/${slug}/products.json?limit=250`,
                        `/collections/${slug.replace(/-/g, '')}/products.json?limit=250`,
                    ];
                    for (const path of candidatePaths) {
                        try {
                            const r = await fetch(path);
                            if (r.ok) {
                                const data = await r.json();
                                if (data && Array.isArray(data.products) && data.products.length > 0) {
                                    return { source: path.split('/products.json')[0], products: data.products };
                                }
                            }
                        } catch (e) {}
                    }
                    try {
                        const r = await fetch(`/search/suggest.json?q=${encodeURIComponent(brandName)}&resources[type]=product&resources[limit]=25`);
                        if (r.ok) {
                            const data = await r.json();
                            const prods = (((data || {}).resources || {}).results || {}).products || [];
                            if (prods.length > 0) {
                                return { source: `/search?q=${encodeURIComponent(brandName)}`, products: prods };
                            }
                        }
                    } catch (e) {}
                    return null;
                }""",
                {"slug": slug, "brandName": brand["name"], "aliases": aliases_lower},
            )

            if shopify_raw and shopify_raw.get("products"):
                matched_prods = []
                for p in shopify_raw["products"]:
                    vendor = p.get("vendor") or ""
                    title = p.get("title") or ""
                    if sme_brands.matches_brand(brand, vendor, title):
                        avail = (
                            any(v.get("available") for v in p["variants"])
                            if isinstance(p.get("variants"), list)
                            else bool(p.get("available", True))
                        )
                        matched_prods.append({"title": title, "available": avail})

                if matched_prods:
                    result["stocks_brand"] = True
                    result["is_ecommerce"] = True
                    result["product_count"] = len(matched_prods)
                    result["in_stock_count"] = sum(1 for x in matched_prods if x["available"])
                    result["out_of_stock_count"] = sum(1 for x in matched_prods if not x["available"])
                    result["brand_url"] = f"{origin}{shopify_raw['source']}"
                    result["sample_products"] = [x["title"] for x in matched_prods[:5]]
                    await page.close()
                    return result

            if not hint_urls:
                result["notes"] = f"Shopify store does not stock {brand['name']}"
                await page.close()
                return result

        # Strategy B: WooCommerce Store API check
        if meta["isWoo"]:
            woo_raw = await page.evaluate(
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
                brand["name"],
            )
            if woo_raw:
                matched_woo = [
                    p for p in woo_raw
                    if sme_brands.matches_brand(
                        brand,
                        (p.get("brands") or [{}])[0].get("name", "") if p.get("brands") else "",
                        p.get("name") or "",
                    )
                ]
                if matched_woo:
                    result["stocks_brand"] = True
                    result["is_ecommerce"] = True
                    result["product_count"] = len(matched_woo)
                    result["in_stock_count"] = sum(1 for p in matched_woo if p.get("is_in_stock") is True)
                    result["out_of_stock_count"] = sum(1 for p in matched_woo if p.get("is_in_stock") is False)
                    result["brand_url"] = f"{origin}/?s={quote_plus(brand['name'])}&post_type=product"
                    result["sample_products"] = [p.get("name", "") for p in matched_woo[:5]]
                    await page.close()
                    return result

        # Strategy C: DOM link inspection on current page or search page
        dom_links = await page.evaluate(
            """(slug) => {
                const seen = new Set();
                const out = [];
                const currentPath = location.pathname.replace(/\\/+$/, '').toLowerCase();
                for (const a of document.querySelectorAll('a[href]')) {
                    const href = a.href.split('#')[0];
                    if (!href.startsWith(location.origin)) continue;
                    const path = new URL(href).pathname.replace(/\\/+$/, '').toLowerCase();
                    if (!path || path === '/' || path === currentPath) continue;
                    if (/\\/(cart|basket|checkout|login|account|contact|about|terms|privacy|blog|news|brands)\\b/.test(path)) continue;
                    const text = ((a.innerText || a.getAttribute('title') || '')).replace(/\\s+/g, ' ').trim();
                    if (!seen.has(href)) {
                        seen.add(href);
                        out.push({ title: text, path, url: href });
                    }
                }
                const h1 = document.querySelector('h1') ? document.querySelector('h1').innerText.replace(/\\s+/g, ' ').trim() : '';
                return { links: out, h1, currentUrl: location.href };
            }""",
            slug,
        )

        matched_dom = []
        for item in dom_links["links"]:
            t = item["title"]
            p_path = item["path"]
            last_seg = p_path.split("/")[-1]
            if last_seg in (slug, f"{slug}.html", f"{slug}.aspx") or re.match(rf"^{re.escape(slug)}-m\d+$", last_seg):
                continue
            if t.lower() in (brand["name"].lower(), f"› {brand['name'].lower()}", f"see all {brand['name'].lower()} products"):
                continue
            if sme_brands.matches_brand(brand, "", f"{t} {p_path.replace('-', ' ')}"):
                matched_dom.append(item)

        if not matched_dom and sme_brands.matches_brand(brand, "", dom_links["h1"]):
            if dom_links["h1"].lower() != brand["name"].lower():
                matched_dom.append({"title": dom_links["h1"], "url": dom_links["currentUrl"]})

        if matched_dom:
            result["stocks_brand"] = True
            result["is_ecommerce"] = True
            result["brand_url"] = page.url
            result["product_count"] = len(matched_dom)
            result["sample_products"] = [m["title"][:100] or m["url"] for m in matched_dom[:5]]

    except Exception as e:
        result["notes"] = str(e)[:150]
    finally:
        await page.close()

    return result


async def discover_for_brand(context, brand: dict, skip_search: bool = False) -> dict:
    slug = brand["slug"]
    name = brand["name"]

    search_discovered: dict[str, list[str]] = {}
    if not skip_search:
        s_page = await context.new_page()
        search_discovered = await discover_from_search(s_page, brand)
        await s_page.close()

    all_candidates: dict[str, dict] = {}
    for dom in UK_INDEPENDENT_RETAILER_POOL:
        c_dom = clean_domain(dom)
        excluded, _ = is_excluded_domain(c_dom)
        if not excluded:
            all_candidates[c_dom] = {"hints": [], "source": "seed_pool"}

    for dom, urls in search_discovered.items():
        if dom in all_candidates:
            for u in urls:
                if u not in all_candidates[dom]["hints"]:
                    all_candidates[dom]["hints"].append(u)
            all_candidates[dom]["source"] = "seed_pool+search"
        else:
            all_candidates[dom] = {"hints": urls, "source": "web_search"}

    print(f"\n=== STEP 2 ({name}): Verifying {len(all_candidates)} Candidate Independent UK Stores ===")
    verified_stockists = []
    checked_all = []

    for idx, (dom, info) in enumerate(all_candidates.items(), 1):
        print(f"  [{idx}/{len(all_candidates)}] Checking {dom} for {name} (source: {info['source']})...")
        res = await check_storefront_for_brand(context, dom, brand, info["hints"], info["source"])
        checked_all.append(res)
        if res["stocks_brand"] and res["is_uk"] and res["is_ecommerce"]:
            verified_stockists.append(res)
            print(
                f"    -> CONFIRMED UK STOCKIST ({name}): {dom} | "
                f"{res['product_count']} product(s) | {res['brand_url']}"
            )

    verified_stockists.sort(key=lambda x: (-x["product_count"], x["domain"]))

    payload = {
        "brand": name,
        "brand_slug": slug,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_candidates_checked": len(checked_all),
        "verified_uk_independent_stockists_count": len(verified_stockists),
        "verified_stockists": verified_stockists,
    }

    out_json = STOCKISTS_DIR / f"{slug}_uk_stockists.json"
    out_md = STOCKISTS_DIR / f"{slug}_uk_stockists.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        f"# Independent UK E-Commerce Stockists: {name}",
        "",
        f"- **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **Candidate UK stores inspected:** {len(checked_all)}",
        f"- **Verified Independent UK Stockists:** **{len(verified_stockists)}**",
        f"- **Excluded DTC domains:** {', '.join(f'`{d}`' for d in brand.get('dtc_domains', []))}",
        "",
        "| # | Independent UK Store | Platform | Products Found | In Stock / OOS | Source | Brand / Collection / Search URL |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(verified_stockists, 1):
        stock_col = (
            f"{s['in_stock_count']} in / {s['out_of_stock_count']} OOS"
            if s["in_stock_count"] is not None
            else "Verified on page"
        )
        md_lines.append(
            f"| {i} | `{s['domain']}` | {s['platform']} | **{s['product_count']}** | {stock_col} | {s['source']} | {s['brand_url']} |"
        )
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"\nSaved {name} stockists to:\n  - {out_json}\n  - {out_md}")
    return payload


async def run_cli(args) -> None:
    if args.list_brands:
        print(f"Configured {len(sme_brands.SME_BRANDS)} UK SME Brands:")
        for i, b in enumerate(sme_brands.SME_BRANDS, 1):
            print(f"  {i:2d}. {b['name']:<24} (slug: {b['slug']})")
        return

    target_brands = []
    if args.all:
        target_brands = sme_brands.SME_BRANDS
    elif args.brands:
        target_brands = [sme_brands.get_brand(b) for b in args.brands]
    elif args.brand:
        target_brands = [sme_brands.get_brand(args.brand)]
    else:
        target_brands = [sme_brands.get_brand("balmonds")]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="en-GB",
            timezone_id="Europe/London",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        for b in target_brands:
            await discover_for_brand(context, b, skip_search=args.skip_search)

        await browser.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-brands", action="store_true", help="List all 24 configured UK SME brands")
    ap.add_argument("--brand", help="Single brand name or slug to discover")
    ap.add_argument("--brands", nargs="+", help="Multiple brand names or slugs to discover")
    ap.add_argument("--all", action="store_true", help="Run discovery across all 24 UK SME brands")
    ap.add_argument("--skip-search", action="store_true", help="Check only the 33 curated UK independent retailers without web search")
    args = ap.parse_args()
    asyncio.run(run_cli(args))


if __name__ == "__main__":
    main()
