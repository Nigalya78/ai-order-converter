import re
from app.catalog import PRODUCT_CATALOG
from app.product_matcher import match_product_name, PRODUCT_SYNONYMS

ENQUIRY_PHRASES = [
    "how much",
    "price",
    "cost",
    "rate",
    "evvalavu",
    "evlo",
    "vilai",
    "rate enna",
]

ORDER_PHRASES = [
    "want",
    "need",
    "order",
    "venum",
    "vendum",
    "kodu",
    "please send",
    "give me",
    "send me",
    "buy",
    "pack",
    "parcel",
    "podungae",
]

def parse_simple_order(message: str) -> dict | None:
    """
    Deterministically parses customer messages with high confidence.
    Supports both bidirectional patterns:
      - [quantity][unit] [product] (e.g., '500g murukku', '1kg laddu')
      - [product] [quantity][unit] (e.g., 'murukku 500g', 'laddu 1kg')
    Supports multi-item sentences and Tanglish phrases.
    """
    text = message.lower().strip()
    # Check for modification or cancellation phrases that require LLM intent extraction
    if any(m in text for m in ["change ", "remove ", "replace ", "mathunga", "korainga", "also add ", "add "]):
        if any(w in text for w in ["change", "remove", "replace", "also", "mathunga", "korainga"]):
            return None

    is_enquiry = any(phrase in text for phrase in ENQUIRY_PHRASES)

    extracted_items = extract_all_items(text)

    if is_enquiry:
        return {
            "intent": "product_enquiry",
            "items": extracted_items,
        }

    if not extracted_items:
        return None

    # Verify that all mentioned known products were captured. If a snack was mentioned
    # but not extracted by regex, pass to LLM to ensure no items are silently dropped.
    mentioned_known_prods = set()
    for cat_prod in PRODUCT_CATALOG.keys():
        if cat_prod in text:
            mentioned_known_prods.add(cat_prod)
    for syn, target in PRODUCT_SYNONYMS.items():
        if syn in text:
            mentioned_known_prods.add(target)

    extracted_prods = {it["product"] for it in extracted_items}
    if len(mentioned_known_prods) > len(extracted_prods):
        return None

    all_complete = all(
        item.get("quantity") is not None and item.get("unit") is not None
        for item in extracted_items
    )

    if not all_complete:
        return None

    return {
        "intent": "new_order",
        "items": extracted_items,
    }


def extract_segment_item(segment: str) -> dict | None:
    """Extract a single product item and quantity from a text clause/segment."""
    clean_seg = segment.strip()
    if not clean_seg:
        return None
    p1 = re.search(r"\b(\d+(?:\.\d+)?)\s*(kg|g)\s*(?:of\s+)?([a-zA-Z\s]{2,15})\b", clean_seg, re.IGNORECASE)
    if p1:
        qty_str, unit, candidate = p1.groups()
        matched = match_product_name(candidate.strip())
        if matched:
            return {
                "product": matched,
                "quantity": float(qty_str),
                "unit": unit.lower(),
            }
    p2 = re.search(r"\b([a-zA-Z]{3,15})\s+(\d+(?:\.\d+)?)\s*(kg|g)\b", clean_seg, re.IGNORECASE)
    if p2:
        candidate, qty_str, unit = p2.groups()
        matched = match_product_name(candidate.strip())
        if matched:
            return {
                "product": matched,
                "quantity": float(qty_str),
                "unit": unit.lower(),
            }

    return None


def extract_all_items(text: str) -> list[dict]:
    """
    Extracts all item pairs of (product, quantity, unit) from text.
    Handles clauses separated by commas, 'and', '+', '&', newlines,
    as well as unseparated sequences like 'muruku 250g thattai 100g'.
    """
    candidates = []

    # Pattern A: <qty><unit> [of] <word> (e.g. "500g murukku", "250 g thattai")
    for m in re.finditer(r"\b(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>kg|g)\b\s*(?:of\s+)?\b(?P<prod>[a-zA-Z]{3,20})\b", text, re.IGNORECASE):
        prod = match_product_name(m.group("prod").strip())
        if prod:
            candidates.append({
                "start": m.start(),
                "end": m.end(),
                "product": prod,
                "quantity": float(m.group("qty")),
                "unit": m.group("unit").lower(),
            })

    # Pattern B: <word> <qty><unit> (e.g. "murukku 500g", "thattai 100g")
    for m in re.finditer(r"\b(?P<prod>[a-zA-Z]{3,20})\b\s+\b(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>kg|g)\b", text, re.IGNORECASE):
        prod = match_product_name(m.group("prod").strip())
        if prod:
            candidates.append({
                "start": m.start(),
                "end": m.end(),
                "product": prod,
                "quantity": float(m.group("qty")),
                "unit": m.group("unit").lower(),
            })

    # Sort candidates by appearance order in text
    candidates.sort(key=lambda c: (c["start"], -(c["end"] - c["start"])))

    # Filter out overlapping matches
    results = []
    seen_prods = set()
    last_end = -1
    for c in candidates:
        if c["start"] >= last_end and c["product"] not in seen_prods:
            results.append({
                "product": c["product"],
                "quantity": c["quantity"],
                "unit": c["unit"],
            })
            seen_prods.add(c["product"])
            last_end = c["end"]

    # Fallback to clause splitting if no candidates found
    if not results:
        clauses = re.split(r"[,+&\n]|\band\b|\balso\b", text, flags=re.IGNORECASE)
        for clause in clauses:
            item = extract_segment_item(clause)
            if item and item["product"] not in seen_prods:
                results.append(item)
                seen_prods.add(item["product"])

    return results
