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

function fmtForDuration(isoStr) {
  if (!isoStr) return 'Currently';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return 'Currently';
  const hours = Math.max(0, (Date.now() - d.getTime()) / 3600000);
  const days = Math.floor(hours / 24);
  const remH = Math.floor(hours % 24);
  const mins = Math.max(1, Math.floor((hours * 60) % 60));
  if (days > 0) {
    return remH > 0 ? `For ${days}d ${remH}h` : `For ${days} day${days === 1 ? '' : 's'}`;
  }
  if (remH > 0) {
    return `For ${remH}h ${mins}m`;
  }
  return `For ${mins}m`;
}

function decodeHtmlEntities(str) {
  return String(str || '')
    .replace(/&#0*38;|&amp;/gi, '&')
    .replace(/&#8211;|&ndash;/gi, '–')
    .replace(/&#8212;|&mdash;/gi, '—')
    .replace(/&#8217;|&#0*39;|&apos;/gi, "'")
    .replace(/&quot;/gi, '"');
}

function cleanProductDisplayName(rawTitle, brandName, normKey = '') {
  if (normKey === 'renaissance_cleansing_gel_200ml') return 'Renaissance Cleansing Gel (200ml Supersize)';
  if (normKey === 'renaissance_cleansing_gel_35ml') return 'Renaissance Cleansing Gel (35ml Travel)';
  if (normKey === 'renaissance_cleansing_gel_100ml') return 'Renaissance Cleansing Gel (100ml)';

  let t = decodeHtmlEntities(rawTitle).split('|')[0].trim();
  if (/\.(?:html?|aspx|php)$/i.test(t) || (t.includes('-') && !t.includes(' '))) {
    t = t
      .replace(/\.(?:html?|aspx|php)$/i, '')
      .replace(/-/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }
  if (brandName) {
    const escaped = brandName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    t = t.replace(new RegExp(`^${escaped}\\s*(?:skincare|london)?\\s*[-–—:]?\\s*`, 'i'), '').trim();
    t = t.replace(new RegExp(`\\s*[-–—:]\\s*${escaped}$`, 'i'), '').trim();
  }
  t = t.replace(/[, -]*\b\d+(?:\.\d+)?\s*(?:ml|g|kg|oz|caps|capsules|tablets|sachets)\b\s*$/i, '').trim();
  return t || decodeHtmlEntities(rawTitle).trim();
}

function isJunkProductRow(s, brandName, brandSlug) {
  const raw = decodeHtmlEntities(s.product_title || '').trim();
  const low = raw.toLowerCase();
  const nk = String(s.normalized_product_key || '').toLowerCase();
  if (!raw) return true;
  if (low === String(brandName || '').toLowerCase()) return true;
  if (/^(?:next|prev|previous|next\s+product|previous\s+product|view\s+all|read\s+more)$/i.test(raw)) return true;
  if (nk === `${brandSlug}_sku` || nk === `other_${brandSlug}_sku` || nk === 'next_product') return true;
  if (/\/(?:brands|collections|category|categories)\//i.test(String(s.product_url || '')) && !s.current_price) return true;
  return false;
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
  const dtcSet = useMemo(
    () => new Set((brand?.dtcDomains || []).map(d => String(d).toLowerCase().replace(/^www\./, ''))),
    [brand]
  );

  function isDtc(domain) {
    const d = String(domain || '').toLowerCase().replace(/^www\./, '');
    return dtcSet.has(d);
  }

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

  // Group active SKUs by Canonical Product Family -> separate Official DTC Reference from Retail Stockists
  const {
    oosProductGroups,
    healthyProductGroups,
    allProductGroups,
    dtcStoreColumn,
    sortedStoreColumns,
    totalRetailStores,
    unforcedOutageCount,
    factoryShortageCount,
    latestCheck
  } = useMemo(() => {
    const activeSkus = data.skus.filter(s => s.is_listed === 1);
    const byProdKey = new Map();
    const storeOosCounter = new Map();
    let dtcDomainFound = (brand?.dtcDomains || [])[0] || null;

    let maxTs = '';
    for (const st of data.stores) {
      if (isDtc(st.domain)) {
        dtcDomainFound = st.domain;
      } else {
        storeOosCounter.set(st.domain, 0);
      }
      if (st.last_checked_at && st.last_checked_at > maxTs) {
        maxTs = st.last_checked_at;
      }
    }

    for (const s of activeSkus) {
      if (isJunkProductRow(s, brand.name, brand.slug)) continue;
      const domIsDtc = isDtc(s.domain);
      if (!domIsDtc && !storeOosCounter.has(s.domain)) {
        storeOosCounter.set(s.domain, 0);
      }
      const pKey = s.normalized_product_key || cleanProductDisplayName(s.product_title, brand.name).toLowerCase();
      if (!byProdKey.has(pKey)) {
        byProdKey.set(pKey, {
          productKey: pKey,
          displayName: cleanProductDisplayName(s.product_title, brand.name, pKey),
          dtcVariants: [],
          oosByStore: new Map(),
          inStockByStore: new Map(),
          oosItems: [],
          inStockItems: [],
          distinctSizes: new Set(),
          oosStores: new Set(),
          inStockStores: new Set(),
          allRetailStores: new Set()
        });
      }
      const grp = byProdKey.get(pKey);

      const candName = cleanProductDisplayName(s.product_title, brand.name, pKey);
      if (
        pKey.startsWith('renaissance_cleansing_gel_') ||
        (candName.length > 2 && candName.length < grp.displayName.length)
      ) {
        grp.displayName = candName;
      }

      const vTitle = s.variant_title && s.variant_title !== 'Default' && s.variant_title !== 'Standard' ? s.variant_title : '';
      if (vTitle) grp.distinctSizes.add(vTitle);

      if (domIsDtc) {
        grp.dtcVariants.push(s);
        continue;
      }

      grp.allRetailStores.add(s.domain);

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
        grp.inStockStores.add(s.domain);
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
    let unforcedCnt = 0;
    let factoryCnt = 0;

    for (const grp of byProdKey.values()) {
      // Only include product groups that exist at 1+ retail stockist (or have retail OOS)
      if (grp.allRetailStores.size === 0) continue;

      // Compute Official DTC Reference status & standard RRP
      if (grp.dtcVariants.length > 0) {
        const stdPool = grp.dtcVariants.filter(
          v => !/\b(?:travel|refill|5\s*litre|10\s*ml|7\s*ml|5\.5\s*ml|14\s*ml|15\s*ml|7\s*capsules|14\s*capsules)\b/i.test(v.variant_title || '')
        );
        const pool = stdPool.length > 0 ? stdPool : grp.dtcVariants;
        const anyInStock = pool.some(v => v.is_available === 1);
        const prices = pool.map(v => v.current_price).filter(p => p !== null && p !== undefined && p > 0);
        grp.dtcStatus = anyInStock ? 'IN_STOCK' : 'OOS';
        grp.dtcRrp = prices.length > 0 ? Math.max(...prices) : null;
        grp.dtcUrl = pool[0]?.product_url || `https://${dtcDomainFound}`;
      } else {
        grp.dtcStatus = 'RETAIL_ONLY';
        grp.dtcRrp = null;
        grp.dtcUrl = dtcDomainFound ? `https://${dtcDomainFound}` : '#';
      }

      if (grp.oosItems.length > 0) {
        if (grp.dtcStatus === 'OOS') {
          grp.diagnosisType = 'FACTORY_SHORTAGE';
          grp.diagnosisLabel = '⚠️ Factory Shortage (Also OOS on DTC)';
          factoryCnt += 1;
        } else if (grp.dtcStatus === 'IN_STOCK') {
          grp.diagnosisType = 'UNFORCED_OUTAGE';
          grp.diagnosisLabel = `🚨 Unforced Outage (In Stock on DTC${grp.dtcRrp ? ` · £${grp.dtcRrp.toFixed(2)}` : ''})`;
          unforcedCnt += 1;
        } else {
          grp.diagnosisType = 'UNFORCED_OUTAGE';
          grp.diagnosisLabel = `🚨 Retail Outage (In Stock at ${grp.inStockStores.size} other stockist${grp.inStockStores.size === 1 ? '' : 's'})`;
          unforcedCnt += 1;
        }
      }

      for (const dom of grp.oosStores) {
        storeOosCounter.set(dom, (storeOosCounter.get(dom) || 0) + 1);
      }
      grp.consolidatedOosStores = Array.from(grp.oosByStore.values()).sort((a, b) => {
        const aTs = a.oldestOosAt || '9999';
        const bTs = b.oldestOosAt || '9999';
        if (aTs !== bTs) return aTs.localeCompare(bTs);
        return a.domain.localeCompare(b.domain);
      });
      grp.oldestOosAt = grp.consolidatedOosStores[0]?.oldestOosAt || '';
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
      // Longest OOS duration first, then by number of OOS stockists
      const aTs = a.oldestOosAt || '9999';
      const bTs = b.oldestOosAt || '9999';
      if (aTs !== bTs) return aTs.localeCompare(bTs);
      if (b.oosStores.size !== a.oosStores.size) return b.oosStores.size - a.oosStores.size;
      return a.displayName.localeCompare(b.displayName);
    });
    healthy.sort((a, b) => {
      if (b.allRetailStores.size !== a.allRetailStores.size) return b.allRetailStores.size - a.allRetailStores.size;
      return a.displayName.localeCompare(b.displayName);
    });

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
      dtcStoreColumn: dtcDomainFound ? { domain: dtcDomainFound, shortLabel: 'Official DTC' } : null,
      sortedStoreColumns: cols,
      totalRetailStores: cols.length,
      unforcedOutageCount: unforcedCnt,
      factoryShortageCount: factoryCnt,
      latestCheck: maxTs
    };
  }, [data.stores, data.skus, brand]);

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

  function formatVariantList(variants, dtcRrp = null) {
    return variants
      .map(v => {
        const sz =
          v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard'
            ? v.variant_title
            : '';
        const numP = v.current_price !== null && v.current_price !== undefined ? Number(v.current_price) : null;
        const pr = numP !== null ? `£${numP.toFixed(2)}` : '';
        let rrpNote = '';
        if (numP !== null && dtcRrp && numP < dtcRrp * 0.92) {
          const pct = Math.round(100 * (1 - numP / dtcRrp));
          rrpNote = ` [-${pct}% vs RRP]`;
        }
        if (sz && pr) return `${sz} (${pr}${rrpNote})`;
        return `${sz || pr || 'Standard'}${rrpNote}`;
      })
      .join(', ');
  }

  function copyList(singleProductKey = null) {
    if (oosProductGroups.length === 0) {
      showToast('All tracked products are currently in stock.');
      return;
    }

    const lines = [];

    if (singleProductKey) {
      const grp = oosProductGroups.find(g => g.productKey === singleProductKey);
      if (!grp) return;
      lines.push(
        `${grp.displayName} — Out of Stock at ${grp.oosStores.size}/${grp.allRetailStores.size} UK stockists:`
      );
      for (const stRow of grp.consolidatedOosStores) {
        const varText = formatVariantList(stRow.variants, grp.dtcRrp);
        const dur = fmtForDuration(stRow.oldestOosAt);
        lines.push(`• ${dur}, ${grp.displayName} (${varText}) has been out of stock at ${stRow.domain}`);
      }
      if (grp.inStockStores.size > 0) {
        lines.push(`In stock at (${grp.inStockStores.size}): ${Array.from(grp.inStockStores).join(', ')}`);
      }

      navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
        showToast(`Copied ${grp.displayName} OOS summary`);
      });
      return;
    }

    lines.push(
      `${brand.name} — UK Retail Out of Stock Report (${oosProductGroups.length} products out of stock across ${totalRetailStores} UK stockists)`
    );
    lines.push(`Checked: ${fmtShortTime(latestCheck)}`);
    lines.push('');

    for (const grp of oosProductGroups) {
      for (const stRow of grp.consolidatedOosStores) {
        const varText = formatVariantList(stRow.variants, grp.dtcRrp);
        const dur = fmtForDuration(stRow.oldestOosAt);
        lines.push(`• ${dur}, ${grp.displayName} (${varText}) has been out of stock at ${stRow.domain}`);
      }
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast('Copied OOS report (duration first)');
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
      const varText = formatVariantList(stCell.variants, grp.dtcRrp);
      const dur = fmtForDuration(stCell.oldestOosAt);
      lines.push(`• ${dur}, ${grp.displayName} (${varText}) has been out of stock at ${domain}`);
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast(`Copied ${domain} OOS list (${col.oosProductCount} product${col.oosProductCount === 1 ? '' : 's'})`);
    });
  }

  function downloadCSV() {
    const headers = ['OOS_Duration', 'Product', 'Stockist', 'Variations_OOS', 'DTC_RRP', 'Stockists_OOS_Ratio', 'In_Stock_Stockists', 'First_Seen_OOS_UTC', 'URL'];
    const rows = [headers.join(',')];

    for (const grp of oosProductGroups) {
      for (const stRow of grp.consolidatedOosStores) {
        const varDesc = formatVariantList(stRow.variants, grp.dtcRrp);
        const age = calcOosAge(stRow.oldestOosAt);
        const competing = Array.from(grp.inStockStores).join(' | ');

        const vals = [
          age,
          grp.displayName,
          stRow.domain,
          varDesc,
          grp.dtcRrp ? `£${grp.dtcRrp.toFixed(2)}` : '',
          `${grp.oosStores.size}/${grp.allRetailStores.size}`,
          competing,
          stRow.oldestOosAt || '',
          stRow.primaryUrl || ''
        ].map(v => `"${String(v ?? '').replace(/"/g, '""')}"`);
        rows.push(vals.join(','));
      }
    }

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${brand.slug}-oos-intelligence.csv`;
    link.click();
  }

  return (
    <div className="sheet sheet-matrix">
      <header className="sheet-header">
        <div>
          <h1 className="sheet-title">{brand.name} — UK Retail Out-of-Stock Intelligence</h1>
          <p className="sheet-summary">
            {totalRetailStores === 0 ? (
              <span>Initial UK stockist scan is queued.</span>
            ) : (
              <>
                <strong className="oos-num">
                  {oosProductGroups.length} product{oosProductGroups.length === 1 ? '' : 's'} out of stock
                </strong>{' '}
                across <strong>{totalRetailStores}</strong> UK retail stockists &amp; Official DTC · Checked{' '}
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
            title="Copy clean OOS report ordered by duration"
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

      {/* MODE 1: PRODUCT-CENTERED LIST VIEW */}
      {displayMode === 'list' && (
        <div className="list-scroll-body">
          {oosProductGroups.length === 0 && totalRetailStores > 0 && (
            <p style={{ padding: '16px 0', color: 'var(--green)', fontWeight: 500 }}>
              All tracked {brand.name} products across all {totalRetailStores} UK retail stockists are currently in stock.
            </p>
          )}

          {oosProductGroups.length > 0 && (
            <div className="list-toolbar">
              <span className="list-toolbar-label">
                Out-of-Stock Products ({oosProductGroups.length}) — Ordered by OOS Duration
              </span>
              <button className="list-expand-btn" onClick={toggleExpandAll}>
                {allOosExpanded ? 'Collapse all ▴' : 'Expand all ▾'}
              </button>
            </div>
          )}

          {oosProductGroups.map(grp => {
            const isExpanded = expandedProducts.has(grp.productKey);
            const storeListPreview = Array.from(grp.oosStores).join(', ');
            const storeCount = grp.oosStores.size;

            return (
              <section key={grp.productKey} className={`store-group ${isExpanded ? 'expanded' : ''}`}>
                <div className="store-group-header" onClick={() => toggleProduct(grp.productKey)}>
                  <div className="store-header-left">
                    <span className="store-chevron">{isExpanded ? '▾' : '▸'}</span>
                    <span className="list-duration-lead">{fmtForDuration(grp.oldestOosAt)},</span>
                    <span className="store-domain">{grp.displayName}</span>
                    <span className="collapsed-preview">
                      has been out of stock at <strong style={{ color: 'var(--ink)', fontWeight: 600 }}>{storeListPreview}</strong>
                    </span>
                  </div>

                  <div className="store-meta" onClick={e => e.stopPropagation()}>
                    <span
                      className="store-oos-count"
                      style={{ cursor: 'pointer' }}
                      onClick={() => toggleProduct(grp.productKey)}
                    >
                      {storeCount}/{grp.allRetailStores.size} stockists
                    </span>
                    <button className="btn-plain btn-xs" onClick={() => copyList(grp.productKey)}>
                      Copy
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <ul className="sku-list">
                    {grp.consolidatedOosStores.map(stRow => {
                      return (
                        <li key={stRow.domain} className="sku-item">
                          <div className="sku-oos-age">{fmtForDuration(stRow.oldestOosAt)},</div>

                          <div className="sku-statement">
                            <span className="sku-prod-name">{grp.displayName}</span>
                            {stRow.variants.map(v => {
                              const hasNamedSize =
                                v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard';
                              const numP =
                                v.current_price !== null && v.current_price !== undefined
                                  ? Number(v.current_price)
                                  : null;
                              const price = numP !== null ? `£${numP.toFixed(2)}` : '';

                              if (!hasNamedSize && !price) return null;
                              return (
                                <span key={v.sku_key} className="var-pill">
                                  {hasNamedSize && <span>{v.variant_title}</span>}
                                  {price && <span className="var-pill-price">{price}</span>}
                                </span>
                              );
                            })}
                            <span className="sku-at-text">has been out of stock at</span>
                            <strong className="sku-store-domain">{stRow.domain}</strong>
                          </div>

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
                    {grp.inStockStores.size > 0 && (
                      <li className="sku-item sku-item-instock">
                        <span>
                          <strong style={{ color: 'var(--green)' }}>In stock at ({grp.inStockStores.size}/{grp.allRetailStores.size}):</strong>{' '}
                          {Array.from(grp.inStockStores).join(', ')}
                        </span>
                      </li>
                    )}
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
                  {healthyProductGroups.length === 1 ? ' has' : 's have'} 0 retail OOS — 100% in stock at their listed UK stockists
                </span>
                <span style={{ fontSize: '0.78rem', color: 'var(--subtle)' }}>
                  {showHealthyProducts ? 'Hide stockist & RRP matrix' : 'View stockist & RRP matrix'}
                </span>
              </button>

              {showHealthyProducts && (
                <div className="healthy-rows">
                  {healthyProductGroups.map(g => (
                    <div key={g.productKey} className="healthy-row">
                      <div className="healthy-prod-name">
                        {g.displayName}
                        {g.dtcRrp && (
                          <span className="sku-variant" style={{ marginLeft: 6 }}>
                            (DTC RRP £{g.dtcRrp.toFixed(2)})
                          </span>
                        )}
                      </div>

                      <div className="healthy-pills">
                        {g.consolidatedInStockStores.map(st => {
                          const firstVar = st.variants[0];
                          const numP =
                            firstVar?.current_price !== null && firstVar?.current_price !== undefined
                              ? Number(firstVar.current_price)
                              : null;
                          const undercutPct =
                            numP !== null && g.dtcRrp && numP < g.dtcRrp * 0.92
                              ? Math.round(100 * (1 - numP / g.dtcRrp))
                              : 0;
                          const priceStr =
                            numP !== null
                              ? `£${numP.toFixed(2)}${undercutPct > 0 ? ` (-${undercutPct}%)` : ''}`
                              : '';

                          return (
                            <a
                              key={st.domain}
                              href={st.primaryUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="healthy-store-pill"
                              title={`${st.domain}: In Stock (${formatVariantList(st.variants, g.dtcRrp)})`}
                            >
                              <span>{st.domain}</span>
                              {priceStr && <span className="healthy-pill-meta">{priceStr}</span>}
                              <span className="healthy-pill-meta">↗</span>
                            </a>
                          );
                        })}
                      </div>

                      <div className="healthy-coverage">
                        ✓ {g.allRetailStores.size} / {totalRetailStores} stockists
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* MODE 2: COMPACT OVERVIEW MATRIX (PRODUCT x OFFICIAL DTC RRP + STOCKIST GRID) */}
      {displayMode === 'matrix' && totalRetailStores > 0 && (
        <div className="matrix-container">
          <div className="matrix-wrap" onScroll={hideCellPopover}>
            <table className="matrix-table">
              <thead>
                <tr>
                  <th className="col-product">
                    Product ({allProductGroups.length})
                  </th>
                  {dtcStoreColumn && (
                    <th
                      style={{ background: '#f1f5f9', borderRight: '2px solid var(--border)' }}
                      title={`${dtcStoreColumn.domain} (Official Brand DTC Master Catalog & RRP Reference)`}
                    >
                      <span>{dtcStoreColumn.shortLabel}</span>
                      <span className="matrix-store-sub" style={{ color: 'var(--subtle)' }}>
                        Master RRP
                      </span>
                    </th>
                  )}
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
                  const isFactory = grp.diagnosisType === 'FACTORY_SHORTAGE';
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
                          title={grp.diagnosisLabel || 'Click to inspect product in List View'}
                        >
                          {grp.displayName}
                          {isFactory && (
                            <span
                              style={{
                                marginLeft: 6,
                                fontSize: '0.7rem',
                                color: '#92400e',
                                background: '#fef3c7',
                                padding: '1px 5px',
                                borderRadius: 4
                              }}
                            >
                              DTC OOS
                            </span>
                          )}
                        </a>
                      </td>

                      {dtcStoreColumn && (
                        <td style={{ background: '#f8fafc', borderRight: '2px solid var(--border)' }}>
                          {grp.dtcStatus === 'IN_STOCK' ? (
                            <a
                              href={grp.dtcUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="cell-in"
                              style={{ fontSize: '0.76rem', fontWeight: 600 }}
                              onMouseEnter={e =>
                                showCellPopover(e, {
                                  title: `${grp.displayName} · Official DTC (${dtcStoreColumn.domain})`,
                                  detail: `In Stock on Brand DTC${grp.dtcRrp ? ` · Official RRP £${grp.dtcRrp.toFixed(2)}` : ''}`,
                                  isOos: false
                                })
                              }
                              onMouseLeave={hideCellPopover}
                            >
                              {grp.dtcRrp ? `✓ £${Math.round(grp.dtcRrp)}` : '✓'}
                            </a>
                          ) : grp.dtcStatus === 'OOS' ? (
                            <a
                              href={grp.dtcUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="cell-oos"
                              style={{ background: '#fef3c7', color: '#92400e' }}
                              onMouseEnter={e =>
                                showCellPopover(e, {
                                  title: `${grp.displayName} · Official DTC (${dtcStoreColumn.domain})`,
                                  detail: `Out of Stock on Brand DTC (Factory / Warehouse Shortage)${grp.dtcRrp ? ` · RRP £${grp.dtcRrp.toFixed(2)}` : ''}`,
                                  isOos: true
                                })
                              }
                              onMouseLeave={hideCellPopover}
                            >
                              DTC OOS
                            </a>
                          ) : (
                            <span
                              className="cell-none"
                              title="Discontinued or not listed on Brand DTC storefront"
                            >
                              —
                            </span>
                          )}
                        </td>
                      )}

                      {sortedStoreColumns.map(col => {
                        const oosCell = grp.oosByStore.get(col.domain);
                        const inCell = grp.inStockByStore.get(col.domain);

                        if (oosCell) {
                          const vCount = oosCell.variants.length;
                          const label = vCount > 1 ? `${vCount} OOS` : 'OOS';
                          const varSummary = formatVariantList(oosCell.variants, grp.dtcRrp);
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
                                    detail: `${varSummary} — ${age} · ${grp.diagnosisLabel}`,
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
                          const varSummary = formatVariantList(inCell.variants, grp.dtcRrp);
                          const firstP = inCell.variants[0]?.current_price;
                          const isUndercut =
                            firstP && grp.dtcRrp && Number(firstP) < grp.dtcRrp * 0.92;

                          return (
                            <td key={col.domain}>
                              <a
                                href={inCell.primaryUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="cell-in"
                                style={isUndercut ? { color: '#b45309', fontWeight: 700 } : undefined}
                                onMouseEnter={e =>
                                  showCellPopover(e, {
                                    title: `${grp.displayName} · ${col.domain}`,
                                    detail: `In Stock (${varSummary})`,
                                    isOos: false
                                  })
                                }
                                onMouseLeave={hideCellPopover}
                              >
                                {isUndercut ? '✓↓' : '✓'}
                              </a>
                            </td>
                          );
                        }

                        return (
                          <td key={col.domain}>
                            <span
                              className="cell-none"
                              onMouseEnter={e =>
                                showCellPopover(e, {
                                  title: `${grp.displayName} · ${col.domain}`,
                                  detail: 'Assortment Gap — Not stocked by this retailer',
                                  isOos: false
                                })
                              }
                              onMouseLeave={hideCellPopover}
                            >
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
              <strong style={{ color: 'var(--red)' }}>OOS</strong> = Retail Out of Stock
            </span>
            <span>
              <strong style={{ color: '#92400e' }}>DTC OOS</strong> = Also OOS on Brand DTC (Factory Shortage)
            </span>
            <span>
              <strong style={{ color: 'var(--green)' }}>✓</strong> = In Stock at RRP
            </span>
            <span>
              <strong style={{ color: '#b45309' }}>✓↓</strong> = In Stock (&gt;8% below DTC RRP)
            </span>
            <span>
              <strong>·</strong> = Assortment Gap (Not stocked)
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
