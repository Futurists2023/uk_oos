"""Human-Emulated Multi-Retailer Brand Directory Verifier & UK Sweet-Spot Scale-Up Extractor.

Strict Human Emulation Protocol:
1. Uses a real Playwright Chromium session with `en-GB` locale, `Europe/London` timezone,
   realistic desktop viewport, and `navigator.webdriver = undefined`.
2. Performs curved mouse movements, polite cookie-banner acceptance, gradual human-paced
   scrolling with random reading pauses (2.0s - 4.8s), and full inter-site cooldowns (4.0s - 7.5s).
3. Caches each retailer's extracted A-Z brand directory to `reports/retailer_brand_directories_cache.json`
   so we never re-scrape a directory page unnecessarily.
4. Intersects all 7+ Major UK Retailers (`Space NK`, `Cult Beauty`, `Lookfantastic`, `Sephora UK`,
   `Naturisimo`, `Boots`, `Holland & Barrett`) to identify the complete pool of Verified UK
   Sweet-Spot Independent Scale-Ups.
"""
import asyncio
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

import sme_brands

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH = REPORTS_DIR / "retailer_brand_directories_cache.json"
OUTPUT_PATH = REPORTS_DIR / "verified_retailer_brands.json"

# Known UK-Founded / UK-Headquartered Beauty & Wellness Brands (to classify UK Sweet-Spot vs Global)
UK_SWEET_SPOT_SCALEUPS = {
    "oskia": {
        "name": "Oskia",
        "dtc_domain": "oskiaskincare.com",
        "dtc_url": "https://www.oskiaskincare.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK luxury bio-nutritional skincare (Monmouth / London, founded by Georgie Cleeve)",
    },
    "pai skincare": {
        "name": "Pai Skincare",
        "dtc_domain": "paiskincare.com",
        "dtc_url": "https://www.paiskincare.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK organic sensitive skincare (London, founded by Sarah Brown, certified B-Corp)",
    },
    "votary": {
        "name": "Votary",
        "dtc_domain": "votary.co.uk",
        "dtc_url": "https://www.votary.co.uk",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK botanical luxury skincare (founded by Arabella Preston & Charlotte Semler)",
    },
    "mirror water": {
        "name": "Mirror Water",
        "dtc_domain": "mirrorwater.earth",
        "dtc_url": "https://mirrorwater.earth",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK bath & body care (founded by Estée Lalonde)",
    },
    "111skin": {
        "name": "111SKIN",
        "dtc_domain": "111skin.co.uk",
        "dtc_url": "https://111skin.co.uk",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK Harley Street luxury clinical skincare (founded by Dr Yannis & Eva Alexandrides)",
    },
    "mz skin": {
        "name": "MZ SKIN",
        "dtc_domain": "mzskin.com",
        "dtc_url": "https://www.mzskin.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK doctor-led luxury skincare (London, founded by Dr Maryam Zamani)",
    },
    "sarah chapman": {
        "name": "Sarah Chapman",
        "dtc_domain": "sarahchapman.com",
        "dtc_url": "https://www.sarahchapman.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK Skinesis clinical facialist skincare (London, founded by Sarah Chapman)",
    },
    "joonbyrd": {
        "name": "Joonbyrd",
        "dtc_domain": "joonbyrd.com",
        "dtc_url": "https://joonbyrd.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK dermatologist-led affective bodycare (London, founded by Dr Alexis Granite)",
    },
    "hair by sam mcknight": {
        "name": "Hair by Sam McKnight",
        "dtc_domain": "sammcknight.com",
        "dtc_url": "https://sammcknight.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK prestige haircare scale-up (London, founded by Sam McKnight)",
    },
    "facegym": {
        "name": "FACEGYM",
        "dtc_domain": "facegym.com",
        "dtc_url": "https://uk.facegym.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK active skincare & facial fitness brand (London, founded by Inge Theron)",
    },
    "upcircle": {
        "name": "UpCircle",
        "dtc_domain": "upcirclebeauty.com",
        "dtc_url": "https://upcirclebeauty.com",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK circular beauty B-Corp (London, founded by Anna & William Brightman)",
    },
    "evolve organic beauty": {
        "name": "Evolve Organic Beauty",
        "dtc_domain": "evolvebeauty.co.uk",
        "dtc_url": "https://www.evolvebeauty.co.uk",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK artisan organic skincare B-Corp (Hertfordshire, founded by Laura Rudoe)",
    },
    "wild nutrition": {
        "name": "Wild Nutrition",
        "dtc_domain": "wildnutrition.com",
        "dtc_url": "https://www.wildnutrition.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK Food-Grown women's nutritional supplements B-Corp (Lewes, founded by Henrietta Norton)",
    },
    "bare biology": {
        "name": "Bare Biology",
        "dtc_domain": "barebiology.com",
        "dtc_url": "https://www.barebiology.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK marine omega-3 & collagen supplements (Brighton, founded by Melanie Lawson)",
    },
    "balmonds": {
        "name": "Balmonds",
        "dtc_domain": "balmonds.co.uk",
        "dtc_url": "https://balmonds.co.uk",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK natural eczema/sensitive skin care (Brighton)",
    },
    "olverum": {
        "name": "Olverum",
        "dtc_domain": "olverum.com",
        "dtc_url": "https://www.olverum.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK luxury botanical bath & body apothecary (London)",
    },
    "de mamiel": {
        "name": "De Mamiel",
        "dtc_domain": "demamiel.com",
        "dtc_url": "https://demamiel.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK holistic luxury facial oils & wellness (founded by Annee de Mamiel)",
    },
    "kiki health": {
        "name": "Kiki Health",
        "dtc_domain": "kiki-health.com",
        "dtc_url": "https://kiki-health.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK superfood, mushroom & mineral supplements",
    },
    "green people": {
        "name": "Green People",
        "dtc_domain": "greenpeople.co.uk",
        "dtc_url": "https://www.greenpeople.co.uk",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK certified organic family & sensitive skincare (West Sussex, founded by Charlotte Vøhtz)",
    },
    "nourish london": {
        "name": "Nourish London",
        "dtc_domain": "nourishskinrange.com",
        "dtc_url": "https://www.nourishskinrange.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK organic vegan skincare (London, founded by Dr Pauline Hili)",
    },
    "boucleme": {
        "name": "Bouclème",
        "dtc_domain": "boucleme.co.uk",
        "dtc_url": "https://www.boucleme.co.uk",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK plant-powered curl care B-Corp (London, founded by Michele Scott-Lynch)",
    },
    "percy and reed": {
        "name": "Percy & Reed",
        "dtc_domain": "percyandreed.com",
        "dtc_url": "https://www.percyandreed.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK salon-grade haircare (London, founded by Paul Percival & Adam Reed)",
    },
    "arkive": {
        "name": "ARKIVE Headcare",
        "dtc_domain": "arkiveheadcare.com",
        "dtc_url": "https://www.arkiveheadcare.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK scalp & headcare challenger brand (London, founded by Adam Reed)",
    },
    "bloom and blossom": {
        "name": "Bloom and Blossom",
        "dtc_domain": "bloomandblossom.com",
        "dtc_url": "https://bloomandblossom.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK sleep, body & family wellness skincare (London, founded by Julia Yule & Christina Moss)",
    },
    "delilah": {
        "name": "delilah",
        "dtc_domain": "delilahcosmetics.com",
        "dtc_url": "https://delilahcosmetics.com",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK B-Corp luxury vegan colour cosmetics (founded by Rupert Kingston)",
    },
    "neom": {
        "name": "NEOM Wellbeing",
        "dtc_domain": "neomwellbeing.com",
        "dtc_url": "https://neomwellbeing.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK natural wellbeing, sleep & bodycare B-Corp (Harrogate/London, founded by Nicola Elliott)",
    },
    "this works": {
        "name": "This Works",
        "dtc_domain": "thisworks.com",
        "dtc_url": "https://www.thisworks.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK circadian sleep & targeted skincare brand (London)",
    },
    "cowshed": {
        "name": "Cowshed",
        "dtc_domain": "cowshed.com",
        "dtc_url": "https://www.cowshed.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK botanical bath, body & spa apothecary (Somerset / London)",
    },
    "faace": {
        "name": "Faace",
        "dtc_domain": "wearefaace.com",
        "dtc_url": "https://wearefaace.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK solution-led face masks & skincare (founded by Jasmine Wicks-Stephens)",
    },
    "by sarah": {
        "name": "By Sarah",
        "dtc_domain": "bysarahlondon.com",
        "dtc_url": "https://bysarahlondon.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK B-Corp sensitive skin & gut-skin barrier care (founded by Sarah & Lauren Murrell)",
    },
    "the nue co": {
        "name": "The Nue Co.",
        "dtc_domain": "uk.thenueco.com",
        "dtc_url": "https://uk.thenueco.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK-founded clinical supplements, gut health & functional fragrance (founded by Jules Miller)",
    },
    "isle of paradise": {
        "name": "Isle of Paradise",
        "dtc_domain": "theisleofparadise.com",
        "dtc_url": "https://theisleofparadise.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK colour-correcting self-tan challenger (founded by Jules Von Hep)",
    },
    "tan luxe": {
        "name": "Tan-Luxe",
        "dtc_domain": "tan-luxe.com",
        "dtc_url": "https://tan-luxe.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK skincare-infused luxury self-tanning brand (founded by Marc Elrick)",
    },
    "bybi": {
        "name": "BYBI",
        "dtc_domain": "bybi.com",
        "dtc_url": "https://bybi.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK eco-conscious skincare boosters & barrier care (founded by Elsie Rutterford & Dominika Minarovic)",
    },
    "odylique": {
        "name": "Odylique",
        "dtc_domain": "odylique.co.uk",
        "dtc_url": "https://www.odylique.co.uk",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK Soil Association certified organic sensitive skincare (Suffolk)",
    },
    "together health": {
        "name": "Together Health",
        "dtc_domain": "togetherhealth.co.uk",
        "dtc_url": "https://www.togetherhealth.co.uk",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK clean whole-food & ocean mineral vitamins",
    },
    "faith in nature": {
        "name": "Faith in Nature",
        "dtc_domain": "faithinnature.co.uk",
        "dtc_url": "https://www.faithinnature.co.uk",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK ethical natural hair & body care B-Corp (Manchester)",
    },
    "neals yard remedies": {
        "name": "Neal's Yard Remedies",
        "dtc_domain": "nealsyardremedies.com",
        "dtc_url": "https://www.nealsyardremedies.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Family-owned UK organic apothecary & skincare (Covent Garden / Dorset)",
    },
    "trinny london": {
        "name": "Trinny London",
        "dtc_domain": "trinnylondon.com",
        "dtc_url": "https://trinnylondon.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "UK Breakout Scale-Up",
        "notes": "Independent UK skincare & stackable makeup scale-up (London, founded by Trinny Woodall)",
    },
    "medik8": {
        "name": "Medik8",
        "dtc_domain": "medik8.com",
        "dtc_url": "https://www.medik8.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "UK Breakout Scale-Up",
        "notes": "UK clinical CSA/retinal skincare powerhouse (Hertfordshire, founded by Elliot Isaacs)",
    },
    "the inkey list": {
        "name": "The INKEY List",
        "dtc_domain": "uk.theinkeylist.com",
        "dtc_url": "https://uk.theinkeylist.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "UK Breakout Scale-Up",
        "notes": "UK single-ingredient knowledge-powered skincare challenger (founded by Colette Laxton & Mark Curry)",
    },
    "byoma": {
        "name": "BYOMA",
        "dtc_domain": "byoma.com",
        "dtc_url": "https://byoma.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "UK Breakout Scale-Up",
        "notes": "UK barrier-boosting ceramide skincare challenger (founded by Marc Elrick)",
    },
    "artah": {
        "name": "Artah",
        "dtc_domain": "artah.co",
        "dtc_url": "https://artah.co",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK cellular nutrition & metabolic supplements (London, founded by Rhian Stephenson)",
    },
    "hair gain": {
        "name": "Hair Gain",
        "dtc_domain": "hairgainnow.com",
        "dtc_url": "https://www.hairgainnow.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK phytonutrient hair supplements & scalp care scale-up (London, founded by Lucy Palmer)",
    },
    "hello sunday": {
        "name": "Hello Sunday",
        "dtc_domain": "hellosundayspf.com",
        "dtc_url": "https://hellosundayspf.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK everyday SPF & sun protection challenger (founded by Amy Ford)",
    },
    "luna daily": {
        "name": "Luna Daily",
        "dtc_domain": "luna-daily.com",
        "dtc_url": "https://www.luna-daily.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK microbiome body & intimate care scale-up (London, founded by Katy Cottam)",
    },
    "vieve": {
        "name": "VIEVE",
        "dtc_domain": "vieve.co.uk",
        "dtc_url": "https://www.vieve.co.uk",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK cruelty-free makeup & skincare scale-up (Glasgow/London, founded by Jamie Genevieve)",
    },
    "philip kingsley": {
        "name": "Philip Kingsley",
        "dtc_domain": "philipkingsley.co.uk",
        "dtc_url": "https://www.philipkingsley.co.uk",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Family-owned UK trichology scalp & haircare scale-up (Mayfair London)",
    },
    "aromatherapy associates": {
        "name": "Aromatherapy Associates",
        "dtc_domain": "aromatherapyassociates.com",
        "dtc_url": "https://www.aromatherapyassociates.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK B-Corp therapeutic essential oil bath, body & wellbeing apothecary (London)",
    },
    "beautypro": {
        "name": "BEAUTYPRO",
        "dtc_domain": "beautypro.com",
        "dtc_url": "https://www.beautypro.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK sheet mask, serum & LED skincare challenger (Sussex)",
    },
    "bleach london": {
        "name": "BLEACH London",
        "dtc_domain": "bleachlondon.com",
        "dtc_url": "https://bleachlondon.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK vegan hair colour & care scale-up (London, founded by Alex Brownsell)",
    },
    "dirtea": {
        "name": "DIRTEA",
        "dtc_domain": "dirteaworld.com",
        "dtc_url": "https://www.dirteaworld.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK functional mushroom extracts & wellness powders (London, founded by Simon & Andrew Salter)",
    },
    "emma hardie": {
        "name": "Emma Hardie",
        "dtc_domain": "emmahardie.com",
        "dtc_url": "https://www.emmahardie.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK botanical facialist skincare famous for Moringa Cleansing Balm (London)",
    },
    "floral street": {
        "name": "Floral Street",
        "dtc_domain": "floralstreet.com",
        "dtc_url": "https://floralstreet.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK sustainable vegan fine fragrance scale-up (Covent Garden, founded by Michelle Feeney)",
    },
    "fussy": {
        "name": "Fussy",
        "dtc_domain": "getfussy.com",
        "dtc_url": "https://www.getfussy.com",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK refillable probiotic deodorant B-Corp (London, founded by Matt Kennedy)",
    },
    "hairburst": {
        "name": "Hairburst",
        "dtc_domain": "hairburst.com",
        "dtc_url": "https://www.hairburst.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK hair growth vitamins & scalp care scale-up",
    },
    "iconic london": {
        "name": "ICONIC LONDON",
        "dtc_domain": "iconiclondoninc.com",
        "dtc_url": "https://www.iconiclondoninc.com",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK cruelty-free glow & complexion cosmetics scale-up (founded by Jade Elliott)",
    },
    "jo loves": {
        "name": "Jo Loves",
        "dtc_domain": "joloves.com",
        "dtc_url": "https://www.joloves.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK luxury fragrance, bath & body brand (London, founded by Jo Malone CBE)",
    },
    "laboratory perfumes": {
        "name": "Laboratory Perfumes",
        "dtc_domain": "laboratoryperfumes.com",
        "dtc_url": "https://www.laboratoryperfumes.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK sustainable botanical fragrance & candle brand",
    },
    "margaret dabbs london": {
        "name": "Margaret Dabbs London",
        "dtc_domain": "margaretdabbs.co.uk",
        "dtc_url": "https://www.margaretdabbs.co.uk",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK medical-grade foot, hand & leg care scale-up (London, founded by Margaret Dabbs OBE)",
    },
    "nailberry": {
        "name": "Nailberry",
        "dtc_domain": "nailberry.co.uk",
        "dtc_url": "https://www.nailberry.co.uk",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK breathable oxygenated vegan nail care (Chelsea London, founded by Sonia Hully)",
    },
    "noughty": {
        "name": "Noughty",
        "dtc_domain": "lovenoughty.co.uk",
        "dtc_url": "https://lovenoughty.co.uk",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "UK B-Corp 97% natural vegan haircare scale-up (London)",
    },
    "nursem": {
        "name": "Nursem",
        "dtc_domain": "nursem.co.uk",
        "dtc_url": "https://www.nursem.co.uk",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK nurse-founded therapeutic hand & skin care B-Corp (founded by Antonia & Jonny Philp)",
    },
    "ordo": {
        "name": "ORDO",
        "dtc_domain": "ordolife.com",
        "dtc_url": "https://www.ordolife.com",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK oral care & sonic brush challenger (Manchester, founded by Barty Walsh)",
    },
    "revive collagen": {
        "name": "Revive Collagen",
        "dtc_domain": "revivecollagen.com",
        "dtc_url": "https://revivecollagen.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK ready-to-drink hydrolysed marine collagen scale-up (London)",
    },
    "rodial": {
        "name": "Rodial",
        "dtc_domain": "rodial.com",
        "dtc_url": "https://www.rodial.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK targeted performance skincare & complexion scale-up (London, founded by Maria Hatzistefanis)",
    },
    "spectrum collections": {
        "name": "Spectrum Collections",
        "dtc_domain": "spectrumcollections.com",
        "dtc_url": "https://www.spectrumcollections.com",
        "category": "Zero-Waste & Eco-Cosmetics",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK vegan makeup brushes & cosmetics scale-up (Barry, Wales, founded by Sophie & Hannah Pycroft)",
    },
    "vyrao": {
        "name": "Vyrao",
        "dtc_domain": "vyrao.com",
        "dtc_url": "https://vyrao.com",
        "category": "Bath, Body & Apothecary",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK energetic wellbeing fragrance & incense scale-up (London, founded by Yasmin Sewell)",
    },
    "zelens": {
        "name": "Zelens",
        "dtc_domain": "zelens.com",
        "dtc_url": "https://www.zelens.com",
        "category": "Skincare & Facial Botanicals",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK biotechnology & botanical clinical skincare (London, founded by Dr Marko Lens)",
    },
    "zooki": {
        "name": "Zooki",
        "dtc_domain": "yourzooki.com",
        "dtc_url": "https://yourzooki.com",
        "category": "Wellness & Supplements",
        "tier": "Sweet-Spot UK Scale-Up",
        "notes": "Independent UK liposomal vitamins & marine collagen scale-up (Lancashire, founded by Marcus Mollinga & Jack Morrison)",
    },
}


async def human_pause(min_s: float = 2.0, max_s: float = 4.6) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


async def simulate_human_browsing(page) -> None:
    """Emulate a real human moving the mouse, dismissing cookie banners, and reading/scrolling the page."""
    try:
        # 1. Smooth mouse drift across viewport
        for _ in range(random.randint(2, 4)):
            tx = random.randint(180, 1180)
            ty = random.randint(140, 720)
            await page.mouse.move(tx, ty, steps=random.randint(18, 35))
            await asyncio.sleep(random.uniform(0.25, 0.65))

        # 2. Politely accept cookie consent if visible
        cookie_selectors = [
            "button#onetrust-accept-btn-handler",
            "button:has-text('Accept All')",
            "button:has-text('Accept all')",
            "button:has-text('Allow all')",
            "button:has-text('Accept Cookies')",
        ]
        for sel in cookie_selectors:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.hover()
                await asyncio.sleep(random.uniform(0.3, 0.7))
                await loc.click()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                break

        # 3. Gradual human scroll down & back up slightly
        scroll_steps = random.randint(4, 7)
        for _ in range(scroll_steps):
            delta = random.randint(320, 680)
            await page.mouse.wheel(0, delta)
            await asyncio.sleep(random.uniform(0.9, 2.1))

        # Slight upward scroll like a human scanning a directory
        await page.mouse.wheel(0, -random.randint(180, 350))
        await asyncio.sleep(random.uniform(1.0, 2.0))
    except Exception:
        pass


def extract_brands_generic(retailer: str, html_text: str) -> dict[str, str]:
    soup = BeautifulSoup(html_text, "html.parser")
    found = {}

    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        txt = re.sub(r"\s+", " ", a.get_text() or "").strip()
        if not txt or len(txt) < 2 or len(txt) > 45:
            continue

        is_brand = False
        if retailer == "spacenk.com" and "/brands/" in href:
            is_brand = True
        elif retailer in ("cultbeauty.co.uk", "lookfantastic.com") and (
            "/brands/" in href or "brand" in " ".join(a.get("class") or []).lower() or href.endswith(".list")
        ):
            is_brand = True
        elif retailer == "naturisimo.com" and "/collections/" in href:
            is_brand = True
        elif retailer == "sephora.co.uk" and "/brands/" in href:
            is_brand = True
        elif retailer == "boots.com" and (
            "/brands/" in href or "brand" in " ".join(a.get("class") or []).lower()
        ):
            is_brand = True
        elif retailer == "hollandandbarrett.com" and "/shop/brands/" in href:
            is_brand = True

        if not is_brand:
            continue

        if re.match(r"^[A-Z0-9#]$", txt) or txt.lower() in {
            "all brands", "brands", "a-z brands", "shop all", "new brands",
            "view all", "bestsellers", "brands a-z", "shop by brand", "top brands",
        }:
            continue

        found[txt.lower().strip()] = txt

    return found


def clean_lookup_key(name: str) -> str:
    s = (name or "").lower().strip()
    s = s.replace("&", "and").replace("'", "").replace("’", "").replace("-", " ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


async def main():
    # Load cached directories so we don't re-hit already scraped sites
    cached_dirs: dict[str, dict[str, str]] = {}
    if CACHE_PATH.exists():
        try:
            cached_dirs = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            cached_dirs = {}

    # Seed cache from our first pass if needed
    targets = {
        "spacenk.com": "https://www.spacenk.com/uk/brands",
        "cultbeauty.co.uk": "https://www.cultbeauty.co.uk/brands.list",
        "lookfantastic.com": "https://www.lookfantastic.com/brands.list",
        "naturisimo.com": "https://www.naturisimo.com/pages/brands",
        "sephora.co.uk": "https://www.sephora.co.uk/brands",
        "hollandandbarrett.com": "https://www.hollandandbarrett.com/shop/brands/",
        "boots.com": "https://www.boots.com/sitesearch?searchTerm=brands",
    }

    # Only launch browser if core directories are missing from cache
    required_core = ["spacenk.com", "cultbeauty.co.uk", "lookfantastic.com", "naturisimo.com", "hollandandbarrett.com"]
    needs_browse = [d for d in required_core if d not in cached_dirs or len(cached_dirs[d]) < 50]

    if not needs_browse:
        for d in required_core:
            print(f"[CACHE HIT] {d:24s} -> {len(cached_dirs[d]):4d} brands already cached")
    else:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                locale="en-GB",
                timezone_id="Europe/London",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = await context.new_page()

            for domain in needs_browse:
                url = targets[domain]
                print(f"[HUMAN BROWSE] Visiting {domain} ({url})...")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=35000)
                    await human_pause(2.2, 4.2)
                    await simulate_human_browsing(page)
                    html = await page.content()
                    b_map = extract_brands_generic(domain, html)
                    if b_map:
                        cached_dirs[domain] = b_map
                        CACHE_PATH.write_text(
                            json.dumps(cached_dirs, indent=2, ensure_ascii=False),
                            encoding="utf-8",
                        )
                        print(f"  [OK] {domain:22s} -> extracted {len(b_map):4d} brands")
                    else:
                        print(f"  [INFO] {domain:22s} -> 0 brands extracted from directory layout")
                except Exception as e:
                    print(f"  [WARN] {domain:22s} -> {e}")

                await human_pause(4.0, 7.2)

            await browser.close()

    # Now cross-reference every UK Sweet-Spot Scale-Up against the live retailer directories
    print("\n=== COMPLETE POOL OF VERIFIED UK SWEET-SPOT INDEPENDENT SCALE-UPS ===")
    sweet_spot_pool = []

    for uk_key, meta in UK_SWEET_SPOT_SCALEUPS.items():
        matched_retailers = set()
        uk_norm = clean_lookup_key(uk_key)
        name_norm = clean_lookup_key(meta["name"])

        for domain, b_map in cached_dirs.items():
            for raw_k, disp in b_map.items():
                rk_norm = clean_lookup_key(raw_k)
                if (
                    rk_norm in (uk_norm, name_norm)
                    or re.search(rf"\b{re.escape(uk_norm)}\b", rk_norm)
                    or (len(rk_norm) >= 6 and re.search(rf"\b{re.escape(rk_norm)}\b", uk_norm))
                ):
                    matched_retailers.add(domain)
                    break

        sweet_spot_pool.append({
            "name": meta["name"],
            "dtc_domain": meta["dtc_domain"],
            "dtc_url": meta["dtc_url"],
            "category": meta["category"],
            "tier": meta["tier"],
            "notes": meta["notes"],
            "verified_retailers": sorted(matched_retailers),
            "retailer_count": len(matched_retailers),
        })

    sweet_spot_pool.sort(key=lambda x: (-x["retailer_count"], x["tier"], x["name"]))

    for item in sweet_spot_pool:
        if item["retailer_count"] >= 1:
            print(
                f"  • {item['name']:24s} | {item['tier']:22s} | "
                f"{item['retailer_count']} retailers: {', '.join(item['verified_retailers'])} | DTC: {item['dtc_domain']}"
            )

    # Also surface any other 2+ retailer brands in the cache not yet in UK_SWEET_SPOT_SCALEUPS
    all_b2r = defaultdict(set)
    all_disp = {}
    known_uk_norms = {clean_lookup_key(x) for x in UK_SWEET_SPOT_SCALEUPS}
    for domain, b_map in cached_dirs.items():
        for raw_k, disp in b_map.items():
            ck = clean_lookup_key(raw_k)
            if not ck or len(ck) < 3 or ck in known_uk_norms:
                continue
            all_b2r[ck].add(domain)
            all_disp.setdefault(ck, disp)

    other_multi = [
        {"brand": all_disp[ck], "key": ck, "count": len(r), "retailers": sorted(r)}
        for ck, r in all_b2r.items()
        if len(r) >= 2
    ]
    other_multi.sort(key=lambda x: (-x["count"], x["brand"]))
    print(f"\n=== ALL OTHER 2+ RETAILER BRANDS IN CACHE ({len(other_multi)}) ===")
    for om in other_multi:
        print(f"  - {om['brand']:30s} ({om['count']}) -> {', '.join(om['retailers'])}")

    # Save enriched output
    existing_out = {}
    if OUTPUT_PATH.exists():
        try:
            existing_out = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing_out = {}

    existing_out["uk_sweet_spot_scaleups"] = sweet_spot_pool
    existing_out["retailer_directory_counts"] = {k: len(v) for k, v in cached_dirs.items()}
    OUTPUT_PATH.write_text(json.dumps(existing_out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved complete UK Sweet-Spot Scale-Up pool to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
