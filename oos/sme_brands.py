"""Master registry of Verified Multi-Retailer UK Sweet-Spot Scale-Up Brands.

Every brand in this registry is a UK-founded / UK-headquartered Challenger or Independent Scale-Up
empirically verified across Major UK Retailers (`Space NK`, `Cult Beauty`, `Lookfantastic`,
`Naturisimo`, `Holland & Barrett`, `Boots`, `Superdrug`, `Sephora UK`) and paired with its official
DTC domain so we can verify "Out of Stock at Major Retailer vs. In Stock on DTC".
"""
import html
import re

SME_BRANDS: list[dict] = [
    # =========================================================================
    # TIER 1: VERIFIED IN 3 TO 4+ MAJOR UK RETAILER DIRECTORIES
    # =========================================================================
    {
        "slug": "oskia",
        "name": "Oskia",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Oskia", "OSKIA", "Oskia Skincare", "Oskia London"],
        "dtc_domains": ["oskiaskincare.com"],
        "verified_retailers": [
            "spacenk.com",
            "cultbeauty.co.uk",
            "lookfantastic.com",
            "ohmycream.co.uk",
            "facethefuture.co.uk",
            "harveynichols.com",
            "flannels.com",
            "houseoffraser.co.uk",
            "bathandunwind.com",
            "alyaka.com",
        ],
        "search_hint": '"Oskia" ("Renaissance Cleansing Gel" OR "Super 16" OR "Isotonic Hydra-Serum" OR "Micro-Exfoliating Balm")',
    },
    {
        "slug": "philip-kingsley",
        "name": "Philip Kingsley",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Philip Kingsley"],
        "dtc_domains": ["philipkingsley.co.uk", "philipkingsley.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Philip Kingsley" ("Elasticizer" OR "Flaky Itchy Scalp" OR "Bond Builder" OR "Density")',
    },
    {
        "slug": "111skin",
        "name": "111SKIN",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["111SKIN", "111 Skin", "111SKIN Harley Street"],
        "dtc_domains": ["111skin.co.uk", "111skin.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"111SKIN" ("Y Theorem" OR "Celestial Black Diamond" OR "Rose Gold Brightening" OR "Sub-Zero De-Puffing")',
    },
    {
        "slug": "artah",
        "name": "Artah",
        "category": "Wellness & Supplements",
        "aliases": ["Artah", "ARTAH"],
        "dtc_domains": ["artah.co"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com", "hollandandbarrett.com"],
        "search_hint": '"Artah" ("Cellular Hydration" OR "Metabolic Fix" OR "Enhanced NAD+" OR "Digestive Enzyme")',
    },
    {
        "slug": "emma-hardie",
        "name": "Emma Hardie",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Emma Hardie", "Emma Hardie Amazing Face"],
        "dtc_domains": ["emmahardie.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com", "boots.com"],
        "search_hint": '"Emma Hardie" ("Moringa Cleansing Balm" OR "Midas Touch" OR "Plump & Glow" OR "Lotus Flower")',
    },
    {
        "slug": "facegym",
        "name": "FACEGYM",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["FACEGYM", "FaceGym", "Face Gym"],
        "dtc_domains": ["uk.facegym.com", "facegym.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"FACEGYM" ("Hydro-Bound" OR "Youth Reformer" OR "Electro-Lite" OR "Liftwear")',
    },
    {
        "slug": "floral-street",
        "name": "Floral Street",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Floral Street", "Floral Street Fragrances"],
        "dtc_domains": ["floralstreet.com"],
        "verified_retailers": ["spacenk.com", "lookfantastic.com", "ohmycream.co.uk", "boots.com"],
        "search_hint": '"Floral Street" ("Wonderland Peony" OR "Arizona Bloom" OR "Wild Vanilla Orchid" OR "Sunflower Pop")',
    },
    {
        "slug": "hair-gain",
        "name": "Hair Gain",
        "category": "Wellness & Supplements",
        "aliases": ["Hair Gain", "HAIR GAIN"],
        "dtc_domains": ["hairgainnow.com"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Hair Gain" ("Capsules" OR "Hair Gummies" OR "Hair Mask" OR "Scalp Foam" OR "Peptide Puff")',
    },
    {
        "slug": "hair-by-sam-mcknight",
        "name": "Hair by Sam McKnight",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Hair by Sam McKnight", "Sam McKnight"],
        "dtc_domains": ["sammcknight.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"Sam McKnight" ("Cool Girl" OR "Modern Hairspray" OR "Happy Endings" OR "Lazy Girl")',
    },
    {
        "slug": "hello-sunday",
        "name": "Hello Sunday",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Hello Sunday", "Hello Sunday SPF"],
        "dtc_domains": ["hellosundayspf.com"],
        "verified_retailers": ["spacenk.com", "lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Hello Sunday" ("The One That" OR "The Everyday One" OR "The Mineral One" OR "SPF 50")',
    },
    {
        "slug": "isle-of-paradise",
        "name": "Isle of Paradise",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Isle of Paradise", "The Isle of Paradise"],
        "dtc_domains": ["theisleofparadise.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com", "boots.com"],
        "search_hint": '"Isle of Paradise" ("Self-Tanning Drops" OR "Self-Tanning Water" OR "Sunny Serum" OR "Express Mousse")',
    },
    {
        "slug": "joonbyrd",
        "name": "Joonbyrd",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Joonbyrd", "JOONBYRD"],
        "dtc_domains": ["joonbyrd.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"Joonbyrd" ("Sunday Sofa" OR "Little Love" OR "Moon Swim" OR "Daydreamer" OR "Violet Haze")',
    },
    {
        "slug": "luna-daily",
        "name": "Luna Daily",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Luna Daily", "LUNA Daily"],
        "dtc_domains": ["luna-daily.com"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Luna Daily" ("The Everywhere Wash" OR "The Everywhere Spray" OR "Hydrating Everything Oil")',
    },
    {
        "slug": "mz-skin",
        "name": "MZ SKIN",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["MZ SKIN", "MZ Skin"],
        "dtc_domains": ["mzskin.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"MZ SKIN" ("Soothe & Smooth" OR "Hydra-Bright" OR "Rest & Revive" OR "Replenish & Restore")',
    },
    {
        "slug": "mirror-water",
        "name": "Mirror Water",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Mirror Water", "MIRROR WATER"],
        "dtc_domains": ["mirrorwater.earth", "mirrorwater.co.uk"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "ohmycream.co.uk"],
        "search_hint": '"Mirror Water" ("BUFF" OR "SMOOTH" OR "SOAK" OR "RUB")',
    },
    {
        "slug": "neom-wellbeing",
        "name": "NEOM Wellbeing",
        "category": "Bath, Body & Apothecary",
        "aliases": ["NEOM Wellbeing", "NEOM", "Neom Organics", "NEOM Organics London"],
        "dtc_domains": ["neomwellbeing.com", "neomorganics.com"],
        "verified_retailers": ["spacenk.com", "lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"NEOM" ("Perfect Night\'s Sleep" OR "Real Luxury" OR "Happiness" OR "Magnesium Body Butter")',
    },
    {
        "slug": "sarah-chapman",
        "name": "Sarah Chapman",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Sarah Chapman", "Sarah Chapman Skinesis", "Skinesis"],
        "dtc_domains": ["sarahchapman.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"Sarah Chapman" ("Overnight Facial" OR "Ultimate Cleanse" OR "Skin Insurance" OR "Eye Recovery")',
    },
    {
        "slug": "tan-luxe",
        "name": "Tan-Luxe",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Tan-Luxe", "Tan Luxe", "TAN-LUXE"],
        "dtc_domains": ["tan-luxe.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com", "boots.com"],
        "search_hint": '"Tan-Luxe" ("The Face" OR "The Butter" OR "The Gradual" OR "Super Glow")',
    },
    {
        "slug": "the-nue-co",
        "name": "The Nue Co.",
        "category": "Wellness & Supplements",
        "aliases": ["The Nue Co.", "The Nue Co", "Nue Co"],
        "dtc_domains": ["uk.thenueco.com", "thenueco.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"The Nue Co" ("Supa_Thick" OR "Debloat+" OR "Prebiotic + Probiotic" OR "Forest Lungs" OR "Magnesium Ease")',
    },
    {
        "slug": "vieve",
        "name": "VIEVE",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["VIEVE", "Vieve", "Vieve Muse"],
        "dtc_domains": ["vieve.co.uk"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "hollandandbarrett.com"],
        "search_hint": '"VIEVE" ("Skin Nova" OR "Sunset Blush" OR "Modern Matte Lipstick" OR "Skin Dew")',
    },
    {
        "slug": "medik8",
        "name": "Medik8",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Medik8", "MEDIK8"],
        "dtc_domains": ["medik8.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"Medik8" ("Crystal Retinal" OR "C-Tetra" OR "Hydr8 B5" OR "Advanced Night Restore" OR "Press & Glow")',
    },
    {
        "slug": "the-inkey-list",
        "name": "The INKEY List",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["The INKEY List", "INKEY List", "The Inkey List"],
        "dtc_domains": ["uk.theinkeylist.com", "theinkeylist.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com", "boots.com"],
        "search_hint": '"The INKEY List" ("Oat Cleansing Balm" OR "Bio-Active Ceramide" OR "Omega Water Cream" OR "Hyaluronic Acid")',
    },

    # =========================================================================
    # TIER 2: VERIFIED IN 2+ MAJOR UK RETAILER DIRECTORIES (+ BOOTS / H&B)
    # =========================================================================
    {
        "slug": "aromatherapy-associates",
        "name": "Aromatherapy Associates",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Aromatherapy Associates", "Aromatherapy Associates London"],
        "dtc_domains": ["aromatherapyassociates.com"],
        "verified_retailers": ["spacenk.com", "lookfantastic.com", "cultbeauty.co.uk", "boots.com"],
        "search_hint": '"Aromatherapy Associates" ("Deep Relax" OR "De-Stress Mind" OR "Revive Morning" OR "Bath & Shower Oil")',
    },
    {
        "slug": "beautypro",
        "name": "BEAUTYPRO",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["BEAUTYPRO", "BeautyPro", "Beauty Pro"],
        "dtc_domains": ["beautypro.com"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"BEAUTYPRO" ("Retinol" OR "Collagen Mask" OR "Warming Eye Mask" OR "LED Wand")',
    },
    {
        "slug": "bleach-london",
        "name": "BLEACH London",
        "category": "Bath, Body & Apothecary",
        "aliases": ["BLEACH London", "Bleach London"],
        "dtc_domains": ["bleachlondon.com"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com", "boots.com", "superdrug.com"],
        "search_hint": '"BLEACH London" ("Reincarnation Mask" OR "Silver Shampoo" OR "Rosé" OR "Super Cool Colour")',
    },
    {
        "slug": "boucleme",
        "name": "Bouclème",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Bouclème", "Boucleme"],
        "dtc_domains": ["boucleme.co.uk", "boucleme.com"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com", "boots.com"],
        "search_hint": '"Bouclème" ("Curl Defining Gel" OR "Curl Cream" OR "Super Hold Styler" OR "Seal + Shield")',
    },
    {
        "slug": "byoma",
        "name": "BYOMA",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["BYOMA", "Byoma"],
        "dtc_domains": ["byoma.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk", "boots.com"],
        "search_hint": '"BYOMA" ("Moisturizing Gel Cream" OR "Creamy Jelly Cleanser" OR "Hydrating Serum" OR "Milky Oil Cleanser")',
    },
    {
        "slug": "dirtea",
        "name": "DIRTEA",
        "category": "Wellness & Supplements",
        "aliases": ["DIRTEA", "Dirtea"],
        "dtc_domains": ["dirteaworld.com"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"DIRTEA" ("Lion\'s Mane" OR "Cordyceps" OR "Tremella" OR "Reishi" OR "Mushroom Coffee" OR "Matcha")',
    },
    {
        "slug": "evolve",
        "name": "Evolve Organic Beauty",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Evolve Organic Beauty", "Evolve Beauty", "Evolve"],
        "dtc_domains": ["evolvebeauty.co.uk", "evolvebeauty.com"],
        "verified_retailers": ["ohmycream.co.uk", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Hyaluronic Serum 200" OR "Daily Renew" OR "Bio-Retinol"',
    },
    {
        "slug": "fussy",
        "name": "Fussy",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Fussy", "Fussy Deodorant", "Get Fussy"],
        "dtc_domains": ["getfussy.com"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Fussy" ("Refill" OR "Deodorant" OR "Wilderness" OR "Wavy Days" OR "Cloud Nine")',
    },
    {
        "slug": "hairburst",
        "name": "Hairburst",
        "category": "Wellness & Supplements",
        "aliases": ["Hairburst", "HAIRBURST"],
        "dtc_domains": ["hairburst.com"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com", "boots.com", "superdrug.com"],
        "search_hint": '"Hairburst" ("Chewable Hair Vitamins" OR "Longer Stronger Hair" OR "Volume & Growth Elixir")',
    },
    {
        "slug": "iconic-london",
        "name": "ICONIC LONDON",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["ICONIC LONDON", "Iconic London"],
        "dtc_domains": ["iconiclondoninc.com"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com", "boots.com"],
        "search_hint": '"ICONIC LONDON" ("Prep-Set-Glow" OR "Illuminator" OR "Underglow Blurring Primer" OR "Triple Threat Mascara")',
    },
    {
        "slug": "jo-loves",
        "name": "Jo Loves",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Jo Loves", "JO LOVES"],
        "dtc_domains": ["joloves.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk"],
        "search_hint": '"Jo Loves" ("Pomelo" OR "Jo by Jo Loves" OR "White Rose & Lemon Leaves" OR "Mango Thai Lime")',
    },
    {
        "slug": "kiki-health",
        "name": "Kiki Health",
        "category": "Wellness & Supplements",
        "aliases": ["Kiki Health", "KIKI Health", "Kiki"],
        "dtc_domains": ["kiki-health.com", "kiki-health.co.uk"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com"],
        "search_hint": '"Kiki Health" ("Shilajit" OR "Body Biotics" OR "Marine Collagen" OR "Ionic")',
    },
    {
        "slug": "laboratory-perfumes",
        "name": "Laboratory Perfumes",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Laboratory Perfumes"],
        "dtc_domains": ["laboratoryperfumes.com"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"Laboratory Perfumes" ("Amber" OR "Gorse" OR "Samphire" OR "Tonka" OR "Atlas")',
    },
    {
        "slug": "margaret-dabbs-london",
        "name": "Margaret Dabbs London",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Margaret Dabbs London", "Margaret Dabbs"],
        "dtc_domains": ["margaretdabbs.co.uk"],
        "verified_retailers": ["spacenk.com", "hollandandbarrett.com", "lookfantastic.com", "cultbeauty.co.uk"],
        "search_hint": '"Margaret Dabbs" ("Intensive Hydrating Foot Lotion" OR "Foot Hygiene Cream" OR "Exfoliating Foot Mousse")',
    },
    {
        "slug": "nailberry",
        "name": "Nailberry",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Nailberry", "NAILBERRY"],
        "dtc_domains": ["nailberry.co.uk"],
        "verified_retailers": ["spacenk.com", "lookfantastic.com"],
        "search_hint": '"Nailberry" ("L\'Oxygéné" OR "Oxygenated Nail Lacquer" OR "Fast Dry Gloss" OR "Acai Nail Elixir")',
    },
    {
        "slug": "noughty",
        "name": "Noughty",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Noughty", "Noughty Haircare"],
        "dtc_domains": ["lovenoughty.co.uk", "lovenoughty.com"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com", "boots.com", "superdrug.com"],
        "search_hint": '"Noughty" ("Wave Hello" OR "To The Rescue" OR "1 Hit Wonder" OR "Pea Complex")',
    },
    {
        "slug": "nursem",
        "name": "Nursem",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Nursem", "NURSEM"],
        "dtc_domains": ["nursem.co.uk"],
        "verified_retailers": ["spacenk.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Nursem" ("Caring Hand Cream" OR "Caring Hand Wash" OR "Ultra Caring Body Balm" OR "Caring Skin Fix")',
    },
    {
        "slug": "ordo",
        "name": "ORDO",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["ORDO", "Ordo", "Ordo Sonic"],
        "dtc_domains": ["ordolife.com"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"ORDO" ("Sonic+" OR "Hydro Sonic" OR "Complete Care Toothpaste" OR "Brush Heads")',
    },
    {
        "slug": "pai-skincare",
        "name": "Pai Skincare",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Pai Skincare", "Pai", "Pai Organic"],
        "dtc_domains": ["paiskincare.com", "paiskincare.co.uk"],
        "verified_retailers": ["cultbeauty.co.uk", "ohmycream.co.uk", "lookfantastic.com", "sephora.co.uk"],
        "search_hint": '"Pai Skincare" ("Rosehip BioRegenerate" OR "Middlemist Seven" OR "The Impossible Glow")',
    },
    {
        "slug": "revive-collagen",
        "name": "Revive Collagen",
        "category": "Wellness & Supplements",
        "aliases": ["Revive Collagen"],
        "dtc_domains": ["revivecollagen.com"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Revive Collagen" ("Enhanced Plus" OR "Hydrolysed Marine Collagen" OR "MenopauseMax" OR "PeriMenopause")',
    },
    {
        "slug": "rodial",
        "name": "Rodial",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Rodial", "RODIAL"],
        "dtc_domains": ["rodial.com"],
        "verified_retailers": ["spacenk.com", "lookfantastic.com", "boots.com"],
        "search_hint": '"Rodial" ("Dragon\'s Blood" OR "Bee Venom" OR "Banana Lowlighter" OR "Vit C Brightening")',
    },
    {
        "slug": "spectrum-collections",
        "name": "Spectrum Collections",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["Spectrum Collections", "Spectrum Brushes"],
        "dtc_domains": ["spectrumcollections.com"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com", "boots.com"],
        "search_hint": '"Spectrum Collections" ("Brush Set" OR "Sculpt" OR "Malachite" OR "Pantherine")',
    },
    {
        "slug": "this-works",
        "name": "This Works",
        "category": "Bath, Body & Apothecary",
        "aliases": ["This Works", "this works"],
        "dtc_domains": ["thisworks.com"],
        "verified_retailers": ["spacenk.com", "lookfantastic.com", "boots.com"],
        "search_hint": '"This Works" ("Deep Sleep Pillow Spray" OR "Morning Expert" OR "Skin Deep Dry Leg Oil" OR "Stress Check")',
    },
    {
        "slug": "votary",
        "name": "Votary",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Votary", "VOTARY", "Votary London"],
        "dtc_domains": ["votary.co.uk", "votary.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk"],
        "search_hint": '"Super Seed" OR "Rose Geranium" OR "Clarifying Cleansing Oil" OR "Intense Night Oil"',
    },
    {
        "slug": "vyrao",
        "name": "Vyrao",
        "category": "Bath, Body & Apothecary",
        "aliases": ["Vyrao", "VYRAO"],
        "dtc_domains": ["vyrao.com"],
        "verified_retailers": ["spacenk.com", "cultbeauty.co.uk"],
        "search_hint": '"Vyrao" ("Witchy Woo" OR "The Sixth" OR "Sun Rae" OR "I Am Verdant" OR "Magnetic 70")',
    },
    {
        "slug": "wild-nutrition",
        "name": "Wild Nutrition",
        "category": "Wellness & Supplements",
        "aliases": ["Wild Nutrition"],
        "dtc_domains": ["wildnutrition.com", "wildnutrition.co.uk"],
        "verified_retailers": ["ohmycream.co.uk", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Wild Nutrition" ("Food-Grown" OR "Magnesium" OR "Ashwagandha" OR "Perimenopause")',
    },
    {
        "slug": "zelens",
        "name": "Zelens",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Zelens", "ZELENS"],
        "dtc_domains": ["zelens.com"],
        "verified_retailers": ["cultbeauty.co.uk", "lookfantastic.com"],
        "search_hint": '"Zelens" ("Power D" OR "Tea Shot" OR "3T Complex" OR "Melatonin" OR "Youth Glow")',
    },
    {
        "slug": "zooki",
        "name": "Zooki",
        "category": "Wellness & Supplements",
        "aliases": ["Zooki", "YourZooki", "Your Zooki"],
        "dtc_domains": ["yourzooki.com"],
        "verified_retailers": ["lookfantastic.com", "hollandandbarrett.com", "boots.com"],
        "search_hint": '"Zooki" ("Vitamin C Zooki" OR "Collagen Zooki" OR "Glutathione" OR "Magnesium Zooki")',
    },

    # =========================================================================
    # TIER 3: ALREADY-TRACKED PHARMACY / ECO / WELLNESS SCALE-UPS
    # =========================================================================
    {
        "slug": "upcircle",
        "name": "UpCircle",
        "category": "Zero-Waste & Eco-Cosmetics",
        "aliases": ["UpCircle", "UpCircle Beauty", "Upcircle"],
        "dtc_domains": ["upcirclebeauty.com", "upcirclebeauty.co.uk"],
        "verified_retailers": ["hollandandbarrett.com", "boots.com", "superdrug.com"],
        "search_hint": '"UpCircle" ("Coffee" OR "Face Serum" OR "Cleansing Balm")',
    },
    {
        "slug": "balmonds",
        "name": "Balmonds",
        "category": "Skincare & Facial Botanicals",
        "aliases": ["Balmonds", "Balmonds Skincare", "Pure Potions"],
        "dtc_domains": ["balmonds.co.uk", "balmonds.com"],
        "verified_retailers": ["hollandandbarrett.com", "boots.com"],
        "search_hint": '"Skin Salvation" OR "Daily Moisturiser" OR "Cooling Cream"',
    },
    {
        "slug": "bare-biology",
        "name": "Bare Biology",
        "category": "Wellness & Supplements",
        "aliases": ["Bare Biology"],
        "dtc_domains": ["barebiology.com", "barebiology.co.uk"],
        "verified_retailers": ["ohmycream.co.uk", "planetorganic.com", "healf.com"],
        "search_hint": '"Skinful" OR "Life & Soul" OR "Omega 3" OR "Ready & Rested"',
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
    "ohmycream.co.uk",
    "sephora.co.uk",
    "planetorganic.com",
    "healf.com",
    "selfridges.com",
    "johnlewis.com",
    "libertylondon.com",
    "harrods.com",
    "harveynichols.com",
    "flannels.com",
    "houseoffraser.co.uk",
    "facethefuture.co.uk",
    "bathandunwind.com",
    "alyaka.com",
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
    "beautybay.com",
    "escentual.com",
    "feelunique.com",
    "asos.com",
    "next.co.uk",
}


ALL_DTC_DOMAINS = {
    d.lower().removeprefix("www.")
    for b in SME_BRANDS
    for d in b.get("dtc_domains", [])
}


def stockist_tier(domain: str) -> str:
    """Return 'Official Brand DTC (Master Catalog)', 'Tier 1 (Major UK Retailer)', or 'Tier 2 (Independent Stockist)'."""
    d = (domain or "").lower().removeprefix("www.")
    if d in ALL_DTC_DOMAINS:
        return "Official Brand DTC (Master Catalog)"
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

    # If strict word boundary is required, require word boundary + context
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
    """Create a cross-store canonical product key for any of the UK Scale-Up brands.

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
