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

function cleanProductDisplayName(rawTitle, brandName) {
  let t = String(rawTitle || '').split('|')[0].trim();
  if (brandName) {
    const escaped = brandName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    t = t.replace(new RegExp(`^${escaped}\\s*[-–—:]?\\s*`, 'i'), '').trim();
  }
  t = t.replace(/[, -]*\b\d+(?:\.\d+)?\s*(?:ml|g|kg|oz|caps|capsules|tablets|sachets)\b\s*$/i, '').trim();
  return t || String(rawTitle || '').trim();
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
    const oosProductsByBrand = new Map();
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
          const pKey = s.normalized_product_key || cleanProductDisplayName(s.product_title, s.brand).toLowerCase();
          if (!oosProductsByBrand.has(s.brand)) oosProductsByBrand.set(s.brand, new Set());
          oosProductsByBrand.get(s.brand).add(pKey);
        }
      }
    }

    const enriched = data.brandsMeta.map(b => {
      const storeCount = storesByBrand.get(b.name) || 0;
      const oosProdCount = oosProductsByBrand.get(b.name)?.size || 0;
      const skuCount = activeSkusByBrand.get(b.name) || 0;
      const lastChecked = lastCheckByBrand.get(b.name) || '';
      return {
        ...b,
        storeCount,
        oosProdCount,
        skuCount,
        lastChecked,
        isActive: storeCount > 0
      };
    });

    enriched.sort((a, b) => {
      if (a.isActive !== b.isActive) return a.isActive ? -1 : 1;
      if (a.oosProdCount !== b.oosProdCount) return b.oosProdCount - a.oosProdCount;
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

  const activeBrandCount = useMemo(
    () => brandRows.filter(b => b.isActive).length,
    [brandRows]
  );

  // Global OOS grouped by Brand + Canonical Product -> consolidated per Stockist
  const globalOosProductGroups = useMemo(() => {
    const oosSkus = data.skus.filter(s => s.is_listed === 1 && s.is_available === 0);
    const byKey = new Map();

    for (const s of oosSkus) {
      const pKey = s.normalized_product_key || cleanProductDisplayName(s.product_title, s.brand).toLowerCase();
      const key = `${s.brand} || ${pKey}`;
      if (!byKey.has(key)) {
        byKey.set(key, {
          key,
          brand: s.brand,
          displayName: cleanProductDisplayName(s.product_title, s.brand),
          oosStores: new Set(),
          byStore: new Map()
        });
      }
      const grp = byKey.get(key);
      const cand = cleanProductDisplayName(s.product_title, s.brand);
      if (cand.length > 2 && cand.length < grp.displayName.length) {
        grp.displayName = cand;
      }
      grp.oosStores.add(s.domain);

      if (!grp.byStore.has(s.domain)) {
        grp.byStore.set(s.domain, {
          domain: s.domain,
          variants: [],
          oldestOosAt: s.first_seen_oos_at || '',
          primaryUrl: s.product_url || '#'
        });
      }
      const stRow = grp.byStore.get(s.domain);
      stRow.variants.push(s);
      if (s.first_seen_oos_at && (!stRow.oldestOosAt || s.first_seen_oos_at < stRow.oldestOosAt)) {
        stRow.oldestOosAt = s.first_seen_oos_at;
      }
    }

    const list = Array.from(byKey.values()).map(g => ({
      ...g,
      consolidatedStores: Array.from(g.byStore.values()).sort((a, b) => {
        if (b.variants.length !== a.variants.length) return b.variants.length - a.variants.length;
        return a.domain.localeCompare(b.domain);
      })
    }));

    list.sort((a, b) => {
      if (b.oosStores.size !== a.oosStores.size) return b.oosStores.size - a.oosStores.size;
      return a.displayName.localeCompare(b.displayName);
    });
    return list;
  }, [data.skus]);

  const [expandedGlobalKeys, setExpandedGlobalKeys] = useState(() =>
    globalOosProductGroups.length > 0 ? new Set([globalOosProductGroups[0].key]) : new Set()
  );

  function toggleGlobalKey(k) {
    setExpandedGlobalKeys(prev => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  }

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
          <h1 className="sheet-title">UK Out of Stock Products — Admin</h1>
          <p className="sheet-summary">
            <strong className="oos-num">{globalOosProductGroups.length} products out of stock</strong> across{' '}
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
            All OOS Products ({globalOosProductGroups.length})
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
                <th>OOS Products</th>
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
                        {b.storeCount} stockist{b.storeCount === 1 ? '' : 's'}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--subtle)' }}>Queued</span>
                    )}
                  </td>
                  <td>
                    {b.isActive ? (
                      b.oosProdCount > 0 ? (
                        <span style={{ color: 'var(--red)', fontWeight: 600 }}>
                          {b.oosProdCount} product{b.oosProdCount === 1 ? '' : 's'}
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

      {/* VIEW 2: ALL OOS PRODUCTS ACROSS ALL BRANDS (CONSOLIDATED PER STOCKIST) */}
      {viewMode === 'all_oos' && (
        <div>
          {globalOosProductGroups.map(grp => {
            const isExpanded = expandedGlobalKeys.has(grp.key);
            const storePreview = Array.from(grp.oosStores).join(', ');
            const storeCount = grp.oosStores.size;

            return (
              <section key={grp.key} className={`store-group ${isExpanded ? 'expanded' : ''}`}>
                <div className="store-group-header" onClick={() => toggleGlobalKey(grp.key)}>
                  <div className="store-header-left">
                    <span className="store-chevron">{isExpanded ? '▾' : '▸'}</span>
                    <span className="store-domain">
                      {grp.brand} · {grp.displayName}
                    </span>
                    {!isExpanded && <span className="collapsed-preview">{storePreview}</span>}
                  </div>
                  <div className="store-meta" onClick={e => e.stopPropagation()}>
                    <span
                      className="store-oos-count"
                      style={{ cursor: 'pointer' }}
                      onClick={() => toggleGlobalKey(grp.key)}
                    >
                      Out of Stock at {storeCount} store{storeCount === 1 ? '' : 's'}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <ul className="sku-list">
                    {grp.consolidatedStores.map(stRow => {
                      const major = isTier1(stRow.domain);

                      return (
                        <li key={stRow.domain} className="sku-item">
                          <div>
                            <span className="sku-name">{stRow.domain}</span>
                            {major && (
                              <span className="tier-tag" style={{ marginLeft: 8 }}>
                                Major Retailer
                              </span>
                            )}
                          </div>

                          <div className="var-pills-wrap">
                            {stRow.variants.map(v => {
                              const hasNamedSize =
                                v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard';
                              const price =
                                v.current_price !== null && v.current_price !== undefined
                                  ? `£${Number(v.current_price).toFixed(2)}`
                                  : '';

                              if (!hasNamedSize && stRow.variants.length === 1) {
                                return (
                                  <span key={v.sku_key} className="sku-price">
                                    {price}
                                  </span>
                                );
                              }

                              return (
                                <span key={v.sku_key} className="var-pill">
                                  {hasNamedSize && <span>{v.variant_title}</span>}
                                  {price && <span className="var-pill-price">{price}</span>}
                                </span>
                              );
                            })}
                          </div>

                          <div className="sku-oos-age">{calcOosAge(stRow.oldestOosAt)}</div>
                          <a
                            href={stRow.primaryUrl}
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
                )}
              </section>
            );
          })}
        </div>
      )}

      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}
