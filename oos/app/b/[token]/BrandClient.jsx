'use client';

import React, { useState, useMemo } from 'react';

function fmtUtc(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return String(isoStr);
  const pad = n => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

function calcDuration(isoStr) {
  if (!isoStr) return { label: '—', hours: 0 };
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return { label: '—', hours: 0 };
  const hours = Math.max(0, (Date.now() - d.getTime()) / 3600000);
  const days = Math.floor(hours / 24);
  const remH = Math.floor(hours % 24);
  const mins = Math.max(1, Math.floor((hours * 60) % 60));
  if (days > 0) return { label: `${days}d ${remH}h`, hours };
  if (remH > 0) return { label: `${remH}h ${mins}m`, hours };
  return { label: `${mins}m`, hours };
}

export default function BrandClient({ initialData }) {
  const [data, setData] = useState(initialData);
  const [syncing, setSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState('skus');

  const [statusFilter, setStatusFilter] = useState('OOS');
  const [tierFilter, setTierFilter] = useState('ALL');
  const [storeFilter, setStoreFilter] = useState('ALL');
  const [sortOrder, setSortOrder] = useState('LONGEST_OOS');
  const [searchQuery, setSearchQuery] = useState('');
  const [toastMsg, setToastMsg] = useState(null);

  const brand = data.brand;
  const tier1Set = useMemo(() => new Set(data.tier1Domains || []), [data.tier1Domains]);

  function isTier1(domain) {
    const d = String(domain || '').toLowerCase().replace(/^www\./, '');
    for (const major of tier1Set) {
      if (d === major || d.endsWith('.' + major)) return true;
    }
    return false;
  }

  function showToast(msg) {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 2600);
  }

  async function refreshBrandData() {
    try {
      setSyncing(true);
      const res = await fetch(`/api/brand/${brand.token}`, { cache: 'no-store' });
      if (res.ok) {
        const fresh = await res.json();
        setData(fresh);
        showToast('Refreshed live shelf data');
      }
    } finally {
      setSyncing(false);
    }
  }

  const storeDomains = useMemo(
    () => Array.from(new Set(data.stores.map(s => s.domain))).sort(),
    [data.stores]
  );

  const kpis = useMemo(() => {
    const activeSkus = data.skus.filter(s => s.is_listed === 1);
    const oosSkus = activeSkus.filter(s => s.is_available === 0);
    const inSkus = activeSkus.filter(s => s.is_available === 1);
    const removedSkus = data.skus.filter(s => s.is_listed === 0);
    const oosRate = activeSkus.length > 0 ? Math.round((oosSkus.length / activeSkus.length) * 100) : 0;

    const t1Count = storeDomains.filter(d => isTier1(d)).length;
    const t2Count = storeDomains.length - t1Count;

    let maxHours = 0;
    let maxLabel = '—';
    for (const s of oosSkus) {
      const dur = calcDuration(s.first_seen_oos_at);
      if (dur.hours > maxHours) {
        maxHours = dur.hours;
        maxLabel = dur.label;
      }
    }

    let latestCheck = '';
    for (const st of data.stores) {
      if (st.last_checked_at && st.last_checked_at > latestCheck) latestCheck = st.last_checked_at;
    }

    return {
      activeCount: activeSkus.length,
      oosCount: oosSkus.length,
      inCount: inSkus.length,
      removedCount: removedSkus.length,
      oosRate,
      uniqueStoreCount: storeDomains.length,
      t1Count,
      t2Count,
      maxLabel,
      latestCheck
    };
  }, [data.skus, data.stores, storeDomains]);

  const visibleSkus = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const filtered = data.skus.filter(s => {
      const statusCode = s.is_listed === 0 ? 'REMOVED' : s.is_available === 0 ? 'OOS' : 'IN_STOCK';
      if (statusFilter !== 'ALL' && statusCode !== statusFilter) return false;

      const tierCode = isTier1(s.domain) ? 'TIER_1' : 'TIER_2';
      if (tierFilter !== 'ALL' && tierCode !== tierFilter) return false;

      if (storeFilter !== 'ALL' && s.domain !== storeFilter) return false;

      if (q) {
        const hay = `${s.domain} ${s.product_title} ${s.variant_title}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    filtered.sort((a, b) => {
      const aOos = a.is_listed === 1 && a.is_available === 0 ? 0 : a.is_listed === 0 ? 1 : 2;
      const bOos = b.is_listed === 1 && b.is_available === 0 ? 0 : b.is_listed === 0 ? 1 : 2;
      if (aOos !== bOos) return aOos - bOos;

      if (sortOrder === 'LONGEST_OOS') {
        const tA = a.first_seen_oos_at || '9999';
        const tB = b.first_seen_oos_at || '9999';
        if (tA !== tB) return tA.localeCompare(tB);
      } else if (sortOrder === 'NEWEST_OOS') {
        const tA = a.first_seen_oos_at || '';
        const tB = b.first_seen_oos_at || '';
        if (tA !== tB) return tB.localeCompare(tA);
      } else if (sortOrder === 'STORE_AZ') {
        if (a.domain !== b.domain) return a.domain.localeCompare(b.domain);
      } else if (sortOrder === 'PRODUCT_AZ') {
        if (a.product_title !== b.product_title) return a.product_title.localeCompare(b.product_title);
      }
      return (a.product_title || '').localeCompare(b.product_title || '');
    });

    return filtered;
  }, [data.skus, statusFilter, tierFilter, storeFilter, sortOrder, searchQuery]);

  function copyReport() {
    const oosItems = visibleSkus.filter(s => s.is_listed === 1 && s.is_available === 0);
    const targetList = oosItems.length > 0 ? oosItems : visibleSkus;
    if (targetList.length === 0) {
      showToast('No Out-of-Stock items in current view to copy.');
      return;
    }

    const lines = [
      `${brand.name} — UK Stockist Out-of-Stock Report`,
      `Generated: ${fmtUtc(new Date().toISOString())}`,
      `Total Out-of-Stock Variants: ${targetList.length}`,
      `------------------------------------------------------------`
    ];

    const grouped = new Map();
    for (const s of targetList) {
      if (!grouped.has(s.domain)) grouped.set(s.domain, []);
      grouped.get(s.domain).push(s);
    }

    for (const [dom, items] of grouped.entries()) {
      const tierLbl = isTier1(dom) ? 'Tier 1 Major Retailer' : 'Tier 2 Independent Stockist';
      lines.push('');
      lines.push(`[${dom}] (${tierLbl}) — ${items.length} OOS variant(s):`);
      for (const item of items) {
        const cleanTitle = String(item.product_title || '').split('|')[0].trim();
        const priceStr =
          item.current_price !== null && item.current_price !== undefined
            ? `£${Number(item.current_price).toFixed(2)}`
            : '—';
        const dur = calcDuration(item.first_seen_oos_at).label;
        const since = fmtUtc(item.first_seen_oos_at);
        lines.push(
          `  • ${cleanTitle} (${item.variant_title || 'Default'}) | Price: ${priceStr} | OOS for ${dur} (since ${since}) | ${item.product_url || ''}`
        );
      }
    }

    navigator.clipboard.writeText(lines.join('\n')).then(() => {
      showToast(`Copied ${targetList.length} OOS variant(s) to clipboard!`);
    });
  }

  function exportCSV() {
    const headers = [
      'Brand',
      'Retailer',
      'Tier',
      'Product',
      'Variant',
      'Shelf_Price_GBP',
      'Status',
      'First_Seen_OOS_UTC',
      'Time_OOS',
      'Last_Checked_UTC',
      'Product_URL'
    ];
    const rows = [headers.join(',')];

    for (const s of visibleSkus) {
      const tierStr = isTier1(s.domain) ? 'Tier 1 (Major UK Retailer)' : 'Tier 2 (Independent Stockist)';
      const statusStr = s.is_listed === 0 ? 'REMOVED' : s.is_available === 0 ? 'OUT_OF_STOCK' : 'IN_STOCK';
      const oosSince =
        s.is_listed === 0 ? fmtUtc(s.silent_removed_at) : s.is_available === 0 ? fmtUtc(s.first_seen_oos_at) : '';
      const durStr =
        s.is_listed === 0
          ? calcDuration(s.silent_removed_at).label
          : s.is_available === 0
          ? calcDuration(s.first_seen_oos_at).label
          : '';
      const cleanTitle = String(s.product_title || '').split('|')[0].trim();
      const priceStr =
        s.current_price !== null && s.current_price !== undefined ? Number(s.current_price).toFixed(2) : '';

      const vals = [
        brand.name,
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
      ].map(v => `"${String(v ?? '').replace(/"/g, '""')}"`);
      rows.push(vals.join(','));
    }

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${brand.slug}_uk_oos_export.csv`;
    link.click();
  }

  return (
    <div className="customer-container">
      <div className="ws-header">
        <div>
          <div className="ws-title">{brand.name} — UK Retail Out-of-Stock Monitor</div>
          <div className="ws-subtitle">
            <span>{brand.category}</span>
            <span>•</span>
            <span className="sync-pill">● Live Shelf Snapshot ({fmtUtc(data.syncedAt)})</span>
          </div>
        </div>
        <div className="ws-actions">
          <button className="btn btn-outline" onClick={refreshBrandData} disabled={syncing}>
            {syncing ? '↻ Refreshing...' : '↻ Refresh Live Data'}
          </button>
          <button className="btn btn-outline" onClick={copyReport}>
            📋 Copy OOS Summary
          </button>
          <button className="btn" onClick={exportCSV}>
            ⬇ Export CSV
          </button>
        </div>
      </div>

      {/* KPI STRIP */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Out of Stock Now</div>
          <div className="kpi-value text-red">{kpis.oosCount}</div>
          <div className="kpi-note">{kpis.oosRate}% of active shelf variants</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">In Stock Variants</div>
          <div className="kpi-value text-green">{kpis.inCount}</div>
          <div className="kpi-note">{kpis.activeCount} total listed variants</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Removed / Delisted</div>
          <div className="kpi-value text-amber">{kpis.removedCount}</div>
          <div className="kpi-note">Previously listed, now 404/removed</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Monitored UK Retailers</div>
          <div className="kpi-value">{kpis.uniqueStoreCount}</div>
          <div className="kpi-note">
            {kpis.t1Count} Tier 1 Major • {kpis.t2Count} Tier 2 Indie
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Longest Active OOS</div>
          <div className="kpi-value text-accent">{kpis.maxLabel}</div>
          <div className="kpi-note">
            Last scan: {kpis.latestCheck ? fmtUtc(kpis.latestCheck) : 'Pending first scan'}
          </div>
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === 'skus' ? 'active' : ''}`}
          onClick={() => setActiveTab('skus')}
        >
          1. Out-of-Stock &amp; Product Availability ({kpis.oosCount} OOS / {data.skus.length} Total)
        </button>
        <button
          className={`tab-btn ${activeTab === 'stores' ? 'active' : ''}`}
          onClick={() => setActiveTab('stores')}
        >
          2. By UK Retailer ({data.stores.length} Stockists)
        </button>
        <button
          className={`tab-btn ${activeTab === 'events' ? 'active' : ''}`}
          onClick={() => setActiveTab('events')}
        >
          3. Recent Stock Transitions ({data.events.length})
        </button>
      </div>

      {activeTab === 'skus' && (
        <div>
          <div className="filter-bar">
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
              <option value="OOS">Out of Stock Only ({kpis.oosCount})</option>
              <option value="ALL">All Tracked Variants ({data.skus.length})</option>
              <option value="IN_STOCK">In Stock Only ({kpis.inCount})</option>
              <option value="REMOVED">Removed / Delisted ({kpis.removedCount})</option>
            </select>
            <select value={tierFilter} onChange={e => setTierFilter(e.target.value)}>
              <option value="ALL">All Stockist Tiers</option>
              <option value="TIER_1">Tier 1: Major UK Retailers</option>
              <option value="TIER_2">Tier 2: Independent Stockists</option>
            </select>
            <select value={storeFilter} onChange={e => setStoreFilter(e.target.value)}>
              <option value="ALL">All UK Retailers ({storeDomains.length})</option>
              {storeDomains.map(d => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <select value={sortOrder} onChange={e => setSortOrder(e.target.value)}>
              <option value="LONGEST_OOS">Sort: Longest OOS First</option>
              <option value="NEWEST_OOS">Sort: Newest OOS First</option>
              <option value="STORE_AZ">Sort: Retailer (A–Z)</option>
              <option value="PRODUCT_AZ">Sort: Product (A–Z)</option>
            </select>
            <input
              type="text"
              placeholder="Search product, variant, size, or retailer..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            <span className="filter-count">{visibleSkus.length} variant(s) shown</span>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
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
              <tbody>
                {visibleSkus.length === 0 ? (
                  <tr>
                    <td colSpan={10} style={{ textAlign: 'center', padding: 28, color: 'var(--muted)' }}>
                      No matching variants found. Switch the dropdown from &ldquo;Out of Stock Only&rdquo; to &ldquo;All Tracked Variants&rdquo; to view in-stock items.
                    </td>
                  </tr>
                ) : (
                  visibleSkus.map(s => {
                    const t1 = isTier1(s.domain);
                    const isRemoved = s.is_listed === 0;
                    const isOos = s.is_listed === 1 && s.is_available === 0;
                    const oosSinceStr = isRemoved
                      ? fmtUtc(s.silent_removed_at)
                      : isOos
                      ? fmtUtc(s.first_seen_oos_at)
                      : '—';
                    const durStr = isRemoved
                      ? calcDuration(s.silent_removed_at).label
                      : isOos
                      ? calcDuration(s.first_seen_oos_at).label
                      : '—';
                    const cleanTitle = String(s.product_title || '').split('|')[0].trim();
                    const cp =
                      s.current_price !== null && s.current_price !== undefined
                        ? `£${Number(s.current_price).toFixed(2)}`
                        : '—';
                    const hasDiscount =
                      s.compare_at_price &&
                      s.current_price &&
                      Number(s.compare_at_price) > Number(s.current_price);

                    return (
                      <tr key={s.sku_key} className={isOos || isRemoved ? 'row-oos' : ''}>
                        <td className="mono">{s.domain}</td>
                        <td>
                          {t1 ? (
                            <span className="badge badge-t1">Tier 1 Major</span>
                          ) : (
                            <span className="badge badge-t2">Tier 2 Indie</span>
                          )}
                        </td>
                        <td>
                          <strong>{cleanTitle}</strong>
                        </td>
                        <td>{s.variant_title || 'Default'}</td>
                        <td className="mono">
                          {cp}
                          {hasDiscount && (
                            <span className="price-was">£{Number(s.compare_at_price).toFixed(2)}</span>
                          )}
                        </td>
                        <td>
                          {isRemoved ? (
                            <span className="badge badge-removed">REMOVED</span>
                          ) : isOos ? (
                            <span className="badge badge-oos">OUT OF STOCK</span>
                          ) : (
                            <span className="badge badge-in">IN STOCK</span>
                          )}
                        </td>
                        <td className="mono">{oosSinceStr}</td>
                        <td className="mono">
                          <strong>{durStr}</strong>
                        </td>
                        <td className="mono" style={{ color: 'var(--muted)' }}>
                          {fmtUtc(s.last_seen_at)}
                        </td>
                        <td>
                          <a href={s.product_url || '#'} target="_blank" rel="noopener noreferrer">
                            Open ↗
                          </a>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'stores' && (
        <div className="table-wrap">
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
                <th>Last Checked (UTC)</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.stores.map(st => {
                const t1 = isTier1(st.domain);
                const stActive = data.skus.filter(s => s.domain === st.domain && s.is_listed === 1);
                const stOos = stActive.filter(s => s.is_available === 0);
                const stIn = stActive.length - stOos.length;
                const oosPct = stActive.length > 0 ? Math.round((stOos.length / stActive.length) * 100) : 0;

                return (
                  <tr key={st.domain}>
                    <td className="mono">
                      <strong>{st.domain}</strong>
                    </td>
                    <td>
                      {t1 ? (
                        <span className="badge badge-t1">Tier 1 Major</span>
                      ) : (
                        <span className="badge badge-t2">Tier 2 Indie</span>
                      )}
                    </td>
                    <td>{st.platform || 'Custom'}</td>
                    <td>{stActive.length}</td>
                    <td className="text-green">{stIn}</td>
                    <td className={stOos.length > 0 ? 'text-red' : ''}>
                      <strong>{stOos.length}</strong>
                    </td>
                    <td>{oosPct}%</td>
                    <td className="mono" style={{ color: 'var(--muted)' }}>
                      {fmtUtc(st.last_checked_at)}
                    </td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => {
                          setStoreFilter(st.domain);
                          setStatusFilter('ALL');
                          setActiveTab('skus');
                        }}
                      >
                        View SKUs
                      </button>
                      <a
                        href={st.brand_url || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-outline btn-sm"
                      >
                        Storefront ↗
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'events' && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp (UTC)</th>
                <th>Event</th>
                <th>Retailer</th>
                <th>Product</th>
                <th>Variant</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {data.events.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: 28, color: 'var(--muted)' }}>
                    No status transitions logged yet.
                  </td>
                </tr>
              ) : (
                data.events.map((ev, idx) => (
                  <tr key={ev.id || idx}>
                    <td className="mono">{fmtUtc(ev.occurred_at)}</td>
                    <td>
                      {ev.event_type === 'WENT_OOS' ? (
                        <span className="badge badge-oos">WENT OOS</span>
                      ) : ev.event_type === 'RESTOCKED' ? (
                        <span className="badge badge-in">RESTOCKED</span>
                      ) : ev.event_type === 'SILENT_REMOVED' ? (
                        <span className="badge badge-removed">REMOVED</span>
                      ) : (
                        <span className="badge badge-t2">{ev.event_type}</span>
                      )}
                    </td>
                    <td className="mono">{ev.domain}</td>
                    <td>{String(ev.product_title || '').split('|')[0].trim()}</td>
                    <td>{ev.variant_title || 'Default'}</td>
                    <td style={{ color: 'var(--muted)' }}>{ev.details || ''}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}
