import crypto from 'crypto';

export const SME_BRANDS = [
  // Tier 1: Verified in 3 to 4+ Major UK Retailer Directories
  { slug: 'oskia', name: 'Oskia', category: 'Skincare & Facial Botanicals', dtcDomains: ['oskiaskincare.com'] },
  { slug: 'philip-kingsley', name: 'Philip Kingsley', category: 'Bath, Body & Apothecary', dtcDomains: ['philipkingsley.co.uk', 'philipkingsley.com'] },
  { slug: '111skin', name: '111SKIN', category: 'Skincare & Facial Botanicals', dtcDomains: ['111skin.co.uk', '111skin.com'] },
  { slug: 'artah', name: 'Artah', category: 'Wellness & Supplements', dtcDomains: ['artah.co'] },
  { slug: 'emma-hardie', name: 'Emma Hardie', category: 'Skincare & Facial Botanicals', dtcDomains: ['emmahardie.com'] },
  { slug: 'facegym', name: 'FACEGYM', category: 'Skincare & Facial Botanicals', dtcDomains: ['uk.facegym.com', 'facegym.com'] },
  { slug: 'floral-street', name: 'Floral Street', category: 'Bath, Body & Apothecary', dtcDomains: ['floralstreet.com'] },
  { slug: 'hair-gain', name: 'Hair Gain', category: 'Wellness & Supplements', dtcDomains: ['hairgainnow.com'] },
  { slug: 'hair-by-sam-mcknight', name: 'Hair by Sam McKnight', category: 'Bath, Body & Apothecary', dtcDomains: ['sammcknight.com'] },
  { slug: 'hello-sunday', name: 'Hello Sunday', category: 'Skincare & Facial Botanicals', dtcDomains: ['hellosundayspf.com'] },
  { slug: 'isle-of-paradise', name: 'Isle of Paradise', category: 'Bath, Body & Apothecary', dtcDomains: ['theisleofparadise.com'] },
  { slug: 'joonbyrd', name: 'Joonbyrd', category: 'Bath, Body & Apothecary', dtcDomains: ['joonbyrd.com'] },
  { slug: 'luna-daily', name: 'Luna Daily', category: 'Bath, Body & Apothecary', dtcDomains: ['luna-daily.com'] },
  { slug: 'mz-skin', name: 'MZ SKIN', category: 'Skincare & Facial Botanicals', dtcDomains: ['mzskin.com'] },
  { slug: 'mirror-water', name: 'Mirror Water', category: 'Bath, Body & Apothecary', dtcDomains: ['mirrorwater.earth'] },
  { slug: 'neom-wellbeing', name: 'NEOM Wellbeing', category: 'Bath, Body & Apothecary', dtcDomains: ['neomwellbeing.com', 'neomorganics.com'] },
  { slug: 'sarah-chapman', name: 'Sarah Chapman', category: 'Skincare & Facial Botanicals', dtcDomains: ['sarahchapman.com'] },
  { slug: 'tan-luxe', name: 'Tan-Luxe', category: 'Bath, Body & Apothecary', dtcDomains: ['tan-luxe.com'] },
  { slug: 'the-nue-co', name: 'The Nue Co.', category: 'Wellness & Supplements', dtcDomains: ['uk.thenueco.com', 'thenueco.com'] },
  { slug: 'vieve', name: 'VIEVE', category: 'Zero-Waste & Eco-Cosmetics', dtcDomains: ['vieve.co.uk'] },
  { slug: 'medik8', name: 'Medik8', category: 'Skincare & Facial Botanicals', dtcDomains: ['medik8.com'] },
  { slug: 'the-inkey-list', name: 'The INKEY List', category: 'Skincare & Facial Botanicals', dtcDomains: ['uk.theinkeylist.com', 'theinkeylist.com'] },

  // Tier 2: Verified in 2+ Major UK Retailer Directories (+ Boots / H&B / Superdrug)
  { slug: 'aromatherapy-associates', name: 'Aromatherapy Associates', category: 'Bath, Body & Apothecary', dtcDomains: ['aromatherapyassociates.com'] },
  { slug: 'beautypro', name: 'BEAUTYPRO', category: 'Skincare & Facial Botanicals', dtcDomains: ['beautypro.com'] },
  { slug: 'bleach-london', name: 'BLEACH London', category: 'Bath, Body & Apothecary', dtcDomains: ['bleachlondon.com'] },
  { slug: 'boucleme', name: 'Bouclème', category: 'Bath, Body & Apothecary', dtcDomains: ['boucleme.co.uk'] },
  { slug: 'byoma', name: 'BYOMA', category: 'Skincare & Facial Botanicals', dtcDomains: ['byoma.com'] },
  { slug: 'dirtea', name: 'DIRTEA', category: 'Wellness & Supplements', dtcDomains: ['dirteaworld.com'] },
  { slug: 'evolve', name: 'Evolve Organic Beauty', category: 'Skincare & Facial Botanicals', dtcDomains: ['evolvebeauty.co.uk'] },
  { slug: 'fussy', name: 'Fussy', category: 'Zero-Waste & Eco-Cosmetics', dtcDomains: ['getfussy.com'] },
  { slug: 'hairburst', name: 'Hairburst', category: 'Wellness & Supplements', dtcDomains: ['hairburst.com'] },
  { slug: 'iconic-london', name: 'ICONIC LONDON', category: 'Zero-Waste & Eco-Cosmetics', dtcDomains: ['iconiclondoninc.com'] },
  { slug: 'jo-loves', name: 'Jo Loves', category: 'Bath, Body & Apothecary', dtcDomains: ['joloves.com'] },
  { slug: 'kiki-health', name: 'Kiki Health', category: 'Wellness & Supplements', dtcDomains: ['kiki-health.com'] },
  { slug: 'laboratory-perfumes', name: 'Laboratory Perfumes', category: 'Bath, Body & Apothecary', dtcDomains: ['laboratoryperfumes.com'] },
  { slug: 'margaret-dabbs-london', name: 'Margaret Dabbs London', category: 'Bath, Body & Apothecary', dtcDomains: ['margaretdabbs.co.uk'] },
  { slug: 'nailberry', name: 'Nailberry', category: 'Zero-Waste & Eco-Cosmetics', dtcDomains: ['nailberry.co.uk'] },
  { slug: 'noughty', name: 'Noughty', category: 'Bath, Body & Apothecary', dtcDomains: ['lovenoughty.co.uk'] },
  { slug: 'nursem', name: 'Nursem', category: 'Bath, Body & Apothecary', dtcDomains: ['nursem.co.uk'] },
  { slug: 'ordo', name: 'ORDO', category: 'Zero-Waste & Eco-Cosmetics', dtcDomains: ['ordolife.com'] },
  { slug: 'pai-skincare', name: 'Pai Skincare', category: 'Skincare & Facial Botanicals', dtcDomains: ['paiskincare.com'] },
  { slug: 'revive-collagen', name: 'Revive Collagen', category: 'Wellness & Supplements', dtcDomains: ['revivecollagen.com'] },
  { slug: 'rodial', name: 'Rodial', category: 'Skincare & Facial Botanicals', dtcDomains: ['rodial.com'] },
  { slug: 'spectrum-collections', name: 'Spectrum Collections', category: 'Zero-Waste & Eco-Cosmetics', dtcDomains: ['spectrumcollections.com'] },
  { slug: 'this-works', name: 'This Works', category: 'Bath, Body & Apothecary', dtcDomains: ['thisworks.com'] },
  { slug: 'votary', name: 'Votary', category: 'Skincare & Facial Botanicals', dtcDomains: ['votary.co.uk'] },
  { slug: 'vyrao', name: 'Vyrao', category: 'Bath, Body & Apothecary', dtcDomains: ['vyrao.com'] },
  { slug: 'wild-nutrition', name: 'Wild Nutrition', category: 'Wellness & Supplements', dtcDomains: ['wildnutrition.com'] },
  { slug: 'zelens', name: 'Zelens', category: 'Skincare & Facial Botanicals', dtcDomains: ['zelens.com'] },
  { slug: 'zooki', name: 'Zooki', category: 'Wellness & Supplements', dtcDomains: ['yourzooki.com'] },

  // Tier 3: Already-Tracked Pharmacy / Eco / Wellness Scale-Ups
  { slug: 'upcircle', name: 'UpCircle', category: 'Zero-Waste & Eco-Cosmetics', dtcDomains: ['upcirclebeauty.com'] },
  { slug: 'balmonds', name: 'Balmonds', category: 'Skincare & Facial Botanicals', dtcDomains: ['balmonds.co.uk', 'balmonds.com'] },
  { slug: 'bare-biology', name: 'Bare Biology', category: 'Wellness & Supplements', dtcDomains: ['barebiology.com', 'barebiology.co.uk'] }
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
