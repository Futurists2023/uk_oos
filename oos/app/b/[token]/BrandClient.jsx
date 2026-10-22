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

function shortStoreLabel(domain) {
  return String(domain || '')
    .toLowerCase()
    .replace(/^www\./, '')
    .replace(/^shop\./, '')
    .replace(/\.(co\.uk|com|org\.uk|org|earth)$/i, '');
}

export default function BrandClient({ initialData }) {
  const [data] = useState(initialData);
  const [displayMode, setDisplayMode] = useState('matrix'); // 'matrix' (default) | 'list'
  const [showHealthyProducts, setShowHealthyProducts] = useState(false);
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

  // Group active SKUs by Canonical Product Family -> then consolidate variations per Stockist
  const {
    oosProductGroups,
    healthyProductGroups,
    allProductGroups,
    sortedStoreColumns,
    totalStores,
    latestCheck
  } = useMemo(() => {
    const activeSkus = data.skus.filter(s => s.is_listed === 1);
    const byProdKey = new Map();
    const storeOosCounter = new Map();

    let maxTs = '';
    for (const st of data.stores) {
      storeOosCounter.set(st.domain, 0);
      if (st.last_checked_at && st.last_checked_at > maxTs) {
        maxTs = st.last_checked_at;
      }
    }

    for (const s of activeSkus) {
      if (!storeOosCounter.has(s.domain)) storeOosCounter.set(s.domain, 0);
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

    for (const grp of byProdKey.values()) {
      for (const dom of grp.oosStores) {
        storeOosCounter.set(dom, (storeOosCounter.get(dom) || 0) + 1);
      }
      grp.consolidatedOosStores = Array.from(grp.oosByStore.values()).sort((a, b) => {
        if (b.variants.length !== a.variants.length) return b.variants.length - a.variants.length;
        return a.domain.localeCompare(b.domain);
      });
      grp.consolidatedInStockStores = Array.from(grp.inStockByStore.values()).sort((a, b) =>
        a.domain.localeCompare(b.domain)
      );

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
    healthy.sort((a, b) => {
      if (b.allStores.size !== a.allStores.size) return b.allStores.size - a.allStores.size;
      return a.displayName.localeCompare(b.displayName);
    });

    // Sort store columns for the Compact Overview Grid: most OOS products first, then alphabetical
    const cols = Array.from(storeOosCounter.entries())
      .map(([domain, oosProductCount]) => ({
        domain,
        shortLabel: shortStoreLabel(domain),
        oosProductCount
      }))
      .sort((a, b) => {
        if (b.oosProductCount !== a.oosProductCount) return b.oosProductCount - a.oosProductCount;
        return a.domain.localeCompare(b.domain);
      });

    return {
      oosProductGroups: withOos,
      healthyProductGroups: healthy,
      allProductGroups: [...withOos, ...healthy],
      sortedStoreColumns: cols,
      totalStores: cols.length,
      latestCheck: maxTs
    };
  }, [data.stores, data.skus, brand.name]);

  // All products collapsed by default so the account manager can pick which product to inspect first
  const [expandedProducts, setExpandedProducts] = useState(() => new Set());
  const [hoverPopover, setHoverPopover] = useState(null);

  useEffect(() => {
    setExpandedProducts(new Set());
  }, [brand.slug]);

  const allOosExpanded =
    oosProductGroups.length > 0 && oosProductGroups.every(g => expandedProducts.has(g.productKey));

  function toggleExpandAll() {
    if (allOosExpanded) {
      setExpandedProducts(new Set());
    } else {
      setExpandedProducts(new Set(oosProductGroups.map(g => g.productKey)));
    }
  }

  function showCellPopover(e, info) {
    const rect = e.currentTarget.getBoundingClientRect();
    const flipBelow = rect.top < 110;
    const rawX = rect.left + rect.width / 2;
    const clampedX = Math.max(150, Math.min(window.innerWidth - 150, rawX));
    setHoverPopover({
      x: clampedX,
      y: flipBelow ? rect.bottom + 8 : rect.top - 6,
      flipBelow,
      ...info
    });
  }

  function hideCellPopover() {
    setHoverPopover(null);
  }

  function toggleProduct(pKey) {
    setExpandedProducts(prev => {
      const next = new Set(prev);
      if (next.has(pKey)) next.delete(pKey);
      else next.add(pKey);
      return next;
    });
  }

  function formatVariantList(variants) {
    return variants
      .map(v => {
        const sz =
          v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard'
            ? v.variant_title
            : '';
        const pr =
          v.current_price !== null && v.current_price !== undefined
            ? `£${Number(v.current_price).toFixed(2)}`
            : '';
        if (sz && pr) return `${sz} (${pr})`;
        return sz || pr || 'Standard';
      })
      .join(', ');
  }

  function copyList(singleProductKey = null) {
    if (oosProductGroups.length === 0) {
      showToast('All tracked products are currently in stock.');
      return;
    }

    const lines = [];

    // Single-product copy (from a product row in List View)
    if (singleProductKey) {
      const grp = oosProductGroups.find(g => g.productKey === singleProductKey);
      if (!grp) return;
      const singleSize = grp.distinctSizes.size === 1 ? ` (${Array.from(grp.distinctSizes)[0]})` : '';
      lines.push(
        `${grp.displayName}${singleSize} — Out of Stock at ${grp.oosStores.size} store${grp.oosStores.size === 1 ? '' : 's'}:`
      );
      for (const stRow of grp.consolidatedOosStores) {
        const varText = formatVariantList(stRow.variants);
        const age = calcOosAge(stRow.oldestOosAt);
        lines.push(`• ${stRow.domain} — ${varText} [${age}]`);
      }

      navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
        showToast(`Copied ${grp.displayName} OOS summary`);
      });
      return;
    }

    // Full-sheet copy: clean Stockist-grouped summary ready for buyer emails / Slack (zero raw URL clutter)
    lines.push(
      `${brand.name} — Out of Stock Summary (${oosProductGroups.length} product${oosProductGroups.length === 1 ? '' : 's'} across ${totalStores} UK stockists)`
    );
    lines.push(`Checked: ${fmtShortTime(latestCheck)}`);
    lines.push('');

    const storesWithOos = sortedStoreColumns.filter(col => col.oosProductCount > 0);
    for (const col of storesWithOos) {
      lines.push(
        `${col.domain} (${col.oosProductCount} product${col.oosProductCount === 1 ? '' : 's'} OOS):`
      );
      for (const grp of oosProductGroups) {
        const stCell = grp.oosByStore.get(col.domain);
        if (!stCell) continue;
        const varText = formatVariantList(stCell.variants);
        const age = calcOosAge(stCell.oldestOosAt);
        lines.push(`• ${grp.displayName} — ${varText} [${age}]`);
      }
      lines.push('');
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast('Copied buyer-ready OOS summary (grouped by stockist)');
    });
  }

  function copyStoreOosList(domain) {
    const col = sortedStoreColumns.find(c => c.domain === domain);
    if (!col || col.oosProductCount === 0) {
      showToast(`All ${brand.name} products at ${domain} are in stock.`);
      return;
    }

    const lines = [
      `${brand.name} — Out of Stock at ${domain} (${col.oosProductCount} product${col.oosProductCount === 1 ? '' : 's'})`,
      `Checked: ${fmtShortTime(latestCheck)}`,
      ''
    ];

    for (const grp of oosProductGroups) {
      const stCell = grp.oosByStore.get(domain);
      if (!stCell) continue;
      const varText = formatVariantList(stCell.variants);
      const age = calcOosAge(stCell.oldestOosAt);
      lines.push(`• ${grp.displayName} — ${varText} [${age}]`);
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast(`Copied ${domain} OOS list (${col.oosProductCount} product${col.oosProductCount === 1 ? '' : 's'})`);
    });
  }

  function downloadCSV() {
    const headers = ['Brand', 'Product', 'Stockist', 'Tier', 'Variations_OOS', 'OOS_Duration', 'First_Seen_OOS_UTC', 'URL'];
    const rows = [headers.join(',')];

    for (const grp of oosProductGroups) {
      for (const stRow of grp.consolidatedOosStores) {
        const tier = isTier1(stRow.domain) ? 'Major Retailer' : 'Independent';
        const varDesc = stRow.variants
          .map(v => {
            const sz = v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard' ? v.variant_title : 'Standard';
            const pr = v.current_price !== null && v.current_price !== undefined ? `£${Number(v.current_price).toFixed(2)}` : '';
            return `${sz} ${pr}`.trim();
          })
          .join(' | ');
        const age = calcOosAge(stRow.oldestOosAt);

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
    <div className="sheet sheet-matrix">
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
          <div className="view-segmented" role="tablist" aria-label="View mode">
            <button
              className={`view-tab ${displayMode === 'matrix' ? 'active' : ''}`}
              onClick={() => setDisplayMode('matrix')}
            >
              Compact Overview
            </button>
            <button
              className={`view-tab ${displayMode === 'list' ? 'active' : ''}`}
              onClick={() => setDisplayMode('list')}
            >
              List View
            </button>
          </div>

          <span className="actions-divider" aria-hidden="true" />

          <button
            className="btn-action"
            onClick={() => copyList(null)}
            title="Copy clean OOS summary grouped by stockist for buyer emails or Slack"
          >
            Copy List
          </button>
          <button
            className="btn-action"
            onClick={downloadCSV}
            title="Download CSV spreadsheet"
          >
            CSV
          </button>
        </div>
      </header>

      {/* MODE 1: PRODUCT-CENTERED LIST VIEW (INTERNAL SCROLL + COMPACT COVERAGE BOTTOM SECTION) */}
      {displayMode === 'list' && (
        <div className="list-scroll-body">
          {oosProductGroups.length === 0 && totalStores > 0 && (
            <p style={{ padding: '16px 0', color: 'var(--green)', fontWeight: 500 }}>
              All tracked {brand.name} products across all {totalStores} UK stockists are currently in stock.
            </p>
          )}

          {oosProductGroups.length > 0 && (
            <div className="list-toolbar">
              <span className="list-toolbar-label">
                Out of Stock Products ({oosProductGroups.length})
              </span>
              <button className="list-expand-btn" onClick={toggleExpandAll}>
                {allOosExpanded ? 'Collapse all ▴' : 'Expand all ▾'}
              </button>
            </div>
          )}

          {oosProductGroups.map(grp => {
            const isExpanded = expandedProducts.has(grp.productKey);
            const singleSize = grp.distinctSizes.size === 1 ? ` (${Array.from(grp.distinctSizes)[0]})` : '';
            const storeListPreview = Array.from(grp.oosStores).join(', ');
            const storeCount = grp.oosStores.size;

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
                    {grp.consolidatedOosStores.map(stRow => {
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

          {healthyProductGroups.length > 0 && (
            <div className="healthy-section">
              <button
                className="healthy-toggle"
                onClick={() => setShowHealthyProducts(v => !v)}
              >
                <span>
                  {showHealthyProducts ? '▾' : '▸'} {healthyProductGroups.length} other {brand.name} product
                  {healthyProductGroups.length === 1 ? ' has' : 's have'} 0 OOS — in stock at their listed stockists
                </span>
                <span style={{ fontSize: '0.78rem', color: 'var(--subtle)' }}>
                  {showHealthyProducts ? 'Hide stockist coverage' : 'View stockist coverage'}
                </span>
              </button>

              {showHealthyProducts && (
                <div className="healthy-rows">
                  {healthyProductGroups.map(g => {
                    const singleSize =
                      g.distinctSizes.size === 1 ? ` (${Array.from(g.distinctSizes)[0]})` : '';

                    return (
                      <div key={g.productKey} className="healthy-row">
                        <div className="healthy-prod-name">
                          {g.displayName}
                          {singleSize && <span className="sku-variant">{singleSize}</span>}
                        </div>

                        <div className="healthy-pills">
                          {g.consolidatedInStockStores.map(st => {
                            const firstVar = st.variants[0];
                            const priceStr =
                              st.variants.length === 1 &&
                              firstVar?.current_price !== null &&
                              firstVar?.current_price !== undefined
                                ? `£${Number(firstVar.current_price).toFixed(2)}`
                                : st.variants.length > 1
                                ? `${st.variants.length} sizes`
                                : '';

                            const tipParts = st.variants.map(v => {
                              const sz =
                                v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard'
                                  ? v.variant_title
                                  : '';
                              const pr =
                                v.current_price !== null && v.current_price !== undefined
                                  ? `£${Number(v.current_price).toFixed(2)}`
                                  : '';
                              return [sz, pr].filter(Boolean).join(' ');
                            });

                            return (
                              <a
                                key={st.domain}
                                href={st.primaryUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="healthy-store-pill"
                                title={`${st.domain}: In Stock (${tipParts.join(', ')})`}
                              >
                                <span>{st.domain}</span>
                                {priceStr && <span className="healthy-pill-meta">{priceStr}</span>}
                                <span className="healthy-pill-meta">↗</span>
                              </a>
                            );
                          })}
                        </div>

                        <div className="healthy-coverage">
                          ✓ {g.allStores.size} / {totalStores} stockists
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* MODE 2: COMPACT OVERVIEW MATRIX (PRODUCT x STOCKIST HOLISTIC GRID) */}
      {displayMode === 'matrix' && totalStores > 0 && (
        <div className="matrix-container">
          <div className="matrix-wrap" onScroll={hideCellPopover}>
            <table className="matrix-table">
              <thead>
                <tr>
                  <th className="col-product">
                    Product ({allProductGroups.length})
                  </th>
                  {sortedStoreColumns.map(col => (
                    <th
                      key={col.domain}
                      className={col.oosProductCount > 0 ? 'matrix-th-clickable' : ''}
                      onClick={() => col.oosProductCount > 0 && copyStoreOosList(col.domain)}
                      title={
                        col.oosProductCount > 0
                          ? `Click to copy ${col.domain}'s ${col.oosProductCount} OOS product${col.oosProductCount === 1 ? '' : 's'}`
                          : `${col.domain} (100% In Stock)`
                      }
                    >
                      <span>{col.shortLabel}</span>
                      <span
                        className="matrix-store-sub"
                        style={{ color: col.oosProductCount > 0 ? 'var(--red)' : 'var(--green)' }}
                      >
                        {col.oosProductCount > 0 ? `${col.oosProductCount} OOS` : '100% In'}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allProductGroups.map(grp => {
                  const singleSize = grp.distinctSizes.size === 1 ? ` (${Array.from(grp.distinctSizes)[0]})` : '';
                  return (
                    <tr key={grp.productKey}>
                      <td className="col-product">
                        <a
                          href="#"
                          onClick={e => {
                            e.preventDefault();
                            setExpandedProducts(new Set([grp.productKey]));
                            setDisplayMode('list');
                          }}
                          title="Click to inspect product in List View"
                        >
                          {grp.displayName}
                          {singleSize && <span className="sku-variant">{singleSize}</span>}
                        </a>
                      </td>

                      {sortedStoreColumns.map(col => {
                        const oosCell = grp.oosByStore.get(col.domain);
                        const inCell = grp.inStockByStore.get(col.domain);

                        if (oosCell) {
                          const vCount = oosCell.variants.length;
                          const label = vCount > 1 ? `${vCount} OOS` : 'OOS';
                          const varSummary = formatVariantList(oosCell.variants);
                          const age = calcOosAge(oosCell.oldestOosAt);

                          return (
                            <td key={col.domain}>
                              <a
                                href={oosCell.primaryUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="cell-oos"
                                onMouseEnter={e =>
                                  showCellPopover(e, {
                                    title: `${grp.displayName} · ${col.domain}`,
                                    detail: `${varSummary} — ${age}`,
                                    isOos: true
                                  })
                                }
                                onMouseLeave={hideCellPopover}
                              >
                                {label}
                              </a>
                            </td>
                          );
                        }

                        if (inCell) {
                          const varSummary = formatVariantList(inCell.variants);

                          return (
                            <td key={col.domain}>
                              <a
                                href={inCell.primaryUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="cell-in"
                                onMouseEnter={e =>
                                  showCellPopover(e, {
                                    title: `${grp.displayName} · ${col.domain}`,
                                    detail: `In Stock (${varSummary})`,
                                    isOos: false
                                  })
                                }
                                onMouseLeave={hideCellPopover}
                              >
                                ✓
                              </a>
                            </td>
                          );
                        }

                        return (
                          <td key={col.domain}>
                            <span className="cell-none">
                              ·
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="matrix-legend">
            <span>
              <strong style={{ color: 'var(--red)' }}>OOS</strong> = Out of Stock (hover for instant size &amp; duration, click cell to open product page)
            </span>
            <span>
              <strong style={{ color: 'var(--green)' }}>✓</strong> = In Stock
            </span>
            <span>
              <strong>·</strong> = Not listed
            </span>
            <span style={{ marginLeft: 'auto' }}>
              Tip: Click any stockist header to copy its OOS list
            </span>
          </div>
        </div>
      )}

      {hoverPopover && (
        <div
          className="cell-popover"
          style={{
            left: hoverPopover.x,
            top: hoverPopover.y,
            transform: hoverPopover.flipBelow ? 'translate(-50%, 0)' : 'translate(-50%, -100%)'
          }}
        >
          <div className="cell-popover-title">{hoverPopover.title}</div>
          <div className="cell-popover-sub">{hoverPopover.detail}</div>
        </div>
      )}

      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}
