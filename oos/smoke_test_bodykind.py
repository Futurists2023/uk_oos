"""Smoke test: Human-emulated browsing on bodykind.com for Balmonds products."""
import asyncio
import json
import random
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")


async def human_pause(min_s: float = 2.5, max_s: float = 4.5, label: str = "") -> None:
    delay = random.uniform(min_s, max_s)
    if label:
        print(f"  [human pause {delay:.1f}s] {label}")
    await asyncio.sleep(delay)


async def smooth_scroll(page, steps: int = 4) -> None:
    """Scroll down gradually like a human reading the page."""
    for _ in range(steps):
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
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = await context.new_page()

        print("1. Visiting Balmonds brand page on bodykind.com: https://www.bodykind.com/balmonds-m245 ...")
        await page.goto("https://www.bodykind.com/balmonds-m245", wait_until="domcontentloaded", timeout=45000)
        await human_pause(3.0, 5.0, "Reading Balmonds brand page")

        # Dismiss #cookie_alert if visible
        try:
            cookie_btn = page.locator("#cookie_alert button, #cookie_alert a.button, #cookie_alert .btn").first
            if await cookie_btn.is_visible(timeout=2000):
                await cookie_btn.click()
                print("  Accepted cookie banner")
                await human_pause(1.5, 2.5)
        except Exception:
            pass

        await smooth_scroll(page, steps=5)
        await human_pause(2.5, 4.0, "Finished scrolling product list")

        # Extract full details from each .product card and check pagination
        data = await page.evaluate("""() => {
            const paginationText = Array.from(document.querySelectorAll('.pagination, .pages, .showing, .results, .product-count, .total'))
                .map(el => el.innerText.replace(/\\s+/g, ' ').trim());

            const products = Array.from(document.querySelectorAll('.product')).map((el, idx) => {
                const titleEl = el.querySelector('.product__title, .title, h2, h3, h4, a[title]');
                const linkEl = el.querySelector('a[href*="-p"]');
                const priceEl = el.querySelector('.product__price, .price, .now, [class*="price"]');
                const buttonEl = el.querySelector('button, .button, .btn, [class*="stock"], [class*="buy"], [class*="basket"]');
                const rawText = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                return {
                    index: idx + 1,
                    title: titleEl ? titleEl.innerText.replace(/\\s+/g, ' ').trim() : '',
                    url: linkEl ? linkEl.href : '',
                    price_text: priceEl ? priceEl.innerText.replace(/\\s+/g, ' ').trim() : '',
                    button_or_stock: buttonEl ? buttonEl.innerText.replace(/\\s+/g, ' ').trim() : '',
                    raw_text: rawText,
                    html: el.innerHTML.slice(0, 800)
                };
            });

            return {
                paginationText,
                productCount: products.length,
                products
            };
        }""")

        print(f"Pagination / count indicators: {data['paginationText']}")
        print(f"Total Balmonds products found: {data['productCount']}")
        print(json.dumps(data["products"], indent=2, ensure_ascii=False))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
