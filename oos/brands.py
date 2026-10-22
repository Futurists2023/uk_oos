"""Brand name normalisation and review hints.

Normalisation is deliberately light: it only merges spellings that are
obviously identical (case, accents, punctuation, '&' vs 'and', 'Ltd').
Anything fuzzier is surfaced as a hint for manual review, never merged.
"""
import re
import unicodedata

_STRIP_SUFFIXES = re.compile(r"\b(ltd|limited|inc|llc)\b")

NOT_A_BRAND_WORDS = (
    "gift card", "giftcard", "gift voucher", "e-gift", "sample", "shipping", "delivery",
    "default", "vendor", "test", "bundle", "free gift", "insurance", "donation",
    "subscription", "route", "shipping protection",
)


def key(name: str) -> str:
    """Normalised comparison key for a brand name."""
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold().replace("&", " and ").replace("+", " and ")
    text = re.sub(r"[™®©]", "", text)
    text = _STRIP_SUFFIXES.sub(" ", text)
    return re.sub(r"[^a-z0-9]", "", text)


def store_name_keys(domain: str) -> set[str]:
    """Keys a store's own name might appear as (e.g. 'naturisimo', 'planetorganic')."""
    stem = domain.split(".")[0]
    return {key(stem), key(stem.replace("the", "", 1))}


def not_a_brand_hint(name: str, own_keys: set[str]) -> str:
    k = key(name)
    if not k:
        return "Blank vendor"
    if k in own_keys:
        return "Store's own label/name"
    low = name.casefold()
    for word in NOT_A_BRAND_WORDS:
        if word in low:
            return f"Contains '{word}'"
    return ""


def similar_keys(keys: list[str], min_len: int = 4) -> dict[str, list[str]]:
    """Map each key to other keys that start with it or contain it at a word edge.

    E.g. 'pai' <-> 'paiskincare', 'drhauschka' <-> 'drhauschkaskincare'.
    """
    out: dict[str, list[str]] = {}
    ordered = sorted(k for k in keys if len(k) >= min_len)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if not b.startswith(a):
                break  # sorted order: no later key can start with `a`
            out.setdefault(a, []).append(b)
            out.setdefault(b, []).append(a)
    return out
