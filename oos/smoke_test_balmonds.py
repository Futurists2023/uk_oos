"""Smoke test: Human-emulated browsing on contentbeautywellbeing.com for Balmonds products."""
import asyncio
import json
import random
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")


async def human_pause(min_s: float = 2.0, max_s: float = 4.5, label: str = "") -> None:
    delay = random.uniform(min_s, max_s)
    if label:
        print(f"  [human pause {delay:.1f}s] {label}")
    await asyncio.sleep(delay)


async def smooth_scroll(page, steps: int = 4) -> None:
    """Scroll down gradually like a human reading the page."""
    for i in range(steps):
        scroll_amount = random.randint(280, 520)
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.9, 1.8))


async def main() -> None:
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
        # Hide webdriver flag
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = await context.new_page()

        print("1. Visiting homepage: https://www.contentbeautywellbeing.com ...")
        await page.goto("https://www.contentbeautywellbeing.com", wait_until="domcontentloaded", timeout=45000)
        await human_pause(3.0, 5.0, "Looking at the homepage")

        # Dismiss cookie banner if present
        for selector in [
            "button:has-text('Accept')",
            "button:has-text('Allow all')",
            "button:has-text('Accept all')",
            "#shopify-pc__banner__btn-accept",
        ]:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    print(f"  Accepted cookies via {selector}")
                    await human_pause(1.5, 2.5)
                    break
            except Exception:
                pass

        await smooth_scroll(page, steps=2)
        await human_pause(2.0, 3.5, "Browsing navigation menu")

        # Look for Balmonds link or navigate via Brands / Search
        print("2. Looking for Brands page or Balmonds collection...")
        balmonds_url = "https://www.contentbeautywellbeing.com/collections/balmonds"

        # Try clicking Brands or navigating naturally
        try:
            brands_link = page.locator("a[href*='/pages/brands'], a[href*='/collections/brands'], a:has-text('Brands')").first
            if await brands_link.is_visible(timeout=2000):
                href = await brands_link.get_attribute("href")
                print(f"  Found Brands navigation link ({href}), visiting...")
                if href and href.startswith("/"):
                    href = f"https://www.contentbeautywellbeing.com{href}"
                if href and href.startswith("http"):
                    await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                    await human_pause(2.5, 4.5, "Scanning the A-Z brands directory for Balmonds")
                    await smooth_scroll(page, steps=2)
                    balmonds_a = page.locator("a[href*='balmonds' i]").first
                    if await balmonds_a.count() > 0:
                        b_href = await balmonds_a.get_attribute("href")
                        if b_href:
                            balmonds_url = b_href if b_href.startswith("http") else f"https://www.contentbeautywellbeing.com{b_href}"
                            print(f"  Found Balmonds link on Brands page: {balmonds_url}")
        except Exception as e:
            print(f"  (Brands nav step note: {e})")

        print(f"3. Navigating to Balmonds collection: {balmonds_url} ...")
        resp = await page.goto(balmonds_url, wait_until="domcontentloaded", timeout=45000)
        print(f"  Status: {resp.status if resp else 'unknown'} | Final URL: {page.url}")
        await human_pause(3.0, 5.0, "Viewing Balmonds collection page")
        await smooth_scroll(page, steps=4)
        await human_pause(2.0, 3.5, "Finished scrolling product grid")

        # Extract product links from the collection page DOM
        dom_products = await page.evaluate("""() => {
            const seen = new Set();
            const items = [];
            for (const a of document.querySelectorAll('a[href*="/products/"]')) {
                const url = new URL(a.href, location.origin);
                const cleanUrl = url.origin + url.pathname;
                if (seen.has(cleanUrl)) continue;
                const text = (a.innerText || a.textContent || '').trim();
                if (!text) continue;
                seen.add(cleanUrl);
                items.push({ url: cleanUrl, text });
            }
            return items;
        }""")

        print(f"  Found {len(dom_products)} unique product links on collection page.")

        # Also check search results as a human shopper might do if looking for all Balmonds items
        await human_pause(2.5, 4.0, "Checking site search for 'Balmonds' to ensure no products were missed")
        search_url = "https://www.contentbeautywellbeing.com/search?q=Balmonds&type=product"
        print(f"4. Visiting search page: {search_url} ...")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
        await human_pause(3.0, 4.5, "Reading search results")
        await smooth_scroll(page, steps=3)

        search_products = await page.evaluate("""() => {
            const seen = new Set();
            const items = [];
            for (const a of document.querySelectorAll('a[href*="/products/"]')) {
                const url = new URL(a.href, location.origin);
                const cleanUrl = url.origin + url.pathname;
                if (seen.has(cleanUrl)) continue;
                const text = (a.innerText || a.textContent || '').trim();
                if (!text) continue;
                seen.add(cleanUrl);
                items.push({ url: cleanUrl, text });
            }
            return items;
        }""")

        # Combine candidate URLs, normalising /collections/.../products/<slug> -> /products/<slug>
        all_urls = []
        seen_handles = set()
        for item in dom_products + search_products:
            u = item["url"]
            if "/products/" in u:
                handle = u.split("/products/", 1)[1].split("?")[0].strip("/")
                canonical = f"https://www.contentbeautywellbeing.com/products/{handle}"
                if handle not in seen_handles:
                    seen_handles.add(handle)
                    all_urls.append(canonical)

        print(f"5. Inspecting {len(all_urls)} candidate product pages at a relaxed human pace...")
        balmonds_products = []
        for idx, prod_url in enumerate(all_urls, 1):
            await human_pause(2.5, 4.5, f"Opening product {idx}/{len(all_urls)}")
            await page.goto(prod_url, wait_until="domcontentloaded", timeout=45000)
            await smooth_scroll(page, steps=2)

            # Read Shopify's embedded product JSON or fetch .js from the browser context
            prod_data = await page.evaluate("""async () => {
                try {
                    const r = await fetch(location.pathname + '.js');
                    if (r.ok) return await r.json();
                } catch (e) {}
                return null;
            }""")

            if prod_data:
                vendor = (prod_data.get("vendor") or "").strip()
                title = prod_data.get("title") or ""
                if "balmonds" in vendor.lower() or "balmonds" in title.lower():
                    variants = [
                        {
                            "title": v.get("title"),
                            "price_gbp": f"£{v.get('price', 0) / 100:.2f}",
                            "available": v.get("available"),
                            "sku": v.get("sku"),
                        }
                        for v in prod_data.get("variants", [])
                    ]
                    balmonds_products.append({
                        "title": title,
                        "vendor": vendor,
                        "url": prod_url,
                        "available": prod_data.get("available"),
                        "variants": variants,
                    })
                    print(f"    -> Confirmed Balmonds product: {title} ({len(variants)} variant(s))")
                else:
                    print(f"    -> Skipped non-Balmonds item: {title} (vendor: {vendor})")

        await browser.close()

        print("\n=== SMOKE TEST SUMMARY ===")
        print(f"Total Balmonds products found: {len(balmonds_products)}")
        print(json.dumps(balmonds_products, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
