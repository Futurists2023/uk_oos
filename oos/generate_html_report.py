"""Generate the Unified OOS Admin Panel (`index.html` & `admin_panel.html`) and Per-Brand OOS Trackers.

Design Principles (Account Manager & Admin MVP):
- 100% factual Out-of-Stock (OOS) tracking. Zero marketing fluff, zero fabricated PO or loss estimates.
- Unified Admin Panel (`oos/reports/index.html` & `oos/reports/admin_panel.html`) shows ALL brands, ALL stockists,
  and ALL Out-of-Stock variants in one single screen with instant multi-filtering and CSV export.
- Per-brand pages (`oos/reports/<slug>_dashboard.html`) provide the same factual OOS tracker scoped to a single brand.
"""
from datetime import datetime, timezone
import html
import json
from pathlib import Path

import sme_brands

HERE = Path(__file__).resolve().parent
REPORTS_DIR = HERE / "reports"
STOCKISTS_DIR = HERE / "stockists"
REPORTS_DIR.mkdir(exist_ok=True)


def esc(val: object) -> str:
    return html.escape(str(val or ""))


def fmt_ts(iso_ts: str | None) -> str:
    if not iso_ts:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_ts)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(iso_ts)


def calc_oos_duration(iso_ts: str | None, now: datetime) -> tuple[str, float]:
    """Return (short_duration_str, hours_float)."""
    if not iso_ts:
        return "—", 0.0
    try:
        dt = datetime.fromisoformat(iso_ts)
        hours = max(0.0, (now - dt).total_seconds() / 3600.0)
        d = int(hours // 24)
        h = int(hours % 24)
        m = int((hours * 60) % 60)
        if d > 0:
            return f"{d}d {h}h", round(hours, 1)
        if h > 0:
            return f"{h}h {m}m", round(hours, 1)
        return f"{max(1, m)}m", round(hours, 2)
    except Exception:
        return "—", 0.0


SHARED_CSS = """
  :root {
    --bg: #0b0f19;
    --panel: #111827;
    --panel-alt: #1f2937;
    --border: #374151;
    --text: #f9fafb;
    --muted: #9ca3af;
    --accent: #38bdf8;
    --red: #ef4444;
    --red-bg: rgba(239, 68, 68, 0.14);
    --green: #10b981;
    --green-bg: rgba(16, 185, 129, 0.14);
    --amber: #f59e0b;
    --amber-bg: rgba(245, 158, 11, 0.14);
    --purple: #a855f7;
    --purple-bg: rgba(168, 85, 247, 0.14);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.45;
    padding: 20px 28px 56px;
    font-size: 14px;
  }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .container { max-width: 1600px; margin: 0 auto; }

  header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
  }
  .title { font-size: 1.45rem; font-weight: 700; letter-spacing: -0.02em; }
  .subtitle { color: var(--muted); font-size: 0.85rem; margin-top: 3px; }
  .header-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

  .btn {
    background: var(--accent);
    color: #0b0f19;
    border: none;
    padding: 8px 14px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    font-size: 0.84rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
  }
  .btn:hover { opacity: 0.92; text-decoration: none; }
  .btn-outline {
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
  }
  .btn-outline:hover { background: var(--panel-alt); }
  .btn-sm { padding: 4px 9px; font-size: 0.78rem; border-radius: 5px; }

  /* KPI Strip */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }
  .kpi-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
  }
  .kpi-label {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin-bottom: 4px;
  }
  .kpi-value { font-size: 1.65rem; font-weight: 700; }
  .kpi-note { font-size: 0.78rem; color: var(--muted); margin-top: 2px; }
  .text-red { color: #f87171; }
  .text-green { color: #34d399; }
  .text-amber { color: #fbbf24; }
  .text-accent { color: var(--accent); }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 6px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
    overflow-x: auto;
  }
  .tab-btn {
    background: transparent;
    color: var(--muted);
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 16px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* Filter Bar */
  .filter-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 12px 14px;
    border-radius: 8px;
    margin-bottom: 14px;
    align-items: center;
  }
  .filter-bar select, .filter-bar input {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 0.84rem;
  }
  .filter-bar input { min-width: 220px; flex: 1; }
  .filter-count { margin-left: auto; font-size: 0.82rem; color: var(--muted); font-weight: 600; }

  /* Tables */
  .table-wrap {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow-x: auto;
  }
  table { width: 100%; border-collapse: collapse; text-align: left; }
  th {
    background: rgba(255, 255, 255, 0.03);
    color: var(--muted);
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  td {
    padding: 9px 12px;
    border-bottom: 1px solid rgba(55, 65, 81, 0.5);
    font-size: 0.85rem;
    vertical-align: middle;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255, 255, 255, 0.02); }
  tr.row-oos td { background: rgba(239, 68, 68, 0.05); }
  tr.row-oos:hover td { background: rgba(239, 68, 68, 0.09); }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .badge-oos { background: var(--red-bg); color: #fca5a5; border: 1px solid rgba(239,68,68,0.35); }
  .badge-in { background: var(--green-bg); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.35); }
  .badge-removed { background: var(--amber-bg); color: #fcd34d; border: 1px solid rgba(245,158,11,0.35); }
  .badge-t1 { background: var(--purple-bg); color: #d8b4fe; border: 1px solid rgba(168,85,247,0.35); }
  .badge-t2 { background: rgba(56,189,248,0.12); color: #7dd3fc; border: 1px solid rgba(56,189,248,0.3); }
  .badge-queued { background: rgba(156,163,175,0.12); color: #9ca3af; border: 1px solid rgba(156,163,175,0.25); }

  .price-was { text-decoration: line-through; color: var(--muted); font-size: 0.76rem; margin-left: 4px; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.8rem; }
"""


def build_sku_row_html(s: dict, now: datetime, include_brand_col: bool = True) -> str:
    brand_name = s["brand"]
    brand_slug = sme_brands.get_brand(brand_name)["slug"] if brand_name else ""
    dom = s["domain"]
    tier_str = sme_brands.stockist_tier(dom)
    is_t1 = tier_str.startswith("Tier 1")
    tier_code = "TIER_1" if is_t1 else "TIER_2"
    tier_badge = (
        '<span class="badge badge-t1">Tier 1 Major</span>'
        if is_t1
        else '<span class="badge badge-t2">Tier 2 Indie</span>'
    )

    is_listed = s.get("is_listed", 1) == 1
    is_avail = s.get("is_available", 1) == 1

    if not is_listed:
        status_code = "REMOVED"
        status_badge = '<span class="badge badge-removed">REMOVED</span>'
        oos_since = fmt_ts(s.get("silent_removed_at"))
        dur_str, _ = calc_oos_duration(s.get("silent_removed_at"), now)
        row_cls = "sku-row row-oos"
    elif not is_avail:
        status_code = "OOS"
        status_badge = '<span class="badge badge-oos">OUT OF STOCK</span>'
        oos_since = fmt_ts(s.get("first_seen_oos_at"))
        dur_str, _ = calc_oos_duration(s.get("first_seen_oos_at"), now)
        row_cls = "sku-row row-oos"
    else:
        status_code = "IN_STOCK"
        status_badge = '<span class="badge badge-in">IN STOCK</span>'
        oos_since = "—"
        dur_str = "—"
        row_cls = "sku-row"

    cp = s.get("current_price")
    cmp_p = s.get("compare_at_price")
    price_str = f"£{cp:.2f}" if cp is not None else "—"
    price_html = esc(price_str)
    if cmp_p and cp and cmp_p > cp:
        price_html += f' <span class="price-was">£{cmp_p:.2f}</span>'

    last_chk = fmt_ts(s.get("last_seen_at"))
    url = s.get("product_url") or "#"
    title_clean = (s.get("product_title") or "").split("|")[0].strip()
    var_clean = s.get("variant_title") or "Default"

    search_blob = f"{brand_name} {dom} {tier_str} {title_clean} {var_clean}".lower()

    brand_td = (
        f'<td><a href="{esc(brand_slug)}_dashboard.html"><strong>{esc(brand_name)}</strong></a></td>'
        if include_brand_col
        else ""
    )

    return f"""
    <tr class="{row_cls}"
        data-brand="{esc(brand_name)}"
        data-tier="{tier_code}"
        data-store="{esc(dom)}"
        data-status="{status_code}"
        data-search="{esc(search_blob)}"
        data-csv-brand="{esc(brand_name)}"
        data-csv-store="{esc(dom)}"
        data-csv-tier="{esc(tier_str)}"
        data-csv-product="{esc(title_clean)}"
        data-csv-variant="{esc(var_clean)}"
        data-csv-price="{esc(price_str)}"
        data-csv-status="{esc(status_code)}"
        data-csv-oos-since="{esc(oos_since)}"
        data-csv-duration="{esc(dur_str)}"
        data-csv-last-checked="{esc(last_chk)}"
        data-csv-url="{esc(url)}">
      {brand_td}
      <td class="mono">{esc(dom)}</td>
      <td>{tier_badge}</td>
      <td><strong>{esc(title_clean)}</strong></td>
      <td>{esc(var_clean)}</td>
      <td class="mono">{price_html}</td>
      <td>{status_badge}</td>
      <td class="mono">{esc(oos_since)}</td>
      <td class="mono"><strong>{esc(dur_str)}</strong></td>
      <td class="mono" style="color:var(--muted)">{esc(last_chk)}</td>
      <td><a href="{esc(url)}" target="_blank" rel="noopener">Open ↗</a></td>
    </tr>
    """


def build_brand_html(brand_cfg: dict, skus: list[dict], stores: list[dict], now: datetime) -> str:
    brand_name = brand_cfg["name"]
    slug = brand_cfg["slug"]
    gen_fmt = now.strftime("%Y-%m-%d %H:%M UTC")

    active_skus = [s for s in skus if s["is_listed"] == 1]
    oos_skus = [s for s in active_skus if s["is_available"] == 0]
    in_skus = [s for s in active_skus if s["is_available"] == 1]
    removed_skus = [s for s in skus if s["is_listed"] == 0]

    # Sort SKUs: OOS first (oldest first_seen_oos_at first), then Removed, then In Stock
    def sort_key(s):
        if s["is_listed"] == 1 and s["is_available"] == 0:
            return (0, s.get("first_seen_oos_at") or "", s["domain"], s["product_title"])
        if s["is_listed"] == 0:
            return (1, s.get("silent_removed_at") or "", s["domain"], s["product_title"])
        return (2, "", s["domain"], s["product_title"])

    sorted_skus = sorted(skus, key=sort_key)
    sku_rows_html = "\n".join(build_sku_row_html(s, now, include_brand_col=False) for s in sorted_skus)

    store_options = "\n".join(
        f'<option value="{esc(st["domain"])}">{esc(st["domain"])}</option>' for st in stores
    )

    store_rows_html = []
    for st in stores:
        dom = st["domain"]
        tier_str = sme_brands.stockist_tier(dom)
        is_t1 = tier_str.startswith("Tier 1")
        tier_badge = (
            '<span class="badge badge-t1">Tier 1 Major</span>'
            if is_t1
            else '<span class="badge badge-t2">Tier 2 Indie</span>'
        )
        st_active = [s for s in active_skus if s["domain"] == dom]
        st_oos = [s for s in st_active if s["is_available"] == 0]
        st_in = len(st_active) - len(st_oos)
        oos_pct = round(100.0 * len(st_oos) / len(st_active)) if st_active else 0
        store_rows_html.append(f"""
        <tr>
          <td class="mono"><strong>{esc(dom)}</strong></td>
          <td>{tier_badge}</td>
          <td>{esc(st.get('platform') or 'Custom')}</td>
          <td>{len(st_active)}</td>
          <td class="text-green">{st_in}</td>
          <td class="{'text-red' if st_oos else ''}"><strong>{len(st_oos)}</strong></td>
          <td>{oos_pct}%</td>
          <td class="mono" style="color:var(--muted)">{esc(fmt_ts(st.get('last_checked_at')))}</td>
          <td>
            <button class="btn btn-outline btn-sm" onclick="filterByStore('{esc(dom)}')">View SKUs</button>
            <a href="{esc(st.get('brand_url') or '#')}" target="_blank" rel="noopener" class="btn btn-outline btn-sm">Storefront ↗</a>
          </td>
        </tr>
        """)

    default_status = "OOS" if len(oos_skus) > 0 else "ALL"

    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(brand_name)} — Out-of-Stock Tracker</title>
<style>{SHARED_CSS}</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <div class="title">{esc(brand_name)} — UK Stockist Out-of-Stock Tracker</div>
      <div class="subtitle">Category: {esc(brand_cfg.get('category', 'UK SME Beauty & Wellness'))} • Snapshot: {esc(gen_fmt)}</div>
    </div>
    <div class="header-actions">
      <a href="index.html" class="btn btn-outline">← Admin Panel (All 43 Brands)</a>
      <button class="btn" onclick="exportCSV('{esc(slug)}_oos_export.csv')">⬇ Export Current Table to CSV</button>
    </div>
  </header>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Monitored UK Stockists</div>
      <div class="kpi-value">{len(stores)}</div>
      <div class="kpi-note">Tier 1 Major &amp; Tier 2 Independent</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Out of Stock Now</div>
      <div class="kpi-value text-red">{len(oos_skus)}</div>
      <div class="kpi-note">Variants currently unavailable</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">In Stock Now</div>
      <div class="kpi-value text-green">{len(in_skus)}</div>
      <div class="kpi-note">Variants available to buy</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Removed / Delisted</div>
      <div class="kpi-value text-amber">{len(removed_skus)}</div>
      <div class="kpi-note">Previously listed, now 404/removed</div>
    </div>
  </div>

  <div class="tabs">
    <button class="tab-btn active" id="tabBtnSkus" onclick="switchTab('tab-skus', this)">1. Product &amp; Variant Availability ({len(oos_skus)} OOS / {len(active_skus)} Listed)</button>
    <button class="tab-btn" id="tabBtnStores" onclick="switchTab('tab-stores', this)">2. Stockist Breakdown ({len(stores)} Retailers)</button>
  </div>

  <div id="tab-skus" class="tab-panel active">
    <div class="filter-bar">
      <select id="filterStatus" onchange="applyFilters()">
        <option value="OOS" {'selected' if default_status == 'OOS' else ''}>Out of Stock Only ({len(oos_skus)})</option>
        <option value="ALL" {'selected' if default_status == 'ALL' else ''}>All Tracked Variants ({len(skus)})</option>
        <option value="IN_STOCK">In Stock Only ({len(in_skus)})</option>
        <option value="REMOVED">Removed / Delisted ({len(removed_skus)})</option>
      </select>
      <select id="filterTier" onchange="applyFilters()">
        <option value="ALL">All Stockist Tiers</option>
        <option value="TIER_1">Tier 1: Major UK Retailers</option>
        <option value="TIER_2">Tier 2: Independent Stockists</option>
      </select>
      <select id="filterStore" onchange="applyFilters()">
        <option value="ALL">All Retailers ({len(stores)})</option>
        {store_options}
      </select>
      <input type="text" id="filterSearch" placeholder="Search product, variant, size, or store..." oninput="applyFilters()">
      <span class="filter-count" id="visibleCount"></span>
    </div>

    <div class="table-wrap">
      <table id="skuTable">
        <thead>
          <tr>
            <th>Retailer</th>
            <th>Tier</th>
            <th>Product</th>
            <th>Variant / Size</th>
            <th>Shelf Price</th>
            <th>Status</th>
            <th>First Seen OOS</th>
            <th>Time OOS</th>
            <th>Last Checked</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>
          {sku_rows_html}
        </tbody>
      </table>
    </div>
  </div>

  <div id="tab-stores" class="tab-panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Retailer</th>
            <th>Tier</th>
            <th>Platform</th>
            <th>Listed Variants</th>
            <th>In Stock</th>
            <th>Out of Stock</th>
            <th>OOS %</th>
            <th>Last Checked</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {"".join(store_rows_html)}
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

function filterByStore(domain) {{
  document.getElementById('filterStore').value = domain;
  document.getElementById('filterStatus').value = 'ALL';
  switchTab('tab-skus', document.getElementById('tabBtnSkus'));
  applyFilters();
}}

function applyFilters() {{
  const statusVal = document.getElementById('filterStatus').value;
  const tierVal = document.getElementById('filterTier').value;
  const storeVal = document.getElementById('filterStore').value;
  const q = document.getElementById('filterSearch').value.trim().toLowerCase();
  let shown = 0;

  document.querySelectorAll('#skuTable tbody tr.sku-row').forEach(row => {{
    const rStatus = row.getAttribute('data-status');
    const rTier = row.getAttribute('data-tier');
    const rStore = row.getAttribute('data-store');
    const rSearch = row.getAttribute('data-search');

    const matchStatus = (statusVal === 'ALL' || rStatus === statusVal);
    const matchTier = (tierVal === 'ALL' || rTier === tierVal);
    const matchStore = (storeVal === 'ALL' || rStore === storeVal);
    const matchQ = (!q || rSearch.includes(q));

    if (matchStatus && matchTier && matchStore && matchQ) {{
      row.style.display = '';
      shown++;
    }} else {{
      row.style.display = 'none';
    }}
  }});
  document.getElementById('visibleCount').textContent = `${{shown}} variant(s) shown`;
}}

function exportCSV(filename) {{
  const headers = ['Brand', 'Retailer', 'Tier', 'Product', 'Variant', 'Shelf_Price', 'Status', 'First_Seen_OOS_UTC', 'Time_OOS', 'Last_Checked_UTC', 'Product_URL'];
  const rows = [headers.join(',')];
  document.querySelectorAll('#skuTable tbody tr.sku-row').forEach(row => {{
    if (row.style.display === 'none') return;
    const vals = [
      row.getAttribute('data-csv-brand'),
      row.getAttribute('data-csv-store'),
      row.getAttribute('data-csv-tier'),
      row.getAttribute('data-csv-product'),
      row.getAttribute('data-csv-variant'),
      row.getAttribute('data-csv-price'),
      row.getAttribute('data-csv-status'),
      row.getAttribute('data-csv-oos-since'),
      row.getAttribute('data-csv-duration'),
      row.getAttribute('data-csv-last-checked'),
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

applyFilters();
</script>
</body>
</html>
"""


def build_admin_panel_html(all_stores: list[dict], all_skus: list[dict], now: datetime) -> str:
    """Build the single Unified Admin Panel (`index.html` & `admin_panel.html`) across all 43 brands."""
    gen_fmt = now.strftime("%Y-%m-%d %H:%M UTC")

    active_skus = [s for s in all_skus if s["is_listed"] == 1]
    oos_skus = [s for s in active_skus if s["is_available"] == 0]
    in_skus = [s for s in active_skus if s["is_available"] == 1]
    removed_skus = [s for s in all_skus if s["is_listed"] == 0]

    unique_domains = sorted({st["domain"] for st in all_stores})
    audited_brands = sorted({st["brand"] for st in all_stores})

    # Sort all SKUs globally: OOS first (oldest first_seen_oos_at first), then Removed, then In Stock
    def sort_key(s):
        if s["is_listed"] == 1 and s["is_available"] == 0:
            return (0, s.get("first_seen_oos_at") or "", s["brand"], s["domain"], s["product_title"])
        if s["is_listed"] == 0:
            return (1, s.get("silent_removed_at") or "", s["brand"], s["domain"], s["product_title"])
        return (2, "", s["brand"], s["domain"], s["product_title"])

    sorted_skus = sorted(all_skus, key=sort_key)
    global_sku_rows_html = "\n".join(build_sku_row_html(s, now, include_brand_col=True) for s in sorted_skus)

    brand_options = "\n".join(
        f'<option value="{esc(b)}">{esc(b)}</option>' for b in audited_brands
    )
    store_options = "\n".join(
        f'<option value="{esc(d)}">{esc(d)}</option>' for d in unique_domains
    )

    # Tab 2: Stockist Breakdown across all brands
    store_rows_html = []
    for st in sorted(all_stores, key=lambda x: (x["brand"], x["domain"])):
        b_name = st["brand"]
        b_slug = sme_brands.get_brand(b_name)["slug"]
        dom = st["domain"]
        tier_str = sme_brands.stockist_tier(dom)
        is_t1 = tier_str.startswith("Tier 1")
        tier_badge = (
            '<span class="badge badge-t1">Tier 1 Major</span>'
            if is_t1
            else '<span class="badge badge-t2">Tier 2 Indie</span>'
        )
        st_active = [s for s in active_skus if s["brand"] == b_name and s["domain"] == dom]
        st_oos = [s for s in st_active if s["is_available"] == 0]
        st_in = len(st_active) - len(st_oos)
        oos_pct = round(100.0 * len(st_oos) / len(st_active)) if st_active else 0
        store_rows_html.append(f"""
        <tr>
          <td><a href="{esc(b_slug)}_dashboard.html"><strong>{esc(b_name)}</strong></a></td>
          <td class="mono"><strong>{esc(dom)}</strong></td>
          <td>{tier_badge}</td>
          <td>{esc(st.get('platform') or 'Custom')}</td>
          <td>{len(st_active)}</td>
          <td class="text-green">{st_in}</td>
          <td class="{'text-red' if st_oos else ''}"><strong>{len(st_oos)}</strong></td>
          <td>{oos_pct}%</td>
          <td class="mono" style="color:var(--muted)">{esc(fmt_ts(st.get('last_checked_at')))}</td>
          <td>
            <button class="btn btn-outline btn-sm" onclick="filterByBrandAndStore('{esc(b_name)}', '{esc(dom)}')">View SKUs</button>
            <a href="{esc(st.get('brand_url') or '#')}" target="_blank" rel="noopener" class="btn btn-outline btn-sm">Storefront ↗</a>
          </td>
        </tr>
        """)

    # Tab 3: All 43 Brands Registry
    brand_rows_html = []
    for idx, b_cfg in enumerate(sme_brands.SME_BRANDS, 1):
        b_name = b_cfg["name"]
        b_slug = b_cfg["slug"]
        b_cat = b_cfg.get("category", "UK SME Beauty & Wellness")
        b_stores = [st for st in all_stores if st["brand"] == b_name]
        b_active = [s for s in active_skus if s["brand"] == b_name]
        b_oos = [s for s in b_active if s["is_available"] == 0]
        b_in = len(b_active) - len(b_oos)
        last_ts = max((st.get("last_checked_at") or "" for st in b_stores), default="")
        stockist_file = STOCKISTS_DIR / f"{b_slug}_uk_stockists.json"

        if b_stores:
            status_badge = '<span class="badge badge-in">ACTIVE MONITORING</span>'
            action_html = (
                f'<button class="btn btn-outline btn-sm" onclick="filterByBrand(\'{esc(b_name)}\')">Filter OOS Table</button> '
                f'<a href="{esc(b_slug)}_dashboard.html" class="btn btn-outline btn-sm">Brand Page →</a>'
            )
        elif stockist_file.exists():
            status_badge = '<span class="badge badge-t2">STOCKISTS DISCOVERED</span>'
            action_html = '<span style="color:var(--muted);font-size:0.78rem;">Awaiting next shelf scan</span>'
        else:
            status_badge = '<span class="badge badge-queued">QUEUED (24/7 AUTO-BATCH)</span>'
            action_html = '<span style="color:var(--muted);font-size:0.78rem;">Scheduled in GitHub Actions</span>'

        brand_rows_html.append(f"""
        <tr>
          <td class="mono" style="color:var(--muted)">{idx}</td>
          <td><strong>{esc(b_name)}</strong></td>
          <td>{esc(b_cat)}</td>
          <td>{status_badge}</td>
          <td>{len(b_stores) if b_stores else '—'}</td>
          <td>{len(b_active) if b_stores else '—'}</td>
          <td class="text-green">{b_in if b_stores else '—'}</td>
          <td class="{'text-red' if b_oos else ''}"><strong>{len(b_oos) if b_stores else '—'}</strong></td>
          <td class="mono" style="color:var(--muted)">{esc(fmt_ts(last_ts)) if last_ts else '—'}</td>
          <td>{action_html}</td>
        </tr>
        """)

    default_status = "OOS" if len(oos_skus) > 0 else "ALL"

    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UK Out-of-Stock Intelligence — Master Admin Panel</title>
<style>{SHARED_CSS}</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <div class="title">UK Stockist Out-of-Stock (OOS) Tracker — Master Admin Panel</div>
      <div class="subtitle">All Brands, Stockists &amp; Out-of-Stock Variants in One View • Updated {esc(gen_fmt)}</div>
    </div>
    <div class="header-actions">
      <button class="btn" onclick="exportCSV('uk_master_oos_export.csv')">⬇ Export Current View to CSV</button>
    </div>
  </header>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Out of Stock Right Now</div>
      <div class="kpi-value text-red">{len(oos_skus)}</div>
      <div class="kpi-note">Across all audited brands &amp; shelves</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">In Stock Variants</div>
      <div class="kpi-value text-green">{len(in_skus)}</div>
      <div class="kpi-note">{len(active_skus)} total active variants tracked</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Removed / Delisted</div>
      <div class="kpi-value text-amber">{len(removed_skus)}</div>
      <div class="kpi-note">Previously listed, now 404/removed</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">UK Retail Stockists</div>
      <div class="kpi-value">{len(unique_domains)}</div>
      <div class="kpi-note">{len(all_stores)} brand-store shelves audited</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Registered UK Brands</div>
      <div class="kpi-value text-accent">{len(audited_brands)} / {len(sme_brands.SME_BRANDS)}</div>
      <div class="kpi-note">{len(audited_brands)} active • {len(sme_brands.SME_BRANDS) - len(audited_brands)} queued in 24/7 rotation</div>
    </div>
  </div>

  <div class="tabs">
    <button class="tab-btn active" id="tabBtnSkus" onclick="switchTab('tab-skus', this)">1. Live Out-of-Stock Feed — All Brands ({len(oos_skus)} OOS / {len(all_skus)} Total)</button>
    <button class="tab-btn" id="tabBtnStores" onclick="switchTab('tab-stores', this)">2. Stockist Shelves Breakdown ({len(all_stores)} Brand-Store Shelves)</button>
    <button class="tab-btn" id="tabBtnBrands" onclick="switchTab('tab-brands', this)">3. All {len(sme_brands.SME_BRANDS)} Brands Registry &amp; Pipeline Status</button>
  </div>

  <!-- TAB 1: MASTER OOS FEED -->
  <div id="tab-skus" class="tab-panel active">
    <div class="filter-bar">
      <select id="filterStatus" onchange="applyFilters()">
        <option value="OOS" {'selected' if default_status == 'OOS' else ''}>Out of Stock Only ({len(oos_skus)})</option>
        <option value="ALL" {'selected' if default_status == 'ALL' else ''}>All Tracked Variants ({len(all_skus)})</option>
        <option value="IN_STOCK">In Stock Only ({len(in_skus)})</option>
        <option value="REMOVED">Removed / Delisted ({len(removed_skus)})</option>
      </select>
      <select id="filterBrand" onchange="applyFilters()">
        <option value="ALL">All Audited Brands ({len(audited_brands)})</option>
        {brand_options}
      </select>
      <select id="filterTier" onchange="applyFilters()">
        <option value="ALL">All Stockist Tiers</option>
        <option value="TIER_1">Tier 1: Major UK Retailers</option>
        <option value="TIER_2">Tier 2: Independent Stockists</option>
      </select>
      <select id="filterStore" onchange="applyFilters()">
        <option value="ALL">All UK Retailers ({len(unique_domains)})</option>
        {store_options}
      </select>
      <input type="text" id="filterSearch" placeholder="Search brand, product, variant, size, or retailer..." oninput="applyFilters()">
      <button class="btn btn-outline btn-sm" onclick="resetFilters()">Reset</button>
      <span class="filter-count" id="visibleCount"></span>
    </div>

    <div class="table-wrap">
      <table id="skuTable">
        <thead>
          <tr>
            <th>Brand</th>
            <th>Retailer</th>
            <th>Tier</th>
            <th>Product</th>
            <th>Variant / Size</th>
            <th>Shelf Price</th>
            <th>Status</th>
            <th>First Seen OOS</th>
            <th>Time OOS</th>
            <th>Last Checked</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>
          {global_sku_rows_html}
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 2: STOCKIST BREAKDOWN -->
  <div id="tab-stores" class="tab-panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Brand</th>
            <th>Retailer</th>
            <th>Tier</th>
            <th>Platform</th>
            <th>Listed Variants</th>
            <th>In Stock</th>
            <th>Out of Stock</th>
            <th>OOS %</th>
            <th>Last Checked</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {"".join(store_rows_html)}
        </tbody>
      </table>
    </div>
  </div>

  <!-- TAB 3: ALL 43 BRANDS REGISTRY -->
  <div id="tab-brands" class="tab-panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Brand</th>
            <th>Category</th>
            <th>Pipeline Status</th>
            <th>UK Stockists</th>
            <th>Tracked Variants</th>
            <th>In Stock</th>
            <th>Out of Stock</th>
            <th>Last Checked</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {"".join(brand_rows_html)}
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

function filterByBrand(brandName) {{
  document.getElementById('filterBrand').value = brandName;
  document.getElementById('filterStore').value = 'ALL';
  document.getElementById('filterStatus').value = 'ALL';
  switchTab('tab-skus', document.getElementById('tabBtnSkus'));
  applyFilters();
}}

function filterByBrandAndStore(brandName, domain) {{
  document.getElementById('filterBrand').value = brandName;
  document.getElementById('filterStore').value = domain;
  document.getElementById('filterStatus').value = 'ALL';
  switchTab('tab-skus', document.getElementById('tabBtnSkus'));
  applyFilters();
}}

function resetFilters() {{
  document.getElementById('filterStatus').value = '{default_status}';
  document.getElementById('filterBrand').value = 'ALL';
  document.getElementById('filterTier').value = 'ALL';
  document.getElementById('filterStore').value = 'ALL';
  document.getElementById('filterSearch').value = '';
  applyFilters();
}}

function applyFilters() {{
  const statusVal = document.getElementById('filterStatus').value;
  const brandVal = document.getElementById('filterBrand').value;
  const tierVal = document.getElementById('filterTier').value;
  const storeVal = document.getElementById('filterStore').value;
  const q = document.getElementById('filterSearch').value.trim().toLowerCase();
  let shown = 0;

  document.querySelectorAll('#skuTable tbody tr.sku-row').forEach(row => {{
    const rStatus = row.getAttribute('data-status');
    const rBrand = row.getAttribute('data-brand');
    const rTier = row.getAttribute('data-tier');
    const rStore = row.getAttribute('data-store');
    const rSearch = row.getAttribute('data-search');

    const matchStatus = (statusVal === 'ALL' || rStatus === statusVal);
    const matchBrand = (brandVal === 'ALL' || rBrand === brandVal);
    const matchTier = (tierVal === 'ALL' || rTier === tierVal);
    const matchStore = (storeVal === 'ALL' || rStore === storeVal);
    const matchQ = (!q || rSearch.includes(q));

    if (matchStatus && matchBrand && matchTier && matchStore && matchQ) {{
      row.style.display = '';
      shown++;
    }} else {{
      row.style.display = 'none';
    }}
  }});
  document.getElementById('visibleCount').textContent = `${{shown}} variant(s) shown`;
}}

function exportCSV(filename) {{
  const headers = ['Brand', 'Retailer', 'Tier', 'Product', 'Variant', 'Shelf_Price', 'Status', 'First_Seen_OOS_UTC', 'Time_OOS', 'Last_Checked_UTC', 'Product_URL'];
  const rows = [headers.join(',')];
  document.querySelectorAll('#skuTable tbody tr.sku-row').forEach(row => {{
    if (row.style.display === 'none') return;
    const vals = [
      row.getAttribute('data-csv-brand'),
      row.getAttribute('data-csv-store'),
      row.getAttribute('data-csv-tier'),
      row.getAttribute('data-csv-product'),
      row.getAttribute('data-csv-variant'),
      row.getAttribute('data-csv-price'),
      row.getAttribute('data-csv-status'),
      row.getAttribute('data-csv-oos-since'),
      row.getAttribute('data-csv-duration'),
      row.getAttribute('data-csv-last-checked'),
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

applyFilters();
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

    now = datetime.now(timezone.utc)
    generated_files: list[Path] = []

    all_stores = [dict(r) for r in conn.execute("SELECT * FROM stores ORDER BY brand, domain").fetchall()]
    all_skus = [dict(r) for r in conn.execute("SELECT * FROM skus ORDER BY brand, domain, product_title").fetchall()]

    audited_brand_names = sorted({st["brand"] for st in all_stores})
    for brand_name in audited_brand_names:
        try:
            brand_cfg = sme_brands.get_brand(brand_name)
        except ValueError:
            brand_cfg = {"name": brand_name, "slug": brand_name.lower().replace(" ", "-"), "category": "UK SME"}
        b_stores = [st for st in all_stores if st["brand"] == brand_name]
        b_skus = [s for s in all_skus if s["brand"] == brand_name]

        html_content = build_brand_html(brand_cfg, b_skus, b_stores, now)
        out_path = REPORTS_DIR / f"{brand_cfg['slug']}_dashboard.html"
        out_path.write_text(html_content, encoding="utf-8")
        generated_files.append(out_path)

    # Write Unified Master Admin Panel to both index.html and admin_panel.html
    admin_html = build_admin_panel_html(all_stores, all_skus, now)
    index_path = REPORTS_DIR / "index.html"
    admin_path = REPORTS_DIR / "admin_panel.html"
    index_path.write_text(admin_html, encoding="utf-8")
    admin_path.write_text(admin_html, encoding="utf-8")
    generated_files.extend([index_path, admin_path])

    if close_after:
        conn.close()
    return generated_files


if __name__ == "__main__":
    paths = generate_all_html_dashboards()
    print("Generated HTML Dashboards:")
    for p in paths:
        print(f"  - {p}")
