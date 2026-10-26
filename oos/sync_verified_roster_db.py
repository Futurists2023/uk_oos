"""Database Cleanup & Deterministic Store Seeding for the 53 Verified UK Scale-Up Brands.

Performs two non-scraping operations:
1. Removes retired micro-artisan brands (brands whose `name` is not in `sme_brands.SME_BRANDS`)
   from local SQLite (`oos_state.db`) and Supabase (`stores`, `skus`, `stock_events`).
2. Registers/updates each verified brand's Official DTC Store (Step 1A) + Verified Major UK Retailers (Step 1B)
   into the `stores` table (SQLite + Supabase) with calibrated URLs, without initiating any OOS scraping.
"""
from datetime import datetime, timezone

import requests

import db
import sme_brands


def build_retailer_brand_url(retailer: str, brand_cfg: dict) -> tuple[str, str]:
    """Return calibrated (platform, brand_url) for a verified major UK retailer or DTC domain."""
    slug = brand_cfg["slug"]

    if retailer == "spacenk.com":
        letter = "%23" if slug[0].isdigit() else slug[0].lower()
        return ("SpaceNK", f"https://www.spacenk.com/uk/brands/{letter}/{slug}")
    if retailer == "cultbeauty.co.uk":
        return ("THG", f"https://www.cultbeauty.co.uk/c/brands/{slug}/")
    if retailer == "lookfantastic.com":
        return ("THG", f"https://www.lookfantastic.com/c/brands/{slug}/")
    if retailer == "ohmycream.co.uk":
        return ("Shopify", f"https://www.ohmycream.co.uk/collections/{slug}")
    if retailer == "hollandandbarrett.com":
        return ("HollandAndBarrett", f"https://www.hollandandbarrett.com/shop/brands/{slug}/")
    if retailer == "boots.com":
        return ("Boots", f"https://www.boots.com/{slug}")
    if retailer == "superdrug.com":
        return ("Custom", f"https://www.superdrug.com/brand/{slug}")
    if retailer == "sephora.co.uk":
        return ("Custom", f"https://www.sephora.co.uk/brands/{slug}")
    if retailer == "planetorganic.com":
        return ("Shopify", f"https://www.planetorganic.com/collections/{slug}")
    if retailer == "healf.com":
        return ("Shopify", f"https://healf.com/collections/{slug}")
    if retailer == "facethefuture.co.uk":
        return ("Shopify", f"https://www.facethefuture.co.uk/collections/{slug}")
    if retailer == "alyaka.com":
        col = f"{slug}-skincare" if slug == "oskia" else slug
        return ("Shopify", f"https://www.alyaka.com/collections/{col}")
    if retailer == "harveynichols.com":
        return ("Frasers", f"https://www.harveynichols.com/{slug}")
    if retailer == "flannels.com":
        return ("Frasers", f"https://www.flannels.com/{slug}")
    if retailer == "houseoffraser.co.uk":
        return ("Frasers", f"https://www.houseoffraser.co.uk/brand/{slug}")
    if retailer == "bathandunwind.com":
        return ("BathAndUnwind", f"https://www.bathandunwind.com/brands/{slug}/")

    # Default / Official DTC store (Step 1A)
    return ("Shopify", f"https://{retailer}")


def main():
    conn = db.get_conn()
    cur = conn.cursor()

    valid_names = {b["name"] for b in sme_brands.SME_BRANDS}
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 1. Identify & purge retired micro-artisan brands from SQLite
    existing_brands = set()
    for table in ("stores", "skus", "stock_events"):
        for r in cur.execute(f"SELECT DISTINCT brand FROM {table}").fetchall():
            if r["brand"]:
                existing_brands.add(r["brand"])

    retired_names = sorted(existing_brands - valid_names)
    if retired_names:
        placeholders = ",".join("?" for _ in retired_names)
        cur.execute(f"DELETE FROM stores WHERE brand IN ({placeholders})", retired_names)
        cur.execute(f"DELETE FROM skus WHERE brand IN ({placeholders})", retired_names)
        cur.execute(f"DELETE FROM stock_events WHERE brand IN ({placeholders})", retired_names)
        conn.commit()
        print(f"Purged {len(retired_names)} retired brands from local SQLite.")

    # 1b. Replace legacy 'naturisimo.com' domain with 'ohmycream.co.uk' (post-acquisition redirect)
    cur.execute("DELETE FROM stores WHERE domain = 'naturisimo.com'")
    cur.execute("UPDATE OR REPLACE skus SET domain = 'ohmycream.co.uk', sku_key = REPLACE(sku_key, 'naturisimo.com::', 'ohmycream.co.uk::'), product_url = REPLACE(product_url, 'naturisimo.com', 'ohmycream.co.uk') WHERE domain = 'naturisimo.com'")
    conn.commit()
    sb_url, sb_key = db.supabase_credentials()
    if sb_url and sb_key:
        for table in ("stores", "skus"):
            try:
                requests.delete(
                    f"{sb_url}/rest/v1/{table}",
                    params={"domain": "eq.naturisimo.com"},
                    headers=db.supabase_headers(sb_key, prefer="return=minimal"),
                    timeout=15,
                )
            except Exception:
                pass

    # 2. Upsert calibrated store URLs for Step 1A (DTC) + Step 1B (Verified Major Retailers)
    updated_count = 0
    for b in sme_brands.SME_BRANDS:
        b_name = b["name"]
        dtc_dom = b["dtc_domains"][0]
        target_domains = [dtc_dom] + [r for r in b.get("verified_retailers", []) if r != dtc_dom]

        for dom in target_domains:
            platform, brand_url = build_retailer_brand_url(dom, b)
            if dom == dtc_dom:
                platform = "Shopify"
                brand_url = f"https://{dom}"

            existing = cur.execute(
                "SELECT * FROM stores WHERE domain = ? AND brand = ?", (dom, b_name)
            ).fetchone()
            if existing:
                cur.execute(
                    "UPDATE stores SET platform = ?, brand_url = ? WHERE domain = ? AND brand = ?",
                    (platform, brand_url, dom, b_name),
                )
            else:
                cur.execute(
                    """INSERT INTO stores (domain, brand, platform, brand_url, first_seen_at, last_checked_at, last_product_count)
                       VALUES (?, ?, ?, ?, ?, ?, 0)""",
                    (dom, b_name, platform, brand_url, now_iso, now_iso),
                )
            updated_count += 1

    conn.commit()
    all_stores = [dict(r) for r in cur.execute("SELECT * FROM stores").fetchall()]
    ok_st = db.sync_rows_to_supabase("stores", all_stores, on_conflict="domain,brand")
    print(f"Upserted {updated_count} calibrated store URLs and synced {len(all_stores)} stores to Supabase: {'OK' if ok_st else 'WARN'}")


if __name__ == "__main__":
    main()
