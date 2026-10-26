import re
import logging
from typing import Any

from app.catalog import PRODUCT_CATALOG
from app.product_matcher import match_product_name
from app.order_engine import process_order
from app.text_normalizer import normalize_message
from app.rule_parser import parse_simple_order, extract_all_items
from app.llm_service import extract, MODEL_NAME
from app.database import (
    create_or_get_chat_session,
    get_chat_session,
    update_chat_session,
    save_chat_message,
    get_chat_messages,
    save_order,
    get_order_by_id,
    update_order_status,
    format_whatsapp_receipt,
)

logger = logging.getLogger(__name__)

GREETING_WORDS = {
    "hi", "hello", "hey", "vanakkam", "vanakam", "good morning", "good evening",
    "good afternoon", "namaste", "hola"
}

THANKS_WORDS = {
    "thanks", "thank you", "thx", "thank u", "nandri", "dhanyavadham", "many thanks"
}

APOLOGY_WORDS = {
    "sorry", "my bad", "apologies", "pardon"
}

FRUSTRATION_WORDS = [
    "idiot", "stupid", "dumb", "fool", "useless", "worst", "nonsense",
    "rubbish", "crazy", "shut up", "get lost", "bad bot", "hate this"
]

CONFIRM_WORDS = [
    "yes", "confirm", "place order", "place the order", "proceed",
    "order pannunga", "checkout", "yes please", "sure place it",
    "confirm order", "confirm the order", "book order", "ok place order",
    "ok confirm", "yes confirm"
]

VIEW_CART_PHRASES = [
    "what is my total",
    "what's my total",
    "show my cart",
    "show cart",
    "view cart",
    "show my order",
    "view my order",
    "review order",
    "review my order",
    "cart total",
    "how much total",
    "current total",
    "total evlo",
    "total evvalavu",
]

WRAP_UP_PHRASES = [
    "nothing else i need",
    "nothing else",
    "that is all",
    "that's all",
    "thats all",
    "that is it",
    "that's it",
    "thats it",
    "no more",
    "done",
    "finish",
    "no that's enough",
    "enough",
    "podhum",
    "avlo dhan",
    "avlodhan",
    "no other items",
    "nothing more",
    "no thanks",
]

CATALOG_QUESTIONS = [
    "what snacks",
    "what products",
    "what is available",
    "what are available",
    "available snacks",
    "menu",
    "show snacks",
    "show catalog",
    "list snacks",
    "what do you have",
    "which snacks",
    "enna snacks",
    "enna irukku",
]

def is_configured_variant(product_name: str, quantity: float, unit: str) -> tuple[bool, str]:
    """Checks whether a given product and quantity match a configured catalogue variant."""
    product = PRODUCT_CATALOG.get(product_name)
    if not product:
        return False, ""
    qty_g = quantity * 1000 if unit == "kg" else quantity
    if qty_g >= 1000:
        variant = f"{qty_g / 1000:g}kg"
    else:
        variant = f"{qty_g:g}g"
    return variant in product.get("variants", {}), variant

def format_cart_summary(cart_items: list[dict], total: float) -> str:
    """Generates a clean text breakdown of the draft cart."""
    if not cart_items:
        return "Your cart is currently empty."

    lines = []
    for it in cart_items:
        size = it.get("variant") or f"{it.get('quantity')}{it.get('unit', '')}"
        lines.append(f"• **{it.get('product', '').title()}** ({size}) - ₹{it.get('price', 0):.0f}")
    lines.append(f"\n**Current Total: ₹{total:.0f}**")
    return "\n".join(lines)

def resolve_contextual_references(text: str, context: dict) -> str:
    """
    Resolves conversational pronouns and references like 'that', 'it', 'previous item'
    using active session context.
    """
    resolved = text
    last_product = context.get("last_discussed_product")
    last_size = context.get("last_discussed_size")
    awaiting_add = context.get("awaiting_add_confirmation", False)

    if not last_product:
        return resolved

    clean_lower = re.sub(r"[^\w\s]", "", resolved.lower()).strip()

    # Check if another catalog product is explicitly mentioned
    other_product_mentioned = any(
        p in clean_lower for p in PRODUCT_CATALOG.keys() if p != last_product
    )
    if other_product_mentioned:
        return resolved

    # Check for removal: "remove that", "delete it", "take out thattai"
    if re.search(r"\b(remove|delete|take out)\s+(that|it)\b", resolved, re.IGNORECASE):
        return f"remove {last_product}"

    # Check for change of quantity: "make it 1kg", "change it to 500g"
    if re.search(r"\b(make|change)\s+(it|that)\s+(?:to\s+)?(\d+(?:\.\d+)?\s*(?:kg|g))\b", resolved, re.IGNORECASE):
        match = re.search(r"\b(make|change)\s+(it|that)\s+(?:to\s+)?(\d+(?:\.\d+)?\s*(?:kg|g))\b", resolved, re.IGNORECASE)
        if match:
            new_qty = match.group(3)
            return f"change {last_product} to {new_qty}"

    # Check for price query pronoun: "price of that", "how much is it"
    if re.search(r"\b(price of|cost of|how much is)\s+(that|it)\b", resolved, re.IGNORECASE):
        return f"price of {last_product}"

    # Check for size-only specification: "500g", "add 500g", "500g venum", "500g please"
    size_match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:kg|g))\b", clean_lower)
    target_size = size_match.group(1).replace(" ", "") if size_match else (last_size or "")

    # Patterns for adding the item:
    # 1. Pronoun add: "add that", "add it", "want it", "need that", "add that too", "add this"
    has_pronoun_add = bool(re.search(r"\b(add|want|need)\s+(that|it|this|them)\b", clean_lower))

    # 2. General add phrases without mentioning another product:
    # e.g., "yess add", "yes add", "add", "please add", "add please", "sure add it", "ok add", "add to cart", "add pannunga"
    is_add_command = bool(
        re.search(
            r"\b(?:ye+s+|yeah|yep|sure|ok|okay)?\s*(?:please\s+)?(?:add|put|include|venum|podu|edunga|kodu)\b",
            clean_lower,
        )
    )

    # 3. Affirmative response when assistant previously asked "Would you like to add it to your draft order?"
    is_affirmative_reply = awaiting_add and bool(
        re.match(
            r"^(?:ye+s+|yeah|yep|sure|ok|okay|please|seri|ama|aama|definitely|of course|why not)(?:\s+(?:please|add|do|it|that|order))*$",
            clean_lower,
        )
    )

    if has_pronoun_add or is_add_command or is_affirmative_reply:
        size_part = f"{target_size} " if target_size else ""
        return f"add {size_part}{last_product}".strip()

    return resolved


def handle_frustration(clean_msg: str, context: dict, cart: dict) -> dict | None:
    """
    Detects customer frustration and de-escalates with contextually accurate responses.
    """
    msg_lower = clean_msg.lower()
    is_frustrated = any(w in msg_lower for w in FRUSTRATION_WORDS)
    if not is_frustrated:
        return None

    last_summary = context.get("last_requested_summary")
    unconfigured = context.get("unconfigured_items", [])

    if last_summary and unconfigured:
        unconf_name = unconfigured[0]["product"].title()
        unconf_var = unconfigured[0]["variant"]
        avail_variants = PRODUCT_CATALOG.get(unconfigured[0]["product"], {}).get("variants", {})
        avail_str = ", ".join(f"{s} (₹{p})" for s, p in avail_variants.items())
        reply = (
            f"Sorry, I misunderstood your order. Let me correct it. "
            f"You asked for {last_summary}. {unconf_name} {unconf_var} isn't a configured size. "
            f"Would you like one of the available sizes ({avail_str}) instead?"
        )
    elif cart.get("items"):
        cart_desc = format_cart_summary(cart["items"], cart["total"])
        reply = (
            f"Sorry for any confusion! Let me help get your order right. "
            f"Your draft cart currently has:\n{cart_desc}\n\n"
            f"What would you like to change or remove?"
        )
    else:
        reply = (
            "I apologize for the misunderstanding! Please tell me what snacks and quantities you'd like, "
            "and I will make sure your order is accurate."
        )

    return {
        "reply": reply,
        "intent": "frustration_handled",
    }


def handle_item_dispute(normalized_message: str, cart: dict) -> dict | None:
    """
    Handles when customer disputes an erroneously added item (e.g. 'I didn't even tell you Thattai 250g').
    Removes the disputed item, recalculates total, and preserves unrelated valid items.
    """
    dispute_phrases = [
        "didn't even tell you", "did not even tell you",
        "didn't tell you", "did not tell you",
        "didn't ask for", "did not ask for",
        "didn't order", "did not order",
        "never asked for", "never ordered",
        "why did you add", "who told you to add",
    ]
    is_dispute = any(phrase in normalized_message for phrase in dispute_phrases)
    if not is_dispute:
        return None

    disputed_product = None
    for tok in normalized_message.split():
        matched = match_product_name(tok.strip("?,.!"))
        if matched:
            disputed_product = matched
            break

    if not disputed_product:
        for name in ["madras mixture", "mothichoor laddu"]:
            if name in normalized_message:
                disputed_product = match_product_name(name)
                break

    if not disputed_product:
        return {
            "reply": "I apologize for the confusion. Which item would you like me to remove from your cart?",
            "intent": "dispute_clarification",
        }

    current_items = list(cart.get("items", []))
    remaining_items = [it for it in current_items if it.get("product") != disputed_product]

    if len(remaining_items) < len(current_items):
        new_total = sum(it["price"] for it in remaining_items)
        new_cart = {"items": remaining_items, "total": new_total}
        if remaining_items:
            summary = format_cart_summary(remaining_items, new_total)
            reply = (
                f"Understood! I've removed {disputed_product.title()} from your cart. "
                f"Your updated draft order has:\n\n{summary}\n\n"
                f"Would you like to add anything else?"
            )
        else:
            reply = (
                f"Understood! I've removed {disputed_product.title()} from your cart. "
                f"Your cart is now empty. What snacks would you like to order instead?"
            )
        return {
            "reply": reply,
            "intent": "dispute_resolved",
            "updated_cart": new_cart,
        }
    else:
        return {
            "reply": f"Understood! {disputed_product.title()} was not in your cart.",
            "intent": "dispute_not_in_cart",
            "updated_cart": cart,
        }


def handle_customer_correction(normalized_message: str, cart: dict) -> dict | None:
    """
    Handles customer corrections like 'I told you Murukku 250g and Thattai 100g.'
    Reconciles intended items without creating duplicate lines or silently substituting variants.
    """
    correction_starters = [
        "i told you", "i already told you", "i said", "i meant", "i wanted",
        "i asked for", "actually i asked for", "i asked you for"
    ]
    is_correction = any(phrase in normalized_message for phrase in correction_starters)
    if not is_correction:
        return None

    extracted = extract_all_items(normalized_message)
    if not extracted:
        return None

    valid_items = []
    unconfigured_items = []

    for item in extracted:
        p_name = item["product"]
        qty = item["quantity"]
        unit = item["unit"]
        is_conf, variant_str = is_configured_variant(p_name, qty, unit)
        if is_conf:
            valid_items.append(item)
        else:
            unconfigured_items.append({"product": p_name, "variant": variant_str})

    current_items = list(cart.get("items", []))
    extracted_prod_names = {it["product"] for it in extracted}
    kept_items = [it for it in current_items if it.get("product") not in extracted_prod_names]

    if valid_items:
        order_engine_result = process_order(valid_items)
        if order_engine_result["valid"]:
            kept_items.extend(order_engine_result["items"])

    new_cart_recalc = process_order([
        {"product": it["product"], "quantity": it["quantity"], "unit": it["unit"]}
        for it in kept_items
    ]) if kept_items else {"valid": True, "items": [], "total": 0}

    new_cart = {
        "items": new_cart_recalc["items"] if new_cart_recalc["valid"] else kept_items,
        "total": new_cart_recalc["total"] if new_cart_recalc["valid"] else sum(it["price"] for it in kept_items),
    }

    req_summary_parts = []
    for it in extracted:
        qty_str = f"{it['quantity']:g}{it['unit']}"
        req_summary_parts.append(f"{it['product'].title()} {qty_str}")
    req_summary = " and ".join(req_summary_parts)

    context_update = {
        "last_requested_summary": req_summary,
        "unconfigured_items": unconfigured_items,
    }

    if unconfigured_items:
        unconf = unconfigured_items[0]
        unconf_name = unconf["product"].title()
        unconf_var = unconf["variant"]
        avail_variants = PRODUCT_CATALOG.get(unconf["product"], {}).get("variants", {})
        avail_str = ", ".join(f"{s} (₹{p})" for s, p in avail_variants.items())

        if valid_items:
            valid_desc = ", ".join(
                f"{it['product'].title()} ({it.get('variant') or str(it['quantity']) + it['unit']})"
                for it in valid_items
            )
            reply = (
                f"I've updated your draft order. **{valid_desc}** is in your cart (current total: **₹{new_cart['total']:.0f}**).\n\n"
                f"However, **{unconf_name} {unconf_var}** isn't a configured size. "
                f"Available sizes are: {avail_str}. Would you like one of these sizes instead?"
            )
        else:
            reply = (
                f"I understand you wanted {req_summary}. However, **{unconf_name} {unconf_var}** isn't a configured size. "
                f"Available sizes are: {avail_str}. Which size would you prefer?"
            )
    else:
        summary = format_cart_summary(new_cart["items"], new_cart["total"])
        reply = (
            f"I have corrected your order to match your request:\n\n{summary}\n\n"
            f"Would you like to confirm and place this order?"
        )

    return {
        "reply": reply,
        "intent": "correction_applied",
        "updated_cart": new_cart,
        "context_update": context_update,
    }


def handle_category_enquiry(normalized_message: str) -> dict | None:
    """
    Handles category queries like 'sweet varietes', 'what sweet', 'savory snacks'.
    """
    msg = normalized_message.lower()

    sweet_triggers = ["sweet", "sweets", "inippu", "mittai"]
    is_sweet = any(re.search(rf"\b{w}\b", msg) for w in sweet_triggers)

    savory_triggers = ["savory", "savoury", "spicy", "karam", "kaaram"]
    is_savory = any(re.search(rf"\b{w}\b", msg) for w in savory_triggers)

    if is_sweet and not is_savory:
        laddu_info = PRODUCT_CATALOG["laddu"]
        variants_str = "\n".join(f"• **{s}**: ₹{p}" for s, p in laddu_info["variants"].items())
        reply = (
            f"Our traditional sweet specialty is **{laddu_info['name']}**!\n\n"
            f"_{laddu_info['description']}_\n\n"
            f"**Available Sizes & Prices:**\n{variants_str}\n\n"
            f"Would you like to add some Laddu to your order?"
        )
        return {
            "reply": reply,
            "intent": "product_enquiry",
            "context_update": {"last_discussed_product": "laddu", "last_discussed_size": "500g"},
        }

    if is_savory and not is_sweet:
        lines = []
        for pid, details in PRODUCT_CATALOG.items():
            if details.get("category", "").lower() == "savory":
                v_str = ", ".join(f"{s} (₹{p})" for s, p in details["variants"].items())
                lines.append(f"• **{details['name']}**: {v_str}")
        reply = (
            "Here are our available savory snacks:\n\n"
            + "\n".join(lines)
            + "\n\nWhich snack and quantity would you like to add?"
        )
        return {
            "reply": reply,
            "intent": "product_enquiry",
            "context_update": {},
        }

    return None


def handle_product_description(normalized_message: str, cart: dict) -> dict | None:
    """
    Handles questions like 'what laddu is this', 'what is mothichoor laddu', 'tell me about thattai'.
    """
    desc_patterns = [
        r"what\s+(?:kind of\s+)?([a-zA-Z\s]{3,15})\s+is\s+this",
        r"what\s+is\s+(?:this\s+)?([a-zA-Z\s]{3,15})",
        r"tell\s+me\s+about\s+([a-zA-Z\s]{3,15})",
        r"([a-zA-Z\s]{3,15})\s+details",
    ]
    matched_prod = None
    for pat in desc_patterns:
        m = re.search(pat, normalized_message, re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            p = match_product_name(cand)
            if p:
                matched_prod = p
                break

    if not matched_prod:
        return None

    p_info = PRODUCT_CATALOG[matched_prod]
    v_str = ", ".join(f"{s} (₹{p})" for s, p in p_info["variants"].items())
    reply = (
        f"We serve authentic **{p_info['name']}** ({p_info.get('category', 'Snack')}).\n\n"
        f"_{p_info['description']}_\n\n"
        f"**Available Packages**: {v_str}."
    )
    prod_in_cart = [it for it in cart.get("items", []) if it.get("product") == matched_prod]
    if prod_in_cart:
        sizes = ", ".join(f"{it.get('variant') or str(it['quantity']) + it['unit']} (₹{it['price']:.0f})" for it in prod_in_cart)
        reply += f"\n\nYour draft order currently includes: **{p_info['name']} {sizes}**."

    return {
        "reply": reply,
        "intent": "product_enquiry",
        "context_update": {"last_discussed_product": matched_prod},
    }


def handle_product_enquiry(normalized_message: str, context: dict) -> dict | None:
    """
    Checks if message is a product enquiry, pricing question, or catalog exploration.
    Retrieves factual details strictly from PRODUCT_CATALOG.
    """
    is_catalog_query = any(phrase in normalized_message for phrase in CATALOG_QUESTIONS)

    if is_catalog_query:
        summary_list = []
        for pid, details in PRODUCT_CATALOG.items():
            variants_str = ", ".join(f"{s} (₹{p})" for s, p in details["variants"].items())
            summary_list.append(f"• **{details.get('name', pid.title())}** ({details.get('category', 'Snack')}): {variants_str}")
        reply = (
            "Here are our available traditional South Indian snacks:\n\n"
            + "\n".join(summary_list)
            + "\n\nWould you like to know more about any snack or add something to your cart?"
        )
        return {
            "reply": reply,
            "intent": "product_enquiry",
            "context_update": {},
        }

    enquiry_indicators = ["price", "cost", "how much", "rate", "evvalavu", "evlo", "available size", "sizes", "variants"]
    has_enquiry_phrase = any(phrase in normalized_message for phrase in enquiry_indicators)

    detected_product = None
    for token in normalized_message.split():
        matched = match_product_name(token.strip("?,.!"))
        if matched:
            detected_product = matched
            break

    if not detected_product and has_enquiry_phrase and context.get("last_discussed_product"):
        detected_product = context.get("last_discussed_product")

    if not detected_product:
        for name in ["madras mixture", "mothichoor laddu"]:
            if name in normalized_message:
                detected_product = match_product_name(name)
                break

    if has_enquiry_phrase and detected_product:
        product_info = PRODUCT_CATALOG.get(detected_product)
        if not product_info:
            return {
                "reply": f"Sorry, {detected_product} is not available in our catalog. We offer Murukku, Thattai, Mixture, and Laddu.",
                "intent": "product_enquiry",
                "context_update": {},
            }

        variants = product_info["variants"]
        size_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(kg|g)\b", normalized_message, re.IGNORECASE)
        requested_size = None
        if size_match:
            qty_val = float(size_match.group(1))
            unit_val = size_match.group(2).lower()
            if unit_val == "kg" and qty_val >= 1:
                requested_size = f"{qty_val:g}kg"
            elif unit_val == "g" and qty_val >= 1000:
                requested_size = f"{qty_val / 1000:g}kg"
            else:
                requested_size = f"{qty_val:g}{unit_val}"

        display_name = product_info.get("name", detected_product.title())

        if requested_size and requested_size in variants:
            price = variants[requested_size]
            reply = (
                f"{requested_size} {display_name} costs **₹{price}**. "
                f"Would you like to add it to your draft order?"
            )
        elif requested_size:
            avail_str = ", ".join(f"{s} (₹{p})" for s, p in variants.items())
            reply = (
                f"{requested_size} {display_name} is not a standard variant. "
                f"Available sizes are: {avail_str}. Would you like one of these?"
            )
        else:
            avail_str = ", ".join(f"{s} - ₹{p}" for s, p in variants.items())
            reply = (
                f"Here are the available sizes and prices for {display_name}: {avail_str}. "
                f"What size would you like to add?"
            )

        return {
            "reply": reply,
            "intent": "product_enquiry",
            "context_update": {
                "last_discussed_product": detected_product,
                "last_discussed_size": requested_size or list(variants.keys())[0],
                "awaiting_add_confirmation": bool(requested_size and requested_size in variants),
            },
        }

    return None


def handle_order_status_query(normalized_message: str, session: dict) -> dict | None:
    """
    Handles order status enquiries.
    """
    status_keywords = ["status of my order", "order status", "track my order", "where is my order", "status of order", "track order"]
    is_status_query = any(phrase in normalized_message for phrase in status_keywords) or re.search(r"\b(status|track)\b.*#?\d+", normalized_message)

    if not is_status_query:
        return None

    order_id_match = re.search(r"(?:order\s*#?|#)\s*(\d+)", normalized_message)
    order_id = int(order_id_match.group(1)) if order_id_match else session.get("created_order_id")

    if not order_id:
        return {
            "reply": "Could you please specify your Order ID? For example: 'What is the status of order #5?'",
            "intent": "order_status",
        }

    order = get_order_by_id(order_id)
    if not order:
        return {
            "reply": f"I couldn't find Order #{order_id} in our registry. Please check the order number.",
            "intent": "order_status",
        }

    status_str = {
        "payment_pending": "⏳ Payment Pending (awaiting customer confirmation)",
        "confirmed": "✅ Confirmed (packing & dispatch preparation)",
        "cancelled": "❌ Cancelled",
    }.get(order["status"], order["status"])

    items_summary = ", ".join(
        f"{it.get('product', '').title()} ({it.get('variant') or str(it.get('quantity')) + it.get('unit', '')})"
        for it in order.get("items", [])
    )

    reply = (
        f"**Order #{order_id}** is currently **{status_str}**.\n\n"
        f"• **Items**: {items_summary}\n"
        f"• **Grand Total**: ₹{order.get('total', 0):.0f}\n"
    )
    return {
        "reply": reply,
        "intent": "order_status",
        "order_id": order_id,
        "status": order["status"],
    }


def handle_order_cancellation(normalized_message: str, session: dict) -> dict | None:
    """
    Handles requests to cancel an order. Follows backend business lifecycle rules.
    """
    cancel_keywords = ["cancel my order", "cancel order", "cancel the order", "order cancel"]
    is_cancel = any(phrase in normalized_message for phrase in cancel_keywords)
    if not is_cancel:
        return None

    order_id_match = re.search(r"(?:order\s*#?|#)\s*(\d+)", normalized_message)
    order_id = int(order_id_match.group(1)) if order_id_match else session.get("created_order_id")

    if not order_id:
        return {
            "reply": "Please specify the Order ID you wish to cancel (e.g., 'Cancel order #3').",
            "intent": "cancel_order",
        }

    order = get_order_by_id(order_id)
    if not order:
        return {
            "reply": f"Order #{order_id} was not found.",
            "intent": "cancel_order",
        }

    if order["status"] == "cancelled":
        return {
            "reply": f"Order #{order_id} is already cancelled.",
            "intent": "cancel_order",
            "order_id": order_id,
            "status": "cancelled",
        }

    try:
        update_order_status(order_id, "cancelled")
        return {
            "reply": f"Order #{order_id} has been cancelled successfully.",
            "intent": "cancel_order",
            "order_id": order_id,
            "status": "cancelled",
        }
    except ValueError as e:
        return {
            "reply": f"Could not cancel Order #{order_id}: {str(e)}",
            "intent": "cancel_order",
            "order_id": order_id,
            "status": order["status"],
        }

def process_chat_message(session_id: str | None, raw_message: str) -> dict:
    """
    Main entry point for conversational chat-to-order processing.
    """
    clean_msg = raw_message.strip()
    session = create_or_get_chat_session(session_id)
    active_sid = session["session_id"]
    cart = session.get("cart", {"items": [], "total": 0})
    context = session.get("context", {})

    save_chat_message(active_sid, "customer", clean_msg)

    # 1. Frustration / Rudeness Check (Polite de-escalation with context)
    frustration_resp = handle_frustration(clean_msg, context, cart)
    if frustration_resp:
        save_chat_message(active_sid, "assistant", frustration_resp["reply"], {"intent": frustration_resp["intent"]})
        return {
            "session_id": active_sid,
            "reply": frustration_resp["reply"],
            "intent": frustration_resp["intent"],
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    normalized = normalize_message(clean_msg).strip().lower()

    # 2. Greetings
    if normalized in GREETING_WORDS or normalized.replace("!", "") in GREETING_WORDS:
        reply = "Vanakkam! Welcome to our Snack House. We have authentic Murukku, Thattai, Madras Mixture, and Mothichoor Laddu. What would you like to explore or order today?"
        save_chat_message(active_sid, "assistant", reply, {"intent": "greeting"})
        return {
            "session_id": active_sid,
            "reply": reply,
            "intent": "greeting",
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 3. Thanks
    if normalized in THANKS_WORDS or any(w in normalized for w in ["thank you", "thanks"]):
        reply = "You're very welcome! Let me know if you would like to add more snacks or if you're ready to place your order."
        save_chat_message(active_sid, "assistant", reply, {"intent": "thanks"})
        return {
            "session_id": active_sid,
            "reply": reply,
            "intent": "thanks",
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 4. Apologies
    if normalized in APOLOGY_WORDS:
        reply = "No worries at all! How can I assist you with your snack order today?"
        save_chat_message(active_sid, "assistant", reply, {"intent": "apology_ack"})
        return {
            "session_id": active_sid,
            "reply": reply,
            "intent": "apology_ack",
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 5. Item Dispute Removal ("I didn't even tell you Thattai 250g")
    dispute_resp = handle_item_dispute(normalized, cart)
    if dispute_resp:
        updated_cart = dispute_resp.get("updated_cart", cart)
        update_chat_session(active_sid, cart=updated_cart)
        save_chat_message(active_sid, "assistant", dispute_resp["reply"], {"intent": dispute_resp["intent"]})
        return {
            "session_id": active_sid,
            "reply": dispute_resp["reply"],
            "intent": dispute_resp["intent"],
            "cart": updated_cart,
            "pending_confirmation": len(updated_cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 6. Customer Corrections ("I told you Murukku 250g and Thattai 100g")
    correction_resp = handle_customer_correction(normalized, cart)
    if correction_resp:
        updated_cart = correction_resp["updated_cart"]
        new_context = {**context, **correction_resp.get("context_update", {})}
        update_chat_session(active_sid, cart=updated_cart, context=new_context)
        save_chat_message(active_sid, "assistant", correction_resp["reply"], {"intent": correction_resp["intent"]})
        return {
            "session_id": active_sid,
            "reply": correction_resp["reply"],
            "intent": correction_resp["intent"],
            "cart": updated_cart,
            "pending_confirmation": len(updated_cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 7. Wrap-up / Done adding items ("nothing else i need", "that's all")
    is_wrap_up = any(normalized == p or normalized.startswith(p) for p in WRAP_UP_PHRASES)
    if is_wrap_up:
        if cart.get("items"):
            summary = format_cart_summary(cart["items"], cart["total"])
            reply = (
                f"Great! Here is your draft order:\n\n{summary}\n\n"
                f"Would you like me to place the order now? Reply **'Yes'** or **'Place order'** to confirm."
            )
            save_chat_message(active_sid, "assistant", reply, {"intent": "wrap_up_ready"})
            return {
                "session_id": active_sid,
                "reply": reply,
                "intent": "wrap_up_ready",
                "cart": cart,
                "pending_confirmation": True,
                "order_id": None,
                "status": None,
            }
        else:
            reply = "No problem! Let me know whenever you'd like to explore our snacks or place an order."
            save_chat_message(active_sid, "assistant", reply, {"intent": "wrap_up_empty"})
            return {
                "session_id": active_sid,
                "reply": reply,
                "intent": "wrap_up_empty",
                "cart": cart,
                "pending_confirmation": False,
                "order_id": None,
                "status": None,
            }

    # Contextual reference resolution (e.g. "add that", "make it 1kg")
    resolved_message = resolve_contextual_references(normalized, context)

    # 7.5 Decline adding previously discussed product
    if context.get("awaiting_add_confirmation") and re.match(r"^(?:no+|no\s+thanks|don'?t\s+add|cancel|nah|not\s+now)\b", normalized):
        new_context = {**context, "awaiting_add_confirmation": False}
        update_chat_session(active_sid, context=new_context)
        reply = "No problem! What other snacks would you like to explore? We offer Murukku, Thattai, Madras Mixture, and Mothichoor Laddu."
        save_chat_message(active_sid, "assistant", reply, {"intent": "decline_add"})
        return {
            "session_id": active_sid,
            "reply": reply,
            "intent": "decline_add",
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 8. Explicit Order Confirmation
    is_confirm = (
        resolved_message in CONFIRM_WORDS
        or any(resolved_message.startswith(w) for w in ["yes, place", "yes place", "please confirm", "place it"])
    )
    if is_confirm:
        if session.get("created_order_id"):
            existing_id = session.get("created_order_id")
            existing_order = get_order_by_id(existing_id)
            if existing_order:
                reply = (
                    f"Order **#{existing_id}** has already been placed! "
                    f"Current status: **{existing_order['status']}**.\n\n"
                    f"Would you like to start a new order or check receipt?"
                )
                save_chat_message(active_sid, "assistant", reply, {"intent": "order_confirmed", "order_id": existing_id})
                return {
                    "session_id": active_sid,
                    "reply": reply,
                    "intent": "order_confirmed",
                    "cart": cart,
                    "pending_confirmation": False,
                    "order_id": existing_id,
                    "status": existing_order["status"],
                }

        if not cart.get("items"):
            reply = "Your cart is currently empty! Would you like to check out our snacks first? We have Murukku, Thattai, Mixture, and Laddu."
            save_chat_message(active_sid, "assistant", reply, {"intent": "cart_empty"})
            return {
                "session_id": active_sid,
                "reply": reply,
                "intent": "cart_empty",
                "cart": cart,
                "pending_confirmation": False,
                "order_id": None,
                "status": None,
            }

        customer_record_msg = f"Conversational chat order (Session {active_sid[:8]}):\n" + "\n".join(
            f"- {it['product'].title()} {it.get('variant', '')} (₹{it['price']})" for it in cart["items"]
        )
        new_order_id = save_order(
            customer_message=customer_record_msg,
            items=cart["items"],
            total=cart["total"],
        )
        update_chat_session(
            active_sid,
            cart={"items": [], "total": 0},
            pending_confirmation=False,
            created_order_id=new_order_id,
            context={"last_order_id": new_order_id},
        )

        receipt = format_whatsapp_receipt({
            "order_id": new_order_id,
            "status": "payment_pending",
            "items": cart["items"],
            "total": cart["total"],
        })

        reply = (
            f"🎉 **Your order has been placed successfully!**\n\n"
            f"• **Order ID**: #{new_order_id}\n"
            f"• **Status**: ⏳ Payment Pending\n"
            f"• **Total**: ₹{cart['total']:.0f}\n\n"
            f"Here is your customer receipt summary:\n```\n{receipt}\n```\n"
            f"You can track this order anytime by asking 'What is the status of my order?'"
        )

        save_chat_message(active_sid, "assistant", reply, {
            "intent": "order_placed",
            "order_id": new_order_id,
            "total": cart["total"],
        })

        return {
            "session_id": active_sid,
            "reply": reply,
            "intent": "order_placed",
            "cart": {"items": [], "total": 0},
            "pending_confirmation": False,
            "order_id": new_order_id,
            "status": "payment_pending",
        }

    # 9. Order Status Query
    status_resp = handle_order_status_query(resolved_message, session)
    if status_resp:
        save_chat_message(active_sid, "assistant", status_resp["reply"], {"intent": status_resp["intent"]})
        return {
            "session_id": active_sid,
            "reply": status_resp["reply"],
            "intent": status_resp["intent"],
            "cart": cart,
            "pending_confirmation": False,
            "order_id": status_resp.get("order_id"),
            "status": status_resp.get("status"),
        }

    # 10. View Cart Query
    is_view_cart = any(phrase in resolved_message for phrase in VIEW_CART_PHRASES)
    if is_view_cart:
        if not cart.get("items"):
            reply = "Your cart is currently empty. What snacks would you like to add? We have Murukku, Thattai, Mixture, and Laddu."
        else:
            cart_summary = format_cart_summary(cart["items"], cart["total"])
            reply = f"Here is your draft order:\n\n{cart_summary}\n\nWould you like to place this order now? (Reply 'Yes' to confirm)"

        save_chat_message(active_sid, "assistant", reply, {"intent": "view_cart"})
        return {
            "session_id": active_sid,
            "reply": reply,
            "intent": "view_cart",
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 11. Order Cancellation Query
    cancel_resp = handle_order_cancellation(resolved_message, session)
    if cancel_resp:
        save_chat_message(active_sid, "assistant", cancel_resp["reply"], {"intent": cancel_resp["intent"]})
        return {
            "session_id": active_sid,
            "reply": cancel_resp["reply"],
            "intent": cancel_resp["intent"],
            "cart": cart,
            "pending_confirmation": False,
            "order_id": cancel_resp.get("order_id"),
            "status": cancel_resp.get("status"),
        }

    # 12. Explicit Item Removal ("remove mixture")
    remove_match = re.search(r"\b(remove|delete|take out|drop)\s+([a-zA-Z\s]{3,15})\b", resolved_message, re.IGNORECASE)
    if remove_match:
        target_candidate = remove_match.group(2).strip()
        matched_target = match_product_name(target_candidate)
        if matched_target:
            current_items = list(cart.get("items", []))
            remaining_items = [it for it in current_items if it.get("product") != matched_target]
            if len(remaining_items) < len(current_items):
                new_total = sum(it["price"] for it in remaining_items)
                new_cart = {"items": remaining_items, "total": new_total}
                update_chat_session(active_sid, cart=new_cart)
                reply = f"Removed {matched_target.title()} from your cart. Your updated total is **₹{new_total:.0f}**."
                save_chat_message(active_sid, "assistant", reply, {"intent": "item_removed"})
                return {
                    "session_id": active_sid,
                    "reply": reply,
                    "intent": "item_removed",
                    "cart": new_cart,
                    "pending_confirmation": len(remaining_items) > 0,
                    "order_id": None,
                    "status": None,
                }
            else:
                reply = f"{matched_target.title()} is not in your cart."
                save_chat_message(active_sid, "assistant", reply, {"intent": "item_not_found"})
                return {
                    "session_id": active_sid,
                    "reply": reply,
                    "intent": "item_not_found",
                    "cart": cart,
                    "pending_confirmation": len(current_items) > 0,
                    "order_id": None,
                    "status": None,
                }

    # 13. Category Enquiries (Sweet vs Savory)
    category_resp = handle_category_enquiry(resolved_message)
    if category_resp:
        new_context = {**context, **category_resp.get("context_update", {})}
        update_chat_session(active_sid, context=new_context)
        save_chat_message(active_sid, "assistant", category_resp["reply"], {"intent": category_resp["intent"]})
        return {
            "session_id": active_sid,
            "reply": category_resp["reply"],
            "intent": category_resp["intent"],
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 14. Product Description Queries ("what laddu is this")
    prod_desc_resp = handle_product_description(resolved_message, cart)
    if prod_desc_resp:
        new_context = {**context, **prod_desc_resp.get("context_update", {})}
        update_chat_session(active_sid, context=new_context)
        save_chat_message(active_sid, "assistant", prod_desc_resp["reply"], {"intent": prod_desc_resp["intent"]})
        return {
            "session_id": active_sid,
            "reply": prod_desc_resp["reply"],
            "intent": prod_desc_resp["intent"],
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 15. General Product / Price Enquiries
    enquiry_resp = handle_product_enquiry(resolved_message, context)
    if enquiry_resp:
        new_context = {**context, **enquiry_resp.get("context_update", {})}
        update_chat_session(active_sid, context=new_context)
        save_chat_message(active_sid, "assistant", enquiry_resp["reply"], {"intent": enquiry_resp["intent"]})
        return {
            "session_id": active_sid,
            "reply": enquiry_resp["reply"],
            "intent": enquiry_resp["intent"],
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 16. Incomplete Product Mentions (Product mentioned without quantity)
    detected_item_product = None
    for tok in resolved_message.split():
        matched = match_product_name(tok.strip("?,.!"))
        if matched:
            detected_item_product = matched
            break

    has_qty = re.search(r"\d+", resolved_message) is not None
    if detected_item_product and not has_qty and any(w in resolved_message for w in ["want", "need", "venum", "add", "order", "some", "give", "parcel"]):
        reply = f"What size of {detected_item_product.title()} would you like? We offer 250g, 500g, and 1kg packages."
        save_chat_message(active_sid, "assistant", reply, {"intent": "clarification_needed"})
        return {
            "session_id": active_sid,
            "reply": reply,
            "intent": "clarification_needed",
            "cart": cart,
            "pending_confirmation": len(cart.get("items", [])) > 0,
            "order_id": None,
            "status": None,
        }

    # 17. Multi-Item Order Extraction & Parsing
    extracted_items = extract_all_items(resolved_message)
    if not extracted_items:
        parsed_simple = parse_simple_order(resolved_message)
        if parsed_simple is not None and parsed_simple.get("intent") == "new_order":
            extracted_items = parsed_simple["items"]

    if not extracted_items:
        # Fall back to LLM extraction service
        extraction = extract(resolved_message)
        if extraction.intent == "product_enquiry":
            enq_resp = handle_product_enquiry(resolved_message, context)
            if enq_resp:
                new_context = {**context, **enq_resp.get("context_update", {})}
                update_chat_session(active_sid, context=new_context)
                save_chat_message(active_sid, "assistant", enq_resp["reply"], {"intent": "product_enquiry"})
                return {
                    "session_id": active_sid,
                    "reply": enq_resp["reply"],
                    "intent": "product_enquiry",
                    "cart": cart,
                    "pending_confirmation": len(cart.get("items", [])) > 0,
                    "order_id": None,
                    "status": None,
                }
        if extraction.needs_clarification or extraction.intent == "unclear" or any(it.quantity is None or it.unit is None for it in extraction.items):
            clarification_q = extraction.clarification_question or "What size or package quantity would you like? We offer 250g, 500g, and 1kg packages."
            if "Murukku" not in clarification_q:
                clarification_q += " We offer Murukku, Thattai, Madras Mixture, and Mothichoor Laddu."
            save_chat_message(active_sid, "assistant", clarification_q, {"intent": "clarification_needed"})
            return {
                "session_id": active_sid,
                "reply": clarification_q,
                "intent": "clarification_needed",
                "cart": cart,
                "pending_confirmation": len(cart.get("items", [])) > 0,
                "order_id": None,
                "status": None,
            }

        extracted_items = [it.model_dump() for it in extraction.items if it.quantity is not None and it.unit is not None]

    if extracted_items:
        valid_items = []
        unconfigured_items = []

        for item in extracted_items:
            p_name = item["product"]
            qty = item["quantity"]
            unit = item["unit"]
            is_conf, variant_str = is_configured_variant(p_name, qty, unit)
            if is_conf:
                valid_items.append(item)
            else:
                unconfigured_items.append({"product": p_name, "variant": variant_str})

        current_items = list(cart.get("items", []))
        added_items = []

        if valid_items:
            order_engine_result = process_order(valid_items)
            if order_engine_result["valid"]:
                added_items = order_engine_result["items"]
                for new_it in added_items:
                    existing_match = next((it for it in current_items if it["product"] == new_it["product"] and it.get("variant") == new_it.get("variant")), None)
                    if existing_match:
                        existing_match["quantity"] += new_it["quantity"]
                    else:
                        current_items.append(new_it)

        cart_recalc = process_order([
            {"product": it["product"], "quantity": it["quantity"], "unit": it["unit"]}
            for it in current_items
        ]) if current_items else {"valid": True, "items": [], "total": 0}

        updated_cart = {
            "items": cart_recalc["items"] if cart_recalc["valid"] else current_items,
            "total": cart_recalc["total"] if cart_recalc["valid"] else sum(it["price"] for it in current_items),
        }

        req_summary_parts = []
        for it in extracted_items:
            qty_str = f"{it['quantity']:g}{it['unit']}"
            req_summary_parts.append(f"{it['product'].title()} {qty_str}")
        req_summary = " and ".join(req_summary_parts)

        new_context = {
            **context,
            "last_requested_summary": req_summary,
            "unconfigured_items": unconfigured_items,
            "awaiting_add_confirmation": False,
        }
        if added_items:
            new_context["last_discussed_product"] = added_items[-1]["product"]
            new_context["last_discussed_size"] = added_items[-1].get("variant")

        update_chat_session(
            active_sid,
            cart=updated_cart,
            pending_confirmation=len(updated_cart["items"]) > 0,
            context=new_context,
        )

        if unconfigured_items:
            unconf = unconfigured_items[0]
            unconf_name = unconf["product"].title()
            unconf_var = unconf["variant"]
            avail_variants = PRODUCT_CATALOG.get(unconf["product"], {}).get("variants", {})
            avail_str = ", ".join(f"{s} (₹{p})" for s, p in avail_variants.items())

            if added_items:
                added_desc = ", ".join(
                    f"{it['product'].title()} ({it.get('variant') or str(it['quantity']) + it['unit']})"
                    for it in added_items
                )
                reply = (
                    f"Added **{added_desc}** to your draft order (current total: **₹{updated_cart['total']:.0f}**).\n\n"
                    f"Note: **{unconf_name} {unconf_var}** is not a configured size. "
                    f"Available sizes are: {avail_str}. Would you like one of these sizes instead?"
                )
            else:
                reply = (
                    f"**{unconf_name} {unconf_var}** is not a configured size. "
                    f"Available sizes are: {avail_str}. Which size would you like to choose?"
                )
        else:
            added_desc = ", ".join(
                f"{it['product'].title()} ({it.get('variant') or str(it['quantity']) + it['unit']})"
                for it in added_items
            )
            reply = (
                f"Added **{added_desc}** to your draft order. "
                f"Your current total is **₹{updated_cart['total']:.0f}**.\n\n"
                f"Would you like to add anything else, or confirm and place the order?"
            )

        save_chat_message(active_sid, "assistant", reply, {
            "intent": "items_added" if added_items else "unconfigured_size_query",
            "added_items": added_items,
            "cart_total": updated_cart["total"],
        })

        return {
            "session_id": active_sid,
            "reply": reply,
            "intent": "items_added" if added_items else "unconfigured_size_query",
            "cart": updated_cart,
            "pending_confirmation": len(updated_cart["items"]) > 0,
            "order_id": None,
            "status": None,
        }

    fallback_reply = (
        "I'm here to help you order traditional South Indian snacks! "
        "We have **Murukku**, **Thattai**, **Madras Mixture**, and **Mothichoor Laddu**. "
        "You can ask for prices (e.g. 'Price of 500g murukku') or directly order (e.g. 'Add 500g murukku and 1kg laddu')."
    )

    save_chat_message(active_sid, "assistant", fallback_reply, {"intent": "general_guidance"})

    return {
        "session_id": active_sid,
        "reply": fallback_reply,
        "intent": "general_guidance",
        "cart": cart,
        "pending_confirmation": len(cart.get("items", [])) > 0,
        "order_id": None,
        "status": None,
    }
