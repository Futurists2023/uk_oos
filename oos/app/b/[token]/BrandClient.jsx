'use client';

import React, { useState, useMemo } from 'react';

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

export default function BrandClient({ initialData }) {
  const [data] = useState(initialData);
  const [showHealthyStores, setShowHealthyStores] = useState(false);
  const [showInStockProducts, setShowInStockProducts] = useState(false);
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

  // Group active SKUs by store
  const { oosStoreGroups, healthyStores, totalOos, totalStores, latestCheck } = useMemo(() => {
    const activeSkus = data.skus.filter(s => s.is_listed === 1);
    const byDomain = new Map();

    for (const st of data.stores) {
      byDomain.set(st.domain, {
        store: st,
        oosItems: [],
        inStockItems: []
      });
    }

    for (const s of activeSkus) {
      if (!byDomain.has(s.domain)) {
        byDomain.set(s.domain, {
          store: { domain: s.domain, brand_url: s.product_url },
          oosItems: [],
          inStockItems: []
        });
      }
      const grp = byDomain.get(s.domain);
      if (s.is_available === 0) {
        grp.oosItems.push(s);
      } else {
        grp.inStockItems.push(s);
      }
    }

    const withOos = [];
    const healthy = [];
    let oosSum = 0;
    let maxTs = '';

    for (const grp of byDomain.values()) {
      if (grp.store.last_checked_at && grp.store.last_checked_at > maxTs) {
        maxTs = grp.store.last_checked_at;
      }
      // Sort OOS items oldest first
      grp.oosItems.sort((a, b) => (a.first_seen_oos_at || '9999').localeCompare(b.first_seen_oos_at || '9999'));
      oosSum += grp.oosItems.length;

      if (grp.oosItems.length > 0) {
        withOos.push(grp);
      } else {
        healthy.push(grp);
      }
    }

    // Sort store groups by most OOS items first
    withOos.sort((a, b) => b.oosItems.length - a.oosItems.length);
    healthy.sort((a, b) => a.store.domain.localeCompare(b.store.domain));

    return {
      oosStoreGroups: withOos,
      healthyStores: healthy,
      totalOos: oosSum,
      totalStores: byDomain.size,
      latestCheck: maxTs
    };
  }, [data.stores, data.skus]);

  function copyList(singleDomain = null) {
    const groups = singleDomain
      ? oosStoreGroups.filter(g => g.store.domain === singleDomain)
      : oosStoreGroups;

    if (groups.length === 0) {
      showToast('All tracked items are currently in stock.');
      return;
    }

    const lines = [];
    if (!singleDomain) {
      lines.push(`${brand.name} — UK Stockist Out of Stock (${totalOos} items across ${oosStoreGroups.length} stockists)`);
      lines.push(`Checked: ${fmtShortTime(latestCheck)}`);
      lines.push('');
    }

    for (const grp of groups) {
      lines.push(`${grp.store.domain} (${grp.oosItems.length} Out of Stock)`);
      for (const s of grp.oosItems) {
        const title = String(s.product_title || '').split('|')[0].trim();
        const variant = s.variant_title && s.variant_title !== 'Default' && s.variant_title !== 'Standard' ? ` (${s.variant_title})` : '';
        const price = s.current_price !== null && s.current_price !== undefined ? `£${Number(s.current_price).toFixed(2)}` : '';
        const age = calcOosAge(s.first_seen_oos_at);
        lines.push(`- ${title}${variant}  ${price}  [${age}]  ${s.product_url || ''}`);
      }
      lines.push('');
    }

    navigator.clipboard.writeText(lines.join('\n').trim()).then(() => {
      showToast(singleDomain ? `Copied ${singleDomain} OOS list` : 'Copied OOS list to clipboard');
    });
  }

  function downloadCSV() {
    const headers = ['Brand', 'Stockist', 'Tier', 'Product', 'Variant', 'Price_GBP', 'Status', 'OOS_Duration', 'First_Seen_OOS_UTC', 'URL'];
    const rows = [headers.join(',')];

    const activeSkus = data.skus.filter(s => s.is_listed === 1 && (showInStockProducts || s.is_available === 0));
    for (const s of activeSkus) {
      const title = String(s.product_title || '').split('|')[0].trim();
      const tier = isTier1(s.domain) ? 'Major Retailer' : 'Independent';
      const status = s.is_available === 0 ? 'Out of Stock' : 'In Stock';
      const age = s.is_available === 0 ? calcOosAge(s.first_seen_oos_at) : '';
      const price = s.current_price !== null && s.current_price !== undefined ? Number(s.current_price).toFixed(2) : '';

      const vals = [
        brand.name,
        s.domain,
        tier,
        title,
        s.variant_title || '',
        price,
        status,
        age,
        s.first_seen_oos_at || '',
        s.product_url || ''
      ].map(v => `"${String(v ?? '').replace(/"/g, '""')}"`);
      rows.push(vals.join(','));
    }

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${brand.slug}-oos.csv`;
    link.click();
  }

  return (
    <div className="sheet">
      <header className="sheet-header">
        <div>
          <h1 className="sheet-title">{brand.name} — UK Stockist Out of Stock</h1>
          <p className="sheet-summary">
            {totalStores === 0 ? (
              <span>Initial UK stockist scan is queued.</span>
            ) : (
              <>
                <strong className="oos-num">{totalOos} out of stock</strong> across{' '}
                <strong>{oosStoreGroups.length}</strong> of <strong>{totalStores}</strong> UK stockists · Checked{' '}
                {fmtShortTime(latestCheck)}
              </>
            )}
          </p>
        </div>

        <div className="sheet-actions">
          <button
            className={`btn-plain ${showInStockProducts ? 'active' : ''}`}
            onClick={() => setShowInStockProducts(v => !v)}
          >
            {showInStockProducts ? 'Hide In-Stock' : 'Show In-Stock'}
          </button>
          <button className="btn-plain" onClick={() => copyList(null)}>
            Copy List
          </button>
          <button className="btn-plain" onClick={downloadCSV}>
            CSV
          </button>
        </div>
      </header>

      {/* STOCKISTS WITH OUT OF STOCK ITEMS */}
      {oosStoreGroups.length === 0 && totalStores > 0 && (
        <p style={{ padding: '24px 0', color: 'var(--green)', fontWeight: 500 }}>
          All tracked products across all {totalStores} UK stockists are currently in stock.
        </p>
      )}

      {oosStoreGroups.map(grp => {
        const dom = grp.store.domain;
        const major = isTier1(dom);
        const itemsToRender = showInStockProducts
          ? [...grp.oosItems, ...grp.inStockItems]
          : grp.oosItems;

        return (
          <section key={dom} className="store-group">
            <div className="store-group-header">
              <div className="store-domain">
                <span>{dom}</span>
                {major && <span className="tier-tag">Major Retailer</span>}
              </div>
              <div className="store-meta">
                <span className="store-oos-count">{grp.oosItems.length} Out of Stock</span>
                <button className="btn-plain btn-xs" onClick={() => copyList(dom)}>
                  Copy
                </button>
                <a
                  href={grp.store.brand_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="store-ext-link"
                >
                  Storefront ↗
                </a>
              </div>
            </div>

            <ul className="sku-list">
              {itemsToRender.map(s => {
                const title = String(s.product_title || '').split('|')[0].trim();
                const variant =
                  s.variant_title && s.variant_title !== 'Default' && s.variant_title !== 'Standard'
                    ? `(${s.variant_title})`
                    : '';
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
                      <span className="sku-name">{title}</span>
                      {variant && <span className="sku-variant">{variant}</span>}
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
                      title="Open product page"
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

      {/* COLLAPSIBLE FOOTER FOR 100% IN-STOCK STOCKISTS */}
      {healthyStores.length > 0 && (
        <div className="healthy-section">
          <button
            className="healthy-toggle"
            onClick={() => setShowHealthyStores(v => !v)}
          >
            {showHealthyStores ? '▾' : '▸'} {healthyStores.length} UK stockist
            {healthyStores.length === 1 ? '' : 's'} with 100% stock availability (
            {healthyStores
              .slice(0, 5)
              .map(g => g.store.domain)
              .join(', ')}
            {healthyStores.length > 5 ? ', …' : ''})
          </button>

          {showHealthyStores && (
            <div className="healthy-list">
              {healthyStores.map(g => (
                <div key={g.store.domain} className="healthy-card">
                  <div>
                    <strong>{g.store.domain}</strong>
                    <div style={{ fontSize: '0.76rem', color: 'var(--muted)' }}>
                      {g.inStockItems.length} variant{g.inStockItems.length === 1 ? '' : 's'} in stock
                    </div>
                  </div>
                  <a
                    href={g.store.brand_url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="store-ext-link"
                  >
                    Storefront ↗
                  </a>
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
