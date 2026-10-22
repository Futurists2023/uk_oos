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
  // Remove trailing size suffix like " 200ml" or ", 25 ml" so product family title is clean
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

  // Group active SKUs by Canonical Product Family (Product-Centered)
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
          oosItems: [],
          inStockItems: [],
          distinctSizes: new Set(),
          oosStores: new Set(),
          allStores: new Set()
        });
      }
      const grp = byProdKey.get(pKey);
      grp.allStores.add(s.domain);

      // Prefer shorter/cleaner display name if one store has a cleaner title
      const candName = cleanProductDisplayName(s.product_title, brand.name);
      if (candName.length > 2 && candName.length < grp.displayName.length) {
        grp.displayName = candName;
      }

      const vTitle = s.variant_title && s.variant_title !== 'Default' && s.variant_title !== 'Standard' ? s.variant_title : '';
      if (vTitle) grp.distinctSizes.add(vTitle);

      if (s.is_available === 0) {
        grp.oosItems.push(s);
        grp.oosStores.add(s.domain);
      } else {
        grp.inStockItems.push(s);
      }
    }

    const withOos = [];
    const healthy = [];
    let oosVariantSum = 0;

    for (const grp of byProdKey.values()) {
      // Sort OOS rows inside a product by store domain, then variant size
      grp.oosItems.sort((a, b) => {
        if (a.domain !== b.domain) return a.domain.localeCompare(b.domain);
        return (a.variant_title || '').localeCompare(b.variant_title || '');
      });
      grp.inStockItems.sort((a, b) => a.domain.localeCompare(b.domain));

      oosVariantSum += grp.oosItems.length;
      if (grp.oosItems.length > 0) {
        withOos.push(grp);
      } else {
        healthy.push(grp);
      }
    }

    // Sort products by number of OOS stores (desc), then number of OOS variants (desc), then name
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
        `${brand.name} — Out of Stock Products (${oosProductGroups.length} products / ${totalOosVariants} variants)`
      );
      lines.push(`Checked: ${fmtShortTime(latestCheck)}`);
      lines.push('');
    }

    for (const grp of groups) {
      const singleSize = grp.distinctSizes.size === 1 ? ` (${Array.from(grp.distinctSizes)[0]})` : '';
      lines.push(
        `${grp.displayName}${singleSize} — Out of Stock at ${grp.oosStores.size} store${grp.oosStores.size === 1 ? '' : 's'}:`
      );
      for (const s of grp.oosItems) {
        const vLabel =
          grp.distinctSizes.size > 1 && s.variant_title && s.variant_title !== 'Default' && s.variant_title !== 'Standard'
            ? ` (${s.variant_title})`
            : '';
        const price =
          s.current_price !== null && s.current_price !== undefined
            ? `£${Number(s.current_price).toFixed(2)}`
            : '';
        const age = calcOosAge(s.first_seen_oos_at);
        lines.push(`  • ${s.domain}${vLabel}  ${price}  [${age}]  ${s.product_url || ''}`);
      }
      lines.push('');
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast(singleProductKey ? 'Copied product OOS list' : 'Copied full OOS product list');
    });
  }

  function downloadCSV() {
    const headers = ['Brand', 'Product', 'Variant', 'Stockist', 'Tier', 'Price_GBP', 'Status', 'OOS_Duration', 'First_Seen_OOS_UTC', 'URL'];
    const rows = [headers.join(',')];

    for (const grp of oosProductGroups) {
      const items = showInStockStores ? [...grp.oosItems, ...grp.inStockItems] : grp.oosItems;
      for (const s of items) {
        const tier = isTier1(s.domain) ? 'Major Retailer' : 'Independent';
        const status = s.is_available === 0 ? 'Out of Stock' : 'In Stock';
        const age = s.is_available === 0 ? calcOosAge(s.first_seen_oos_at) : '';
        const price = s.current_price !== null && s.current_price !== undefined ? Number(s.current_price).toFixed(2) : '';

        const vals = [
          brand.name,
          grp.displayName,
          s.variant_title || '',
          s.domain,
          tier,
          price,
          status,
          age,
          s.first_seen_oos_at || '',
          s.product_url || ''
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
                ({totalOosVariants} variant{totalOosVariants === 1 ? '' : 's'}) out of stock across{' '}
                <strong>{totalStores}</strong> monitored UK stockists · Checked {fmtShortTime(latestCheck)}
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
        const variantCount = grp.oosItems.length;
        const rightCountText =
          variantCount > storeCount
            ? `Out of Stock at ${storeCount} store${storeCount === 1 ? '' : 's'} (${variantCount} sizes)`
            : `Out of Stock at ${storeCount} store${storeCount === 1 ? '' : 's'}`;

        const rowsToRender = showInStockStores
          ? [...grp.oosItems, ...grp.inStockItems]
          : grp.oosItems;

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
                  {rightCountText}
                </span>
                <button className="btn-plain btn-xs" onClick={() => copyList(grp.productKey)}>
                  Copy
                </button>
              </div>
            </div>

            {isExpanded && (
              <ul className="sku-list">
                {rowsToRender.map(s => {
                  const major = isTier1(s.domain);
                  const showVariantTag =
                    s.variant_title && s.variant_title !== 'Default' && s.variant_title !== 'Standard';
                  const price =
                    s.current_price !== null && s.current_price !== undefined
                      ? `£${Number(s.current_price).toFixed(2)}`
                      : '';
                  const hasDiscount =
                    s.compare_at_price &&
                    s.current_price &&
                    Number(s.compare_at_price) > Number(s.current_price);
                  const isOos = s.is_available === 0;

                  return (
                    <li key={s.sku_key} className="sku-item">
                      <div>
                        <span className="sku-name">{s.domain}</span>
                        {showVariantTag && <span className="sku-variant">({s.variant_title})</span>}
                        {major && (
                          <span className="tier-tag" style={{ marginLeft: 8 }}>
                            Major Retailer
                          </span>
                        )}
                      </div>
                      <div className="sku-price">
                        {price}
                        {hasDiscount && (
                          <span className="sku-price-was">£{Number(s.compare_at_price).toFixed(2)}</span>
                        )}
                      </div>
                      {isOos ? (
                        <div className="sku-oos-age">{calcOosAge(s.first_seen_oos_at)}</div>
                      ) : (
                        <div className="sku-in-badge">In Stock</div>
                      )}
                      <a
                        href={s.product_url || '#'}
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
