import crypto from 'crypto';

export const SME_BRANDS = [
  { slug: 'austin-austin', name: 'Austin Austin', category: 'Bath, Body & Apothecary' },
  { slug: 'balmonds', name: 'Balmonds', category: 'Skincare & Facial Botanicals' },
  { slug: 'bare-biology', name: 'Bare Biology', category: 'Wellness & Supplements' },
  { slug: 'bramley', name: 'Bramley', category: 'Bath, Body & Apothecary' },
  { slug: 'corinne-taylor', name: 'Corinne Taylor', category: 'Bath, Body & Apothecary' },
  { slug: 'de-mamiel', name: 'De Mamiel', category: 'Skincare & Facial Botanicals' },
  { slug: 'disciple-skincare', name: 'Disciple Skincare', category: 'Skincare & Facial Botanicals' },
  { slug: 'earth-conscious', name: 'Earth Conscious', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'earth-tan', name: 'Earth Tan', category: 'Skincare & Facial Botanicals' },
  { slug: 'ede', name: 'Ede', category: 'Skincare & Facial Botanicals' },
  { slug: 'elytrum', name: 'Elytrum', category: 'Bath, Body & Apothecary' },
  { slug: 'evolve', name: 'Evolve Organic Beauty', category: 'Skincare & Facial Botanicals' },
  { slug: 'faace', name: 'Faace', category: 'Skincare & Facial Botanicals' },
  { slug: 'flawless-vegan-beauty', name: 'Flawless Vegan Beauty', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'georganics', name: 'Georganics', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'green-people', name: 'Green People', category: 'Skincare & Facial Botanicals' },
  { slug: 'haeckels', name: 'Haeckels', category: 'Bath, Body & Apothecary' },
  { slug: 'inlight-beauty', name: 'Inlight Beauty', category: 'Skincare & Facial Botanicals' },
  { slug: 'kiki-health', name: 'Kiki Health', category: 'Wellness & Supplements' },
  { slug: 'kutis-skincare', name: 'Kutis Skincare', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'lily-lolo', name: 'Lily Lolo', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'lolas-apothecary', name: "Lola's Apothecary", category: 'Bath, Body & Apothecary' },
  { slug: 'love-bites-only', name: 'Love Bites Only', category: 'Wellness & Supplements' },
  { slug: 'megi-wellness', name: 'Megi Wellness', category: 'Wellness & Supplements' },
  { slug: 'mirror-water', name: 'Mirror Water', category: 'Bath, Body & Apothecary' },
  { slug: 'moa', name: 'MOA', category: 'Skincare & Facial Botanicals' },
  { slug: 'nathalie-bond', name: 'Nathalie Bond', category: 'Bath, Body & Apothecary' },
  { slug: 'neighbourhood-botanicals', name: 'Neighbourhood Botanicals', category: 'Skincare & Facial Botanicals' },
  { slug: 'nini-organics', name: 'Nini Organics', category: 'Skincare & Facial Botanicals' },
  { slug: 'nourish-london', name: 'Nourish London', category: 'Skincare & Facial Botanicals' },
  { slug: 'olverum', name: 'Olverum', category: 'Bath, Body & Apothecary' },
  { slug: 'pai-skincare', name: 'Pai Skincare', category: 'Skincare & Facial Botanicals' },
  { slug: 'plum-and-ashby', name: 'Plum & Ashby', category: 'Bath, Body & Apothecary' },
  { slug: 'sister-and-co', name: 'Sister & Co.', category: 'Bath, Body & Apothecary' },
  { slug: 'skin-sapiens', name: 'Skin Sapiens', category: 'Skincare & Facial Botanicals' },
  { slug: 'sknfed', name: 'Sknfed', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'therapi', name: 'Therapi', category: 'Skincare & Facial Botanicals' },
  { slug: 'this-is-silk', name: 'This Is Silk', category: 'Bath, Body & Apothecary' },
  { slug: 'upcircle', name: 'UpCircle', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'votary', name: 'Votary', category: 'Skincare & Facial Botanicals' },
  { slug: 'wild-nutrition', name: 'Wild Nutrition', category: 'Wellness & Supplements' },
  { slug: 'wilder-botanics', name: 'Wilder Botanics', category: 'Skincare & Facial Botanicals' },
  { slug: 'yes', name: 'YES', category: 'Wellness & Supplements' }
];

export const TIER_1_MAJOR_UK_RETAILERS = [
  'boots.com',
  'hollandandbarrett.com',
  'superdrug.com',
  'spacenk.com',
  'cultbeauty.co.uk',
  'cultbeauty.com',
  'lookfantastic.com',
  'selfridges.com',
  'johnlewis.com',
  'libertylondon.com',
  'harrods.com',
  'harveynichols.com',
  'fenwick.co.uk',
  'marksandspencer.com',
  'waitrose.com',
  'ocado.com',
  'sainsburys.co.uk',
  'tesco.com',
  'asda.com',
  'morrisons.com',
  'lloydspharmacy.com',
  'well.co.uk',
  'sephora.co.uk',
  'beautybay.com',
  'escentual.com',
  'feelunique.com',
  'asos.com',
  'next.co.uk'
];

export function isTier1Domain(domain) {
  const d = String(domain || '').toLowerCase().replace(/^www\./, '');
  return TIER_1_MAJOR_UK_RETAILERS.some(m => d === m || d.endsWith('.' + m));
}

function getSecretSalt() {
  return process.env.BRAND_LINK_SECRET || process.env.SUPABASE_SERVICE_ROLE_KEY || 'uk-oos-sme-secret-v1';
}

/**
 * Generates an un-indexed, unguessable token for a brand slug, e.g. `balmonds-9a4e1c7b2d`
 */
export function getBrandShareToken(slug) {
  const hmac = crypto
    .createHmac('sha256', getSecretSalt())
    .update(`uk-oos-brand:${slug}`)
    .digest('hex')
    .slice(0, 10);
  return `${slug}-${hmac}`;
}

/**
 * Returns the full list of 43 brands enriched with their secret un-indexed path (`/b/<token>`)
 */
export function getBrandsWithTokens() {
  return SME_BRANDS.map((b, idx) => {
    const token = getBrandShareToken(b.slug);
    return {
      ...b,
      index: idx + 1,
      token,
      sharePath: `/b/${token}`
    };
  });
}

/**
 * Verifies a `/b/[token]` parameter on the server and returns the matching brand object or null.
 */
export function resolveBrandFromToken(token) {
  if (!token || typeof token !== 'string') return null;
  for (const b of SME_BRANDS) {
    const expected = getBrandShareToken(b.slug);
    if (token === expected) {
      return {
        ...b,
        token: expected,
        sharePath: `/b/${expected}`
      };
    }
  }
  return null;
}
