"""Self-Contained Interactive HTML Dashboard Generator for Brand Owners.

Reads the JSON intelligence reports in `oos/reports/<slug>_intelligence_report.json`
and generates:
  - `oos/reports/<slug>_dashboard.html` (per-brand interactive dashboard with built-in CSV export)
  - `oos/reports/index.html` (multi-brand portfolio overview)

Usage:
    python generate_html_report.py
"""
import html
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS_DIR = HERE / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def esc(val) -> str:
    return html.escape(str(val or ""))


def build_brand_html(report: dict, all_skus: list[dict], stores: list[dict]) -> str:
    brand = report["brand"]
    slug = report["brand_slug"]
    gen_at = report.get("generated_at", "")
    try:
        gen_fmt = datetime.fromisoformat(gen_at).strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        gen_fmt = gen_at

    summary = report["summary"]
    total_stores = summary["monitored_uk_independent_stores"]
    total_skus = summary["total_listed_skus_variants"]
    total_oos = summary["out_of_stock_skus_variants"]
    total_silent = summary["silent_removed_skus"]
    total_po = summary["estimated_immediate_replenishment_po_gbp"]
    in_stock_cnt = max(0, total_skus - total_oos)
    health_pct = round(100.0 * in_stock_cnt / total_skus, 1) if total_skus else 100.0

    oos_by_key = {item["sku_key"]: item for item in report.get("out_of_stock_alerts", [])}
    heroes = report.get("hero_sku_benchmarks", [])
    hero_keys = [h for h in heroes if h.get("is_hero")]

    # Build enriched rows for all SKUs (both OOS and In Stock) so the user can filter between OOS and All
    table_rows_data = []
    for s in all_skus:
        if not s.get("is_listed", 1):
            continue
        k = s["sku_key"]
        oos_info = oos_by_key.get(k)
        is_avail = bool(s.get("is_available"))
        price = s.get("current_price")
        comp = s.get("compare_at_price")
        rrp = price or s.get("last_in_stock_price") or 16.0
        est_po = round((rrp * 0.5) * 6, 2) if not is_avail else 0.0

        if is_avail:
            signal_type = "IN_STOCK"
            signal_badge = '<span class="badge badge-green">In Stock</span>'
            duration_label = "Active on shelf"
        else:
            duration_label = oos_info["duration_label"] if oos_info else "Out of Stock"
            if comp and price and comp > price:
                disc_pct = round(100 * (1 - price / comp))
                signal_type = "CLEARANCE_OOS"
                signal_badge = f'<span class="badge badge-amber">⚠️ OOS after -{disc_pct}% Discount (Delist Risk)</span>'
            else:
                signal_type = "FULL_PRICE_OOS"
                signal_badge = '<span class="badge badge-red">🔥 Sold Out at Full RRP (Reorder Now)</span>'

        table_rows_data.append({
            "domain": s["domain"],
            "product_title": s["product_title"],
            "variant_title": s["variant_title"],
            "price": price,
            "compare_at_price": comp,
            "is_available": is_avail,
            "signal_type": signal_type,
            "signal_badge": signal_badge,
            "duration_label": duration_label,
            "est_po": est_po,
            "product_url": s.get("product_url") or "#",
        })

    # Sort so Out-of-Stock items appear first, then by store and product title
    table_rows_data.sort(key=lambda r: (1 if r["is_available"] else 0, -r["est_po"], r["domain"], r["product_title"]))

    # Store options for filter dropdown
    store_options_html = "\n".join(
        f'<option value="{esc(st["domain"])}">{esc(st["domain"])}</option>'
        for st in stores
    )

    # Build HTML rows for Tab 1 (SKU Table)
    sku_rows_html = []
    for r in table_rows_data:
        p_str = f"£{r['price']:.2f}" if r["price"] is not None else "—"
        if r["compare_at_price"] and r["price"] and r["compare_at_price"] > r["price"]:
            p_str += f' <del class="muted">£{r["compare_at_price"]:.2f}</del>'
        po_str = f"£{r['est_po']:.2f}" if r["est_po"] > 0 else "—"
        row_cls = "row-oos" if not r["is_available"] else "row-instock"
        sku_rows_html.append(f"""
            <tr class="sku-row {row_cls}"
                data-store="{esc(r['domain'])}"
                data-signal="{esc(r['signal_type'])}"
                data-avail="{'in' if r['is_available'] else 'oos'}"
                data-search="{esc((r['domain'] + ' ' + r['product_title'] + ' ' + r['variant_title']).lower())}"
                data-csv-store="{esc(r['domain'])}"
                data-csv-product="{esc(r['product_title'])}"
                data-csv-variant="{esc(r['variant_title'])}"
                data-csv-price="{r['price'] if r['price'] is not None else ''}"
                data-csv-status="{'In Stock' if r['is_available'] else 'Out of Stock'}"
                data-csv-duration="{esc(r['duration_label'])}"
                data-csv-signal="{esc(r['signal_type'])}"
                data-csv-po="{r['est_po'] if r['est_po'] > 0 else '0'}"
                data-csv-url="{esc(r['product_url'])}">
                <td class="font-mono store-cell">{esc(r['domain'])}</td>
                <td class="product-cell"><strong>{esc(r['product_title'])}</strong></td>
                <td><span class="pill">{esc(r['variant_title'])}</span></td>
                <td class="num-cell">{p_str}</td>
                <td>{r['signal_badge']}</td>
                <td class="duration-cell">{esc(r['duration_label'])}</td>
                <td class="num-cell po-cell">{po_str}</td>
                <td><a href="{esc(r['product_url'])}" target="_blank" rel="noopener" class="link-btn">View Shelf ↗</a></td>
            </tr>
        """)

    # Build HTML cards for Tab 2 (Store Account Health Cards)
    store_cards_html = []
    for st in stores:
        dom = st["domain"]
        st_rows = [r for r in table_rows_data if r["domain"] == dom]
        st_oos = [r for r in st_rows if not r["is_available"]]
        st_in = len(st_rows) - len(st_oos)
        st_total = max(1, len(st_rows))
        st_pct = round(100.0 * st_in / st_total)
        st_po = sum(r["est_po"] for r in st_oos)

        missing_for_store = [
            h["product_family"] for h in hero_keys if dom in h.get("missing_in", [])
        ]

        bar_color = "#10b981" if st_pct == 100 else ("#f59e0b" if st_pct >= 60 else "#ef4444")
        oos_list_html = (
            "<ul class='card-list'>"
            + "".join(
                f"<li><strong>{esc(r['product_title'])}</strong> ({esc(r['variant_title'])}) — "
                f"<span class='text-red'>{esc(r['duration_label'])}</span> "
                f"[Est. PO: £{r['est_po']:.2f}]</li>"
                for r in st_oos
            )
            + "</ul>"
            if st_oos
            else "<p class='text-green'>✓ All listed variants are currently In Stock on shelf.</p>"
        )

        upsell_html = (
            "<div class='upsell-box'><strong>★ Missing Hero SKUs (Carried by 50%+ of UK Peers):</strong><br>"
            + ", ".join(esc(m) for m in missing_for_store)
            + "</div>"
            if missing_for_store
            else "<div class='upsell-box ok'>✓ Carries 100% of peer-validated UK Hero SKUs.</div>"
        )

        store_cards_html.append(f"""
            <div class="account-card">
                <div class="account-card-header">
                    <div>
                        <h3>{esc(dom)} <span class="platform-tag">{esc(st.get('platform', ''))}</span></h3>
                        <a href="{esc(st.get('brand_url', '#'))}" target="_blank" rel="noopener" class="small-link">{esc(st.get('brand_url', ''))} ↗</a>
                    </div>
                    <div class="account-kpis">
                        <span class="kpi-mini"><strong>{st_in}</strong> In Stock</span>
                        <span class="kpi-mini {'kpi-danger' if st_oos else ''}"><strong>{len(st_oos)}</strong> OOS</span>
                        <span class="kpi-mini kpi-po">Est. PO: <strong>£{st_po:.2f}</strong></span>
                    </div>
                </div>
                <div class="progress-wrap">
                    <div class="progress-bar" style="width: {st_pct}%; background: {bar_color};"></div>
                </div>
                <div class="progress-caption">{st_pct}% Shelf Availability ({st_in} of {len(st_rows)} variants available)</div>
                <div class="card-section">
                    <h4>Replenishment Opportunities (Out of Stock)</h4>
                    {oos_list_html}
                </div>
                {upsell_html}
            </div>
        """)

    # Build HTML rows for Tab 3 (Hero SKU Penetration Matrix)
    hero_rows_html = []
    for h in heroes[:25]:
        is_h = h.get("is_hero")
        badge = '<span class="badge badge-purple">★ HERO SKU (50%+ Peers)</span>' if is_h else '<span class="badge badge-gray">Secondary SKU</span>'
        missing_pills = (
            " ".join(f'<span class="store-pill">{esc(d)}</span>' for d in h.get("missing_in", []))
            if h.get("missing_in")
            else '<span class="text-green">✓ Stocked by 100% of audited UK stores</span>'
        )
        hero_rows_html.append(f"""
            <tr>
                <td><strong>{esc(h['product_family'])}</strong></td>
                <td>
                    <div class="pen-wrap">
                        <span class="pen-num">{h['penetration_pct']}%</span>
                        <span class="muted">({h['stores_carrying']}/{h['total_stores']} stores)</span>
                    </div>
                </td>
                <td>{badge}</td>
                <td>{missing_pills}</td>
            </tr>
        """)

    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(brand)} — UK Wholesale Shelf & OOS Intelligence</title>
<style>
  :root {{
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-hover: #263449;
    --border: #334155;
    --text: #f8fafc;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --green: #10b981;
    --green-bg: rgba(16, 185, 129, 0.14);
    --red: #f43f5e;
    --red-bg: rgba(244, 63, 94, 0.15);
    --amber: #f59e0b;
    --amber-bg: rgba(245, 158, 11, 0.15);
    --purple: #a855f7;
    --purple-bg: rgba(168, 85, 247, 0.16);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 28px 32px;
  }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    padding-bottom: 22px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
    flex-wrap: wrap;
  }}
  .brand-title {{ font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; }}
  .brand-sub {{ color: var(--muted); font-size: 0.92rem; margin-top: 4px; }}
  .header-actions {{ display: flex; gap: 10px; align-items: center; }}
  .btn {{
    background: var(--accent);
    color: #0f172a;
    border: none;
    padding: 9px 16px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.88rem;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .btn:hover {{ opacity: 0.92; }}
  .btn-outline {{
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 16px;
    margin-bottom: 26px;
  }}
  .kpi-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px;
  }}
  .kpi-label {{ color: var(--muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em; }}
  .kpi-value {{ font-size: 1.85rem; font-weight: 700; margin-top: 6px; }}
  .kpi-note {{ font-size: 0.8rem; color: var(--muted); margin-top: 4px; }}
  .text-red {{ color: var(--red); }}
  .text-green {{ color: var(--green); }}
  .text-amber {{ color: var(--amber); }}
  .text-accent {{ color: var(--accent); }}
  .tabs {{
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
    flex-wrap: wrap;
  }}
  .tab-btn {{
    background: transparent;
    color: var(--muted);
    border: 1px solid transparent;
    padding: 9px 18px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.92rem;
    cursor: pointer;
  }}
  .tab-btn.active {{
    background: var(--surface);
    color: var(--text);
    border-color: var(--accent);
  }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .filter-bar {{
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    background: var(--surface);
    padding: 14px 16px;
    border-radius: 10px;
    border: 1px solid var(--border);
    flex-wrap: wrap;
    align-items: center;
  }}
  .filter-bar select, .filter-bar input {{
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.88rem;
  }}
  .filter-bar input {{ flex: 1; min-width: 220px; }}
  .table-wrap {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow-x: auto;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th {{
    text-align: left;
    padding: 13px 16px;
    background: rgba(15, 23, 42, 0.6);
    color: var(--muted);
    font-weight: 600;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--border);
  }}
  td {{ padding: 13px 16px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: var(--surface-hover); }}
  .row-oos td {{ background: rgba(244, 63, 94, 0.04); }}
  .badge {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
  }}
  .badge-red {{ background: var(--red-bg); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.35); }}
  .badge-amber {{ background: var(--amber-bg); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.35); }}
  .badge-green {{ background: var(--green-bg); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.35); }}
  .badge-purple {{ background: var(--purple-bg); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.35); }}
  .badge-gray {{ background: rgba(148, 163, 184, 0.12); color: var(--muted); }}
  .pill {{
    background: var(--bg);
    border: 1px solid var(--border);
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.8rem;
  }}
  .font-mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.85rem; }}
  .num-cell {{ font-variant-numeric: tabular-nums; font-weight: 600; }}
  .po-cell {{ color: var(--accent); }}
  .muted {{ color: var(--muted); font-weight: 400; font-size: 0.82rem; }}
  .link-btn {{
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    font-size: 0.84rem;
  }}
  .link-btn:hover {{ text-decoration: underline; }}
  .cards-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 18px;
  }}
  .account-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }}
  .account-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }}
  .platform-tag {{
    font-size: 0.74rem;
    background: var(--bg);
    color: var(--muted);
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 6px;
    font-weight: 500;
  }}
  .small-link {{ color: var(--accent); font-size: 0.8rem; text-decoration: none; word-break: break-all; }}
  .account-kpis {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .kpi-mini {{
    background: var(--bg);
    border: 1px solid var(--border);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
  }}
  .kpi-danger {{ border-color: rgba(244, 63, 94, 0.5); color: #fda4af; }}
  .kpi-po {{ border-color: rgba(56, 189, 248, 0.4); color: var(--accent); }}
  .progress-wrap {{
    height: 8px;
    background: var(--bg);
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 6px;
  }}
  .progress-bar {{ height: 100%; border-radius: 999px; }}
  .progress-caption {{ font-size: 0.78rem; color: var(--muted); margin-bottom: 14px; }}
  .card-section h4 {{ font-size: 0.85rem; color: var(--muted); text-transform: uppercase; margin-bottom: 8px; }}
  .card-list {{ padding-left: 18px; font-size: 0.88rem; margin-bottom: 14px; }}
  .card-list li {{ margin-bottom: 5px; }}
  .upsell-box {{
    background: rgba(168, 85, 247, 0.1);
    border: 1px solid rgba(168, 85, 247, 0.3);
    padding: 10px 12px;
    border-radius: 8px;
    font-size: 0.84rem;
    margin-top: 12px;
  }}
  .upsell-box.ok {{
    background: rgba(16, 185, 129, 0.08);
    border-color: rgba(16, 185, 129, 0.25);
    color: #6ee7b7;
  }}
  .store-pill {{
    display: inline-block;
    background: var(--bg);
    border: 1px solid var(--border);
    padding: 2px 8px;
    border-radius: 5px;
    font-family: ui-monospace, monospace;
    font-size: 0.78rem;
    margin: 2px;
  }}
  .pen-num {{ font-weight: 700; font-size: 1rem; margin-right: 4px; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <div class="brand-title">{esc(brand)} — UK Independent Stockist Intelligence</div>
      <div class="brand-sub">Live Shelf Availability, Out-of-Stock Aging &amp; Peer Hero SKU Assortment Benchmark • Updated {esc(gen_fmt)}</div>
    </div>
    <div class="header-actions">
      <a href="index.html" class="btn btn-outline">← All Monitored Brands</a>
      <button class="btn" onclick="exportVisibleToCSV('{esc(slug)}_uk_shelf_audit.csv')">⬇ Export Current View to CSV</button>
    </div>
  </header>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">UK Independent Stockists</div>
      <div class="kpi-value">{total_stores}</div>
      <div class="kpi-note">Verified UK e-commerce accounts</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Active Variants Tracked</div>
      <div class="kpi-value">{total_skus}</div>
      <div class="kpi-note">{in_stock_cnt} In Stock • {total_oos} Out of Stock</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">UK Shelf Availability</div>
      <div class="kpi-value {'text-green' if health_pct >= 80 else 'text-amber'}">{health_pct}%</div>
      <div class="kpi-note">Across all monitored independent shelves</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Active Stockout Alerts</div>
      <div class="kpi-value text-red">{total_oos}</div>
      <div class="kpi-note">{total_silent} silent removals detected</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Est. Replenishment PO Value</div>
      <div class="kpi-value text-accent">£{total_po:,.2f}</div>
      <div class="kpi-note">Based on 6-unit wholesale cases (50% margin)</div>
    </div>
  </div>

  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('tab-skus', this)">1. Live Shelf &amp; Stockout Aging ({total_oos} OOS / {total_skus} Total)</button>
    <button class="tab-btn" onclick="switchTab('tab-stores', this)">2. Retailer Account Action Cards ({total_stores} Stores)</button>
    <button class="tab-btn" onclick="switchTab('tab-heroes', this)">3. UK Peer Hero SKU Matrix ({len(hero_keys)} Hero SKUs)</button>
  </div>

  <!-- TAB 1: SKU TABLE -->
  <div id="tab-skus" class="tab-panel active">
    <div class="filter-bar">
      <select id="filterStore" onchange="applyFilters()">
        <option value="ALL">All Independent UK Stores ({total_stores})</option>
        {store_options_html}
      </select>
      <select id="filterSignal" onchange="applyFilters()">
        <option value="OOS_ONLY">Out of Stock Only ({total_oos})</option>
        <option value="ALL" selected>All Tracked SKUs ({total_skus})</option>
        <option value="FULL_PRICE_OOS">🔥 Sold Out at Full RRP (Immediate Reorder)</option>
        <option value="CLEARANCE_OOS">⚠️ Discounted Before OOS (Delist Risk)</option>
        <option value="IN_STOCK">✓ In Stock Only ({in_stock_cnt})</option>
      </select>
      <input type="text" id="filterSearch" placeholder="Search product name, size/variant, or store domain..." oninput="applyFilters()">
      <span id="visibleCount" class="muted">Showing {len(table_rows_data)} rows</span>
    </div>

    <div class="table-wrap">
      <table id="skuTable">
        <thead>
          <tr>
            <th>UK Stockist</th>
            <th>Product</th>
            <th>Size / Variant</th>
            <th>Retail Price</th>
            <th>Shelf Status &amp; Signal</th>
            <th>OOS Duration / Aging</th>
            <th>Est. 6-Unit PO</th>
            <th>Verify</th>
          </tr>
        </thead>
        <tbody>
          {"".join(sku_rows_html)}
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 2: STORE CARDS -->
  <div id="tab-stores" class="tab-panel">
    <div class="cards-grid">
      {"".join(store_cards_html)}
    </div>
  </div>

  <!-- TAB 3: HERO BENCHMARK -->
  <div id="tab-heroes" class="tab-panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Product Family</th>
            <th>UK Stockist Penetration</th>
            <th>Classification</th>
            <th>Active UK Stockists Missing This SKU (Upsell Targets)</th>
          </tr>
        </thead>
        <tbody>
          {"".join(hero_rows_html)}
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
function switchTab(tabId, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  btn.classList.add('active');
}}

function applyFilters() {{
  const storeVal = document.getElementById('filterStore').value;
  const sigVal = document.getElementById('filterSignal').value;
  const q = document.getElementById('filterSearch').value.trim().toLowerCase();
  let shown = 0;

  document.querySelectorAll('#skuTable tbody tr.sku-row').forEach(row => {{
    const rStore = row.getAttribute('data-store');
    const rSig = row.getAttribute('data-signal');
    const rAvail = row.getAttribute('data-avail');
    const rSearch = row.getAttribute('data-search');

    let matchStore = (storeVal === 'ALL' || rStore === storeVal);
    let matchSig = true;
    if (sigVal === 'OOS_ONLY') matchSig = (rAvail === 'oos');
    else if (sigVal !== 'ALL') matchSig = (rSig === sigVal);

    let matchQ = (!q || rSearch.includes(q));
    if (matchStore && matchSig && matchQ) {{
      row.style.display = '';
      shown++;
    }} else {{
      row.style.display = 'none';
    }}
  }});
  document.getElementById('visibleCount').textContent = `Showing ${{shown}} row(s)`;
}}

function exportVisibleToCSV(filename) {{
  const headers = ['Store', 'Product', 'Variant', 'Price_GBP', 'Status', 'OOS_Duration', 'Signal', 'Est_6Unit_PO_GBP', 'Product_URL'];
  const rows = [headers.join(',')];
  document.querySelectorAll('#skuTable tbody tr.sku-row').forEach(row => {{
    if (row.style.display === 'none') return;
    const vals = [
      row.getAttribute('data-csv-store'),
      row.getAttribute('data-csv-product'),
      row.getAttribute('data-csv-variant'),
      row.getAttribute('data-csv-price'),
      row.getAttribute('data-csv-status'),
      row.getAttribute('data-csv-duration'),
      row.getAttribute('data-csv-signal'),
      row.getAttribute('data-csv-po'),
      row.getAttribute('data-csv-url')
    ].map(v => `"${{String(v || '').replace(/"/g, '""')}}"`);
    rows.push(vals.join(','));
  }});
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
}}
</script>
</body>
</html>
"""


def generate_all_html_dashboards(conn=None) -> list[Path]:
    import db as db_mod
    close_after = False
    if conn is None:
        conn = db_mod.get_conn()
        close_after = True

    generated_files = []
    portfolio_cards = []

    for report_file in sorted(REPORTS_DIR.glob("*_intelligence_report.json")):
        report = json.loads(report_file.read_text(encoding="utf-8"))
        brand_name = report["brand"]
        slug = report["brand_slug"]

        stores = [
            dict(r) for r in conn.execute(
                "SELECT * FROM stores WHERE brand = ? ORDER BY domain", (brand_name,)
            ).fetchall()
        ]
        all_skus = [
            dict(r) for r in conn.execute(
                "SELECT * FROM skus WHERE brand = ? ORDER BY domain, product_title", (brand_name,)
            ).fetchall()
        ]

        html_content = build_brand_html(report, all_skus, stores)
        out_path = REPORTS_DIR / f"{slug}_dashboard.html"
        out_path.write_text(html_content, encoding="utf-8")
        generated_files.append(out_path)

        s = report["summary"]
        portfolio_cards.append({
            "brand": brand_name,
            "slug": slug,
            "stores": s["monitored_uk_independent_stores"],
            "skus": s["total_listed_skus_variants"],
            "oos": s["out_of_stock_skus_variants"],
            "po": s["estimated_immediate_replenishment_po_gbp"],
            "href": f"{slug}_dashboard.html",
        })

    # Write portfolio index.html
    cards_html = "\n".join(
        f"""
        <a href="{esc(c['href'])}" class="brand-card">
          <div class="brand-card-title">{esc(c['brand'])}</div>
          <div class="brand-card-stats">
            <span><strong>{c['stores']}</strong> UK Stockists</span>
            <span><strong>{c['skus']}</strong> Variants</span>
            <span class="oos-highlight"><strong>{c['oos']}</strong> OOS</span>
          </div>
          <div class="brand-card-po">Est. Immediate Replenishment PO: <strong>£{c['po']:,.2f}</strong></div>
        </a>
        """
        for c in portfolio_cards
    )

    index_html = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<title>UK SME Beauty &amp; Wellness — Wholesale Shelf Intelligence Portfolio</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    background: #0f172a; color: #f8fafc; padding: 36px;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 1.9rem; margin-bottom: 6px; }}
  p.sub {{ color: #94a3b8; margin-bottom: 28px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; }}
  .brand-card {{
    display: block; text-decoration: none; color: inherit;
    background: #1e293b; border: 1px solid #334155; border-radius: 12px;
    padding: 22px; transition: border-color 0.15s, transform 0.15s;
  }}
  .brand-card:hover {{ border-color: #38bdf8; transform: translateY(-2px); }}
  .brand-card-title {{ font-size: 1.3rem; font-weight: 700; margin-bottom: 12px; }}
  .brand-card-stats {{ display: flex; gap: 14px; font-size: 0.9rem; color: #cbd5e1; margin-bottom: 14px; }}
  .oos-highlight {{ color: #fda4af; }}
  .brand-card-po {{ font-size: 0.92rem; color: #38bdf8; }}
</style>
</head>
<body>
<div class="container">
  <h1>UK SME Wholesale Shelf Intelligence — Audited Brands</h1>
  <p class="sub">Select a brand to inspect live UK independent stockists, Out-of-Stock aging, and Hero SKU assortment gaps.</p>
  <div class="grid">
    {cards_html}
  </div>
</div>
</body>
</html>
"""
    index_path = REPORTS_DIR / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    generated_files.append(index_path)

    if close_after:
        conn.close()
    return generated_files


if __name__ == "__main__":
    paths = generate_all_html_dashboards()
    print("Generated HTML Dashboards:")
    for p in paths:
        print(f"  - {p}")
