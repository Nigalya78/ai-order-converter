import json
import logging
import ollama

from app.schemas import OrderExtraction, OrderItem
from app.product_matcher import match_product_name
from app.catalog import PRODUCT_CATALOG

logger = logging.getLogger(__name__)
MODEL_NAME = "llama3.1"


def extract(message: str) -> OrderExtraction:
    """
    Extracts structured order/enquiry/modification intent from customer messages
    using Ollama Llama 3.1 with heuristic fallback.
    """
    data = None

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """
You convert customer messages into structured order data.
Understand informal English and Tamil-English messages.

Allowed intents:
new_order, modify_order, product_enquiry, cancel_order, unclear

Allowed units: packet, kg, g

Never invent products, quantities, units, or order changes.
Do not calculate prices.
Use only the products explicitly mentioned by the customer.

GENERAL RULES:
- If the message is unclear, ask a specific clarification question.
- Set needs_clarification to true when required information is missing.
- Put the question in clarification_question.
- Otherwise, set needs_clarification to false and clarification_question to null.
- Never use "clarification" as a product name.

PRODUCT ENQUIRY RULES:
- Questions about price, cost, rates, or available sizes are product_enquiry.
- Examples:
  "What is the price of murukku?"
  "What is the price of 500g murukku?"
  "How much does 1kg laddu cost?"
  "Do you have 250g mixture?"
- Put the identified product in items.
- Extract quantity and unit if a size is specified.
- If no size is specified, quantity and unit must be null.
- Set changes to [].
- Do not ask for clarification if the product can be identified.

NEW ORDER RULES:
- A desire to buy a product is new_order, not product_enquiry.
- Put every requested product in items.
- Set changes to [].
- Never assume a quantity or unit.
- If the product is known but its quantity or unit is missing,
  set the missing field to null, set needs_clarification to true,
  and ask for the missing quantity or size.
- Do not treat an incomplete order as a product enquiry.

CLEAR NEW ORDER EXAMPLES:
Message: "2kg laddu please"
Intent: new_order
Items: [{"product": "laddu", "quantity": 2, "unit": "kg"}]

Message: "I need 500g murukku and 1kg laddu"
Intent: new_order
Items: [{"product": "murukku", "quantity": 500, "unit": "g"}, {"product": "laddu", "quantity": 1, "unit": "kg"}]

Message: "murukku 500g venum"
Intent: new_order
Items: [{"product": "murukku", "quantity": 500, "unit": "g"}]

Message: "I want murukku"
Intent: new_order
Items: [{"product": "murukku", "quantity": null, "unit": null}]

ORDER MODIFICATION RULES:
- Use modify_order when the customer wants to change an existing order.
- Put modifications in changes, never in items.
- Allowed actions: add, set_quantity, remove.
- For add, include the product and requested quantity and unit.
- For set_quantity, include the product and new quantity and unit.
- For remove, include the product.
- Words such as "add", "also add", "include", and "சேர்த்து"
  may indicate a modification to an existing order.

CLEAR MODIFICATION EXAMPLES:
Message: "Add 250g mixture also"
Intent: modify_order
Changes: [{"action": "add", "product": "mixture", "quantity": 250, "unit": "g"}]

Message: "Remove the laddu"
Intent: modify_order
Changes: [{"action": "remove", "product": "laddu"}]

Message: "Change murukku to 500g"
Intent: modify_order
Changes: [{"action": "set_quantity", "product": "murukku", "quantity": 500, "unit": "g"}]
"""
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            format=OrderExtraction.model_json_schema(),
        )
        data = json.loads(response["message"]["content"])
    except Exception as exc:
        logger.warning(f"Ollama chat call failed or unavailable ({exc}). Using heuristic fallback.")
        data = _heuristic_fallback(message)

    if not data:
        data = _heuristic_fallback(message)

    message_lower = message.lower()
    price_question = any(
        phrase in message_lower
        for phrase in ["price", "how much", "cost", "rate", "evvalavu", "vilai"]
    )

    order_desire = any(
        phrase in message_lower
        for phrase in [
            "want", "need", "order", "venum", "give me", "send me", "buy", "pack",
            "deliver", "send", "bring", "parcel", "kodu", "vendum", "edunga", "please send"
        ]
    )

    if price_question and data.get("intent") in {"unclear", "product_enquiry"}:
        data["intent"] = "product_enquiry"
        data["changes"] = []
        data["needs_clarification"] = False
        data["clarification_question"] = None
    elif order_desire and not price_question:
        if data.get("intent") == "product_enquiry":
            data["intent"] = "new_order"

    if data.get("intent") == "new_order":
        data["changes"] = []

    for item in data.get("items", []):
        if isinstance(item.get("unit"), str):
            item["unit"] = item["unit"].lower().strip()
        # Normalize decimal kg (e.g. 0.5kg -> 500g, 0.25kg -> 250g)
        if item.get("unit") == "kg" and isinstance(item.get("quantity"), (int, float)) and 0 < item["quantity"] < 1:
            item["quantity"] = float(item["quantity"] * 1000)
            item["unit"] = "g"

    for change in data.get("changes", []):
        if isinstance(change.get("unit"), str):
            change["unit"] = change["unit"].lower().strip()
        if change.get("unit") == "kg" and isinstance(change.get("quantity"), (int, float)) and 0 < change["quantity"] < 1:
            change["quantity"] = float(change["quantity"] * 1000)
            change["unit"] = "g"

    if data.get("intent") == "new_order":
        items = data.get("items", [])

        if not items:
            # Check if any catalog snack was mentioned in the message text
            detected_prods = []
            for p in PRODUCT_CATALOG.keys():
                if p in message_lower:
                    detected_prods.append(p)
            if detected_prods:
                data["needs_clarification"] = True
                data["clarification_question"] = f"What quantity or size of {detected_prods[0]} would you like? We offer 250g, 500g, and 1kg packages."
            else:
                data["needs_clarification"] = True
                data["clarification_question"] = "Which product and what quantity would you like?"
        else:
            missing_details = []
            has_packet_unit = False
            for item in items:
                product = item.get("product")
                unit = item.get("unit")
                qty = item.get("quantity")
                if not product:
                    missing_details.append("product")
                elif qty is None or unit is None:
                    missing_details.append(product)
                elif unit == "packet":
                    has_packet_unit = True
                    missing_details.append(product)

            if missing_details:
                data["needs_clarification"] = True
                if "product" in missing_details:
                    data["clarification_question"] = "Which product would you like to order?"
                elif has_packet_unit:
                    product = missing_details[0]
                    data["clarification_question"] = f"What package size of {product} would you like? We offer 250g, 500g, and 1kg packages."
                else:
                    product = missing_details[0]
                    data["clarification_question"] = f"What quantity or size of {product} would you like?"
    for item in data.get("items", []):
        product = item.get("product")
        if product:
            matched = match_product_name(product)
            if matched:
                item["product"] = matched
            elif data.get("intent") in {"new_order", "product_enquiry"}:
                data["needs_clarification"] = True
                data["clarification_question"] = (
                    f"We couldn't identify '{product}'. Which product did you mean?"
                )

    return OrderExtraction.model_validate(data)

def _heuristic_fallback(message: str) -> dict:
    """Heuristic fallback parser when LLM is unavailable."""
    msg = message.lower()
    if any(w in msg for w in ["cancel", "cancel order", "stop order"]):
        return {
            "intent": "cancel_order",
            "items": [],
            "changes": [],
            "needs_clarification": False,
            "clarification_question": None,
        }
    detected_items = []
    for product_key in PRODUCT_CATALOG.keys():
        if product_key in msg:
            detected_items.append({"product": product_key, "quantity": None, "unit": None})

    if detected_items:
        is_price = any(w in msg for w in ["price", "cost", "how much", "rate", "evvalavu"])
        return {
            "intent": "product_enquiry" if is_price else "new_order",
            "items": detected_items,
            "changes": [],
            "needs_clarification": True if not is_price else False,
            "clarification_question": f"Please specify the quantity or size for {detected_items[0]['product']}." if not is_price else None,
        }

    return {
        "intent": "unclear",
        "items": [],
        "changes": [],
        "needs_clarification": True,
        "clarification_question": "Could you please specify which snacks and quantities you would like?",
    }