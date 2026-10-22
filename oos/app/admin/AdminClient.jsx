'use client';

import React, { useState, useMemo } from 'react';
import BrandClient from '../b/[token]/BrandClient';

function fmtShortTime(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return String(isoStr);
  const pad = n => String(n).padStart(2, '0');
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${d.getUTCDate()} ${months[d.getUTCMonth()]}, ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

function calcOosAge(isoStr) {
  if (!isoStr) return 'OOS';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return 'OOS';
  const hours = Math.max(0, (Date.now() - d.getTime()) / 3600000);
  const days = Math.floor(hours / 24);
  const remH = Math.floor(hours % 24);
  const mins = Math.max(1, Math.floor((hours * 60) % 60));
  if (days > 0) return `${days}d ${remH}h OOS`;
  if (remH > 0) return `${remH}h OOS`;
  return `${mins}m OOS`;
}

export default function AdminClient({ initialData }) {
  const [data, setData] = useState(initialData);
  const [viewMode, setViewMode] = useState('directory'); // 'directory' | 'all_oos' | 'brand_sheet'
  const [selectedBrandSlug, setSelectedBrandSlug] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState('ALL'); // 'ALL' | 'ACTIVE' | 'QUEUED'
  const [syncing, setSyncing] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);

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
    setTimeout(() => setToastMsg(null), 2400);
  }

  async function refreshLive() {
    try {
      setSyncing(true);
      const res = await fetch('/api/admin/data', { cache: 'no-store' });
      if (res.ok) {
        const fresh = await res.json();
        setData(fresh);
        showToast('Synced latest data from Supabase');
      }
    } finally {
      setSyncing(false);
    }
  }

  function copyShareLink(sharePath, brandName) {
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    const fullUrl = `${origin}${sharePath}`;
    navigator.clipboard.writeText(fullUrl).then(() => {
      showToast(`Copied ${brandName} link: ${fullUrl}`);
    });
  }

  // Per-brand metrics
  const brandRows = useMemo(() => {
    const storesByBrand = new Map();
    const lastCheckByBrand = new Map();
    const oosByBrand = new Map();
    const activeSkusByBrand = new Map();

    for (const st of data.stores) {
      storesByBrand.set(st.brand, (storesByBrand.get(st.brand) || 0) + 1);
      const prevTs = lastCheckByBrand.get(st.brand) || '';
      if (st.last_checked_at && st.last_checked_at > prevTs) {
        lastCheckByBrand.set(st.brand, st.last_checked_at);
      }
    }

    for (const s of data.skus) {
      if (s.is_listed === 1) {
        activeSkusByBrand.set(s.brand, (activeSkusByBrand.get(s.brand) || 0) + 1);
        if (s.is_available === 0) {
          oosByBrand.set(s.brand, (oosByBrand.get(s.brand) || 0) + 1);
        }
      }
    }

    const enriched = data.brandsMeta.map(b => {
      const storeCount = storesByBrand.get(b.name) || 0;
      const oosCount = oosByBrand.get(b.name) || 0;
      const skuCount = activeSkusByBrand.get(b.name) || 0;
      const lastChecked = lastCheckByBrand.get(b.name) || '';
      return {
        ...b,
        storeCount,
        oosCount,
        skuCount,
        lastChecked,
        isActive: storeCount > 0
      };
    });

    // Sort active brands with OOS first, then alphabetical
    enriched.sort((a, b) => {
      if (a.isActive !== b.isActive) return a.isActive ? -1 : 1;
      if (a.oosCount !== b.oosCount) return b.oosCount - a.oosCount;
      return a.name.localeCompare(b.name);
    });

    return enriched;
  }, [data.brandsMeta, data.stores, data.skus]);

  const filteredBrandRows = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return brandRows.filter(b => {
      if (filterMode === 'ACTIVE' && !b.isActive) return false;
      if (filterMode === 'QUEUED' && b.isActive) return false;
      if (q && !b.name.toLowerCase().includes(q) && !b.category.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [brandRows, searchQuery, filterMode]);

  const totalOosGlobal = useMemo(
    () => data.skus.filter(s => s.is_listed === 1 && s.is_available === 0).length,
    [data.skus]
  );
  const activeBrandCount = useMemo(
    () => brandRows.filter(b => b.isActive).length,
    [brandRows]
  );

  // Global OOS grouped by Brand + Store
  const globalOosGroups = useMemo(() => {
    const oosSkus = data.skus.filter(s => s.is_listed === 1 && s.is_available === 0);
    const byKey = new Map();

    for (const s of oosSkus) {
      const key = `${s.brand} || ${s.domain}`;
      if (!byKey.has(key)) {
        const stObj = data.stores.find(st => st.brand === s.brand && st.domain === s.domain);
        byKey.set(key, {
          brand: s.brand,
          domain: s.domain,
          brandUrl: stObj?.brand_url || s.product_url,
          items: []
        });
      }
      byKey.get(key).items.push(s);
    }

    const list = Array.from(byKey.values());
    list.sort((a, b) => {
      if (a.brand !== b.brand) return a.brand.localeCompare(b.brand);
      return b.items.length - a.items.length;
    });
    return list;
  }, [data.skus, data.stores]);

  // If viewing a single brand sheet inline inside Admin
  if (viewMode === 'brand_sheet' && selectedBrandSlug) {
    const bMeta = data.brandsMeta.find(b => b.slug === selectedBrandSlug);
    if (bMeta) {
      const singleBrandData = {
        syncedAt: data.syncedAt,
        brand: bMeta,
        tier1Domains: data.tier1Domains,
        stores: data.stores.filter(s => s.brand === bMeta.name),
        skus: data.skus.filter(s => s.brand === bMeta.name),
        events: data.events.filter(e => e.brand === bMeta.name)
      };

      return (
        <div>
          <div
            style={{
              maxWidth: 920,
              margin: '0 auto',
              padding: '18px 24px 0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <button
              className="btn-plain"
              onClick={() => {
                setViewMode('directory');
                setSelectedBrandSlug(null);
              }}
            >
              ← All 43 Brands
            </button>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                Customer Link: <code>{bMeta.sharePath}</code>
              </span>
              <button
                className="btn-plain"
                onClick={() => copyShareLink(bMeta.sharePath, bMeta.name)}
              >
                Copy Secret Link
              </button>
              <a
                href={bMeta.sharePath}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-plain"
              >
                Open Standalone ↗
              </a>
            </div>
          </div>
          <BrandClient initialData={singleBrandData} />
          {toastMsg && <div className="toast">{toastMsg}</div>}
        </div>
      );
    }
  }

  return (
    <div className="sheet">
      <header className="sheet-header">
        <div>
          <h1 className="sheet-title">UK Stockist Out of Stock — Admin</h1>
          <p className="sheet-summary">
            <strong className="oos-num">{totalOosGlobal} out of stock</strong> across{' '}
            <strong>{activeBrandCount}</strong> active brands ({data.brandsMeta.length} total in directory) ·{' '}
            {fmtShortTime(data.syncedAt)}
          </p>
        </div>

        <div className="sheet-actions">
          <button
            className={`btn-plain ${viewMode === 'directory' ? 'active' : ''}`}
            onClick={() => setViewMode('directory')}
          >
            Brands ({data.brandsMeta.length})
          </button>
          <button
            className={`btn-plain ${viewMode === 'all_oos' ? 'active' : ''}`}
            onClick={() => setViewMode('all_oos')}
          >
            All OOS ({totalOosGlobal})
          </button>
          <button className="btn-plain" onClick={refreshLive} disabled={syncing}>
            {syncing ? 'Syncing…' : 'Refresh'}
          </button>
        </div>
      </header>

      {/* VIEW 1: CLEAN 43-BRAND DIRECTORY */}
      {viewMode === 'directory' && (
        <div>
          <div className="search-line">
            <input
              type="text"
              className="input-plain"
              placeholder="Search 43 brands..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            <button
              className={`btn-plain ${filterMode === 'ALL' ? 'active' : ''}`}
              onClick={() => setFilterMode('ALL')}
            >
              All ({brandRows.length})
            </button>
            <button
              className={`btn-plain ${filterMode === 'ACTIVE' ? 'active' : ''}`}
              onClick={() => setFilterMode('ACTIVE')}
            >
              Active ({activeBrandCount})
            </button>
            <button
              className={`btn-plain ${filterMode === 'QUEUED' ? 'active' : ''}`}
              onClick={() => setFilterMode('QUEUED')}
            >
              Queued ({brandRows.length - activeBrandCount})
            </button>
          </div>

          <table className="dir-table">
            <thead>
              <tr>
                <th>Brand</th>
                <th>Category</th>
                <th>UK Stockists</th>
                <th>Out of Stock</th>
                <th>Checked</th>
                <th style={{ textAlign: 'right' }}>Share / View</th>
              </tr>
            </thead>
            <tbody>
              {filteredBrandRows.map(b => (
                <tr key={b.slug}>
                  <td>
                    <a
                      href="#"
                      onClick={e => {
                        e.preventDefault();
                        setSelectedBrandSlug(b.slug);
                        setViewMode('brand_sheet');
                      }}
                      style={{ fontWeight: 600 }}
                    >
                      {b.name}
                    </a>
                  </td>
                  <td style={{ color: 'var(--muted)' }}>{b.category}</td>
                  <td>
                    {b.isActive ? (
                      <span>
                        {b.storeCount} stockist{b.storeCount === 1 ? '' : 's'} ({b.skuCount} SKUs)
                      </span>
                    ) : (
                      <span style={{ color: 'var(--subtle)' }}>Queued</span>
                    )}
                  </td>
                  <td>
                    {b.isActive ? (
                      b.oosCount > 0 ? (
                        <span style={{ color: 'var(--red)', fontWeight: 600 }}>
                          {b.oosCount} OOS
                        </span>
                      ) : (
                        <span style={{ color: 'var(--green)' }}>0 OOS</span>
                      )
                    ) : (
                      <span style={{ color: 'var(--subtle)' }}>—</span>
                    )}
                  </td>
                  <td style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>
                    {b.lastChecked ? fmtShortTime(b.lastChecked) : '—'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: 6 }}>
                      <button
                        className="btn-plain btn-xs"
                        onClick={() => copyShareLink(b.sharePath, b.name)}
                      >
                        Copy Link
                      </button>
                      <button
                        className="btn-plain btn-xs"
                        onClick={() => {
                          setSelectedBrandSlug(b.slug);
                          setViewMode('brand_sheet');
                        }}
                      >
                        Sheet →
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* VIEW 2: ALL OOS ACROSS ALL BRANDS, GROUPED BY BRAND + STOCKIST */}
      {viewMode === 'all_oos' && (
        <div>
          {globalOosGroups.map(grp => {
            const major = isTier1(grp.domain);
            return (
              <section key={`${grp.brand}-${grp.domain}`} className="store-group">
                <div className="store-group-header">
                  <div className="store-domain">
                    <span>
                      {grp.brand} · {grp.domain}
                    </span>
                    {major && <span className="tier-tag">Major Retailer</span>}
                  </div>
                  <div className="store-meta">
                    <span className="store-oos-count">{grp.items.length} Out of Stock</span>
                    <a
                      href={grp.brandUrl || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="store-ext-link"
                    >
                      Storefront ↗
                    </a>
                  </div>
                </div>

                <ul className="sku-list">
                  {grp.items.map(s => {
                    const title = String(s.product_title || '').split('|')[0].trim();
                    const variant =
                      s.variant_title && s.variant_title !== 'Default' && s.variant_title !== 'Standard'
                        ? `(${s.variant_title})`
                        : '';
                    const price =
                      s.current_price !== null && s.current_price !== undefined
                        ? `£${Number(s.current_price).toFixed(2)}`
                        : '';

                    return (
                      <li key={s.sku_key} className="sku-item">
                        <div>
                          <span className="sku-name">{title}</span>
                          {variant && <span className="sku-variant">{variant}</span>}
                        </div>
                        <div className="sku-price">{price}</div>
                        <div className="sku-oos-age">{calcOosAge(s.first_seen_oos_at)}</div>
                        <a
                          href={s.product_url || '#'}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="sku-open"
                        >
                          ↗
                        </a>
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
      )}

      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}
