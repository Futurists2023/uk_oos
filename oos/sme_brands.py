"""Master registry of the 43 UK SME Beauty & Wellness Brands.

Includes brand aliases, DTC domains (to exclude from 3rd-party stockist results),
and disambiguation rules for short/common brand names (e.g. 'YES', 'Ede', 'MOA').
"""
import html
import re

SME_BRANDS: list[dict] = [
    {
        "slug": "austin-austin",
        "name": "Austin Austin",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Austin Austin", "Austin Austin Organic"],
        "dtc_domains": ["austinaustinorganic.com", "austinaustin.co.uk"],
        "search_hint": '"Palmarosa & Vetiver" OR "Neroli & Petitgrain" OR "Bergamot & Juniper"',
    },
    {
        "slug": "balmonds",
        "name": "Balmonds",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Balmonds", "Balmonds Skincare", "Pure Potions"],
        "dtc_domains": ["balmonds.co.uk", "balmonds.com"],
        "search_hint": '"Skin Salvation" OR "Daily Moisturiser" OR "Cooling Cream"',
    },
    {
        "slug": "bare-biology",
        "name": "Bare Biology",
        "category": "Wellness & Supplements",
        "aliases": ["Bare Biology"],
        "dtc_domains": ["barebiology.com", "barebiology.co.uk"],
        "search_hint": '"Skinful" OR "Life & Soul" OR "Omega 3" OR "Ready & Rested"',
    },
    {
        "slug": "bramley",
        "name": "Bramley",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Bramley", "Bramley Products", "Bramley Bath & Body"],
        "dtc_domains": ["bramleyproducts.co.uk", "bramleyproducts.com"],
        "search_hint": '"Bramley" ("Hand Wash" OR "Body Wash" OR "Bubble Bath" OR "Body Lotion" OR "Calm" OR "Sleep")',
    },
    {
        "slug": "corinne-taylor",
        "name": "Corinne Taylor",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Corinne Taylor", "Corinne Taylor Aromatherapy"],
        "dtc_domains": ["corinnetaylor.co.uk", "corinnetaylor.com"],
        "search_hint": '"Corinne Taylor" ("Bath Salts" OR "Body Oil" OR "Soy Candle" OR "Soothe" OR "Calm")',
    },
    {
        "slug": "de-mamiel",
        "name": "De Mamiel",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["De Mamiel", "de Mamiel"],
        "dtc_domains": ["demamiel.com", "demamiel.co.uk"],
        "search_hint": '"Altitude Oil" OR "Gravity Fix" OR "Facial Oil"',
    },
    {
        "slug": "disciple-skincare",
        "name": "Disciple Skincare",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Disciple Skincare", "Disciple", "Disciple London"],
        "dtc_domains": ["discipleskincare.com", "discipleskincare.co.uk"],
        "search_hint": '"Good Skin" OR "Dreamy Skin" OR "What Spot" OR "Disciple Skincare"',
    },
    {
        "slug": "earth-conscious",
        "name": "Earth Conscious",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Earth Conscious"],
        "dtc_domains": ["earthconscious.co.uk", "earthconscious.com"],
        "search_hint": '"Natural Deodorant" OR "Bare Bar" OR "Baby Balm" OR "Jasmine & Rose"',
    },
    {
        "slug": "earth-tan",
        "name": "Earth Tan",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Earth Tan"],
        "dtc_domains": ["earthtan.co.uk", "earthtan.com"],
        "search_hint": '"Earth Tan" tanning OR tan OR skincare',
    },
    {
        "slug": "ede",
        "name": "Ede",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Ede", "Ède", "Ede Skincare", "Ede Aromatherapy"],
        "dtc_domains": ["edestore.co.uk", "edeskincare.com"],
        "search_hint": '"Ede" ("roll-on" OR "facial" OR "serum" OR "skincare" OR "huile")',
        "strict_word_boundary": True,
    },
    {
        "slug": "elytrum",
        "name": "Elytrum",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Elytrum"],
        "dtc_domains": ["elytrum.co.uk", "elytrum.com"],
        "search_hint": '"Elytrum" "Body Brush" OR "Dry Body Brush"',
    },
    {
        "slug": "evolve",
        "name": "Evolve Organic Beauty",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Evolve Organic Beauty", "Evolve Beauty", "Evolve"],
        "dtc_domains": ["evolvebeauty.co.uk", "evolvebeauty.com"],
        "search_hint": '"Hyaluronic Serum 200" OR "Daily Renew" OR "Bio-Retinol"',
    },
    {
        "slug": "faace",
        "name": "Faace",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Faace", "We Are Faace"],
        "dtc_domains": ["wearefaace.com", "wearefaace.co.uk"],
        "search_hint": '"Period Faace" OR "Tired Faace" OR "Sweaty Faace" OR "Menopause Faace"',
    },
    {
        "slug": "flawless-vegan-beauty",
        "name": "Flawless Vegan Beauty",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Flawless Vegan Beauty", "Flawless Vegan", "Flawless Zero Waste"],
        "dtc_domains": ["flawless-beauty.co.uk", "flawlessvegan.co.uk", "flawlessbeauty.co.uk"],
        "search_hint": '"Flawless" ("Vegan" OR "Zero Waste" OR "Konjac" OR "Cuticle Oil" OR "Micellar")',
    },
    {
        "slug": "georganics",
        "name": "Georganics",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Georganics"],
        "dtc_domains": ["georganics.com", "georganics.co.uk"],
        "search_hint": '"Toothpaste" OR "Mouthwash Tablets" OR "Oil Pulling"',
    },
    {
        "slug": "green-people",
        "name": "Green People",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Green People", "Green People Organic"],
        "dtc_domains": ["greenpeople.co.uk", "greenpeople.com"],
        "search_hint": '"Green People" ("Sun Cream" OR "Cleanser" OR "Shampoo" OR "Quinoa")',
    },
    {
        "slug": "haeckels",
        "name": "Haeckels",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Haeckels", "Haeckels Margate"],
        "dtc_domains": ["haeckels.co.uk", "haeckels.com"],
        "search_hint": '"Bladderwrack" OR "Eco Marine" OR "Seaweed Bath" OR "Margate"',
    },
    {
        "slug": "inlight-beauty",
        "name": "Inlight Beauty",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Inlight Beauty", "Inlight", "Inlight Organic Skincare"],
        "dtc_domains": ["inlightbeauty.co.uk", "inlightbeauty.com"],
        "search_hint": '"Inlight" ("Night Balm" OR "Face Cleanser" OR "Line Softener")',
    },
    {
        "slug": "kiki-health",
        "name": "Kiki Health",
        "category": "Wellness & Supplements",
        "aliases": ["Kiki Health", "KIKI Health", "Kiki"],
        "dtc_domains": ["kiki-health.com", "kiki-health.co.uk"],
        "search_hint": '"Kiki Health" ("Shilajit" OR "Body Biotics" OR "Marine Collagen")',
    },
    {
        "slug": "kutis-skincare",
        "name": "Kutis Skincare",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Kutis Skincare", "Kutis"],
        "dtc_domains": ["kutisskincare.co.uk", "kutisskincare.com"],
        "search_hint": '"Kutis" ("Deodorant" OR "Lip Balm" OR "Skincare")',
    },
    {
        "slug": "lily-lolo",
        "name": "Lily Lolo",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Lily Lolo", "Lily Lolo Mineral Cosmetics"],
        "dtc_domains": ["lilylolo.co.uk", "lilylolo.com"],
        "search_hint": '"Lily Lolo" ("Mineral Foundation" OR "Mascara" OR "BB Cream")',
    },
    {
        "slug": "lolas-apothecary",
        "name": "Lola's Apothecary",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Lola's Apothecary", "Lolas Apothecary"],
        "dtc_domains": ["lolasapothecary.com", "lolasapothecary.co.uk"],
        "search_hint": '"Breath of Clarity" OR "Tranquil Isle" OR "Delicate Romance" OR "Sweet Lullaby"',
    },
    {
        "slug": "love-bites-only",
        "name": "Love Bites Only",
        "category": "Wellness & Supplements",
        "aliases": ["Love Bites Only"],
        "dtc_domains": ["lovebitesonly.co.uk", "lovebitesonly.com"],
        "search_hint": '"Love Bites Only"',
    },
    {
        "slug": "megi-wellness",
        "name": "Megi Wellness",
        "category": "Wellness & Supplements",
        "aliases": ["Megi Wellness", "Megi"],
        "dtc_domains": ["megiwellness.com", "megiwellness.co.uk"],
        "search_hint": '"Megi Wellness"',
    },
    {
        "slug": "mirror-water",
        "name": "Mirror Water",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Mirror Water", "MIRROR WATER"],
        "dtc_domains": ["mirrorwater.earth", "mirrorwater.co.uk"],
        "search_hint": '"Mirror Water" ("BUFF" OR "SMOOTH" OR "SOAK" OR "RUB")',
    },
    {
        "slug": "moa",
        "name": "MOA",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["MOA", "Magic Organic Apothecary", "MOA London"],
        "dtc_domains": ["moa.co.uk", "magicorganicapothecary.com"],
        "search_hint": '"Green Balm" OR "Magic Organic Apothecary" OR "Fortifying Green Bath Potion" OR "Hello Sunshine"',
        "strict_word_boundary": True,
        "required_context_regex": r"\b(magic\s+organic\s+apothecary|green\s+balm|fortifying\s+green|hello\s+sunshine|daily\s+cleansing\s+ritual|aphrodite\s+facial\s+oil|moa\s+the\s+green\s+balm|moa\s+fortifying)\b",
    },
    {
        "slug": "nathalie-bond",
        "name": "Nathalie Bond",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Nathalie Bond", "Nathalie Bond Organics"],
        "dtc_domains": ["nathaliebond.com", "nathaliebond.co.uk"],
        "search_hint": '"Unwind" OR "Sunshine" OR "Bloom" OR "Glow Face Oil" OR "Peppermint & Eucalyptus"',
    },
    {
        "slug": "neighbourhood-botanicals",
        "name": "Neighbourhood Botanicals",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Neighbourhood Botanicals"],
        "dtc_domains": ["neighbourhoodbotanicals.com", "neighbourhoodbotanicals.co.uk"],
        "search_hint": '"The Daily Glow" OR "Dream Dream Dream" OR "Acid Washed" OR "Big Strong Man"',
    },
    {
        "slug": "nini-organics",
        "name": "Nini Organics",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Nini Organics", "NINI Organics"],
        "dtc_domains": ["niniorganics.com", "niniorganics.co.uk"],
        "search_hint": '"Nini Organics" ("Crimson Beauty" OR "Moonlight" OR "Halo")',
    },
    {
        "slug": "nourish-london",
        "name": "Nourish London",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Nourish London", "Nourish Skin Range"],
        "dtc_domains": ["nourishskinrange.com", "nourishlondon.com", "nourishlondon.co.uk"],
        "search_hint": '"Argan Skin Renew" OR "Kale 3D Cleanse" OR "Probiotic Multi-Mineral" OR "Ceramide Moisture"',
    },
    {
        "slug": "olverum",
        "name": "Olverum",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Olverum"],
        "dtc_domains": ["olverum.com", "olverum.co.uk"],
        "search_hint": '"Olverum" ("Bath Oil" OR "Body Polish" OR "Pillow Mist")',
    },
    {
        "slug": "pai-skincare",
        "name": "Pai Skincare",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Pai Skincare", "Pai", "Pai Organic"],
        "dtc_domains": ["paiskincare.com", "paiskincare.co.uk"],
        "search_hint": '"Pai Skincare" ("Rosehip BioRegenerate" OR "Middlemist Seven")',
    },
    {
        "slug": "plum-and-ashby",
        "name": "Plum & Ashby",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Plum & Ashby", "Plum and Ashby"],
        "dtc_domains": ["plumandashby.co.uk", "plumandashby.com"],
        "search_hint": '"Seaweed & Samphire" OR "Vetiver & Lavender" OR "Wild Fig & Saffron" OR "Green Fig"',
    },
    {
        "slug": "sister-and-co",
        "name": "Sister & Co.",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Sister & Co.", "Sister & Co", "Sister and Co", "Sister & Co Skin Food"],
        "dtc_domains": ["sisterandcompany.com", "sisterandcompany.co.uk"],
        "search_hint": '"Raw Coconut" OR "Skin Food" OR "Charcoal Tooth Whitening" OR "Bath Soak"',
    },
    {
        "slug": "skin-sapiens",
        "name": "Skin Sapiens",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Skin Sapiens"],
        "dtc_domains": ["skinsapiens.com", "skinsapiens.co.uk"],
        "search_hint": '"Facial Cleansing Gel" OR "Baby Balm" OR "Skin Sapiens"',
    },
    {
        "slug": "sknfed",
        "name": "Sknfed",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Sknfed", "SKNFED"],
        "dtc_domains": ["sknfed.com", "sknfed.co.uk"],
        "search_hint": '"Sknfed" ("Body Butter" OR "Face Oil" OR "Coffee Scrub" OR "Whipped Shea")',
    },
    {
        "slug": "therapi",
        "name": "Therapi",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Therapi", "Therapi Honey Skincare"],
        "dtc_domains": ["therapi.com", "therapihoneyskincare.com"],
        "search_hint": '"Therapi" "Honey Skincare" OR "Propolis"',
    },
    {
        "slug": "this-is-silk",
        "name": "This Is Silk",
        "category": "Bath, Body & Apothecary",
        "aliases": ["This Is Silk"],
        "dtc_domains": ["thisissilk.com", "thisissilk.co.uk"],
        "search_hint": '"This Is Silk" ("Pillowcase" OR "Silk" OR "Hair")',
    },
    {
        "slug": "upcircle",
        "name": "UpCircle",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["UpCircle", "UpCircle Beauty", "Upcircle"],
        "dtc_domains": ["upcirclebeauty.com", "upcirclebeauty.co.uk"],
        "search_hint": '"UpCircle" ("Coffee" OR "Face Serum" OR "Cleansing Balm")',
    },
    {
        "slug": "votary",
        "name": "Votary",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Votary", "VOTARY", "Votary London"],
        "dtc_domains": ["votary.co.uk", "votary.com"],
        "search_hint": '"Super Seed" OR "Rose Geranium" OR "Clarifying Cleansing Oil" OR "Intense Night Oil"',
    },
    {
        "slug": "wild-nutrition",
        "name": "Wild Nutrition",
        "category": "Wellness & Supplements",
        "aliases": ["Wild Nutrition"],
        "dtc_domains": ["wildnutrition.com", "wildnutrition.co.uk"],
        "search_hint": '"Wild Nutrition" ("Food-Grown" OR "Magnesium" OR "Ashwagandha")',
    },
    {
        "slug": "wilder-botanics",
        "name": "Wilder Botanics",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Wilder Botanics"],
        "dtc_domains": ["wilderbotanics.com", "wilderbotanics.co.uk"],
        "search_hint": '"Wilder Botanics"',
    },
    {
        "slug": "yes",
        "name": "YES",
        "category": "Wellness & Supplements",
        "aliases": ["YES", "YES Organic", "YES Intimate", "The Yes Yes Company"],
        "dtc_domains": ["yesyesyes.org", "yesyesyes.co.uk"],
        "search_hint": '"YES" ("WB" OR "OB" OR "VM" OR "Organic Lubricant" OR "Intimate")',
        "strict_word_boundary": True,
        "required_context_regex": r"\b(yes\s+(wb|ob|vm|cleanse|butters)|intimate|lubricant|vaginal|applicator|organic\s+lubricant|yes\s+organic)\b",
    },
]

BRANDS_BY_SLUG = {b["slug"]: b for b in SME_BRANDS}

# Tier 1: Major & Prestige UK National Retailers (captured & tagged distinctly from Tier 2 Independents)
TIER_1_MAJOR_UK_RETAILERS = {
    "boots.com",
    "hollandandbarrett.com",
    "superdrug.com",
    "spacenk.com",
    "cultbeauty.co.uk",
    "cultbeauty.com",
    "lookfantastic.com",
    "selfridges.com",
    "johnlewis.com",
    "libertylondon.com",
    "harrods.com",
    "harveynichols.com",
    "fenwick.co.uk",
    "marksandspencer.com",
    "waitrose.com",
    "ocado.com",
    "sainsburys.co.uk",
    "tesco.com",
    "asda.com",
    "morrisons.com",
    "lloydspharmacy.com",
    "well.co.uk",
    "sephora.co.uk",
    "beautybay.com",
    "escentual.com",
    "feelunique.com",
    "asos.com",
    "next.co.uk",
}


def stockist_tier(domain: str) -> str:
    """Return 'Tier 1 (Major UK Retailer)' or 'Tier 2 (Independent Stockist)'."""
    d = (domain or "").lower().removeprefix("www.")
    for major in TIER_1_MAJOR_UK_RETAILERS:
        if d == major or d.endswith("." + major):
            return "Tier 1 (Major UK Retailer)"
    return "Tier 2 (Independent Stockist)"


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
    """Create a cross-store canonical product key for any of the 43 SME brands.

    Decodes HTML entities, strips file extensions (.html/.aspx), brand names/aliases,
    conjunctions ('and'/'&'/'plus'), sizes/weights/counts (e.g. 50ml, 100g, 60 caps),
    and punctuation so the same SKU across different UK retailers groups together.
    """
    low = html.unescape(title or "").lower()
    low = re.sub(r"\.(?:html?|aspx|php)$", "", low)
    low = low.replace("-", " ")
    # Remove anything after pipe '|' or ' – ' if it's an ingredient subtitle or brand suffix
    low = low.split("|")[0].split("–")[0].split("—")[0]

    # Strip brand aliases from start/anywhere
    for al in sorted(brand["aliases"], key=len, reverse=True):
        low = re.sub(r"\b" + re.escape(al.lower().replace("-", " ")) + r"\b", " ", low)

    # Strip sizes, weights, capsule/tablet counts, pack sizes, prices
    low = re.sub(r"£\d+(?:\.\d{2})?", " ", low)
    low = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ml|g|kg|oz|fl\s*oz|l|caps|capsules|tablets|tabs|sachets|pieces|pcs|pack|pk|m)\b", " ", low, flags=re.I)
    low = re.sub(r"\b(?:pack\s+of\s+\d+|size|default\s+title|standard|incl\s+vat|new|organic|natural|and|plus|with|for)\b", " ", low, flags=re.I)
    low = re.sub(r"[^a-z0-9]+", " ", low).strip()
    low = re.sub(r"\s+", "_", low)

    # Canonical family unification across UK stockist naming variations
    if brand["slug"] == "balmonds":
        if "skin_salvation" in low and "bath" not in low and "hand" not in low:
            return "skin_salvation"
        if "daily_moisturis" in low:
            return "daily_moisturiser"
        if "face_the_day" in low:
            return "face_the_day_spf30"
        if "top_to_toe" in low:
            return "top_to_toe_spf30"
        if "scalp_oil" in low:
            return "hair_scalp_oil"
        if "tea_tree" in low:
            return "tea_tree_balm"
        if "bath_body" in low or "hydrating_body_oil" in low or "bath_oil" in low:
            return "hydrating_body_oil"
        if "body_hand_hair_wash" in low or "shampoo_body_wash" in low:
            return "body_hand_hair_wash"
        if "omega_rich_facial_oil" in low or "intensive_facial_oil" in low:
            return "omega_facial_oil"
        if "omega_rich_cleansing_oil" in low:
            return "omega_cleansing_oil"
        if "rosehip_scar_oil" in low or "scar_stretch_mark_oil" in low:
            return "scar_stretch_mark_oil"
    elif brand["slug"] == "bare-biology":
        if "action_hero" in low or "super_hero" in low:
            return "action_heroes_omega_3"
        if "mums_bumps" in low or "mum_s_bumps" in low:
            return "mums_bumps_omega_3"
        if "vim_vigour" in low or "vegan_omega_3" in low:
            return "vim_vigour_vegan_omega_3"
        if "rise_shine" in low:
            return "rise_shine_omega_3_vitamin_d3"
        if "mindful" in low:
            return "mindful_omega_3"
        if "ready_rested" in low:
            return "ready_rested_magnesium"
        if "high_flyer" in low or "creatine_monohydrate" in low:
            return "high_flyer_creatine"
        if "fundamental" in low:
            return "fundamental_collagen"
        if "skinful" in low and "strawberry" in low:
            return "skinful_marine_collagen_vitamin_c"
        if "skinful" in low:
            return "skinful_pure_marine_collagen"
        if "beam" in low and "balance" in low:
            return "beam_balance_vitamin_d3_k2"
        if "life_soul" in low and "mini" in low:
            return "life_soul_omega_3_mini_capsules"
        if "life_soul" in low and ("liquid" in low or "daily_omega" in low and "cap" not in title.lower()):
            return "life_soul_liquid_omega_3"
        if "life_soul" in low:
            return "life_soul_omega_3_capsules"

    return low or f"{brand['slug']}_sku"
