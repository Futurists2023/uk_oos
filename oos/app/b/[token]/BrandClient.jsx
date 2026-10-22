'use client';

import React, { useState, useMemo, useEffect } from 'react';

function fmtShortTime(isoStr) {
  if (!isoStr) return 'recently';
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

export default function BrandClient({ initialData }) {
  const [data] = useState(initialData);
  const [showHealthyProducts, setShowHealthyProducts] = useState(false);
  const [showInStockStores, setShowInStockStores] = useState(false);
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
    setTimeout(() => setToastMsg(null), 2400);
  }

  // Group active SKUs by Canonical Product Family -> then consolidate variations per Stockist!
  const { oosProductGroups, healthyProductGroups, totalOosVariants, totalStores, latestCheck } = useMemo(() => {
    const activeSkus = data.skus.filter(s => s.is_listed === 1);
    const byProdKey = new Map();

    let maxTs = '';
    for (const st of data.stores) {
      if (st.last_checked_at && st.last_checked_at > maxTs) {
        maxTs = st.last_checked_at;
      }
    }

    for (const s of activeSkus) {
      const pKey = s.normalized_product_key || cleanProductDisplayName(s.product_title, brand.name).toLowerCase();
      if (!byProdKey.has(pKey)) {
        byProdKey.set(pKey, {
          productKey: pKey,
          displayName: cleanProductDisplayName(s.product_title, brand.name),
          oosByStore: new Map(),
          inStockByStore: new Map(),
          oosItems: [],
          inStockItems: [],
          distinctSizes: new Set(),
          oosStores: new Set(),
          allStores: new Set()
        });
      }
      const grp = byProdKey.get(pKey);
      grp.allStores.add(s.domain);

      const candName = cleanProductDisplayName(s.product_title, brand.name);
      if (candName.length > 2 && candName.length < grp.displayName.length) {
        grp.displayName = candName;
      }

      const vTitle = s.variant_title && s.variant_title !== 'Default' && s.variant_title !== 'Standard' ? s.variant_title : '';
      if (vTitle) grp.distinctSizes.add(vTitle);

      if (s.is_available === 0) {
        grp.oosItems.push(s);
        grp.oosStores.add(s.domain);
        if (!grp.oosByStore.has(s.domain)) {
          grp.oosByStore.set(s.domain, {
            domain: s.domain,
            isOos: true,
            variants: [],
            oldestOosAt: s.first_seen_oos_at || '',
            primaryUrl: s.product_url || '#'
          });
        }
        const stRow = grp.oosByStore.get(s.domain);
        stRow.variants.push(s);
        if (s.first_seen_oos_at && (!stRow.oldestOosAt || s.first_seen_oos_at < stRow.oldestOosAt)) {
          stRow.oldestOosAt = s.first_seen_oos_at;
        }
      } else {
        grp.inStockItems.push(s);
        if (!grp.inStockByStore.has(s.domain)) {
          grp.inStockByStore.set(s.domain, {
            domain: s.domain,
            isOos: false,
            variants: [],
            oldestOosAt: '',
            primaryUrl: s.product_url || '#'
          });
        }
        grp.inStockByStore.get(s.domain).variants.push(s);
      }
    }

    const withOos = [];
    const healthy = [];
    let oosVariantSum = 0;

    for (const grp of byProdKey.values()) {
      grp.consolidatedOosStores = Array.from(grp.oosByStore.values()).sort((a, b) => {
        if (b.variants.length !== a.variants.length) return b.variants.length - a.variants.length;
        return a.domain.localeCompare(b.domain);
      });
      grp.consolidatedInStockStores = Array.from(grp.inStockByStore.values()).sort((a, b) =>
        a.domain.localeCompare(b.domain)
      );

      oosVariantSum += grp.oosItems.length;
      if (grp.oosItems.length > 0) {
        withOos.push(grp);
      } else {
        healthy.push(grp);
      }
    }

    withOos.sort((a, b) => {
      if (b.oosStores.size !== a.oosStores.size) return b.oosStores.size - a.oosStores.size;
      if (b.oosItems.length !== a.oosItems.length) return b.oosItems.length - a.oosItems.length;
      return a.displayName.localeCompare(b.displayName);
    });
    healthy.sort((a, b) => a.displayName.localeCompare(b.displayName));

    return {
      oosProductGroups: withOos,
      healthyProductGroups: healthy,
      totalOosVariants: oosVariantSum,
      totalStores: data.stores.length,
      latestCheck: maxTs
    };
  }, [data.stores, data.skus, brand.name]);

  // First product expanded by default; subsequent products collapsed into their heading
  const [expandedProducts, setExpandedProducts] = useState(() => {
    if (oosProductGroups.length > 0) {
      return new Set([oosProductGroups[0].productKey]);
    }
    return new Set();
  });

  useEffect(() => {
    if (oosProductGroups.length > 0) {
      setExpandedProducts(new Set([oosProductGroups[0].productKey]));
    }
  }, [brand.slug]);

  function toggleProduct(pKey) {
    setExpandedProducts(prev => {
      const next = new Set(prev);
      if (next.has(pKey)) next.delete(pKey);
      else next.add(pKey);
      return next;
    });
  }

  const allExpanded = oosProductGroups.length > 1 && expandedProducts.size === oosProductGroups.length;

  function toggleExpandAll() {
    if (allExpanded) {
      setExpandedProducts(oosProductGroups.length > 0 ? new Set([oosProductGroups[0].productKey]) : new Set());
    } else {
      setExpandedProducts(new Set(oosProductGroups.map(g => g.productKey)));
    }
  }

  function copyList(singleProductKey = null) {
    const groups = singleProductKey
      ? oosProductGroups.filter(g => g.productKey === singleProductKey)
      : oosProductGroups;

    if (groups.length === 0) {
      showToast('All tracked products are currently in stock.');
      return;
    }

    const lines = [];
    if (!singleProductKey) {
      lines.push(
        `${brand.name} — Out of Stock Products (${oosProductGroups.length} products across UK stockists)`
      );
      lines.push(`Checked: ${fmtShortTime(latestCheck)}`);
      lines.push('');
    }

    for (const grp of groups) {
      const singleSize = grp.distinctSizes.size === 1 ? ` (${Array.from(grp.distinctSizes)[0]})` : '';
      lines.push(
        `${grp.displayName}${singleSize} — Out of Stock at ${grp.oosStores.size} store${grp.oosStores.size === 1 ? '' : 's'}:`
      );
      for (const stRow of grp.consolidatedOosStores) {
        const varParts = stRow.variants.map(v => {
          const sz = v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard' ? v.variant_title : '';
          const pr = v.current_price !== null && v.current_price !== undefined ? `£${Number(v.current_price).toFixed(2)}` : '';
          return [sz, pr].filter(Boolean).join(' ');
        });
        const age = calcOosAge(stRow.oldestOosAt);
        lines.push(`  • ${stRow.domain} — ${varParts.join(', ')} [${age}] ${stRow.primaryUrl}`);
      }
      lines.push('');
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast(singleProductKey ? 'Copied product OOS list' : 'Copied full OOS product list');
    });
  }

  function downloadCSV() {
    const headers = ['Brand', 'Product', 'Stockist', 'Tier', 'Variations_OOS', 'OOS_Duration', 'First_Seen_OOS_UTC', 'URL'];
    const rows = [headers.join(',')];

    for (const grp of oosProductGroups) {
      const storeRows = showInStockStores
        ? [...grp.consolidatedOosStores, ...grp.consolidatedInStockStores]
        : grp.consolidatedOosStores;

      for (const stRow of storeRows) {
        const tier = isTier1(stRow.domain) ? 'Major Retailer' : 'Independent';
        const varDesc = stRow.variants
          .map(v => {
            const sz = v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard' ? v.variant_title : 'Standard';
            const pr = v.current_price !== null && v.current_price !== undefined ? `£${Number(v.current_price).toFixed(2)}` : '';
            return `${sz} ${pr}`.trim();
          })
          .join(' | ');
        const age = stRow.isOos ? calcOosAge(stRow.oldestOosAt) : 'In Stock';

        const vals = [
          brand.name,
          grp.displayName,
          stRow.domain,
          tier,
          varDesc,
          age,
          stRow.oldestOosAt || '',
          stRow.primaryUrl || ''
        ].map(v => `"${String(v ?? '').replace(/"/g, '""')}"`);
        rows.push(vals.join(','));
      }
    }

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${brand.slug}-oos-products.csv`;
    link.click();
  }

  return (
    <div className="sheet">
      <header className="sheet-header">
        <div>
          <h1 className="sheet-title">{brand.name} — Out of Stock Products</h1>
          <p className="sheet-summary">
            {totalStores === 0 ? (
              <span>Initial UK stockist scan is queued.</span>
            ) : (
              <>
                <strong className="oos-num">
                  {oosProductGroups.length} product{oosProductGroups.length === 1 ? '' : 's'}
                </strong>{' '}
                out of stock across <strong>{totalStores}</strong> monitored UK stockists · Checked{' '}
                {fmtShortTime(latestCheck)}
              </>
            )}
          </p>
        </div>

        <div className="sheet-actions">
          {oosProductGroups.length > 1 && (
            <button className="btn-plain" onClick={toggleExpandAll}>
              {allExpanded ? 'Collapse Others' : 'Expand All'}
            </button>
          )}
          <button
            className={`btn-plain ${showInStockStores ? 'active' : ''}`}
            onClick={() => setShowInStockStores(v => !v)}
          >
            {showInStockStores ? 'Hide In-Stock Stores' : 'Show In-Stock Stores'}
          </button>
          <button className="btn-plain" onClick={() => copyList(null)}>
            Copy List
          </button>
          <button className="btn-plain" onClick={downloadCSV}>
            CSV
          </button>
        </div>
      </header>

      {oosProductGroups.length === 0 && totalStores > 0 && (
        <p style={{ padding: '24px 0', color: 'var(--green)', fontWeight: 500 }}>
          All tracked {brand.name} products across all {totalStores} UK stockists are currently in stock.
        </p>
      )}

      {/* PRODUCT-CENTERED ACCORDION (FIRST PRODUCT EXPANDED, SUBSEQUENT COLLAPSED) */}
      {oosProductGroups.map(grp => {
        const isExpanded = expandedProducts.has(grp.productKey);
        const singleSize = grp.distinctSizes.size === 1 ? ` (${Array.from(grp.distinctSizes)[0]})` : '';
        const storeListPreview = Array.from(grp.oosStores).join(', ');
        const storeCount = grp.oosStores.size;

        const storeRowsToRender = showInStockStores
          ? [...grp.consolidatedOosStores, ...grp.consolidatedInStockStores]
          : grp.consolidatedOosStores;

        return (
          <section key={grp.productKey} className={`store-group ${isExpanded ? 'expanded' : ''}`}>
            <div className="store-group-header" onClick={() => toggleProduct(grp.productKey)}>
              <div className="store-header-left">
                <span className="store-chevron">{isExpanded ? '▾' : '▸'}</span>
                <span className="store-domain">
                  {grp.displayName}
                  {singleSize && <span className="sku-variant">{singleSize}</span>}
                </span>
                {!isExpanded && <span className="collapsed-preview">{storeListPreview}</span>}
              </div>

              <div className="store-meta" onClick={e => e.stopPropagation()}>
                <span
                  className="store-oos-count"
                  style={{ cursor: 'pointer' }}
                  onClick={() => toggleProduct(grp.productKey)}
                >
                  Out of Stock at {storeCount} store{storeCount === 1 ? '' : 's'}
                </span>
                <button className="btn-plain btn-xs" onClick={() => copyList(grp.productKey)}>
                  Copy
                </button>
              </div>
            </div>

            {isExpanded && (
              <ul className="sku-list">
                {storeRowsToRender.map(stRow => {
                  const major = isTier1(stRow.domain);

                  return (
                    <li key={`${stRow.domain}-${stRow.isOos ? 'oos' : 'in'}`} className="sku-item">
                      <div>
                        <span className="sku-name">{stRow.domain}</span>
                        {major && (
                          <span className="tier-tag" style={{ marginLeft: 8 }}>
                            Major Retailer
                          </span>
                        )}
                      </div>

                      {/* CONSOLIDATED VARIATIONS ON THIS STOCKIST */}
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

                      {stRow.isOos ? (
                        <div className="sku-oos-age">{calcOosAge(stRow.oldestOosAt)}</div>
                      ) : (
                        <div className="sku-in-badge">In Stock</div>
                      )}

                      <a
                        href={stRow.primaryUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="sku-open"
                        title="Open product page on stockist"
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

      {/* COLLAPSIBLE FOOTER FOR PRODUCTS THAT ARE 100% IN STOCK ACROSS ALL UK STOCKISTS */}
      {healthyProductGroups.length > 0 && (
        <div className="healthy-section">
          <button
            className="healthy-toggle"
            onClick={() => setShowHealthyProducts(v => !v)}
          >
            {showHealthyProducts ? '▾' : '▸'} {healthyProductGroups.length} other {brand.name} product
            {healthyProductGroups.length === 1 ? ' is' : 's are'} 100% in stock across all monitored UK stockists (
            {healthyProductGroups
              .slice(0, 4)
              .map(g => g.displayName)
              .join(', ')}
            {healthyProductGroups.length > 4 ? ', …' : ''})
          </button>

          {showHealthyProducts && (
            <div className="healthy-list">
              {healthyProductGroups.map(g => (
                <div key={g.productKey} className="healthy-card">
                  <div>
                    <strong>{g.displayName}</strong>
                    <div style={{ fontSize: '0.76rem', color: 'var(--muted)' }}>
                      In stock at {g.allStores.size} UK stockist{g.allStores.size === 1 ? '' : 's'} (
                      {Array.from(g.allStores).join(', ')})
                    </div>
                  </div>
                  <span style={{ color: 'var(--green)', fontSize: '0.78rem', fontWeight: 600 }}>100% In Stock</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}
