from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.llm_service import extract
from app.order_engine import process_order
from app.database import (
    init_db,
    save_order,
    get_orders,
    get_order_by_id,
    update_order_status,
    update_order_items,
    save_pending_clarification,
    get_pending_clarification,
    get_order_stats,
    format_whatsapp_receipt,
    get_chat_session,
    get_chat_messages,
    reset_chat_session,
)
import urllib.parse
from typing import Literal
from app.catalog import PRODUCT_CATALOG
from app.text_normalizer import normalize_message
from app.rule_parser import parse_simple_order
from app.schemas import OrderExtraction, OrderChange, ChatRequest, ChatResponse
import re
from app.chat_service import process_chat_message

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

class Message(BaseModel):
    message: str

class OrderStatusUpdate(BaseModel):
    status: Literal["payment_pending", "confirmed", "cancelled"]

class OrderModification(BaseModel):
    customer_message: str
    items: list[dict]
    action: Literal["add", "replace"] = "add"

class OrderMessage(BaseModel):
    message: str

@app.post("/extract")
def question(request: Message):
    
    normalized_message = normalize_message(request.message)

    parsed = parse_simple_order(normalized_message)

    if parsed is not None:
        result = OrderExtraction.model_validate(parsed)
    else:
        result = extract(normalized_message)
    if result.intent == "product_enquiry":
        product_name = (
            result.items[0].product.strip().lower()
            if result.items
            else None
        )

        product = PRODUCT_CATALOG.get(product_name)

        if product is None:
            return {
                "extraction": result,
                "order": None,
                "order_id": None,
                "status": None,
                "message": (
                    f"Sorry, {product_name or 'that product'} "
                    "is not available in our catalog."
                ),
            }
        variants = product["variants"]
        requested_size = None

        if result.items:
            quantity = result.items[0].quantity
            unit = result.items[0].unit

            if quantity is not None and unit is not None:
                if unit == "g":
                    requested_size = f"{quantity:g}g"
                elif unit == "kg":
                    requested_size = f"{quantity:g}kg"

        if requested_size is not None:
            if requested_size in variants:
                price_details = [
                    {
                        "size": requested_size,
                        "price": variants[requested_size],
                    }
                ]
            else:
                available_sizes = ", ".join(variants.keys())
                return {
                    "extraction": result,
                    "order": None,
                    "order_id": None,
                    "status": None,
                    "product": product_name,
                    "prices": [],
                    "message": (
                        f"{requested_size} is unavailable. "
                        f"Available sizes: {available_sizes}."
                    ),
                }
        else:
            price_details = [
                {"size": size, "price": price}
                for size, price in variants.items()
            ]

        if len(price_details) == 1:
            size = price_details[0]["size"]
            price = price_details[0]["price"]

            response_message = (
                f"The price of {size} {product_name} is "
                f"₹{price}. Would you like to place an order?"
            )
        else:
            price_list = ", ".join(
                f"{item['size']} - ₹{item['price']}"
                for item in price_details
            )

            response_message = (
                f"Here are the available sizes and prices for "
                f"{product_name}: {price_list}. "
                "Would you like to place an order?"
            )

        return {
            "extraction": result,
            "order": None,
            "order_id": None,
            "status": None,
            "product": product_name,
            "prices": price_details,
            "message": response_message,
        }
    if result.intent == "cancel_order":
        return {
            "extraction": result,
            "order": None,
            "order_id": None,
            "status": None,
            "message": "Cancellation request detected. Please identify the existing order."
        }
    if result.intent == "unclear":
        return {
            "extraction": result,
            "order": None,
            "order_id": None,
            "status": None,
            "message": result.clarification_question or "Could you clarify your request?"
        }
    if (
        result.intent in {"new_order", "modify_order"}
        and any(
            item.quantity is None or item.unit is None
            for item in result.items
        )
    ):
        result.needs_clarification = True
        if not result.clarification_question:
            result.clarification_question = (
                "Please specify the quantity or package size."
            )
    if result.needs_clarification:
        return {
            "extraction": result,
            "order": None,
            "message": (
                result.clarification_question
                or "Please specify the quantity or package size."
            ),
        }
    order_result = process_order(
        [item.model_dump() for item in result.items]
    )
    order_id = None

    if order_result["valid"]:
        order_id = save_order(
            customer_message=request.message,
            items=order_result["items"],
            total=order_result["total"],
        )
    return {
        "extraction": result,
        "order": order_result,
        "message": (
            "Order processed successfully."
            if order_result["valid"]
            else "Please check the order errors and correct your request."
        ),
        "order_id": order_id,
        "status": "payment_pending" if order_id is not None else None,
    }

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Conversational AI Chat-to-Order endpoint.
    Maintains multi-turn context, draft cart, product enquiries, and order placement.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        result = process_chat_message(request.session_id, request.message)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(exc)}")


@app.get("/chat/sessions/{session_id}")
def get_chat_session_endpoint(session_id: str):
    """
    Retrieves full conversation session state, draft cart, and chronological history.
    Enables resuming conversations seamlessly after a browser refresh.
    """
    session = get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation session not found.")

    messages = get_chat_messages(session_id)
    return {
        "session_id": session["session_id"],
        "cart": session.get("cart", {"items": [], "total": 0}),
        "pending_confirmation": session.get("pending_confirmation", False),
        "created_order_id": session.get("created_order_id"),
        "messages": messages,
    }


@app.post("/chat/sessions/{session_id}/reset")
def reset_chat_session_endpoint(session_id: str):
    """
    Resets the active draft cart and context while keeping the session intact.
    """
    session = get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversation session not found.")

    reset_state = reset_chat_session(session_id)
    return {
        "message": "Session reset successfully.",
        "session": reset_state,
    }


@app.get("/catalog")
def get_catalog():
    """Returns the snack product catalogue with available variants and pricing."""
    formatted_catalog = []
    for product_id, details in PRODUCT_CATALOG.items():
        formatted_catalog.append({
            "id": product_id,
            "name": details.get("name", product_id.title()),
            "category": details.get("category", "Snack"),
            "description": details.get("description", ""),
            "variants": [
                {"size": size, "price": price}
                for size, price in details["variants"].items()
            ],
        })
    return {"products": formatted_catalog}


@app.get("/orders/stats")
def order_statistics():
    """Returns aggregated operational and financial statistics."""
    return get_order_stats()


@app.get("/orders/{order_id}/receipt")
def get_order_receipt(order_id: int):
    """Generates customer receipt formatted for WhatsApp."""
    order = get_order_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    receipt_text = format_whatsapp_receipt(order)
    encoded_text = urllib.parse.quote(receipt_text)

    return {
        "order_id": order_id,
        "receipt": receipt_text,
        "whatsapp_url": f"https://wa.me/?text={encoded_text}",
    }


@app.get("/orders")
def list_orders(status: str | None = None, search: str | None = None):
    orders = get_orders()

    allowed_statuses = {
        "payment_pending",
        "confirmed",
        "cancelled",
    }

    if status is not None:
        if status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Use payment_pending, confirmed, or cancelled.",
            )

        orders = [
            order for order in orders
            if order["status"] == status
        ]

    if search is not None and search.strip():
        q = search.lower().strip()
        orders = [
            order for order in orders
            if q in str(order["order_id"])
            or q in (order.get("customer_message") or "").lower()
            or any(q in item.get("product", "").lower() for item in order.get("items", []))
        ]

    return {
        "count": len(orders),
        "orders": orders,
    }

@app.get("/orders/{order_id}")
def get_single_order(order_id: int):
    order = get_order_by_id(order_id)

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order

@app.patch("/orders/{order_id}/status")
def change_order_status(order_id: int, request: OrderStatusUpdate):
    try:
        updated = update_order_status(order_id, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order_id,
        "status": request.status,
        "message": "Order status updated successfully.",
    }


@app.patch("/orders/{order_id}/items")
def modify_order(order_id: int, request: OrderModification):
    existing_order = get_order_by_id(order_id)

    if existing_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if existing_order["status"] != "payment_pending":
        raise HTTPException(
            status_code=400,
            detail="Only payment-pending orders can be modified.",
        )
    new_result = process_order(request.items)

    if not new_result["valid"]:
        raise HTTPException(status_code=400, detail=new_result["errors"])
    if request.action == "add":
        combined_items = existing_order["items"] + new_result["items"]
    else:
        combined_items = new_result["items"]
    combined_total = sum(item["price"] for item in combined_items)
    try:
        updated = update_order_items(
            order_id=order_id,
            customer_message=request.customer_message,
            items=combined_items,
            total=combined_total,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order_id,
        "items": combined_items,
        "total": combined_total,
        "message": "Order items updated successfully.",
    }



@app.patch("/orders/{order_id}/modify-message")
def modify_order_from_message(
    order_id: int,
    request: OrderMessage,
):
    existing_order = get_order_by_id(order_id)

    if existing_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if existing_order["status"] != "payment_pending":
        raise HTTPException(
            status_code=400,
            detail="Only payment-pending orders can be modified.",
        )
    previous_message = existing_order.get("customer_message", "")

    if any(
        line.strip().lower()
        == f"modification: {request.message.strip()}".lower()
        for line in previous_message.splitlines()
    ):
        raise HTTPException(
            status_code=409,
            detail="This modification message has already been applied.",
        )
    pending = get_pending_clarification(order_id)

    if pending:
        reply = normalize_message(request.message).strip().lower()
        pending_changes = pending.get("changes", [])

        size_map = {
            "250g": (250, "g"),
            "250 g": (250, "g"),
            "500g": (500, "g"),
            "500 g": (500, "g"),
            "1kg": (1, "kg"),
            "1 kg": (1, "kg"),
        }

        if reply in size_map:
            if len(pending_changes) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Could not identify which item needs a size.",
                )

            pending_change = pending_changes[0]
            action = pending_change.get("action")
            product = pending_change.get("product")

            if action not in {"add", "set_quantity"} or not product:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "This pending modification cannot be "
                        "completed with a size alone."
                    ),
                )

            quantity, unit = size_map[reply]
            result = OrderExtraction(
                intent="modify_order",
                items=[],
                changes=[
                    OrderChange(
                        action=action,
                        product=product,
                        quantity=quantity,
                        unit=unit,
                    )
                ],
                needs_clarification=False,
                clarification_question=None,
            )

        else:
            original_message = pending["message"]
            combined_message = (
                f"{original_message}. Customer clarification: "
                f"{request.message.strip()}"
            )
            result = extract(normalize_message(combined_message))

    else:
        normalized_message = normalize_message(request.message).strip()
        add_match = re.fullmatch(
            r"add\s+(\d+(?:\.\d+)?)\s*"
            r"(kilograms?|kg|grams?|g)\s+(.+)",
            normalized_message,
            re.IGNORECASE,
        )

        if add_match:
            quantity = float(add_match.group(1))
            unit_text = add_match.group(2).lower()
            product = add_match.group(3).strip().lower()

            unit = (
                "kg"
                if unit_text.startswith("kg")
                or unit_text.startswith("kilogram")
                else "g"
            )

            result = OrderExtraction(
                intent="modify_order",
                items=[],
                changes=[
                    OrderChange(
                        action="add",
                        product=product,
                        quantity=quantity,
                        unit=unit,
                    )
                ],
                needs_clarification=False,
                clarification_question=None,
            )
        
        else:
            tanglish_size_change = re.fullmatch(
                r"([a-zA-Z]+)\s+(\d+(?:\.\d+)?)\s*"
                r"(kg|kgs|kilograms?|g|gm|gms|grams?)"
                r"(?:\s+(podhum|mattum\s+venum|ah\s+mathunga))?",
                normalized_message,
                re.IGNORECASE,
            )
            print("DEBUG normalized:", repr(normalized_message))
            print("DEBUG Tanglish match:", tanglish_size_change)
            if tanglish_size_change:
                product = tanglish_size_change.group(1).lower()
                quantity = float(tanglish_size_change.group(2))
                unit_text = tanglish_size_change.group(3).lower()

                unit = (
                    "kg"
                    if unit_text.startswith(("kg", "kilo"))
                    else "g"
                )

                result = OrderExtraction(
                    intent="modify_order",
                    items=[],
                    changes=[
                        OrderChange(
                            action="set_quantity",
                            product=product,
                            quantity=quantity,
                            unit=unit,
                        )
                    ],
                    needs_clarification=False,
                    clarification_question=None,
                )
            else:
                result = extract(normalized_message)
    incomplete_changes = any(
        (
            change.action in {"add", "set_quantity"}
            and (
                not change.product
                or change.quantity is None
                or change.unit is None
            )
        )
        or (
            change.action == "remove"
            and not change.product
        )
        for change in result.changes
    )

    if incomplete_changes:
        result.needs_clarification = True

        if not result.clarification_question:
            change = next(
                change
                for change in result.changes
                if (
                    change.action in {"add", "set_quantity"}
                    and (
                        not change.product
                        or change.quantity is None
                        or change.unit is None
                    )
                )
                or (
                    change.action == "remove"
                    and not change.product
                )
            )

            if change.action == "add":
                if not change.product:
                    question = "Which product would you like to add?"
                else:
                    question = (
                        f"What size of {change.product} "
                        "would you like to add?"
                    )
            elif change.action == "set_quantity":
                if not change.product:
                    question = "Which product would you like to change?"
                else:
                    question = (
                        f"What new size of {change.product} "
                        "would you like?"
                    )
            else:
                question = "Which product would you like to remove?"

            result.clarification_question = question
    if result.needs_clarification:
        save_pending_clarification(
            order_id,
            {
                "message": (
                    pending["message"]
                    if pending
                    else request.message.strip()
                ),
                "changes": [
                    change.model_dump()
                    for change in result.changes
                ],
            },
        )

        return {
            "order_id": order_id,
            "needs_clarification": True,
            "message": (
                result.clarification_question
                or "Could you clarify the requested modification?"
            ),
            "changes": [
                change.model_dump()
                for change in result.changes
            ],
        }

    if result.intent != "modify_order":
        raise HTTPException(
            status_code=400,
            detail="Message was not identified as an order modification.",
        )

    if not result.changes:
        raise HTTPException(
            status_code=400,
            detail="No order changes were identified in the message.",
        )
    updated_items = list(existing_order["items"])

    for change in result.changes:
        if not change.product:
            raise HTTPException(
                status_code=400,
                detail="Product is required for this modification.",
            )

        product = change.product.strip().lower()

        matching_indices = [
            i
            for i, item in enumerate(updated_items)
            if item["product"].strip().lower() == product
        ]

        if change.action == "add":
            new_result = process_order([
                {
                    "product": product,
                    "quantity": change.quantity,
                    "unit": change.unit,
                }
            ])

            if not new_result["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=new_result["errors"],
                )

            updated_items.extend(new_result["items"])

        elif change.action == "remove":
            if not matching_indices:
                raise HTTPException(
                    status_code=400,
                    detail=f"{product} is not in this order.",
                )

            if len(matching_indices) > 1:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Multiple {product} items found. "
                        "Specify which size to remove."
                    ),
                )

            updated_items.pop(matching_indices[0])

        elif change.action == "set_quantity":
            if not matching_indices:
                raise HTTPException(
                    status_code=400,
                    detail=f"{product} is not in this order.",
                )

            if len(matching_indices) > 1:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Multiple {product} items found. "
                        "Specify which size to change."
                    ),
                )

            new_result = process_order([
                {
                    "product": product,
                    "quantity": change.quantity,
                    "unit": change.unit,
                }
            ])

            if not new_result["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=new_result["errors"],
                )

            updated_items[matching_indices[0]] = new_result["items"][0]
    combined_total = sum(item["price"] for item in updated_items)
    updated_message = (
        f"{previous_message}\nModification: {request.message.strip()}"
    ).strip()

    try:
        updated = update_order_items(
            order_id=order_id,
            customer_message=updated_message,
            items=updated_items,
            total=combined_total,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")
    save_pending_clarification(order_id, None)

    return {
        "order_id": order_id,
        "changes": [
            change.model_dump() for change in result.changes
        ],
        "items": updated_items,
        "total": combined_total,
        "message": "Order modified successfully.",
    }