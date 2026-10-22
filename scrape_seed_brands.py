"""Phase 1 - collect every brand from the seed stores.

Usage:
    python scrape_seed_brands.py              # fetch all seed stores, write reports
    python scrape_seed_brands.py --cached     # rebuild reports from data/raw (no fetching)
    python scrape_seed_brands.py --only naturisimo.com mypure.co.uk

Outputs (Markdown):
    output/01_seed_brands/00_summary.md          store-by-store overview
    output/01_seed_brands/stores/<domain>.md     brand list per store
    review/brand_review.md                       all brands across stores, for manual sorting
                                                 (your Keep / SME / Notes columns are preserved on re-run)

Manual additions:
    input/manual_brands/<domain>.md  - one brand per line as "- Brand Name". Brands listed here
    are added to that store's list. A template is created automatically for any store that
    could not be scraped.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import config
from oos import brand_pages, brands, md, shopify, woocommerce

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "output" / "01_seed_brands"
REVIEW_FILE = ROOT / "review" / "brand_review.md"
MANUAL_DIR = ROOT / "input" / "manual_brands"

PLATFORM_LABEL = {
    "shopify": "Shopify",
    "woocommerce": "WooCommerce",
    "bigcommerce": "BigCommerce",
    "ziracle": "Ziracle (Next.js)",
    "none": "-",
}
REVIEW_USER_COLUMNS = ["Keep (Y/N)", "SME (Y/N/?)", "Notes"]


# --------------------------------------------------------------------------- collection

def fetch_store(store: dict) -> dict:
    """Fetch raw data for one store using its platform reader."""
    domain, platform = store["domain"], store["platform"]
    if platform == "shopify":
        data = shopify.fetch(domain)
    elif platform == "woocommerce":
        data = woocommerce.fetch(domain)
    elif platform == "bigcommerce":
        data = brand_pages.bigcommerce_brands(domain)
    elif platform == "ziracle":
        data = brand_pages.ziracle_brands(domain)
    else:
        raise RuntimeError(f"No reader for platform '{platform}'")
    data.update({
        "domain": domain,
        "platform": platform,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return data


def raw_path(domain: str) -> Path:
    return RAW_DIR / f"{domain}.json"


def read_manual_brands(domain: str) -> list[str]:
    path = MANUAL_DIR / f"{domain}.md"
    if not path.exists():
        return []
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*[-*]\s+(?!\[)(.+?)\s*$", line)
        if m:
            names.append(m.group(1))
    return names


def write_manual_template(store: dict, reason: str) -> None:
    path = MANUAL_DIR / f"{store['domain']}.md"
    if path.exists():
        return
    md.write(path, f"""# Manual brand list: {store['domain']}

Automatic collection failed ({reason}).
Copy brand names from the store's brand A-Z page below, one per line, starting with "- ".
Then run: `python scrape_seed_brands.py --cached`

<!-- Example:
- Brand One
- Brand Two
-->
""")


def summarise_store(store: dict, raw: dict | None, error: str | None) -> dict:
    """Turn raw store data into a per-brand summary."""
    domain = store["domain"]
    own_keys = brands.store_name_keys(domain)
    if store.get("successor"):
        own_keys |= brands.store_name_keys(store["successor"])

    per_brand: dict[str, dict] = {}

    def entry(name: str) -> dict:
        return per_brand.setdefault(name, {
            "products": 0, "in_stock": 0, "types": Counter(), "example": "", "source": set(),
        })

    product_count = None
    has_products = bool(raw and "products" in raw)
    if raw and "products" in raw:
        product_count = len(raw["products"])
        for p in raw["products"]:
            e = entry(p["brand"] or "(no brand)")
            e["products"] += 1
            available = p.get("in_stock")
            if available is None:
                available = any(v.get("available") for v in p.get("variants", []))
            e["in_stock"] += 1 if available else 0
            if p.get("product_type"):
                e["types"][p["product_type"]] += 1
            e["example"] = e["example"] or p["title"]
            e["source"].add("scraped")
    elif raw and "brands" in raw:
        for name in raw["brands"]:
            entry(name)["source"].add("scraped")

    for name in read_manual_brands(domain):
        entry(name)["source"].add("manual")

    for name, e in per_brand.items():
        e["hint"] = brands.not_a_brand_hint(name, own_keys) if name != "(no brand)" else "Blank vendor"

    return {
        "store": store,
        "status": store.get("status", "active"),
        "platform": raw.get("platform", store["platform"]) if raw else store["platform"],
        "fetched_at": raw.get("fetched_at") if raw else None,
        "base_url": raw.get("base_url") if raw else None,
        "product_count": product_count,
        "has_products": has_products,
        "brands": per_brand,
        "error": error,
        "extra": {"unmatched_slugs": raw.get("unmatched_slugs")} if raw and raw.get("unmatched_slugs") else {},
    }


def collect(only: set[str] | None, cached: bool) -> list[dict]:
    results = []
    for store in config.SEED_STORES:
        domain = store["domain"]
        raw, error = None, None
        selected = not only or domain in only

        if store.get("status") == "closed":
            print(f"- {domain}: closed - skipped")
        elif cached or not selected:
            path = raw_path(domain)
            raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            if raw is None:
                error = "No cached data - run without --cached"
            print(f"- {domain}: {'cache' if raw else 'no cache'}")
        else:
            print(f"- {domain}: fetching ({store['platform']})")
            try:
                raw = fetch_store(store)
                raw_path(domain).parent.mkdir(parents=True, exist_ok=True)
                raw_path(domain).write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception as exc:  # keep going - one bad store must not stop the run
                error = str(exc).splitlines()[0][:200]
                print(f"    FAILED: {error}")
                write_manual_template(store, error)
        results.append(summarise_store(store, raw, error))
    return results


# --------------------------------------------------------------------------- reports

def short(domain: str) -> str:
    return re.sub(r"\.(co\.uk|com)$", "", domain)


def fmt_time(iso: str | None) -> str:
    if not iso:
        return "-"
    return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M UTC")


def status_label(r: dict) -> str:
    s = r["store"]
    if r["status"] == "closed":
        return "Closed"
    if r["error"]:
        return "Failed"
    label = "Rebranded" if r["status"] == "rebranded" else "OK"
    if s.get("weak_seed"):
        label += " (weak seed)"
    return label


def write_store_report(r: dict) -> None:
    s = r["store"]
    rows_meta = [
        ["Platform", PLATFORM_LABEL.get(r["platform"], r["platform"])],
        ["Status", status_label(r)],
        ["Read from", r["base_url"] or "-"],
        ["Collected", fmt_time(r["fetched_at"])],
        ["Products read", f"{r['product_count']:,}" if r["product_count"] is not None else "n/a (brand list only)"],
        ["Brands found", len(r["brands"])],
    ]
    parts = [f"# Brands at {s['domain']}", "", md.table(["Field", "Value"], rows_meta)]
    if s.get("note"):
        parts += ["", f"> {s['note']}"]
    if r["error"]:
        parts += ["", f"> **Collection failed:** {r['error']}"]
    if r["extra"].get("unmatched_slugs"):
        parts += ["", f"> {len(r['extra']['unmatched_slugs'])} brands in the sitemap were not linked on the "
                      "brands page; their names were derived from the URL."]

    ordered = sorted(r["brands"].items(), key=lambda kv: (-kv[1]["products"], kv[0].casefold()))
    if r["has_products"]:
        headers = ["#", "Brand", "Products", "In stock", "Product types", "Example product", "Hint"]
        rows = [[i, name, e["products"], e["in_stock"],
                 ", ".join(t for t, _ in e["types"].most_common(3)), e["example"], e["hint"]]
                for i, (name, e) in enumerate(ordered, 1)]
    else:
        headers = ["#", "Brand", "Source", "Hint"]
        rows = [[i, name, ", ".join(sorted(e["source"])), e["hint"]] for i, (name, e) in enumerate(ordered, 1)]
    parts += ["", "## Brands", "", md.table(headers, rows) if rows else "_No brands collected._"]
    md.write(OUT_DIR / "stores" / f"{s['domain']}.md", "\n".join(parts))


def aggregate(results: list[dict]) -> dict[str, dict]:
    """Group brands across stores by normalised key."""
    agg: dict[str, dict] = defaultdict(lambda: {
        "spellings": Counter(), "stores": [], "products": 0, "hints": set(),
    })
    for r in results:
        s = r["store"]
        for name, e in r["brands"].items():
            if name == "(no brand)":
                continue
            k = brands.key(name)
            if not k:
                continue
            a = agg[k]
            a["spellings"][name] += 1
            if s["domain"] not in [x["domain"] for x in a["stores"]]:
                a["stores"].append(s)
            a["products"] += e["products"]
            if e["hint"]:
                a["hints"].add(f"{e['hint']} ({short(s['domain'])})" if "own" in e["hint"] else e["hint"])
    return agg


def display_name(spellings: Counter) -> str:
    return sorted(spellings.items(), key=lambda kv: (-kv[1], kv[0].casefold()))[0][0]


def split_row(line: str) -> list[str]:
    cells = re.split(r"(?<!\\)\|", line.strip())
    return [c.strip().replace("\\|", "|") for c in cells[1:-1]]


def load_review_decisions() -> dict[str, dict]:
    """Read the user's Keep/SME/Notes columns from an existing review file."""
    if not REVIEW_FILE.exists():
        return {}
    decisions, header = {}, None
    for line in REVIEW_FILE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            header = None if not line.strip() else header
            continue
        cells = split_row(line)
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        if "Brand" in row:
            brand = re.sub(r"^\(not found this run\)\s*", "", row["Brand"])
            values = {c: row.get(c, "") for c in REVIEW_USER_COLUMNS}
            if any(values.values()):
                decisions[brands.key(brand)] = {**values, "_brand": brand}
    return decisions


def write_review(agg: dict[str, dict]) -> tuple[int, int]:
    decisions = load_review_decisions()
    similar = brands.similar_keys(list(agg))

    def sort_key(item):
        k, a = item
        strong = sum(1 for s in a["stores"] if not s.get("weak_seed"))
        return (-strong, -len(a["stores"]), display_name(a["spellings"]).casefold())

    rows = []
    for i, (k, a) in enumerate(sorted(agg.items(), key=sort_key), 1):
        name = display_name(a["spellings"])
        strong = sum(1 for s in a["stores"] if not s.get("weak_seed"))
        found_in = ", ".join(short(s["domain"]) + ("*" if s.get("weak_seed") else "")
                             for s in sorted(a["stores"], key=lambda s: s["domain"]))
        variants = ", ".join(sp for sp in a["spellings"] if sp != name)
        hints = sorted(a["hints"])
        if k in similar:
            hints.append("Similar: " + ", ".join(display_name(agg[o]["spellings"]) for o in similar[k]))
        d = decisions.get(k, {})
        rows.append([i, name, len(a["stores"]), strong, found_in, a["products"] or "", variants,
                     "; ".join(hints), *(d.get(c, "") for c in REVIEW_USER_COLUMNS)])

    # Keep rows the user annotated that were not found this run.
    missing = [k for k in decisions if k not in agg]
    for k in missing:
        d = decisions[k]
        rows.append(["", f"(not found this run) {d['_brand']}", 0, 0, "", "", "", "Not found in latest scrape",
                     *(d.get(c, "") for c in REVIEW_USER_COLUMNS)])

    qualified = sum(1 for a in agg.values() if sum(1 for s in a["stores"] if not s.get("weak_seed")) >= 2)
    content = f"""# Brand review: all seed-store brands

Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `scrape_seed_brands.py`.

- **{len(agg)}** unique brands, of which **{qualified}** are found in 2 or more seed stores (not counting weak seeds).
- **Stores** = number of seed stores carrying the brand. **Excl. weak** leaves out weak seeds (marked `*` in *Found in*).
- **Products** = total products across stores with a product feed (blank = brand-list-only stores).
- **Hints** are suggestions only: likely non-brands, store own-labels and possibly duplicated names.
- Fill in the last three columns. They are **kept when the script is re-run** (matched by brand name).

{md.table(["#", "Brand", "Stores", "Excl. weak", "Found in", "Products", "Spelling variants", "Hints",
            *REVIEW_USER_COLUMNS], rows)}
"""
    md.write(REVIEW_FILE, content)
    return len(agg), qualified


def write_summary(results: list[dict], totals: tuple[int, int], agg: dict[str, dict]) -> None:
    rows = []
    for i, r in enumerate(results, 1):
        s = r["store"]
        link = f"[{s['domain']}](stores/{s['domain']}.md)" if r["status"] != "closed" else s["domain"]
        rows.append([i, link, PLATFORM_LABEL.get(r["platform"], r["platform"]), status_label(r),
                     f"{r['product_count']:,}" if r["product_count"] is not None else "-",
                     len(r["brands"]) or "-", s.get("note", "") + (f" ERROR: {r['error']}" if r["error"] else "")])
    # md.table escapes pipes; links contain none, so they render fine.

    dist = Counter(sum(1 for s in a["stores"] if not s.get("weak_seed")) for a in agg.values())
    dist_rows = [[n, dist[n]] for n in sorted(dist, reverse=True)]

    ok = sum(1 for r in results if r["brands"])
    content = f"""# Phase 1: Seed store brand collection

Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.

- Seed stores: **{len(results)}** in total, **{ok}** with brands collected.
- Unique brands: **{totals[0]}**. Found in 2+ seed stores (excl. weak seeds): **{totals[1]}**.
- Sorting worksheet: [review/brand_review.md](../../review/brand_review.md)

## Stores

{md.table(["#", "Store", "Platform", "Status", "Products", "Brands", "Notes"], rows)}

## How many seed stores carry each brand

{md.table(["Seed stores (excl. weak)", "Brands"], dist_rows)}
"""
    md.write(OUT_DIR / "00_summary.md", content)


# --------------------------------------------------------------------------- main

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cached", action="store_true", help="rebuild reports from data/raw without fetching")
    ap.add_argument("--only", nargs="+", metavar="DOMAIN", help="fetch only these domains (others use cache)")
    args = ap.parse_args()

    results = collect(set(args.only) if args.only else None, args.cached)
    for r in results:
        if r["status"] != "closed":
            write_store_report(r)
    agg = aggregate(results)
    totals = write_review(agg)
    write_summary(results, totals, agg)
    print(f"\nDone: {totals[0]} unique brands, {totals[1]} in 2+ seed stores.")
    print(f"  {OUT_DIR / '00_summary.md'}")
    print(f"  {REVIEW_FILE}")


if __name__ == "__main__":
    main()
