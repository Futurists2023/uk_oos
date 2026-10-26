import crypto from 'crypto';

export const SME_BRANDS = [
  // Tier 1: Verified in 3 to 4+ Major UK Retailer Directories
  { slug: 'oskia', name: 'Oskia', category: 'Skincare & Facial Botanicals' },
  { slug: 'philip-kingsley', name: 'Philip Kingsley', category: 'Bath, Body & Apothecary' },
  { slug: '111skin', name: '111SKIN', category: 'Skincare & Facial Botanicals' },
  { slug: 'artah', name: 'Artah', category: 'Wellness & Supplements' },
  { slug: 'emma-hardie', name: 'Emma Hardie', category: 'Skincare & Facial Botanicals' },
  { slug: 'facegym', name: 'FACEGYM', category: 'Skincare & Facial Botanicals' },
  { slug: 'floral-street', name: 'Floral Street', category: 'Bath, Body & Apothecary' },
  { slug: 'hair-gain', name: 'Hair Gain', category: 'Wellness & Supplements' },
  { slug: 'hair-by-sam-mcknight', name: 'Hair by Sam McKnight', category: 'Bath, Body & Apothecary' },
  { slug: 'hello-sunday', name: 'Hello Sunday', category: 'Skincare & Facial Botanicals' },
  { slug: 'isle-of-paradise', name: 'Isle of Paradise', category: 'Bath, Body & Apothecary' },
  { slug: 'joonbyrd', name: 'Joonbyrd', category: 'Bath, Body & Apothecary' },
  { slug: 'luna-daily', name: 'Luna Daily', category: 'Bath, Body & Apothecary' },
  { slug: 'mz-skin', name: 'MZ SKIN', category: 'Skincare & Facial Botanicals' },
  { slug: 'mirror-water', name: 'Mirror Water', category: 'Bath, Body & Apothecary' },
  { slug: 'neom-wellbeing', name: 'NEOM Wellbeing', category: 'Bath, Body & Apothecary' },
  { slug: 'sarah-chapman', name: 'Sarah Chapman', category: 'Skincare & Facial Botanicals' },
  { slug: 'tan-luxe', name: 'Tan-Luxe', category: 'Bath, Body & Apothecary' },
  { slug: 'the-nue-co', name: 'The Nue Co.', category: 'Wellness & Supplements' },
  { slug: 'vieve', name: 'VIEVE', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'medik8', name: 'Medik8', category: 'Skincare & Facial Botanicals' },
  { slug: 'the-inkey-list', name: 'The INKEY List', category: 'Skincare & Facial Botanicals' },

  // Tier 2: Verified in 2+ Major UK Retailer Directories (+ Boots / H&B / Superdrug)
  { slug: 'aromatherapy-associates', name: 'Aromatherapy Associates', category: 'Bath, Body & Apothecary' },
  { slug: 'beautypro', name: 'BEAUTYPRO', category: 'Skincare & Facial Botanicals' },
  { slug: 'bleach-london', name: 'BLEACH London', category: 'Bath, Body & Apothecary' },
  { slug: 'boucleme', name: 'Bouclème', category: 'Bath, Body & Apothecary' },
  { slug: 'byoma', name: 'BYOMA', category: 'Skincare & Facial Botanicals' },
  { slug: 'dirtea', name: 'DIRTEA', category: 'Wellness & Supplements' },
  { slug: 'evolve', name: 'Evolve Organic Beauty', category: 'Skincare & Facial Botanicals' },
  { slug: 'fussy', name: 'Fussy', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'hairburst', name: 'Hairburst', category: 'Wellness & Supplements' },
  { slug: 'iconic-london', name: 'ICONIC LONDON', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'jo-loves', name: 'Jo Loves', category: 'Bath, Body & Apothecary' },
  { slug: 'kiki-health', name: 'Kiki Health', category: 'Wellness & Supplements' },
  { slug: 'laboratory-perfumes', name: 'Laboratory Perfumes', category: 'Bath, Body & Apothecary' },
  { slug: 'margaret-dabbs-london', name: 'Margaret Dabbs London', category: 'Bath, Body & Apothecary' },
  { slug: 'nailberry', name: 'Nailberry', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'noughty', name: 'Noughty', category: 'Bath, Body & Apothecary' },
  { slug: 'nursem', name: 'Nursem', category: 'Bath, Body & Apothecary' },
  { slug: 'ordo', name: 'ORDO', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'pai-skincare', name: 'Pai Skincare', category: 'Skincare & Facial Botanicals' },
  { slug: 'revive-collagen', name: 'Revive Collagen', category: 'Wellness & Supplements' },
  { slug: 'rodial', name: 'Rodial', category: 'Skincare & Facial Botanicals' },
  { slug: 'spectrum-collections', name: 'Spectrum Collections', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'this-works', name: 'This Works', category: 'Bath, Body & Apothecary' },
  { slug: 'votary', name: 'Votary', category: 'Skincare & Facial Botanicals' },
  { slug: 'vyrao', name: 'Vyrao', category: 'Bath, Body & Apothecary' },
  { slug: 'wild-nutrition', name: 'Wild Nutrition', category: 'Wellness & Supplements' },
  { slug: 'zelens', name: 'Zelens', category: 'Skincare & Facial Botanicals' },
  { slug: 'zooki', name: 'Zooki', category: 'Wellness & Supplements' },

  // Tier 3: Already-Tracked Pharmacy / Eco / Wellness Scale-Ups
  { slug: 'upcircle', name: 'UpCircle', category: 'Zero-Waste & Eco-Cosmetics' },
  { slug: 'balmonds', name: 'Balmonds', category: 'Skincare & Facial Botanicals' },
  { slug: 'bare-biology', name: 'Bare Biology', category: 'Wellness & Supplements' }
];

export const TIER_1_MAJOR_UK_RETAILERS = [
  'boots.com',
  'hollandandbarrett.com',
  'superdrug.com',
  'spacenk.com',
  'cultbeauty.co.uk',
  'cultbeauty.com',
  'lookfantastic.com',
  'ohmycream.co.uk',
  'sephora.co.uk',
  'planetorganic.com',
  'healf.com',
  'selfridges.com',
  'johnlewis.com',
  'libertylondon.com',
  'harrods.com',
  'harveynichols.com',
  'flannels.com',
  'houseoffraser.co.uk',
  'facethefuture.co.uk',
  'bathandunwind.com',
  'alyaka.com',
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
 * Returns the full list of 53 verified UK Scale-Up brands enriched with their secret un-indexed path (`/b/<token>`)
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
