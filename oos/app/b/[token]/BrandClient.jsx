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

function calcOutOfStockBadge(isoStr) {
  if (!isoStr) return 'Out of stock';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return 'Out of stock';
  const hours = Math.max(0, (Date.now() - d.getTime()) / 3600000);
  const days = Math.floor(hours / 24);
  const remH = Math.round(hours % 24);
  const roundedH = Math.round(hours);
  const mins = Math.max(1, Math.floor((hours * 60) % 60));
  if (days > 0) {
    return remH > 0 && remH < 24 ? `${days}d ${remH}h Out of stock` : `${days + (remH === 24 ? 1 : 0)}d Out of stock`;
  }
  if (roundedH > 0) return `${roundedH}h Out of stock`;
  return `${mins}m Out of stock`;
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

const RETAILER_PRIORITY_ORDER = [
  'spacenk.com',
  'cultbeauty.co.uk',
  'lookfantastic.com',
  'boots.com',
  'selfridges.com',
  'harveynichols.com',
  'johnlewis.com',
  'harrods.com',
  'libertylondon.com',
  'marksandspencer.com',
  'fenwick.co.uk',
  'flannels.com',
  'houseoffraser.co.uk',
  'facethefuture.co.uk',
  'bathandunwind.com',
  'ohmycream.co.uk',
  'naturisimo.com',
  'planetorganic.com',
  'wholefoodsmarket.co.uk',
  'hollandandbarrett.com',
  'ocado.com',
  'waitrose.com',
  'sainsburys.co.uk',
  'tesco.com',
  'superdrug.com',
  'victoriahealth.com',
  'contentbeautywellbeing.com',
  'alyaka.com'
];

function getRetailerPriorityRank(domain, isMajorFn) {
  const clean = String(domain || '').toLowerCase().replace(/^www\./, '');
  const idx = RETAILER_PRIORITY_ORDER.indexOf(clean);
  if (idx !== -1) return idx;
  if (isMajorFn && isMajorFn(clean)) return 40;
  return 100;
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
    const storeTotalCounter = new Map();
    let dtcDomainFound = (brand?.dtcDomains || [])[0] || null;

    let maxTs = '';
    for (const st of data.stores) {
      if (isDtc(st.domain)) {
        dtcDomainFound = st.domain;
      } else {
        storeOosCounter.set(st.domain, 0);
        storeTotalCounter.set(st.domain, 0);
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

      for (const dom of grp.allRetailStores) {
        storeTotalCounter.set(dom, (storeTotalCounter.get(dom) || 0) + 1);
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
        oosProductCount,
        totalProductCount: storeTotalCounter.get(domain) || oosProductCount
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

  const retailersWithOosCount = sortedStoreColumns.filter(col => col.oosProductCount > 0).length;
  const inStockOnParentCount = oosProductGroups.filter(grp => grp.dtcStatus === 'IN_STOCK').length;
  const parentSiteDomain = dtcStoreColumn?.domain || (brand?.dtcDomains || [])[0] || null;

  const { retailersWithOos, healthyRetailers } = useMemo(() => {
    const withOos = sortedStoreColumns
      .filter(col => col.oosProductCount > 0)
      .map(col => {
        const items = [];
        for (const grp of oosProductGroups) {
          const stRow = grp.oosByStore.get(col.domain);
          if (stRow) {
            items.push({ grp, stRow });
          }
        }
        items.sort((a, b) => {
          const aTs = a.stRow.oldestOosAt || '9999';
          const bTs = b.stRow.oldestOosAt || '9999';
          if (aTs !== bTs) return aTs.localeCompare(bTs);
          return a.grp.displayName.localeCompare(b.grp.displayName);
        });
        return {
          domain: col.domain,
          oosCount: items.length,
          totalCount: col.totalProductCount,
          priorityRank: getRetailerPriorityRank(col.domain, isTier1),
          items
        };
      })
      .sort((a, b) => {
        if (a.priorityRank !== b.priorityRank) return a.priorityRank - b.priorityRank;
        if (b.oosCount !== a.oosCount) return b.oosCount - a.oosCount;
        return a.domain.localeCompare(b.domain);
      });

    const healthy = sortedStoreColumns
      .filter(col => col.oosProductCount === 0)
      .map(col => ({
        domain: col.domain,
        totalCount: col.totalProductCount,
        priorityRank: getRetailerPriorityRank(col.domain, isTier1)
      }))
      .sort((a, b) => {
        if (a.priorityRank !== b.priorityRank) return a.priorityRank - b.priorityRank;
        return a.domain.localeCompare(b.domain);
      });

    return { retailersWithOos: withOos, healthyRetailers: healthy };
  }, [sortedStoreColumns, oosProductGroups]);

  function formatVariantList(variants, dtcRrp = null) {
    return variants
      .map(v => {
        const sz =
          v.variant_title && v.variant_title !== 'Default' && v.variant_title !== 'Standard'
            ? v.variant_title
            : '';
        const numP = v.current_price !== null && v.current_price !== undefined ? Number(v.current_price) : null;
        const pr = numP !== null ? `£${numP.toFixed(2)}` : '';
        if (sz && pr) return `${sz} ${pr}`;
        return sz || pr || 'Standard';
      })
      .join(', ');
  }

  function copyList() {
    if (retailersWithOos.length === 0) {
      showToast('All tracked products are currently in stock.');
      return;
    }

    const lines = [
      `${brand.name} — UK Retail Stockist Report`,
      `${oosProductGroups.length} products out of stock at ${retailersWithOosCount} of ${totalRetailStores} UK stockists${parentSiteDomain && inStockOnParentCount > 0 ? ` (${inStockOnParentCount} in stock at ${parentSiteDomain})` : ''} · Checked ${fmtShortTime(latestCheck)}`,
      ''
    ];

    for (const ret of retailersWithOos) {
      lines.push(
        `${ret.domain} — ${ret.oosCount} of ${ret.totalCount} product${ret.totalCount === 1 ? '' : 's'} out of stock:`
      );
      for (const { grp, stRow } of ret.items) {
        const badge = calcOutOfStockBadge(stRow.oldestOosAt);
        const varText = formatVariantList(stRow.variants, grp.dtcRrp);
        lines.push(`• [${badge}] ${grp.displayName} (${varText})`);
      }
      lines.push('');
    }

    if (healthyRetailers.length > 0) {
      lines.push(
        `100% in stock at (${healthyRetailers.length}): ${healthyRetailers.map(h => `${h.domain} (${h.totalCount})`).join(', ')}`
      );
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast('Copied retailer-first OOS report');
    });
  }

  function copyStoreOosList(domain) {
    const ret = retailersWithOos.find(r => r.domain === domain);
    if (!ret || ret.oosCount === 0) {
      showToast(`All ${brand.name} products at ${domain} are in stock.`);
      return;
    }

    const lines = [
      `${brand.name} — ${ret.domain} (${ret.oosCount} of ${ret.totalCount} product${ret.totalCount === 1 ? '' : 's'} out of stock)`,
      `Checked: ${fmtShortTime(latestCheck)}`,
      ''
    ];

    for (const { grp, stRow } of ret.items) {
      const badge = calcOutOfStockBadge(stRow.oldestOosAt);
      const varText = formatVariantList(stRow.variants, grp.dtcRrp);
      lines.push(`• [${badge}] ${grp.displayName} (${varText})`);
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast(`Copied ${domain} OOS list (${ret.oosCount} of ${ret.totalCount})`);
    });
  }

  function downloadCSV() {
    const headers = ['Stockist', 'Stockist_OOS_Ratio', 'OOS_Duration', 'Product', 'Variations_OOS', 'DTC_RRP', 'In_Stock_At', 'First_Seen_OOS_UTC', 'URL'];
    const rows = [headers.join(',')];

    for (const ret of retailersWithOos) {
      for (const { grp, stRow } of ret.items) {
        const varDesc = formatVariantList(stRow.variants, grp.dtcRrp);
        const age = calcOutOfStockBadge(stRow.oldestOosAt);
        const inStockList = [];
        if (grp.dtcStatus === 'IN_STOCK' && dtcStoreColumn?.domain) {
          inStockList.push(`${dtcStoreColumn.domain} (DTC)`);
        }
        for (const dom of grp.inStockStores) {
          inStockList.push(dom);
        }

        const vals = [
          ret.domain,
          `${ret.oosCount} of ${ret.totalCount}`,
          age,
          grp.displayName,
          varDesc,
          grp.dtcRrp ? `£${grp.dtcRrp.toFixed(2)}` : '',
          inStockList.join(' | '),
          stRow.oldestOosAt || '',
          stRow.primaryUrl || ''
        ].map(v => `"${String(v ?? '').replace(/"/g, '""')}"`);
        rows.push(vals.join(','));
      }
    }

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${brand.slug}-oos-report.csv`;
    link.click();
  }

  return (
    <div className="sheet">
      <header className="sheet-header">
        <div>
          <h1 className="sheet-title">{brand.name} — UK Retail Stockist Report</h1>
          <p className="sheet-summary">
            {totalRetailStores === 0 ? (
              <span>Initial UK stockist scan is queued.</span>
            ) : (
              <>
                <strong>
                  {oosProductGroups.length} product{oosProductGroups.length === 1 ? '' : 's'} out of stock
                </strong>{' '}
                at <strong>{retailersWithOosCount} of {totalRetailStores}</strong> UK stockists
                {parentSiteDomain && inStockOnParentCount > 0 && (
                  <>
                    {' '}
                    (<strong>{inStockOnParentCount} in stock at {parentSiteDomain}</strong>)
                  </>
                )}{' '}
                · Checked {fmtShortTime(latestCheck)}
              </>
            )}
          </p>
        </div>

        <div className="sheet-actions">
          <button
            className="btn-action"
            onClick={copyList}
            title="Copy clean retailer-first OOS report"
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

      {/* RETAILER-FIRST ZERO-CLICK REPORT */}
      <div>
        {oosProductGroups.length === 0 && totalRetailStores > 0 && (
          <p style={{ padding: '16px 0', color: 'var(--green)', fontWeight: 500 }}>
            All tracked {brand.name} products across all {totalRetailStores} UK retail stockists are currently in stock.
          </p>
        )}

        {oosProductGroups.length > 0 && (
          <div className="retailer-feed">
            {retailersWithOos.map(ret => (
              <section key={ret.domain} className="retailer-block">
                <div className="retailer-block-header">
                  <div className="retailer-block-title">
                    <span className="retailer-domain-name">{ret.domain}</span>
                    <span className="retailer-oos-summary">
                      — {ret.oosCount} of {ret.totalCount} product{ret.totalCount === 1 ? '' : 's'} out of stock
                    </span>
                  </div>
                  <button
                    className="btn-plain btn-xs"
                    onClick={() => copyStoreOosList(ret.domain)}
                  >
                    Copy {shortStoreLabel(ret.domain)}
                  </button>
                </div>

                <ul className="flat-oos-list">
                  {ret.items.map(({ grp, stRow }) => {
                    const firstVar = stRow.variants?.[0];
                    const hasNamedSize =
                      firstVar?.variant_title &&
                      firstVar.variant_title !== 'Default' &&
                      firstVar.variant_title !== 'Standard';
                    const rawPrice =
                      firstVar?.current_price !== null && firstVar?.current_price !== undefined
                        ? Number(firstVar.current_price)
                        : grp.dtcRrp;
                    const priceStr =
                      rawPrice !== null && rawPrice !== undefined ? `£${Number(rawPrice).toFixed(2)}` : '';

                    const inStockList = [];
                    if (grp.dtcStatus === 'IN_STOCK' && dtcStoreColumn?.domain) {
                      inStockList.push(`${dtcStoreColumn.domain} (DTC)`);
                    }
                    for (const dom of grp.inStockStores) {
                      inStockList.push(dom);
                    }

                    return (
                      <li key={`${ret.domain}__${grp.productKey}`} className="flat-oos-entry">
                        <div className="flat-oos-main">
                          <span className="list-duration-lead">{calcOutOfStockBadge(stRow.oldestOosAt)}</span>
                          <span className="store-domain">{grp.displayName}</span>

                          {(hasNamedSize || priceStr) && (
                            <span className="var-pill">
                              {hasNamedSize && <span>{firstVar.variant_title}</span>}
                              {priceStr && <span className="var-pill-price">{priceStr}</span>}
                            </span>
                          )}

                          <a
                            href={stRow.primaryUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flat-oos-store-link"
                            title={`Open ${grp.displayName} on ${ret.domain}`}
                          >
                            <span className="sku-open">↗</span>
                          </a>
                        </div>

                        <div className="flat-oos-sub">
                          {inStockList.length > 0 ? (
                            <>
                              <span className="flat-oos-sub-label">In stock at:</span> {inStockList.join(', ')}
                            </>
                          ) : (
                            <span className="flat-oos-sub-label">Out of stock across all tracked stockists</span>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}

            {healthyRetailers.length > 0 && (
              <div className="retailer-healthy-footer">
                <strong style={{ color: 'var(--green)' }}>
                  ✓ 100% in stock at ({healthyRetailers.length}):
                </strong>{' '}
                {healthyRetailers.map(h => `${h.domain} (${h.totalCount})`).join(', ')}
              </div>
            )}
          </div>
        )}
      </div>

      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}
