from rapidfuzz import process, fuzz
from app.catalog import PRODUCT_CATALOG

PRODUCT_SYNONYMS: dict[str, str] = {
    "laddoo": "laddu",
    "ladoo": "laddu",
    "ladu": "laddu",
    "mottichoor": "laddu",
    "mothichoor": "laddu",
    "mothichur": "laddu",
    "boondi laddu": "laddu",
    "thattuvadai": "thattai",
    "thattu vadai": "thattai",
    "thatay": "thattai",
    "thatai": "thattai",
    "thttai": "thattai",
    "muruku": "murukku",
    "murku": "murukku",
    "chakli": "murukku",
    "kai murukku": "murukku",
    "mullu murukku": "murukku",
    "mix": "mixture",
    "spicy mixture": "mixture",
    "madras mixture": "mixture",
}

STOP_WORDS = {
    "add", "and", "want", "need", "order", "have", "with", "pack", "send", "take",
    "drop", "make", "also", "some", "more", "give", "kodu", "venum", "vendum", "then",
    "cost", "price", "rate", "what", "which", "how", "much", "many", "varieties",
    "varietes", "items", "snacks", "total", "cart", "tell", "show", "list", "nothing",
    "else", "enough", "podhum", "ready", "place", "confirm", "yes", "no", "that", "this",
    "these", "those", "please", "kind", "type", "types", "sweet", "sweets", "savory",
    "savoury", "spicy", "deliver", "packet", "packets", "parcel", "bring"
}

def match_product_name(product_name: str) -> str | None:
    """Return a catalogue product name only when the match is confident."""
    if not product_name or not product_name.strip():
        return None

    name = product_name.lower().strip()
    if name in STOP_WORDS:
        return None

    if name in PRODUCT_CATALOG:
        return name

    if name in PRODUCT_SYNONYMS:
        return PRODUCT_SYNONYMS[name]

    for syn, target in PRODUCT_SYNONYMS.items():
        if syn in name:
            return target

    # Avoid fuzzy false positives on short words (< 4 characters)
    if len(name) < 4:
        return None

    catalog_names = list(PRODUCT_CATALOG.keys())
    token_result = process.extractOne(
        name,
        catalog_names,
        scorer=fuzz.token_set_ratio,
        score_cutoff=82,
    )
    if token_result is not None:
        return token_result[0]

    ratio_result = process.extractOne(
        name,
        catalog_names,
        scorer=fuzz.ratio,
        score_cutoff=82,
    )
    if ratio_result is not None:
        return ratio_result[0]

    return None
