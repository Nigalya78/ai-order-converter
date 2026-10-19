from fastapi import FastAPI,HTTPException
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
)
from typing import Literal
from app.catalog import PRODUCT_CATALOG
from app.text_normalizer import normalize_message
from app.rule_parser import parse_simple_order
from app.text_normalizer import normalize_message
from app.schemas import OrderExtraction

app = FastAPI()
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
        
    # Handle product enquiries
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

        # Check whether the customer requested a specific size
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

    # Handle cancellation requests separately
    if result.intent == "cancel_order":
        return {
            "extraction": result,
            "order": None,
            "order_id": None,
            "status": None,
            "message": "Cancellation request detected. Please identify the existing order."
        }

    # Handle unclear messages
    if result.intent == "unclear":
        return {
            "extraction": result,
            "order": None,
            "order_id": None,
            "status": None,
            "message": result.clarification_question or "Could you clarify your request?"
        }

    # Check whether any item has a missing quantity
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
    # Stop here if clarification is needed
    if result.needs_clarification:
        return {
            "extraction": result,
            "order": None,
            "message": (
                result.clarification_question
                or "Please specify the quantity or package size."
            ),
        }
    # Process the order only when clarification is not needed
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

@app.get("/orders")
def list_orders(status: str | None = None):
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
    # 1. Find the existing order
    existing_order = get_order_by_id(order_id)

    if existing_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if existing_order["status"] != "payment_pending":
        raise HTTPException(
            status_code=400,
            detail="Only payment-pending orders can be modified.",
        )

    # 2. Process the newly submitted items
    new_result = process_order(request.items)

    if not new_result["valid"]:
        raise HTTPException(status_code=400, detail=new_result["errors"])

    # 3. Add new items or replace existing items
    if request.action == "add":
        combined_items = existing_order["items"] + new_result["items"]
    else:
        combined_items = new_result["items"]

    # 4. Recalculate the total from all items
    combined_total = sum(item["price"] for item in combined_items)

    # 5. Save the updated order
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
    # 1. Find the existing order
    existing_order = get_order_by_id(order_id)

    if existing_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if existing_order["status"] != "payment_pending":
        raise HTTPException(
            status_code=400,
            detail="Only payment-pending orders can be modified.",
        )
    # Prevent an exact modification message from being applied twice
    previous_message = existing_order.get("customer_message", "")

    if any(
        line.strip().lower() == f"modification: {request.message.strip()}".lower()
        for line in previous_message.splitlines()
    ):
        raise HTTPException(
            status_code=409,
            detail="This modification message has already been applied.",
        )
    # 2. Normalize the customer's message
    normalized_message = normalize_message(request.message)

    # 3. Use the LLM to understand the modification
    result = extract(normalized_message)

    if result.intent != "modify_order":
        raise HTTPException(
            status_code=400,
            detail="Message was not identified as an order modification.",
        )

    
    # 4. Ensure the LLM identified at least one change
    if not result.changes:
        raise HTTPException(
            status_code=400,
            detail="No order changes were identified in the message.",
        )

    # 5. Start with the existing order items
    updated_items = list(existing_order["items"])

    # 6. Apply each requested change
    for change in result.changes:
        product = change.product.strip().lower()

        matching_indices = [
            i for i, item in enumerate(updated_items)
            if item["product"].strip().lower() == product
        ]

        if change.action == "add":
            new_result = process_order([{
                "product": product,
                "quantity": change.quantity,
                "unit": change.unit,
            }])

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
                    detail=f"Multiple {product} items found. Specify which size to remove.",
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
                    detail=f"Multiple {product} items found. Specify which size to change.",
                )

            if change.quantity is None or change.unit is None:
                raise HTTPException(
                    status_code=400,
                    detail="Please specify the new size.",
                )

            new_result = process_order([{
                "product": product,
                "quantity": change.quantity,
                "unit": change.unit,
            }])

            if not new_result["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=new_result["errors"],
                )

            updated_items[matching_indices[0]] = new_result["items"][0]

    # 7. Recalculate the order total
    combined_total = sum(item["price"] for item in updated_items)

    # 8. Record the modification
    previous_message = existing_order.get("customer_message", "")
    updated_message = (
        f"{previous_message}\nModification: {request.message}"
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
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return {
        "order_id": order_id,
        "changes": [
            change.model_dump() for change in result.changes
        ],
        "items": updated_items,
        "total": combined_total,
        "message": "Order modified successfully.",
    }
