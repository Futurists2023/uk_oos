"""Master registry of the 24 UK SME Beauty & Wellness Brands.

Includes brand aliases, DTC domains (to exclude from 3rd-party stockist results),
and disambiguation rules for short/common brand names (e.g. 'YES', 'Ede').
"""
import re

SME_BRANDS: list[dict] = [
    {
        "slug": "balmonds",
        "name": "Balmonds",
        "aliases": ["Balmonds", "Balmonds Skincare", "Pure Potions"],
        "dtc_domains": ["balmonds.co.uk", "balmonds.com"],
        "search_hint": '"Skin Salvation" OR "Daily Moisturiser" OR "Cooling Cream"',
    },
    {
        "slug": "bare-biology",
        "name": "Bare Biology",
        "aliases": ["Bare Biology"],
        "dtc_domains": ["barebiology.com", "barebiology.co.uk"],
        "search_hint": '"Skinful" OR "Life & Soul" OR "Omega 3" OR "Ready & Rested"',
    },
    {
        "slug": "de-mamiel",
        "name": "De Mamiel",
        "aliases": ["De Mamiel", "de Mamiel"],
        "dtc_domains": ["demamiel.com", "demamiel.co.uk"],
        "search_hint": '"Altitude Oil" OR "Gravity Fix" OR "Facial Oil"',
    },
    {
        "slug": "earth-tan",
        "name": "Earth Tan",
        "aliases": ["Earth Tan"],
        "dtc_domains": ["earthtan.co.uk", "earthtan.com"],
        "search_hint": '"Earth Tan" tanning OR tan OR skincare',
    },
    {
        "slug": "ede",
        "name": "Ede",
        "aliases": ["Ede", "Ède", "Ede Skincare", "Ede Aromatherapy"],
        "dtc_domains": ["edestore.co.uk", "edeskincare.com"],
        "search_hint": '"Ede" ("roll-on" OR "facial" OR "serum" OR "skincare" OR "huile")',
        "strict_word_boundary": True,
    },
    {
        "slug": "elytrum",
        "name": "Elytrum",
        "aliases": ["Elytrum"],
        "dtc_domains": ["elytrum.co.uk", "elytrum.com"],
        "search_hint": '"Elytrum" "Body Brush" OR "Dry Body Brush"',
    },
    {
        "slug": "evolve",
        "name": "Evolve Organic Beauty",
        "aliases": ["Evolve Organic Beauty", "Evolve Beauty", "Evolve"],
        "dtc_domains": ["evolvebeauty.co.uk", "evolvebeauty.com"],
        "search_hint": '"Hyaluronic Serum 200" OR "Daily Renew" OR "Bio-Retinol"',
    },
    {
        "slug": "georganics",
        "name": "Georganics",
        "aliases": ["Georganics"],
        "dtc_domains": ["georganics.com", "georganics.co.uk"],
        "search_hint": '"Toothpaste" OR "Mouthwash Tablets" OR "Oil Pulling"',
    },
    {
        "slug": "green-people",
        "name": "Green People",
        "aliases": ["Green People", "Green People Organic"],
        "dtc_domains": ["greenpeople.co.uk", "greenpeople.com"],
        "search_hint": '"Green People" ("Sun Cream" OR "Cleanser" OR "Shampoo" OR "Quinoa")',
    },
    {
        "slug": "inlight-beauty",
        "name": "Inlight Beauty",
        "aliases": ["Inlight Beauty", "Inlight", "Inlight Organic Skincare"],
        "dtc_domains": ["inlightbeauty.co.uk", "inlightbeauty.com"],
        "search_hint": '"Inlight" ("Night Balm" OR "Face Cleanser" OR "Line Softener")',
    },
    {
        "slug": "kiki-health",
        "name": "Kiki Health",
        "aliases": ["Kiki Health", "KIKI Health", "Kiki"],
        "dtc_domains": ["kiki-health.com", "kiki-health.co.uk"],
        "search_hint": '"Kiki Health" ("Shilajit" OR "Body Biotics" OR "Marine Collagen")',
    },
    {
        "slug": "lily-lolo",
        "name": "Lily Lolo",
        "aliases": ["Lily Lolo", "Lily Lolo Mineral Cosmetics"],
        "dtc_domains": ["lilylolo.co.uk", "lilylolo.com"],
        "search_hint": '"Lily Lolo" ("Mineral Foundation" OR "Mascara" OR "BB Cream")',
    },
    {
        "slug": "love-bites-only",
        "name": "Love Bites Only",
        "aliases": ["Love Bites Only"],
        "dtc_domains": ["lovebitesonly.co.uk", "lovebitesonly.com"],
        "search_hint": '"Love Bites Only"',
    },
    {
        "slug": "megi-wellness",
        "name": "Megi Wellness",
        "aliases": ["Megi Wellness", "Megi"],
        "dtc_domains": ["megiwellness.com", "megiwellness.co.uk"],
        "search_hint": '"Megi Wellness"',
    },
    {
        "slug": "mirror-water",
        "name": "Mirror Water",
        "aliases": ["Mirror Water", "MIRROR WATER"],
        "dtc_domains": ["mirrorwater.earth", "mirrorwater.co.uk"],
        "search_hint": '"Mirror Water" ("BUFF" OR "SMOOTH" OR "SOAK" OR "RUB")',
    },
    {
        "slug": "nini-organics",
        "name": "Nini Organics",
        "aliases": ["Nini Organics", "NINI Organics"],
        "dtc_domains": ["niniorganics.com", "niniorganics.co.uk"],
        "search_hint": '"Nini Organics" ("Crimson Beauty" OR "Moonlight" OR "Halo")',
    },
    {
        "slug": "olverum",
        "name": "Olverum",
        "aliases": ["Olverum"],
        "dtc_domains": ["olverum.com", "olverum.co.uk"],
        "search_hint": '"Olverum" ("Bath Oil" OR "Body Polish" OR "Pillow Mist")',
    },
    {
        "slug": "pai-skincare",
        "name": "Pai Skincare",
        "aliases": ["Pai Skincare", "Pai", "Pai Organic"],
        "dtc_domains": ["paiskincare.com", "paiskincare.co.uk"],
        "search_hint": '"Pai Skincare" ("Rosehip BioRegenerate" OR "Middlemist Seven")',
    },
    {
        "slug": "therapi",
        "name": "Therapi",
        "aliases": ["Therapi", "Therapi Honey Skincare"],
        "dtc_domains": ["therapi.com", "therapihoneyskincare.com"],
        "search_hint": '"Therapi" "Honey Skincare" OR "Propolis"',
    },
    {
        "slug": "this-is-silk",
        "name": "This Is Silk",
        "aliases": ["This Is Silk"],
        "dtc_domains": ["thisissilk.com", "thisissilk.co.uk"],
        "search_hint": '"This Is Silk" ("Pillowcase" OR "Silk" OR "Hair")',
    },
    {
        "slug": "upcircle",
        "name": "UpCircle",
        "aliases": ["UpCircle", "UpCircle Beauty", "Upcircle"],
        "dtc_domains": ["upcirclebeauty.com", "upcirclebeauty.co.uk"],
        "search_hint": '"UpCircle" ("Coffee" OR "Face Serum" OR "Cleansing Balm")',
    },
    {
        "slug": "wild-nutrition",
        "name": "Wild Nutrition",
        "aliases": ["Wild Nutrition"],
        "dtc_domains": ["wildnutrition.com", "wildnutrition.co.uk"],
        "search_hint": '"Wild Nutrition" ("Food-Grown" OR "Magnesium" OR "Ashwagandha")',
    },
    {
        "slug": "wilder-botanics",
        "name": "Wilder Botanics",
        "aliases": ["Wilder Botanics"],
        "dtc_domains": ["wilderbotanics.com", "wilderbotanics.co.uk"],
        "search_hint": '"Wilder Botanics"',
    },
    {
        "slug": "yes",
        "name": "YES",
        "aliases": ["YES", "YES Organic", "YES Intimate", "The Yes Yes Company"],
        "dtc_domains": ["yesyesyes.org", "yesyesyes.co.uk"],
        "search_hint": '"YES" ("WB" OR "OB" OR "VM" OR "Organic Lubricant" OR "Intimate")',
        "strict_word_boundary": True,
        "required_context_regex": r"\b(yes\s+(wb|ob|vm|cleanse|butters)|intimate|lubricant|vaginal|applicator|organic\s+lubricant|yes\s+organic)\b",
    },
]

BRANDS_BY_SLUG = {b["slug"]: b for b in SME_BRANDS}


def get_brand(name_or_slug: str) -> dict:
    """Resolve a brand by slug, name, or alias (case-insensitive)."""
    q = (name_or_slug or "").strip().lower()
    if q in BRANDS_BY_SLUG:
        return BRANDS_BY_SLUG[q]
    slug_cand = re.sub(r"[^a-z0-9]+", "-", q).strip("-")
    if slug_cand in BRANDS_BY_SLUG:
        return BRANDS_BY_SLUG[slug_cand]
    for b in SME_BRANDS:
        if b["name"].lower() == q:
            return b
        for al in b["aliases"]:
            if al.lower() == q:
                return b
    raise ValueError(
        f"Unknown brand '{name_or_slug}'. Available slugs: {', '.join(BRANDS_BY_SLUG.keys())}"
    )


def matches_brand(brand: dict, vendor: str, title: str) -> bool:
    """Return True if a product's vendor or title genuinely belongs to `brand`."""
    v_low = (vendor or "").strip().lower()
    t_low = (title or "").strip().lower()
    combined = f"{v_low} {t_low}"

    # Check if vendor matches an alias directly
    for al in brand["aliases"]:
        al_low = al.lower()
        if v_low == al_low:
            return True
        if not brand.get("strict_word_boundary") and al_low in v_low:
            return True

    # If strict word boundary is required (e.g. 'YES', 'Ede'), require word boundary + context
    if brand.get("strict_word_boundary"):
        pattern = r"\b(" + "|".join(re.escape(a.lower()) for a in brand["aliases"]) + r")\b"
        if not re.search(pattern, combined):
            return False
        ctx_re = brand.get("required_context_regex")
        if ctx_re and not re.search(ctx_re, combined, re.I):
            return False
        return True

    # Normal brand matching in title or vendor
    for al in brand["aliases"]:
        al_low = al.lower()
        if re.search(r"\b" + re.escape(al_low) + r"\b", combined):
            return True
    return False


def normalize_product_family_key(brand: dict, title: str) -> str:
    """Create a cross-store canonical product key for any of the 24 SME brands.

    Strips brand names/aliases, sizes/weights/counts (e.g. 50ml, 100g, 60 caps),
    and punctuation so the same SKU across different UK retailers groups together
    for Hero SKU penetration benchmarking.
    """
    low = (title or "").lower().replace(".html", "").replace(".aspx", "")
    # Remove anything after pipe '|' or ' - ' if it's an ingredient subtitle or size suffix
    low = low.split("|")[0]

    # Strip brand aliases from start/anywhere
    for al in sorted(brand["aliases"], key=len, reverse=True):
        low = re.sub(r"\b" + re.escape(al.lower()) + r"\b", " ", low)

    # Strip sizes, weights, capsule/tablet counts, pack sizes, prices
    low = re.sub(r"£\d+(?:\.\d{2})?", " ", low)
    low = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ml|g|kg|oz|fl\s*oz|l|caps|capsules|tablets|tabs|sachets|pieces|pcs|pack|pk|m)\b", " ", low, flags=re.I)
    low = re.sub(r"\b(?:pack\s+of\s+\d+|size|default\s+title|standard|incl\s+vat|new|organic|natural)\b", " ", low, flags=re.I)
    low = re.sub(r"[^a-z0-9]+", " ", low).strip()
    low = re.sub(r"\s+", "_", low)
    return low or f"{brand['slug']}_sku"
