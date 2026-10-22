"""Project configuration: seed stores and scraping settings."""

# Seed stores used for Phase 1 brand curation.
#   platform  - which reader collects the brand list (see scrape_seed_brands.py)
#   status    - "active" (default), "closed" or "rebranded"
#   weak_seed - kept in the list but flagged as low-signal
SEED_STORES = [
    {"domain": "contentbeautywellbeing.com", "platform": "shopify"},
    {"domain": "naturisimo.com", "platform": "shopify"},
    {"domain": "mypure.co.uk", "platform": "shopify"},
    {"domain": "thecleanbeautyclub.co.uk", "platform": "shopify", "weak_seed": True,
     "note": "Only ~15 products / 3 brands - looks like a subscription box, not a multi-brand retailer."},
    {"domain": "planetorganic.com", "platform": "shopify",
     "note": "Grocery + beauty retailer - expect many food/drink vendors."},
    {"domain": "revital.co.uk", "platform": "none", "status": "closed",
     "note": "Domain redirects to a Shopify 'Coming Soon' placeholder (checked 17 Oct 2026)."},
    {"domain": "gloworganic.co.uk", "platform": "woocommerce",
     "note": "Brand read from product tags named 'Brand_<name>'."},
    {"domain": "lovelula.com", "platform": "none", "status": "closed",
     "note": "Cloudflare DNS resolution error / TLS failure - site offline (checked 17 Oct 2026)."},
    {"domain": "plasticfreedom.co.uk", "platform": "shopify"},
    {"domain": "baldwins.co.uk", "platform": "shopify"},
    {"domain": "allnaturalme.co.uk", "platform": "shopify"},
    {"domain": "ohmycream.co.uk", "platform": "shopify"},
    {"domain": "liveinthelight.co.uk", "platform": "shopify"},
    {"domain": "blommabeauty.com", "platform": "shopify"},
    {"domain": "victoriahealth.com", "platform": "bigcommerce",
     "note": "BigCommerce - brand list read from the /brands/ page (no product counts)."},
    {"domain": "wearthlondon.com", "platform": "ziracle", "status": "rebranded",
     "successor": "ziracle.com",
     "note": "'Wearth is now Ziracle' - brands read from ziracle.com/brands/ (no product counts). "
             "Ziracle also sells food, style and home brands."},
    {"domain": "justbeyoutiful.co.uk", "platform": "shopify"},
    {"domain": "ethicalhouse.co.uk", "platform": "shopify"},
]

# Polite scraping settings.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
REQUEST_TIMEOUT = 30          # seconds
DELAY_BETWEEN_REQUESTS = 1.5  # seconds between page requests to the same store
MAX_RETRIES = 4
