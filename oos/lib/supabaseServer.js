import { getBrandsWithTokens, TIER_1_MAJOR_UK_RETAILERS } from './brands';

function getSupabaseServerConfig() {
  const url = (process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || '').replace(/\/$/, '');
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
  return { url, key };
}

function normalizeSkuRow(s) {
  return {
    ...s,
    current_price: s.current_price !== null && s.current_price !== undefined ? Number(s.current_price) : null,
    compare_at_price: s.compare_at_price !== null && s.compare_at_price !== undefined ? Number(s.compare_at_price) : null,
    is_available: s.is_available === true || s.is_available === 1 ? 1 : 0,
    is_listed: s.is_listed === false || s.is_listed === 0 ? 0 : 1
  };
}

/**
 * Fetches global data for the Master Admin Panel (`/admin`).
 * Runs exclusively on the server so `SUPABASE_SERVICE_ROLE_KEY` is never exposed to the client.
 */
export async function fetchAllAdminData() {
  const { url, key } = getSupabaseServerConfig();
  const brandsMeta = getBrandsWithTokens();

  if (!url || !key) {
    return {
      syncedAt: new Date().toISOString(),
      brandsMeta,
      tier1Domains: TIER_1_MAJOR_UK_RETAILERS,
      stores: [],
      skus: [],
      events: []
    };
  }

  const headers = {
    apikey: key,
    Authorization: `Bearer ${key}`
  };

  const [stRes, skRes, evRes] = await Promise.all([
    fetch(`${url}/rest/v1/stores?select=*&order=brand.asc,domain.asc&limit=5000`, { headers, cache: 'no-store' }),
    fetch(`${url}/rest/v1/skus?select=*&order=brand.asc,domain.asc,product_title.asc&limit=10000`, { headers, cache: 'no-store' }),
    fetch(`${url}/rest/v1/stock_events?select=*&order=occurred_at.desc&limit=300`, { headers, cache: 'no-store' })
  ]);

  const stores = stRes.ok ? await stRes.json() : [];
  const rawSkus = skRes.ok ? await skRes.json() : [];
  const events = evRes.ok ? await evRes.json() : [];

  return {
    syncedAt: new Date().toISOString(),
    brandsMeta,
    tier1Domains: TIER_1_MAJOR_UK_RETAILERS,
    stores: Array.isArray(stores) ? stores : [],
    skus: Array.isArray(rawSkus) ? rawSkus.map(normalizeSkuRow) : [],
    events: Array.isArray(events) ? events : []
  };
}

/**
 * Fetches strictly isolated data for a single Brand (`/b/[token]`).
 * No other brand's stores, SKUs, or events ever leave the server.
 */
export async function fetchSingleBrandData(brandObj) {
  const { url, key } = getSupabaseServerConfig();
  const encodedBrand = encodeURIComponent(brandObj.name);

  if (!url || !key) {
    return {
      syncedAt: new Date().toISOString(),
      brand: brandObj,
      tier1Domains: TIER_1_MAJOR_UK_RETAILERS,
      stores: [],
      skus: [],
      events: []
    };
  }

  const headers = {
    apikey: key,
    Authorization: `Bearer ${key}`
  };

  const [stRes, skRes, evRes] = await Promise.all([
    fetch(`${url}/rest/v1/stores?select=*&brand=eq.${encodedBrand}&order=domain.asc&limit=1000`, { headers, cache: 'no-store' }),
    fetch(`${url}/rest/v1/skus?select=*&brand=eq.${encodedBrand}&order=domain.asc,product_title.asc&limit=5000`, { headers, cache: 'no-store' }),
    fetch(`${url}/rest/v1/stock_events?select=*&brand=eq.${encodedBrand}&order=occurred_at.desc&limit=150`, { headers, cache: 'no-store' })
  ]);

  const stores = stRes.ok ? await stRes.json() : [];
  const rawSkus = skRes.ok ? await skRes.json() : [];
  const events = evRes.ok ? await evRes.json() : [];

  return {
    syncedAt: new Date().toISOString(),
    brand: brandObj,
    tier1Domains: TIER_1_MAJOR_UK_RETAILERS,
    stores: Array.isArray(stores) ? stores : [],
    skus: Array.isArray(rawSkus) ? rawSkus.map(normalizeSkuRow) : [],
    events: Array.isArray(events) ? events : []
  };
}
