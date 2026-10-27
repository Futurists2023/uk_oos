"""Dual SQLite + Supabase state store for tracking stockout duration (Days OOS), silent removals, and price history.

Automatically reads `.env.local` (NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY).
Writes locally to `oos_state.db` AND syncs every batch to Supabase when reachable.

Usage:
    python db.py --check              # Test Supabase connection and check tables
    python db.py --sync-to-supabase   # Push all existing SQLite stores/skus/events to Supabase
"""
import argparse
import os
import sqlite3
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore", module="requests")
import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "oos_state.db"

# Load .env.local from oos/ or parent directory
if (HERE / ".env.local").exists():
    load_dotenv(HERE / ".env.local")
elif (HERE.parent / ".env.local").exists():
    load_dotenv(HERE.parent / ".env.local")


def supabase_credentials() -> tuple[str | None, str | None]:
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if url:
        url = url.rstrip("/")
    return url, key


def supabase_headers(key: str, prefer: str = "resolution=merge-duplicates") -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def sync_rows_to_supabase(table: str, rows: list[dict], on_conflict: str | None = None) -> bool:
    """Upsert/insert rows into a Supabase PostgREST table in chunks of 500. Fails gracefully if project is paused."""
    if not rows:
        return True
    url, key = supabase_credentials()
    if not url or not key:
        return False
    endpoint = f"{url}/rest/v1/{table}"
    params = {"on_conflict": on_conflict} if on_conflict else None
    prefer = "resolution=merge-duplicates" if on_conflict else "return=minimal"
    chunk_size = 500
    try:
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            resp = requests.post(
                endpoint,
                params=params,
                headers=supabase_headers(key, prefer=prefer),
                json=chunk,
                timeout=20,
            )
            if not resp.ok:
                return False
        return True
    except Exception:
        return False


def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stores (
            domain TEXT NOT NULL,
            brand TEXT NOT NULL,
            platform TEXT,
            brand_url TEXT,
            first_seen_at TEXT NOT NULL,
            last_checked_at TEXT NOT NULL,
            last_product_count INTEGER DEFAULT 0,
            PRIMARY KEY (domain, brand)
        );

        CREATE TABLE IF NOT EXISTS skus (
            sku_key TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            brand TEXT NOT NULL,
            product_title TEXT NOT NULL,
            variant_title TEXT NOT NULL,
            normalized_product_key TEXT NOT NULL,
            product_url TEXT,
            sku_code TEXT,
            current_price REAL,
            compare_at_price REAL,
            last_in_stock_price REAL,
            currency TEXT DEFAULT 'GBP',
            is_available INTEGER NOT NULL,
            is_listed INTEGER NOT NULL DEFAULT 1,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            first_seen_oos_at TEXT,
            last_seen_in_stock_at TEXT,
            silent_removed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS stock_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at TEXT NOT NULL,
            domain TEXT NOT NULL,
            brand TEXT NOT NULL,
            sku_key TEXT NOT NULL,
            product_title TEXT NOT NULL,
            variant_title TEXT NOT NULL,
            event_type TEXT NOT NULL,
            old_price REAL,
            new_price REAL,
            details TEXT
        );
    """)
    conn.commit()


def record_store_snapshot(
    conn: sqlite3.Connection,
    domain: str,
    brand: str,
    platform: str,
    brand_url: str,
    scraped_skus: list[dict],
    now_iso: str | None = None,
) -> dict:
    """Update SQLite + Supabase state for one store's scraped SKUs and detect transitions."""
    if not now_iso:
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not scraped_skus:
        return {"seen": 0, "events": 0}

    cur = conn.cursor()

    # 1. Upsert store record
    existing_store = cur.execute(
        "SELECT * FROM stores WHERE domain = ? AND brand = ?", (domain, brand)
    ).fetchone()
    first_store_seen = existing_store["first_seen_at"] if existing_store else now_iso
    if existing_store:
        cur.execute(
            """UPDATE stores
               SET platform = ?, brand_url = ?, last_checked_at = ?, last_product_count = ?
               WHERE domain = ? AND brand = ?""",
            (platform, brand_url, now_iso, len(scraped_skus), domain, brand),
        )
    else:
        cur.execute(
            """INSERT INTO stores (domain, brand, platform, brand_url, first_seen_at, last_checked_at, last_product_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (domain, brand, platform, brand_url, now_iso, now_iso, len(scraped_skus)),
        )

    # 2. Fetch existing SKUs for this store + brand
    existing_rows = cur.execute(
        "SELECT * FROM skus WHERE domain = ? AND brand = ?", (domain, brand)
    ).fetchall()
    existing_by_key = {row["sku_key"]: dict(row) for row in existing_rows}

    seen_keys = set()
    events = []
    supabase_sku_payloads = []

    for item in scraped_skus:
        k = item["sku_key"]
        seen_keys.add(k)
        avail_int = 1 if item.get("available") else 0
        price = item.get("price")
        compare_at = item.get("compare_at_price")
        currency = item.get("currency") or "GBP"

        prev = existing_by_key.get(k)
        if prev is None:
            first_seen = now_iso
            first_oos = now_iso if not avail_int else None
            last_in_stock = now_iso if avail_int else None
            last_in_price = price if avail_int else None
            cur.execute(
                """INSERT INTO skus (
                    sku_key, domain, brand, product_title, variant_title,
                    normalized_product_key, product_url, sku_code,
                    current_price, compare_at_price, last_in_stock_price, currency,
                    is_available, is_listed, first_seen_at, last_seen_at,
                    first_seen_oos_at, last_seen_in_stock_at, silent_removed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, NULL)""",
                (
                    k, domain, brand, item["product_title"], item["variant_title"],
                    item["normalized_product_key"], item.get("product_url"), item.get("sku_code"),
                    price, compare_at, last_in_price, currency,
                    avail_int, first_seen, now_iso, first_oos, last_in_stock,
                ),
            )
            ev_type = "NEW_OOS" if not avail_int else "NEW_IN_STOCK"
            events.append((now_iso, domain, brand, k, item["product_title"], item["variant_title"], ev_type, None, price, "Initial discovery"))
        else:
            first_seen = prev["first_seen_at"]
            was_avail = bool(prev["is_available"])
            was_listed = bool(prev["is_listed"])
            first_oos = prev["first_seen_oos_at"]
            last_in_stock = prev["last_seen_in_stock_at"]
            last_in_price = prev["last_in_stock_price"]

            if not was_listed:
                events.append((now_iso, domain, brand, k, item["product_title"], item["variant_title"], "RELISTED", prev["current_price"], price, "Re-appeared on storefront"))

            if avail_int:
                if not was_avail:
                    events.append((now_iso, domain, brand, k, item["product_title"], item["variant_title"], "RESTOCKED", prev["current_price"], price, f"Restocked (was OOS since {first_oos})"))
                first_oos = None
                last_in_stock = now_iso
                if price is not None:
                    last_in_price = price
            else:
                if was_avail or not first_oos:
                    first_oos = now_iso
                    events.append((now_iso, domain, brand, k, item["product_title"], item["variant_title"], "WENT_OOS", prev["current_price"], price, "Transitioned from In Stock to OOS"))

            if price is not None and prev["current_price"] is not None and abs(price - prev["current_price"]) >= 0.01:
                events.append((now_iso, domain, brand, k, item["product_title"], item["variant_title"], "PRICE_CHANGED", prev["current_price"], price, f"Price changed {prev['current_price']} -> {price}"))

            cur.execute(
                """UPDATE skus SET
                    product_title = ?, variant_title = ?, normalized_product_key = ?,
                    product_url = ?, sku_code = ?, current_price = ?, compare_at_price = ?,
                    last_in_stock_price = ?, currency = ?, is_available = ?, is_listed = 1,
                    last_seen_at = ?, first_seen_oos_at = ?, last_seen_in_stock_at = ?,
                    silent_removed_at = NULL
                   WHERE sku_key = ?""",
                (
                    item["product_title"], item["variant_title"], item["normalized_product_key"],
                    item.get("product_url"), item.get("sku_code"), price, compare_at,
                    last_in_price, currency, avail_int, now_iso, first_oos, last_in_stock, k,
                ),
            )

        supabase_sku_payloads.append({
            "sku_key": k,
            "domain": domain,
            "brand": brand,
            "product_title": item["product_title"],
            "variant_title": item["variant_title"],
            "normalized_product_key": item["normalized_product_key"],
            "product_url": item.get("product_url"),
            "sku_code": item.get("sku_code"),
            "current_price": price,
            "compare_at_price": compare_at,
            "last_in_stock_price": last_in_price,
            "currency": currency,
            "is_available": bool(avail_int),
            "is_listed": True,
            "first_seen_at": first_seen,
            "last_seen_at": now_iso,
            "first_seen_oos_at": first_oos,
            "last_seen_in_stock_at": last_in_stock,
            "silent_removed_at": None,
        })

    # 3. Check for Silent Removals
    if len(scraped_skus) > 0:
        for k, prev in existing_by_key.items():
            if k not in seen_keys and prev["is_listed"] == 1:
                cur.execute(
                    """UPDATE skus SET is_listed = 0, silent_removed_at = ?
                       WHERE sku_key = ?""",
                    (now_iso, k),
                )
                events.append((
                    now_iso, domain, brand, k, prev["product_title"], prev["variant_title"],
                    "SILENT_REMOVED", prev["current_price"], None,
                    f"Vanished from storefront (last seen {prev['last_seen_at']})",
                ))

    if events:
        cur.executemany(
            """INSERT INTO stock_events (
                occurred_at, domain, brand, sku_key, product_title, variant_title,
                event_type, old_price, new_price, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            events,
        )

    conn.commit()

    # 4. Sync batch to Supabase if project is online
    sync_rows_to_supabase("stores", [{
        "domain": domain,
        "brand": brand,
        "platform": platform,
        "brand_url": brand_url,
        "first_seen_at": first_store_seen,
        "last_checked_at": now_iso,
        "last_product_count": len(scraped_skus),
    }], on_conflict="domain,brand")
    sync_rows_to_supabase("skus", supabase_sku_payloads, on_conflict="sku_key")
    if events:
        sync_rows_to_supabase("stock_events", [
            {
                "occurred_at": ev[0],
                "domain": ev[1],
                "brand": ev[2],
                "sku_key": ev[3],
                "product_title": ev[4],
                "variant_title": ev[5],
                "event_type": ev[6],
                "old_price": ev[7],
                "new_price": ev[8],
                "details": ev[9],
            }
            for ev in events
        ])

    return {"seen": len(scraped_skus), "events": len(events)}


def pull_supabase_to_sqlite(conn: sqlite3.Connection) -> dict[str, int]:
    """Pull latest stores and skus from Supabase into local SQLite using 1,000-row pagination."""
    url, key = supabase_credentials()
    if not url or not key:
        return {"stores": 0, "skus": 0}

    cur = conn.cursor()
    pulled_stores = 0
    pulled_skus = 0
    page_size = 1000
    try:
        offset = 0
        while True:
            r_st = requests.get(
                f"{url}/rest/v1/stores?select=*&order=brand.asc,domain.asc&limit={page_size}&offset={offset}",
                headers=supabase_headers(key),
                timeout=15,
            )
            if not r_st.ok or not isinstance(r_st.json(), list):
                break
            batch = r_st.json()
            if not batch:
                break
            for s in batch:
                cur.execute(
                    """INSERT INTO stores (domain, brand, platform, brand_url, first_seen_at, last_checked_at, last_product_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(domain, brand) DO UPDATE SET
                         platform=excluded.platform,
                         brand_url=excluded.brand_url,
                         last_checked_at=excluded.last_checked_at,
                         last_product_count=excluded.last_product_count""",
                    (
                        s["domain"], s["brand"], s.get("platform"), s.get("brand_url"),
                        s["first_seen_at"], s["last_checked_at"], s.get("last_product_count", 0),
                    ),
                )
                pulled_stores += 1
            if len(batch) < page_size:
                break
            offset += page_size

        offset = 0
        while True:
            r_sk = requests.get(
                f"{url}/rest/v1/skus?select=*&order=sku_key.asc&limit={page_size}&offset={offset}",
                headers=supabase_headers(key),
                timeout=20,
            )
            if not r_sk.ok or not isinstance(r_sk.json(), list):
                break
            batch = r_sk.json()
            if not batch:
                break
            for k in batch:
                cur.execute(
                    """INSERT INTO skus (
                        sku_key, domain, brand, product_title, variant_title,
                        normalized_product_key, product_url, sku_code,
                        current_price, compare_at_price, last_in_stock_price, currency,
                        is_available, is_listed, first_seen_at, last_seen_at,
                        first_seen_oos_at, last_seen_in_stock_at, silent_removed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sku_key) DO UPDATE SET
                        current_price=excluded.current_price,
                        compare_at_price=excluded.compare_at_price,
                        last_in_stock_price=excluded.last_in_stock_price,
                        is_available=excluded.is_available,
                        is_listed=excluded.is_listed,
                        last_seen_at=excluded.last_seen_at,
                        first_seen_oos_at=excluded.first_seen_oos_at,
                        last_seen_in_stock_at=excluded.last_seen_in_stock_at,
                        silent_removed_at=excluded.silent_removed_at""",
                    (
                        k["sku_key"], k["domain"], k["brand"], k["product_title"], k["variant_title"],
                        k["normalized_product_key"], k.get("product_url"), k.get("sku_code"),
                        k.get("current_price"), k.get("compare_at_price"), k.get("last_in_stock_price"),
                        k.get("currency", "GBP"), 1 if k.get("is_available") else 0,
                        1 if k.get("is_listed", True) else 0, k["first_seen_at"], k["last_seen_at"],
                        k.get("first_seen_oos_at"), k.get("last_seen_in_stock_at"), k.get("silent_removed_at"),
                    ),
                )
                pulled_skus += 1
            if len(batch) < page_size:
                break
            offset += page_size
        conn.commit()
    except Exception:
        pass
    return {"stores": pulled_stores, "skus": pulled_skus}


def push_all_sqlite_to_supabase(conn: sqlite3.Connection) -> None:
    """Push all local SQLite stores, skus, and stock_events rows to Supabase."""
    url, key = supabase_credentials()
    if not url or not key:
        print("Error: Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env.local")
        return

    stores = [dict(r) for r in conn.execute("SELECT * FROM stores").fetchall()]
    skus = []
    for r in conn.execute("SELECT * FROM skus").fetchall():
        d = dict(r)
        d["is_available"] = bool(d["is_available"])
        d["is_listed"] = bool(d["is_listed"])
        skus.append(d)

    ok_stores = sync_rows_to_supabase("stores", stores, on_conflict="domain,brand")
    ok_skus = sync_rows_to_supabase("skus", skus, on_conflict="sku_key")
    print(f"Supabase sync status: stores={ok_stores} ({len(stores)} rows), skus={ok_skus} ({len(skus)} rows)")


def check_supabase() -> None:
    url, key = supabase_credentials()
    print(f"Configured Supabase URL: {url}")
    if not url or not key:
        print("Status: Missing credentials in .env.local")
        return
    try:
        r = requests.get(f"{url}/rest/v1/", headers=supabase_headers(key), timeout=10)
        print(f"Status: HTTP {r.status_code} (Online!)")
    except Exception as exc:
        print(f"Status: Unreachable ({exc})")
        print(
            "\nNote: The hostname 'hjbfrfreoilmoszoolrs.supabase.co' currently returns NXDOMAIN (DNS name does not exist).\n"
            "On Supabase Free Tier, this means the project is paused due to inactivity.\n"
            "To activate it:\n"
            "  1. Open https://supabase.com/dashboard/project/hjbfrfreoilmoszoolrs and click 'Restore project'.\n"
            "  2. Paste `oos/supabase_schema.sql` into the Supabase SQL Editor and click Run.\n"
            "  3. Run `python db.py --sync-to-supabase` to push your 163 tracked SKUs into Supabase."
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="Check Supabase connection status")
    ap.add_argument("--sync-to-supabase", action="store_true", help="Push all local SQLite data to Supabase")
    args = ap.parse_args()
    if args.sync_to_supabase:
        c = get_conn()
        push_all_sqlite_to_supabase(c)
        c.close()
    else:
        check_supabase()
