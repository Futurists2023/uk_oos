"""Generate the Live Supabase-Connected Master Admin Panel (`index.html` & `admin_panel.html`)
and Per-Brand Standalone OOS Trackers.

Key Architecture:
1. Live Supabase Web App:
   - Fetches real-time `stores`, `skus`, and `stock_events` directly from Supabase PostgREST API in the browser
     on page load and via the "↻ Sync Live" button (no `git pull` required after cloud runs).
   - Also embeds the latest local SQLite snapshot as an instant zero-latency initial state / offline fallback.
   - Writes `oos/reports/admin_local_config.js` (gitignored) with local read credentials so opening the file locally
     connects to Supabase with zero setup.
2. Left Brand Sidebar + Main Workspace Layout:
   - Left sidebar displays all 43 UK SME brands with live red OOS badges (`9 OOS`, `31 OOS`), status indicators,
     category grouping, search, and quick filter pills (`All` | `Active` | `Has OOS` | `Queued`).
   - Main workspace displays factual KPIs, the Product & Variant Availability table, Stockist Breakdown, and
     Chronological Stock Event Log.
3. Zero Marketing Fluff / Account Manager Export:
   - No fabricated PO values or estimated loss figures.
   - 1-click "📋 Copy OOS Report for Account Manager" (copies clean plain-text/Markdown summary grouped by retailer)
     and "⬇ Export CSV".
"""
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path

from dotenv import load_dotenv
import sme_brands

HERE = Path(__file__).resolve().parent
REPORTS_DIR = HERE / "reports"
STOCKISTS_DIR = HERE / "stockists"
REPORTS_DIR.mkdir(exist_ok=True)

if (HERE / ".env.local").exists():
    load_dotenv(HERE / ".env.local")
elif (HERE.parent / ".env.local").exists():
    load_dotenv(HERE.parent / ".env.local")


def esc(val: object) -> str:
    return html.escape(str(val or ""))


def write_local_supabase_config() -> None:
    """Write gitignored `oos/reports/admin_local_config.js` so local browser opens connect to Supabase even if RLS blocks anon."""
    supa_url = (os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or ""
    if supa_url and supa_key:
        cfg_path = REPORTS_DIR / "admin_local_config.js"
        cfg_path.write_text(
            f"// Local-only Supabase config (gitignored - never committed to GitHub)\n"
            f"window.__LOCAL_SUPABASE_Config = {{\n"
            f"  url: {json.dumps(supa_url)},\n"
            f"  key: {json.dumps(supa_key)}\n"
            f"}};\n",
            encoding="utf-8",
        )


def build_master_admin_html(
    all_stores: list[dict],
    all_skus: list[dict],
    all_events: list[dict],
    now: datetime,
    initial_brand: str = "ALL",
) -> str:
    """Build the Live Supabase Web App Master Admin Panel with Left Brand Sidebar + Main Workspace."""
    supa_url = (os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    supa_anon = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or ""

    # Prepare serializable brand metadata for all 43 configured brands
    brands_meta = []
    for idx, b in enumerate(sme_brands.SME_BRANDS, 1):
        st_file = STOCKISTS_DIR / f"{b['slug']}_uk_stockists.json"
        brands_meta.append({
            "index": idx,
            "slug": b["slug"],
            "name": b["name"],
            "category": b.get("category", "UK SME Beauty & Wellness"),
            "has_stockist_file": st_file.exists(),
        })

    tier1_domains = sorted(sme_brands.TIER_1_MAJOR_UK_RETAILERS)

    embedded_payload = {
        "generated_at": now.isoformat(timespec="seconds"),
        "supabase_url": supa_url,
        "supabase_anon_key": supa_anon,
        "initial_brand": initial_brand,
        "brands_meta": brands_meta,
        "tier1_domains": tier1_domains,
        "stores": all_stores,
        "skus": all_skus,
        "events": all_events,
    }
    json_blob = json.dumps(embedded_payload, ensure_ascii=False).replace("</", "<\\/")

    title_str = (
        "UK Stockist Out-of-Stock Tracker — Master Admin Panel"
        if initial_brand == "ALL"
        else f"{initial_brand} — UK Stockist Out-of-Stock Tracker"
    )

    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title_str)}</title>
<style>
  :root {{
    --bg: #090d16;
    --sidebar-bg: #0f1624;
    --panel: #131c2e;
    --panel-alt: #1b273d;
    --border: #26354d;
    --text: #f8fafc;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --accent-bg: rgba(56, 189, 248, 0.12);
    --red: #ef4444;
    --red-bg: rgba(239, 68, 68, 0.15);
    --green: #10b981;
    --green-bg: rgba(16, 185, 129, 0.15);
    --amber: #f59e0b;
    --amber-bg: rgba(245, 158, 11, 0.15);
    --purple: #a855f7;
    --purple-bg: rgba(168, 85, 247, 0.15);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 13.5px;
    line-height: 1.45;
    height: 100vh;
    overflow: hidden;
    display: flex;
  }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  /* Layout: Left Sidebar + Right Main Workspace */
  .sidebar {{
    width: 300px;
    min-width: 300px;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    height: 100vh;
  }}
  .sidebar-header {{
    padding: 16px 16px 12px;
    border-bottom: 1px solid var(--border);
  }}
  .sidebar-title {{
    font-size: 0.98rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .sidebar-sub {{
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 2px;
  }}
  .sidebar-search {{
    margin-top: 10px;
    width: 100%;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 0.82rem;
  }}
  .sidebar-pills {{
    display: flex;
    gap: 4px;
    margin-top: 8px;
  }}
  .side-pill {{
    flex: 1;
    text-align: center;
    background: var(--panel);
    color: var(--muted);
    border: 1px solid var(--border);
    padding: 4px 6px;
    border-radius: 5px;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
  }}
  .side-pill.active {{
    background: var(--accent-bg);
    color: var(--accent);
    border-color: rgba(56, 189, 248, 0.4);
  }}
  .sidebar-list {{
    flex: 1;
    overflow-y: auto;
    padding: 10px 8px 24px;
  }}
  .cat-header {{
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    padding: 12px 10px 4px;
    font-weight: 700;
  }}
  .brand-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 10px;
    border-radius: 6px;
    cursor: pointer;
    margin-bottom: 2px;
    border: 1px solid transparent;
    transition: background 0.12s;
  }}
  .brand-item:hover {{
    background: rgba(255, 255, 255, 0.04);
  }}
  .brand-item.active {{
    background: var(--accent-bg);
    border-color: rgba(56, 189, 248, 0.35);
  }}
  .brand-item-left {{
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }}
  .status-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  .dot-active {{ background: var(--green); box-shadow: 0 0 6px rgba(16, 185, 129, 0.6); }}
  .dot-oos {{ background: var(--red); box-shadow: 0 0 6px rgba(239, 68, 68, 0.6); }}
  .dot-queued {{ background: #475569; }}
  .brand-item-name {{
    font-weight: 600;
    font-size: 0.83rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .brand-badge {{
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 999px;
    flex-shrink: 0;
  }}
  .bb-oos {{ background: var(--red-bg); color: #fca5a5; border: 1px solid rgba(239,68,68,0.35); }}
  .bb-ok {{ background: var(--green-bg); color: #6ee7b7; }}
  .bb-queued {{ background: rgba(148,163,184,0.1); color: #64748b; font-weight: 500; }}

  /* Main Workspace */
  .workspace {{
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow-y: auto;
    padding: 20px 26px 48px;
  }}
  .ws-header {{
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-start;
    gap: 14px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 18px;
  }}
  .ws-title {{ font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; }}
  .ws-subtitle {{ color: var(--muted); font-size: 0.83rem; margin-top: 3px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
  .sync-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    padding: 2px 9px;
    border-radius: 999px;
    background: var(--panel);
    border: 1px solid var(--border);
    color: var(--muted);
  }}
  .sync-pill.live {{
    color: #6ee7b7;
    border-color: rgba(16,185,129,0.35);
    background: rgba(16,185,129,0.08);
  }}

  .ws-actions {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
  .btn {{
    background: var(--accent);
    color: #090d16;
    border: none;
    padding: 7px 13px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    font-size: 0.82rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: opacity 0.12s;
  }}
  .btn:hover {{ opacity: 0.9; text-decoration: none; }}
  .btn-outline {{
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
  }}
  .btn-outline:hover {{ background: var(--panel-alt); }}
  .btn-sm {{ padding: 4px 8px; font-size: 0.76rem; border-radius: 5px; }}

  /* KPI Grid */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
    gap: 12px;
    margin-bottom: 18px;
  }}
  .kpi-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 13px 15px;
  }}
  .kpi-label {{
    font-size: 0.71rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin-bottom: 4px;
  }}
  .kpi-value {{ font-size: 1.55rem; font-weight: 700; }}
  .kpi-note {{ font-size: 0.76rem; color: var(--muted); margin-top: 2px; }}
  .text-red {{ color: #f87171; }}
  .text-green {{ color: #34d399; }}
  .text-amber {{ color: #fbbf24; }}
  .text-accent {{ color: var(--accent); }}

  /* Workspace Tabs */
  .tabs {{
    display: flex;
    gap: 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 14px;
  }}
  .tab-btn {{
    background: transparent;
    color: var(--muted);
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 15px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
  }}
  .tab-btn:hover {{ color: var(--text); }}
  .tab-btn.active {{
    color: var(--accent);
    border-bottom-color: var(--accent);
  }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* Filter Bar */
  .filter-bar {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 10px 12px;
    border-radius: 8px;
    margin-bottom: 12px;
    align-items: center;
  }}
  .filter-bar select, .filter-bar input {{
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 0.82rem;
  }}
  .filter-bar input {{ min-width: 210px; flex: 1; }}
  .filter-count {{ margin-left: auto; font-size: 0.8rem; color: var(--muted); font-weight: 600; }}

  /* Tables */
  .table-wrap {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow-x: auto;
  }}
  table {{ width: 100%; border-collapse: collapse; text-align: left; }}
  th {{
    background: rgba(255, 255, 255, 0.025);
    color: var(--muted);
    font-size: 0.71rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 9px 11px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }}
  td {{
    padding: 8px 11px;
    border-bottom: 1px solid rgba(38, 53, 77, 0.6);
    font-size: 0.83rem;
    vertical-align: middle;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}
  tr.row-oos td {{ background: rgba(239, 68, 68, 0.045); }}
  tr.row-oos:hover td {{ background: rgba(239, 68, 68, 0.085); }}

  /* Badges */
  .badge {{
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    white-space: nowrap;
  }}
  .badge-oos {{ background: var(--red-bg); color: #fca5a5; border: 1px solid rgba(239,68,68,0.35); }}
  .badge-in {{ background: var(--green-bg); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.35); }}
  .badge-removed {{ background: var(--amber-bg); color: #fcd34d; border: 1px solid rgba(245,158,11,0.35); }}
  .badge-t1 {{ background: var(--purple-bg); color: #d8b4fe; border: 1px solid rgba(168,85,247,0.35); }}
  .badge-t2 {{ background: var(--accent-bg); color: #7dd3fc; border: 1px solid rgba(56,189,248,0.3); }}

  .price-was {{ text-decoration: line-through; color: var(--muted); font-size: 0.74rem; margin-left: 4px; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.78rem; }}

  /* Toast Notification */
  #toast {{
    position: fixed;
    bottom: 22px;
    right: 24px;
    background: #10b981;
    color: #06281e;
    font-weight: 700;
    padding: 10px 16px;
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.45);
    display: none;
    z-index: 9999;
    font-size: 0.84rem;
  }}
</style>
<!-- Optional local gitignored Supabase config for instant live queries -->
<script src="admin_local_config.js" onerror="/* optional in cloud */"></script>
</head>
<body>

<!-- LEFT BRAND SIDEBAR -->
<aside class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-title">
      <span>UK OOS Admin Panel</span>
      <span id="sidebarTotalBrands" style="font-size:0.74rem;color:var(--muted);">43 Brands</span>
    </div>
    <div class="sidebar-sub">Select a brand or view all at once</div>
    <input type="text" id="brandSearchInput" class="sidebar-search" placeholder="Filter 43 brands..." oninput="renderSidebar()">
    <div class="sidebar-pills">
      <button class="side-pill active" data-side-filter="ALL" onclick="setSidebarFilter('ALL', this)">All</button>
      <button class="side-pill" data-side-filter="ACTIVE" onclick="setSidebarFilter('ACTIVE', this)">Active</button>
      <button class="side-pill" data-side-filter="OOS" onclick="setSidebarFilter('OOS', this)">Has OOS</button>
      <button class="side-pill" data-side-filter="QUEUED" onclick="setSidebarFilter('QUEUED', this)">Queued</button>
    </div>
  </div>
  <div class="sidebar-list" id="sidebarBrandList"></div>
</aside>

<!-- RIGHT MAIN WORKSPACE -->
<main class="workspace">
  <div class="ws-header">
    <div>
      <div class="ws-title" id="wsTitle">All Brands — UK Out-of-Stock Tracker</div>
      <div class="ws-subtitle">
        <span id="wsCategory">Global Portfolio View (43 UK SME Brands)</span>
        <span>•</span>
        <span class="sync-pill" id="syncStatusPill">● Snapshot Loaded</span>
      </div>
    </div>
    <div class="ws-actions">
      <button class="btn btn-outline" onclick="syncFromSupabase(true)" title="Fetch latest stores, SKUs and events directly from Supabase">↻ Sync Live from Supabase</button>
      <button class="btn btn-outline" onclick="copyAccountManagerReport()" title="Copy a clean, zero-fluff OOS summary grouped by retailer for the Account Manager">📋 Copy OOS Report for Account Manager</button>
      <button class="btn" onclick="exportCurrentViewToCSV()">⬇ Export CSV</button>
    </div>
  </div>

  <!-- KPI STRIP -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Out of Stock Now</div>
      <div class="kpi-value text-red" id="kpiOosCount">0</div>
      <div class="kpi-note" id="kpiOosNote">Variants currently unavailable</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">In Stock Variants</div>
      <div class="kpi-value text-green" id="kpiInStockCount">0</div>
      <div class="kpi-note" id="kpiTotalActiveNote">0 total active variants</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Removed / Delisted</div>
      <div class="kpi-value text-amber" id="kpiRemovedCount">0</div>
      <div class="kpi-note">Previously listed, now 404/removed</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Monitored UK Stockists</div>
      <div class="kpi-value" id="kpiStoreCount">0</div>
      <div class="kpi-note" id="kpiStoreTierNote">Tier 1 Major &amp; Tier 2 Indie</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Longest Active OOS</div>
      <div class="kpi-value text-accent" id="kpiLongestOos">—</div>
      <div class="kpi-note" id="kpiLastCheckedNote">Last checked: —</div>
    </div>
  </div>

  <!-- WORKSPACE TABS -->
  <div class="tabs">
    <button class="tab-btn active" id="tabBtnSkus" onclick="switchTab('tab-skus', this)">1. Out-of-Stock &amp; Shelf Availability</button>
    <button class="tab-btn" id="tabBtnStores" onclick="switchTab('tab-stores', this)">2. Stockist Breakdown</button>
    <button class="tab-btn" id="tabBtnEvents" onclick="switchTab('tab-events', this)">3. Chronological Stock Event Log</button>
  </div>

  <!-- TAB 1: OOS & AVAILABILITY TABLE -->
  <div id="tab-skus" class="tab-panel active">
    <div class="filter-bar">
      <select id="filterStatus" onchange="renderSkuTable()">
        <option value="OOS" selected>Out of Stock Only</option>
        <option value="ALL">All Tracked Variants</option>
        <option value="IN_STOCK">In Stock Only</option>
        <option value="REMOVED">Removed / Delisted</option>
      </select>
      <select id="filterTier" onchange="renderSkuTable()">
        <option value="ALL">All Stockist Tiers</option>
        <option value="TIER_1">Tier 1: Major UK Retailers</option>
        <option value="TIER_2">Tier 2: Independent Stockists</option>
      </select>
      <select id="filterStore" onchange="renderSkuTable()">
        <option value="ALL">All UK Retailers</option>
      </select>
      <select id="sortOrder" onchange="renderSkuTable()">
        <option value="LONGEST_OOS">Sort: Longest OOS First</option>
        <option value="NEWEST_OOS">Sort: Newest OOS First</option>
        <option value="STORE_AZ">Sort: Retailer (A–Z)</option>
        <option value="PRODUCT_AZ">Sort: Product (A–Z)</option>
      </select>
      <input type="text" id="filterSearch" placeholder="Search product, variant, size, retailer, or brand..." oninput="renderSkuTable()">
      <button class="btn btn-outline btn-sm" onclick="resetTableFilters()">Reset</button>
      <span class="filter-count" id="visibleCount">0 shown</span>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th id="thBrand">Brand</th>
            <th>Retailer</th>
            <th>Tier</th>
            <th>Product</th>
            <th>Variant / Size</th>
            <th>Shelf Price</th>
            <th>Status</th>
            <th>First Seen OOS (UTC)</th>
            <th>Time OOS</th>
            <th>Last Checked (UTC)</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody id="skuTableBody"></tbody>
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
            <th>Last Checked (UTC)</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="storeTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- TAB 3: CHRONOLOGICAL STOCK EVENT LOG -->
  <div id="tab-events" class="tab-panel">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Timestamp (UTC)</th>
            <th>Event</th>
            <th>Brand</th>
            <th>Retailer</th>
            <th>Product</th>
            <th>Variant</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody id="eventTableBody"></tbody>
      </table>
    </div>
  </div>
</main>

<div id="toast">Copied to clipboard!</div>

<script id="initialData" type="application/json">{json_blob}</script>
<script>
const APP_DATA = JSON.parse(document.getElementById('initialData').textContent);

let state = {{
  selectedBrand: APP_DATA.initial_brand || 'ALL',
  sidebarFilter: 'ALL',
  brandsMeta: APP_DATA.brands_meta || [],
  tier1Set: new Set(APP_DATA.tier1_domains || []),
  stores: APP_DATA.stores || [],
  skus: APP_DATA.skus || [],
  events: APP_DATA.events || [],
  currentVisibleSkus: []
}};

function escHtml(str) {{
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}}

function isTier1(domain) {{
  const d = String(domain || '').toLowerCase().replace(/^www\\./, '');
  for (const major of state.tier1Set) {{
    if (d === major || d.endsWith('.' + major)) return true;
  }}
  return false;
}}

function fmtUtc(isoStr) {{
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return String(isoStr);
  const pad = n => String(n).padStart(2, '0');
  return `${{d.getUTCFullYear()}}-${{pad(d.getUTCMonth()+1)}}-${{pad(d.getUTCDate())}} ${{pad(d.getUTCHours())}}:${{pad(d.getUTCMinutes())}} UTC`;
}}

function calcDuration(isoStr) {{
  if (!isoStr) return {{ label: '—', hours: 0 }};
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return {{ label: '—', hours: 0 }};
  const hours = Math.max(0, (Date.now() - d.getTime()) / 3600000);
  const days = Math.floor(hours / 24);
  const remH = Math.floor(hours % 24);
  const mins = Math.max(1, Math.floor((hours * 60) % 60));
  if (days > 0) return {{ label: `${{days}}d ${{remH}}h`, hours }};
  if (remH > 0) return {{ label: `${{remH}}h ${{mins}}m`, hours }};
  return {{ label: `${{mins}}m`, hours }};
}}

function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => {{ t.style.display = 'none'; }}, 2600);
}}

/* LIVE SUPABASE FETCH */
async function syncFromSupabase(manualClick = false) {{
  const localCfg = window.__LOCAL_SUPABASE_Config || {{}};
  const url = localCfg.url || APP_DATA.supabase_url;
  const key = localCfg.key || APP_DATA.supabase_anon_key;
  const pill = document.getElementById('syncStatusPill');

  if (!url || !key) {{
    pill.textContent = '● Local Snapshot Mode';
    return;
  }}

  try {{
    pill.textContent = '↻ Syncing with Supabase...';
    const headers = {{
      'apikey': key,
      'Authorization': 'Bearer ' + key
    }};

    const [stRes, skRes, evRes] = await Promise.all([
      fetch(`${{url}}/rest/v1/stores?select=*&order=brand.asc,domain.asc&limit=5000`, {{ headers }}),
      fetch(`${{url}}/rest/v1/skus?select=*&order=brand.asc,domain.asc,product_title.asc&limit=10000`, {{ headers }}),
      fetch(`${{url}}/rest/v1/stock_events?select=*&order=occurred_at.desc&limit=300`, {{ headers }})
    ]);

    if (stRes.ok && skRes.ok) {{
      const storesData = await stRes.json();
      const skusData = await skRes.json();
      const eventsData = evRes.ok ? await evRes.json() : [];

      if (Array.isArray(storesData) && storesData.length > 0) {{
        state.stores = storesData;
        state.skus = skusData.map(s => ({{
          ...s,
          current_price: s.current_price !== null ? Number(s.current_price) : null,
          compare_at_price: s.compare_at_price !== null ? Number(s.compare_at_price) : null,
          is_available: s.is_available === true || s.is_available === 1 ? 1 : 0,
          is_listed: s.is_listed === false || s.is_listed === 0 ? 0 : 1
        }}));
        if (Array.isArray(eventsData)) {{
          state.events = eventsData;
        }}
        const nowStr = new Date().toLocaleTimeString('en-GB', {{ hour: '2-digit', minute: '2-digit', second: '2-digit' }});
        pill.textContent = `● Live Supabase Connected (${{nowStr}})`;
        pill.classList.add('live');
        renderAll();
        if (manualClick) showToast(`Synced ${{state.stores.length}} stores & ${{state.skus.length}} SKUs live from Supabase`);
        return;
      }}
    }}
    pill.textContent = `● Snapshot Loaded (${{fmtUtc(APP_DATA.generated_at)}})`;
  }} catch (err) {{
    pill.textContent = `● Offline Snapshot (${{fmtUtc(APP_DATA.generated_at)}})`;
  }}
}}

/* LEFT SIDEBAR RENDERING */
function setSidebarFilter(mode, btn) {{
  state.sidebarFilter = mode;
  document.querySelectorAll('.side-pill').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderSidebar();
}}

function selectBrand(brandName) {{
  state.selectedBrand = brandName;
  document.getElementById('filterStore').value = 'ALL';
  renderAll();
}}

function renderSidebar() {{
  const q = document.getElementById('brandSearchInput').value.trim().toLowerCase();
  const listEl = document.getElementById('sidebarBrandList');

  // Compute per-brand counts
  const storesByBrand = new Map();
  for (const st of state.stores) {{
    storesByBrand.set(st.brand, (storesByBrand.get(st.brand) || 0) + 1);
  }}

  const oosByBrand = new Map();
  const activeByBrand = new Map();
  let totalGlobalOos = 0;

  for (const s of state.skus) {{
    if (s.is_listed === 1) {{
      activeByBrand.set(s.brand, (activeByBrand.get(s.brand) || 0) + 1);
      if (s.is_available === 0) {{
        oosByBrand.set(s.brand, (oosByBrand.get(s.brand) || 0) + 1);
        totalGlobalOos++;
      }}
    }}
  }}

  let html = `
    <div class="brand-item ${{state.selectedBrand === 'ALL' ? 'active' : ''}}" onclick="selectBrand('ALL')">
      <div class="brand-item-left">
        <span class="status-dot dot-oos"></span>
        <span class="brand-item-name">All ${{(state.brandsMeta || []).length}} Brands (Global)</span>
      </div>
      <span class="brand-badge bb-oos">${{totalGlobalOos}} OOS</span>
    </div>
  `;

  // Group brands by category
  const byCat = new Map();
  for (const b of state.brandsMeta) {{
    const stCnt = storesByBrand.get(b.name) || 0;
    const oosCnt = oosByBrand.get(b.name) || 0;
    const isActive = stCnt > 0;

    if (q && !b.name.toLowerCase().includes(q) && !b.category.toLowerCase().includes(q)) continue;
    if (state.sidebarFilter === 'ACTIVE' && !isActive) continue;
    if (state.sidebarFilter === 'OOS' && oosCnt === 0) continue;
    if (state.sidebarFilter === 'QUEUED' && isActive) continue;

    if (!byCat.has(b.category)) byCat.set(b.category, []);
    byCat.get(b.category).push({{ ...b, stCnt, oosCnt, isActive }});
  }}

  for (const [cat, items] of byCat.entries()) {{
    html += `<div class="cat-header">${{escHtml(cat)}} (${{items.length}})</div>`;
    for (const item of items) {{
      const isSel = state.selectedBrand === item.name;
      let dotCls = 'dot-queued';
      let badgeHtml = `<span class="brand-badge bb-queued">Queued</span>`;
      if (item.isActive) {{
        if (item.oosCnt > 0) {{
          dotCls = 'dot-oos';
          badgeHtml = `<span class="brand-badge bb-oos">${{item.oosCnt}} OOS</span>`;
        }} else {{
          dotCls = 'dot-active';
          badgeHtml = `<span class="brand-badge bb-ok">0 OOS</span>`;
        }}
      }}
      html += `
        <div class="brand-item ${{isSel ? 'active' : ''}}" onclick="selectBrand('${{escHtml(item.name).replace(/'/g, "\\'")}}')">
          <div class="brand-item-left">
            <span class="status-dot ${{dotCls}}"></span>
            <span class="brand-item-name" title="${{escHtml(item.name)}}">${{escHtml(item.name)}}</span>
          </div>
          ${{badgeHtml}}
        </div>
      `;
    }}
  }}

  listEl.innerHTML = html;
}}

/* MAIN WORKSPACE RENDERING */
function populateStoreFilterDropdown(scopedStores) {{
  const sel = document.getElementById('filterStore');
  const prev = sel.value;
  const domains = Array.from(new Set(scopedStores.map(s => s.domain))).sort();
  let opts = `<option value="ALL">All UK Retailers (${{domains.length}})</option>`;
  for (const d of domains) {{
    opts += `<option value="${{escHtml(d)}}">${{escHtml(d)}}</option>`;
  }}
  sel.innerHTML = opts;
  if (domains.includes(prev)) sel.value = prev;
  else sel.value = 'ALL';
}}

function renderKpisAndHeader(scopedStores, scopedSkus) {{
  const isAll = state.selectedBrand === 'ALL';
  const brandMeta = state.brandsMeta.find(b => b.name === state.selectedBrand);

  document.getElementById('wsTitle').textContent = isAll
    ? 'All Brands — UK Stockist Out-of-Stock Tracker'
    : `${{state.selectedBrand}} — UK Stockist Out-of-Stock Tracker`;

  document.getElementById('wsCategory').textContent = isAll
    ? `Global Portfolio View (${{state.brandsMeta.length}} UK SME Brands)`
    : `Category: ${{brandMeta ? brandMeta.category : 'UK SME Beauty & Wellness'}}`;

  const activeSkus = scopedSkus.filter(s => s.is_listed === 1);
  const oosSkus = activeSkus.filter(s => s.is_available === 0);
  const inSkus = activeSkus.filter(s => s.is_available === 1);
  const removedSkus = scopedSkus.filter(s => s.is_listed === 0);

  const uniqueDomains = Array.from(new Set(scopedStores.map(s => s.domain)));
  const t1Count = uniqueDomains.filter(d => isTier1(d)).length;
  const t2Count = uniqueDomains.length - t1Count;

  let maxHours = 0;
  let maxLabel = '—';
  for (const s of oosSkus) {{
    const dur = calcDuration(s.first_seen_oos_at);
    if (dur.hours > maxHours) {{
      maxHours = dur.hours;
      maxLabel = dur.label;
    }}
  }}

  let latestCheck = '';
  for (const st of scopedStores) {{
    if (st.last_checked_at && st.last_checked_at > latestCheck) latestCheck = st.last_checked_at;
  }}

  const oosRate = activeSkus.length > 0 ? Math.round((oosSkus.length / activeSkus.length) * 100) : 0;

  document.getElementById('kpiOosCount').textContent = oosSkus.length;
  document.getElementById('kpiOosNote').textContent = `${{oosRate}}% of active shelf variants`;
  document.getElementById('kpiInStockCount').textContent = inSkus.length;
  document.getElementById('kpiTotalActiveNote').textContent = `${{activeSkus.length}} total listed variants`;
  document.getElementById('kpiRemovedCount').textContent = removedSkus.length;
  document.getElementById('kpiStoreCount').textContent = uniqueDomains.length;
  document.getElementById('kpiStoreTierNote').textContent = `${{t1Count}} Tier 1 Major • ${{t2Count}} Tier 2 Indie`;
  document.getElementById('kpiLongestOos').textContent = maxLabel;
  document.getElementById('kpiLastCheckedNote').textContent = `Last scan: ${{latestCheck ? fmtUtc(latestCheck) : 'Queued'}}`;

  document.getElementById('tabBtnSkus').textContent = `1. Out-of-Stock & Shelf Availability (${{oosSkus.length}} OOS / ${{scopedSkus.length}} Total)`;
  document.getElementById('tabBtnStores').textContent = `2. Stockist Breakdown (${{scopedStores.length}} Shelves)`;
}}

function renderSkuTable() {{
  const isAll = state.selectedBrand === 'ALL';
  document.getElementById('thBrand').style.display = isAll ? '' : 'none';

  const scopedSkus = isAll
    ? state.skus
    : state.skus.filter(s => s.brand === state.selectedBrand);

  const statusFilter = document.getElementById('filterStatus').value;
  const tierFilter = document.getElementById('filterTier').value;
  const storeFilter = document.getElementById('filterStore').value;
  const sortOrder = document.getElementById('sortOrder').value;
  const q = document.getElementById('filterSearch').value.trim().toLowerCase();

  let filtered = scopedSkus.filter(s => {{
    const statusCode = s.is_listed === 0 ? 'REMOVED' : (s.is_available === 0 ? 'OOS' : 'IN_STOCK');
    if (statusFilter !== 'ALL' && statusCode !== statusFilter) return false;

    const tierCode = isTier1(s.domain) ? 'TIER_1' : 'TIER_2';
    if (tierFilter !== 'ALL' && tierCode !== tierFilter) return false;

    if (storeFilter !== 'ALL' && s.domain !== storeFilter) return false;

    if (q) {{
      const hay = `${{s.brand}} ${{s.domain}} ${{s.product_title}} ${{s.variant_title}}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }}
    return true;
  }});

  filtered.sort((a, b) => {{
    const aOos = (a.is_listed === 1 && a.is_available === 0) ? 0 : (a.is_listed === 0 ? 1 : 2);
    const bOos = (b.is_listed === 1 && b.is_available === 0) ? 0 : (b.is_listed === 0 ? 1 : 2);
    if (aOos !== bOos) return aOos - bOos;

    if (sortOrder === 'LONGEST_OOS') {{
      const tA = a.first_seen_oos_at || '9999';
      const tB = b.first_seen_oos_at || '9999';
      if (tA !== tB) return tA.localeCompare(tB);
    }} else if (sortOrder === 'NEWEST_OOS') {{
      const tA = a.first_seen_oos_at || '';
      const tB = b.first_seen_oos_at || '';
      if (tA !== tB) return tB.localeCompare(tA);
    }} else if (sortOrder === 'STORE_AZ') {{
      if (a.domain !== b.domain) return a.domain.localeCompare(b.domain);
    }} else if (sortOrder === 'PRODUCT_AZ') {{
      if (a.product_title !== b.product_title) return a.product_title.localeCompare(b.product_title);
    }}
    return (a.product_title || '').localeCompare(b.product_title || '');
  }});

  state.currentVisibleSkus = filtered;
  document.getElementById('visibleCount').textContent = `${{filtered.length}} variant(s) shown`;

  const tbody = document.getElementById('skuTableBody');
  if (filtered.length === 0) {{
    const colSpan = isAll ? 11 : 10;
    tbody.innerHTML = `<tr><td colspan="${{colSpan}}" style="text-align:center;padding:28px;color:var(--muted);">No matching variants found for current filter selection. (Switch Status dropdown to "All Tracked Variants" to inspect in-stock items.)</td></tr>`;
    return;
  }}

  const rowsHtml = filtered.map(s => {{
    const t1 = isTier1(s.domain);
    const tierBadge = t1
      ? '<span class="badge badge-t1">Tier 1 Major</span>'
      : '<span class="badge badge-t2">Tier 2 Indie</span>';

    let statusBadge = '';
    let oosSinceStr = '—';
    let durStr = '—';
    let rowCls = '';

    if (s.is_listed === 0) {{
      statusBadge = '<span class="badge badge-removed">REMOVED</span>';
      oosSinceStr = fmtUtc(s.silent_removed_at);
      durStr = calcDuration(s.silent_removed_at).label;
      rowCls = 'row-oos';
    }} else if (s.is_available === 0) {{
      statusBadge = '<span class="badge badge-oos">OUT OF STOCK</span>';
      oosSinceStr = fmtUtc(s.first_seen_oos_at);
      durStr = calcDuration(s.first_seen_oos_at).label;
      rowCls = 'row-oos';
    }} else {{
      statusBadge = '<span class="badge badge-in">IN STOCK</span>';
    }}

    const cp = s.current_price !== null && s.current_price !== undefined ? `£${{Number(s.current_price).toFixed(2)}}` : '—';
    let priceHtml = escHtml(cp);
    if (s.compare_at_price && s.current_price && Number(s.compare_at_price) > Number(s.current_price)) {{
      priceHtml += ` <span class="price-was">£${{Number(s.compare_at_price).toFixed(2)}}</span>`;
    }}

    const cleanTitle = String(s.product_title || '').split('|')[0].trim();
    const brandTd = isAll
      ? `<td><a href="#" onclick="selectBrand('${{escHtml(s.brand).replace(/'/g, "\\'")}}');return false;"><strong>${{escHtml(s.brand)}}</strong></a></td>`
      : '';

    return `
      <tr class="${{rowCls}}">
        ${{brandTd}}
        <td class="mono">${{escHtml(s.domain)}}</td>
        <td>${{tierBadge}}</td>
        <td><strong>${{escHtml(cleanTitle)}}</strong></td>
        <td>${{escHtml(s.variant_title || 'Default')}}</td>
        <td class="mono">${{priceHtml}}</td>
        <td>${{statusBadge}}</td>
        <td class="mono">${{escHtml(oosSinceStr)}}</td>
        <td class="mono"><strong>${{escHtml(durStr)}}</strong></td>
        <td class="mono" style="color:var(--muted)">${{escHtml(fmtUtc(s.last_seen_at))}}</td>
        <td><a href="${{escHtml(s.product_url || '#')}}" target="_blank" rel="noopener">Open ↗</a></td>
      </tr>
    `;
  }}).join('');

  tbody.innerHTML = rowsHtml;
}}

function renderStoreTable(scopedStores, scopedSkus) {{
  const tbody = document.getElementById('storeTableBody');
  if (scopedStores.length === 0) {{
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:28px;color:var(--muted);">This brand is currently queued in the 24/7 GitHub Actions auto-discovery rotation.</td></tr>`;
    return;
  }}

  const rowsHtml = scopedStores.map(st => {{
    const t1 = isTier1(st.domain);
    const tierBadge = t1
      ? '<span class="badge badge-t1">Tier 1 Major</span>'
      : '<span class="badge badge-t2">Tier 2 Indie</span>';

    const stActive = scopedSkus.filter(s => s.brand === st.brand && s.domain === st.domain && s.is_listed === 1);
    const stOos = stActive.filter(s => s.is_available === 0);
    const stIn = stActive.length - stOos.length;
    const oosPct = stActive.length > 0 ? Math.round((stOos.length / stActive.length) * 100) : 0;

    return `
      <tr>
        <td><strong>${{escHtml(st.brand)}}</strong></td>
        <td class="mono"><strong>${{escHtml(st.domain)}}</strong></td>
        <td>${{tierBadge}}</td>
        <td>${{escHtml(st.platform || 'Custom')}}</td>
        <td>${{stActive.length}}</td>
        <td class="text-green">${{stIn}}</td>
        <td class="${{stOos.length > 0 ? 'text-red' : ''}}"><strong>${{stOos.length}}</strong></td>
        <td>${{oosPct}}%</td>
        <td class="mono" style="color:var(--muted)">${{escHtml(fmtUtc(st.last_checked_at))}}</td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="drillIntoStore('${{escHtml(st.brand).replace(/'/g, "\\'")}}', '${{escHtml(st.domain)}}')">View SKUs</button>
          <a href="${{escHtml(st.brand_url || '#')}}" target="_blank" rel="noopener" class="btn btn-outline btn-sm">Storefront ↗</a>
        </td>
      </tr>
    `;
  }}).join('');

  tbody.innerHTML = rowsHtml;
}}

function renderEventTable(scopedEvents) {{
  const tbody = document.getElementById('eventTableBody');
  document.getElementById('tabBtnEvents').textContent = `3. Chronological Stock Event Log (${{scopedEvents.length}})`;

  if (scopedEvents.length === 0) {{
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:28px;color:var(--muted);">No status transitions logged yet for this selection. Transitions (WENT_OOS, RESTOCKED, SILENT_REMOVED) are recorded automatically on each 6-hour audit.</td></tr>`;
    return;
  }}

  tbody.innerHTML = scopedEvents.map(ev => {{
    let badge = `<span class="badge badge-t2">${{escHtml(ev.event_type)}}</span>`;
    if (ev.event_type === 'WENT_OOS') badge = '<span class="badge badge-oos">WENT OOS</span>';
    else if (ev.event_type === 'RESTOCKED') badge = '<span class="badge badge-in">RESTOCKED</span>';
    else if (ev.event_type === 'SILENT_REMOVED') badge = '<span class="badge badge-removed">REMOVED</span>';

    return `
      <tr>
        <td class="mono">${{escHtml(fmtUtc(ev.occurred_at))}}</td>
        <td>${{badge}}</td>
        <td><strong>${{escHtml(ev.brand)}}</strong></td>
        <td class="mono">${{escHtml(ev.domain)}}</td>
        <td>${{escHtml(String(ev.product_title || '').split('|')[0].trim())}}</td>
        <td>${{escHtml(ev.variant_title || 'Default')}}</td>
        <td style="color:var(--muted)">${{escHtml(ev.details || '')}}</td>
      </tr>
    `;
  }}).join('');
}}

function drillIntoStore(brandName, domain) {{
  state.selectedBrand = brandName;
  renderAll();
  document.getElementById('filterStore').value = domain;
  document.getElementById('filterStatus').value = 'ALL';
  switchTab('tab-skus', document.getElementById('tabBtnSkus'));
  renderSkuTable();
}}

function resetTableFilters() {{
  document.getElementById('filterStatus').value = 'OOS';
  document.getElementById('filterTier').value = 'ALL';
  document.getElementById('filterStore').value = 'ALL';
  document.getElementById('sortOrder').value = 'LONGEST_OOS';
  document.getElementById('filterSearch').value = '';
  renderSkuTable();
}}

function switchTab(tabId, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  btn.classList.add('active');
}}

/* ACCOUNT MANAGER EXPORT: COPY & CSV */
function copyAccountManagerReport() {{
  const isAll = state.selectedBrand === 'ALL';
  const oosItems = state.currentVisibleSkus.filter(s => s.is_listed === 1 && s.is_available === 0);
  const targetList = oosItems.length > 0 ? oosItems : state.currentVisibleSkus;

  if (targetList.length === 0) {{
    showToast('No Out-of-Stock items in current view to copy.');
    return;
  }}

  const headerTitle = isAll ? 'UK Stockist Out-of-Stock Report (All Brands)' : `${{state.selectedBrand}} — UK Stockist Out-of-Stock Report`;
  const lines = [
    `${{headerTitle}}`,
    `Generated: ${{fmtUtc(new Date().toISOString())}}`,
    `Total Out-of-Stock Variants Listed Below: ${{targetList.length}}`,
    `------------------------------------------------------------`
  ];

  // Group by Brand -> Retailer
  const grouped = new Map();
  for (const s of targetList) {{
    const key = `${{s.brand}} || ${{s.domain}}`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(s);
  }}

  for (const [key, items] of grouped.entries()) {{
    const [bName, dom] = key.split(' || ');
    const tierLbl = isTier1(dom) ? 'Tier 1 Major Retailer' : 'Tier 2 Independent Stockist';
    lines.push('');
    lines.push(`[${{dom}}] (${{tierLbl}})${{isAll ? ' — Brand: ' + bName : ''}} — ${{items.length}} OOS variant(s):`);
    for (const item of items) {{
      const cleanTitle = String(item.product_title || '').split('|')[0].trim();
      const priceStr = item.current_price !== null && item.current_price !== undefined ? `£${{Number(item.current_price).toFixed(2)}}` : '—';
      const dur = calcDuration(item.first_seen_oos_at).label;
      const since = fmtUtc(item.first_seen_oos_at);
      lines.push(`  • ${{cleanTitle}} (${{item.variant_title || 'Default'}}) | Price: ${{priceStr}} | OOS for ${{dur}} (since ${{since}}) | ${{item.product_url || ''}}`);
    }}
  }}

  navigator.clipboard.writeText(lines.join('\\n')).then(() => {{
    showToast(`Copied ${{targetList.length}} OOS variant(s) for Account Manager!`);
  }});
}}

function exportCurrentViewToCSV() {{
  const headers = ['Brand', 'Retailer', 'Tier', 'Product', 'Variant', 'Shelf_Price_GBP', 'Status', 'First_Seen_OOS_UTC', 'Time_OOS', 'Last_Checked_UTC', 'Product_URL'];
  const rows = [headers.join(',')];

  for (const s of state.currentVisibleSkus) {{
    const tierStr = isTier1(s.domain) ? 'Tier 1 (Major UK Retailer)' : 'Tier 2 (Independent Stockist)';
    const statusStr = s.is_listed === 0 ? 'REMOVED' : (s.is_available === 0 ? 'OUT_OF_STOCK' : 'IN_STOCK');
    const oosSince = s.is_listed === 0 ? fmtUtc(s.silent_removed_at) : (s.is_available === 0 ? fmtUtc(s.first_seen_oos_at) : '');
    const durStr = s.is_listed === 0 ? calcDuration(s.silent_removed_at).label : (s.is_available === 0 ? calcDuration(s.first_seen_oos_at).label : '');
    const cleanTitle = String(s.product_title || '').split('|')[0].trim();
    const priceStr = s.current_price !== null && s.current_price !== undefined ? Number(s.current_price).toFixed(2) : '';

    const vals = [
      s.brand,
      s.domain,
      tierStr,
      cleanTitle,
      s.variant_title || 'Default',
      priceStr,
      statusStr,
      oosSince,
      durStr,
      fmtUtc(s.last_seen_at),
      s.product_url || ''
    ].map(v => `"${{String(v ?? '').replace(/"/g, '""')}}"`);
    rows.push(vals.join(','));
  }}

  const slug = state.selectedBrand === 'ALL' ? 'all_brands' : state.selectedBrand.toLowerCase().replace(/[^a-z0-9]+/g, '_');
  const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${{slug}}_uk_oos_export.csv`;
  link.click();
}}

function renderAll() {{
  renderSidebar();
  const isAll = state.selectedBrand === 'ALL';
  const scopedStores = isAll ? state.stores : state.stores.filter(s => s.brand === state.selectedBrand);
  const scopedSkus = isAll ? state.skus : state.skus.filter(s => s.brand === state.selectedBrand);
  const scopedEvents = isAll ? state.events : state.events.filter(e => e.brand === state.selectedBrand);

  populateStoreFilterDropdown(scopedStores);
  renderKpisAndHeader(scopedStores, scopedSkus);
  renderSkuTable();
  renderStoreTable(scopedStores, scopedSkus);
  renderEventTable(scopedEvents);
}}

// Initial render from embedded snapshot, then immediately sync live from Supabase
renderAll();
syncFromSupabase(false);
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
    write_local_supabase_config()
    generated_files: list[Path] = []

    all_stores = [dict(r) for r in conn.execute("SELECT * FROM stores ORDER BY brand, domain").fetchall()]
    all_skus = [dict(r) for r in conn.execute("SELECT * FROM skus ORDER BY brand, domain, product_title").fetchall()]
    all_events = [dict(r) for r in conn.execute("SELECT * FROM stock_events ORDER BY id DESC LIMIT 300").fetchall()]

    # Generate Master Admin Panel (index.html and admin_panel.html)
    admin_html = build_master_admin_html(all_stores, all_skus, all_events, now, initial_brand="ALL")
    index_path = REPORTS_DIR / "index.html"
    admin_path = REPORTS_DIR / "admin_panel.html"
    index_path.write_text(admin_html, encoding="utf-8")
    admin_path.write_text(admin_html, encoding="utf-8")
    generated_files.extend([index_path, admin_path])

    # Also generate per-brand pre-selected views for direct links
    audited_brand_names = sorted({st["brand"] for st in all_stores})
    for brand_name in audited_brand_names:
        try:
            brand_cfg = sme_brands.get_brand(brand_name)
            slug = brand_cfg["slug"]
        except ValueError:
            slug = brand_name.lower().replace(" ", "-")
        b_html = build_master_admin_html(all_stores, all_skus, all_events, now, initial_brand=brand_name)
        out_path = REPORTS_DIR / f"{slug}_dashboard.html"
        out_path.write_text(b_html, encoding="utf-8")
        generated_files.append(out_path)

    if close_after:
        conn.close()
    return generated_files


if __name__ == "__main__":
    paths = generate_all_html_dashboards()
    print("Generated HTML Dashboards:")
    for p in paths:
        print(f"  - {p}")
