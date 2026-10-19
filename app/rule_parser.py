
import re

from app.catalog import PRODUCT_CATALOG


def parse_simple_order(message: str) -> dict | None:
    text = message.lower().strip()

    # Detect price enquiries before attempting order parsing
    enquiry_phrases = [
        "how much",
        "price",
        "cost",
        "rate",
    ]

    if any(phrase in text for phrase in enquiry_phrases):
        return {
            "intent": "product_enquiry",
            "items": extract_items(text),
        }

    # Only handle messages that clearly indicate an order
    order_phrases = [
        "want",
        "need",
        "order",
        "venum",
        "venum",
        "please send",
        "give me",
    ]

    has_order_intent = any(
        phrase in text for phrase in order_phrases
    )

    if not has_order_intent:
        return None

    items = extract_items(text)

    if not items:
        return None

    item = items[0]

    if item["quantity"] is None or item["unit"] is None:
        return None

    return {
        "intent": "new_order",
        "items": items,
    }



def extract_items(text: str) -> list[dict]:
    # Find all quantities and their units, e.g. 500g or 1kg
    quantity_matches = list(
        re.finditer(r"\b(\d+(?:\.\d+)?)\s*(kg|g)\b", text)
    )

    products = [
        (name, match.start())
        for name in PRODUCT_CATALOG
        for match in re.finditer(
            rf"\b{re.escape(name)}\b", text
        )
    ]

    products.sort(key=lambda item: item[1])

    # Only parse when each product can be paired with a quantity
    if not products or len(products) != len(quantity_matches):
        return []

    items = []

    for (product_name, product_position), quantity_match in zip(
        products, quantity_matches
    ):
        # Require the quantity to appear before its product name
        if quantity_match.start() > product_position:
            return []

        items.append({
            "product": product_name,
            "quantity": float(quantity_match.group(1)),
            "unit": quantity_match.group(2),
        })

    return items
