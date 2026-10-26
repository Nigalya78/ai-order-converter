
import datetime
import json
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    Float,
    DateTime,
    Boolean,
    text,
    select,
)
from sqlalchemy.engine import URL

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Check your project's .env file."
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

metadata = MetaData()

orders_table = Table(
    "orders",
    metadata,
    Column("order_id", Integer, primary_key=True, autoincrement=True),
    Column("customer_message", Text, nullable=False),
    Column("items_json", Text, nullable=False),
    Column("total", Float, nullable=False),
    Column(
        "status",
        Text,
        nullable=False,
        server_default=text("'payment_pending'"),
    ),
    Column("pending_clarification", Text, nullable=True),
    Column(
        "created_at",
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
    ),
)

chat_sessions_table = Table(
    "chat_sessions",
    metadata,
    Column("session_id", Text, primary_key=True),
    Column("cart_json", Text, nullable=False, server_default=text("'{\"items\": [], \"total\": 0}'")),
    Column("pending_confirmation", Boolean, nullable=False, server_default=text("false")),
    Column("created_order_id", Integer, nullable=True),
    Column("context_json", Text, nullable=True),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

chat_messages_table = Table(
    "chat_messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", Text, nullable=False, index=True),
    Column("role", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("metadata_json", Text, nullable=True),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)


def init_db():
    metadata.create_all(engine)


def save_order(
    customer_message: str,
    items: list[dict],
    total: float,
) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            orders_table.insert()
            .values(
                customer_message=customer_message,
                items_json=json.dumps(items),
                total=total,
            )
            .returning(orders_table.c.order_id)
        )
        return result.scalar_one()


def _format_order(row):
    if row is None:
        return None

    order = dict(row)
    order["items"] = json.loads(order.pop("items_json"))
    return order


def get_orders():
    with engine.connect() as conn:
        result = conn.execute(
            select(
                orders_table.c.order_id,
                orders_table.c.customer_message,
                orders_table.c.items_json,
                orders_table.c.total,
                orders_table.c.status,
                orders_table.c.created_at,
            ).order_by(orders_table.c.order_id.desc())
        )

        return [
            _format_order(row)
            for row in result.mappings().all()
        ]


def get_order_by_id(order_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            select(
                orders_table.c.order_id,
                orders_table.c.customer_message,
                orders_table.c.items_json,
                orders_table.c.total,
                orders_table.c.status,
                orders_table.c.created_at,
            ).where(orders_table.c.order_id == order_id)
        )

        return _format_order(result.mappings().first())


def update_order_status(order_id: int, status: str):
    allowed_transitions = {
        "payment_pending": ["confirmed", "cancelled"],
        "confirmed": ["cancelled"],
        "cancelled": [],
    }

    with engine.begin() as conn:
        row = conn.execute(
            select(orders_table.c.status).where(
                orders_table.c.order_id == order_id
            )
        ).first()

        if row is None:
            return False

        current_status = row.status

        if status == current_status:
            return True

        if status not in allowed_transitions.get(current_status, []):
            raise ValueError(
                f"Cannot change order status from "
                f"{current_status} to {status}"
            )

        conn.execute(
            orders_table.update()
            .where(orders_table.c.order_id == order_id)
            .values(status=status)
        )

        return True


def update_order_items(
    order_id: int,
    customer_message: str,
    items: list[dict],
    total: float,
):
    with engine.begin() as conn:
        row = conn.execute(
            select(orders_table.c.status).where(
                orders_table.c.order_id == order_id
            )
        ).first()

        if row is None:
            return False

        if row.status != "payment_pending":
            raise ValueError(
                "Only payment-pending orders can be modified."
            )

        conn.execute(
            orders_table.update()
            .where(orders_table.c.order_id == order_id)
            .values(
                customer_message=customer_message,
                items_json=json.dumps(items),
                total=total,
            )
        )

        return True


def save_pending_clarification(
    order_id: int,
    clarification: dict | None,
):
    with engine.begin() as conn:
        conn.execute(
            orders_table.update()
            .where(orders_table.c.order_id == order_id)
            .values(
                pending_clarification=(
                    json.dumps(clarification)
                    if clarification
                    else None
                )
            )
        )

def get_pending_clarification(order_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            select(orders_table.c.pending_clarification).where(
                orders_table.c.order_id == order_id
            )
        )

        row = result.first()

        if row is None or row.pending_clarification is None:
            return None

        return json.loads(row.pending_clarification)


def get_order_stats() -> dict:
    """Aggregates operational and sales statistics across all orders."""
    all_orders = get_orders()
    total_orders = len(all_orders)
    pending_orders = sum(1 for o in all_orders if o["status"] == "payment_pending")
    confirmed_orders = sum(1 for o in all_orders if o["status"] == "confirmed")
    cancelled_orders = sum(1 for o in all_orders if o["status"] == "cancelled")

    total_revenue = sum(o["total"] for o in all_orders if o["status"] != "cancelled")
    confirmed_revenue = sum(o["total"] for o in all_orders if o["status"] == "confirmed")

    active_orders_count = total_orders - cancelled_orders
    avg_order_value = round(total_revenue / active_orders_count, 2) if active_orders_count > 0 else 0.0

    product_counts: dict[str, int] = {}
    for o in all_orders:
        if o["status"] != "cancelled":
            for item in o.get("items", []):
                p = item.get("product", "unknown").lower()
                product_counts[p] = product_counts.get(p, 0) + 1

    top_products = [
        {"product": p, "count": c}
        for p, c in sorted(product_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "confirmed_orders": confirmed_orders,
        "cancelled_orders": cancelled_orders,
        "total_revenue": total_revenue,
        "confirmed_revenue": confirmed_revenue,
        "avg_order_value": avg_order_value,
        "top_products": top_products,
    }


def format_whatsapp_receipt(order: dict) -> str:
    """Generates a clean, formatted text receipt for customer WhatsApp sharing."""
    order_id = order["order_id"]
    status_emoji = {
        "payment_pending": "⏳ Payment Pending",
        "confirmed": "✅ Confirmed",
        "cancelled": "❌ Cancelled",
    }.get(order["status"], order["status"])

    items_text = []
    for item in order.get("items", []):
        size = item.get("variant") or f"{item.get('quantity')}{item.get('unit', '')}"
        items_text.append(f"• {item.get('product', '').title()} ({size}) - ₹{item.get('price')}")

    lines = [
        "📦 *AI Snack Order Confirmation*",
        f"Order ID: *#{order_id}*",
        f"Status: *{status_emoji}*",
        "",
        "*Items Ordered:*",
        *(items_text if items_text else ["• No items"]),
        "",
        f"*Total Amount:* *₹{order.get('total', 0):.0f}*",
        "",
        "Thank you for ordering with us! 🙏",
    ]
    return "\n".join(lines)

def create_or_get_chat_session(session_id: str | None = None) -> dict:
    """Retrieves an existing conversation session or initializes a fresh one."""
    if not session_id or not session_id.strip():
        session_id = str(uuid.uuid4())

    with engine.begin() as conn:
        row = conn.execute(
            select(chat_sessions_table).where(
                chat_sessions_table.c.session_id == session_id
            )
        ).mappings().first()

        if row is not None:
            data = dict(row)
            data["cart"] = json.loads(data.pop("cart_json") or '{"items": [], "total": 0}')
            data["context"] = json.loads(data.pop("context_json") or "{}")
            return data
        empty_cart = {"items": [], "total": 0}
        empty_context = {}
        conn.execute(
            chat_sessions_table.insert().values(
                session_id=session_id,
                cart_json=json.dumps(empty_cart),
                pending_confirmation=False,
                created_order_id=None,
                context_json=json.dumps(empty_context),
            )
        )
        return {
            "session_id": session_id,
            "cart": empty_cart,
            "pending_confirmation": False,
            "created_order_id": None,
            "context": empty_context,
        }



def get_chat_session(session_id: str) -> dict | None:
    """Fetches session metadata, draft cart, and context state."""
    with engine.connect() as conn:
        row = conn.execute(
            select(chat_sessions_table).where(
                chat_sessions_table.c.session_id == session_id
            )
        ).mappings().first()

        if row is None:
            return None

        data = dict(row)
        data["cart"] = json.loads(data.pop("cart_json") or '{"items": [], "total": 0}')
        data["context"] = json.loads(data.pop("context_json") or "{}")
        return data


def update_chat_session(
    session_id: str,
    cart: dict | None = None,
    pending_confirmation: bool | None = None,
    created_order_id: int | None = None,
    context: dict | None = None,
) -> bool:
    """Updates cart, confirmation status, context, or linked order for a session."""
    values: dict = {"updated_at": datetime.datetime.utcnow()}
    if cart is not None:
        values["cart_json"] = json.dumps(cart)
    if pending_confirmation is not None:
        values["pending_confirmation"] = pending_confirmation
    if created_order_id is not None:
        values["created_order_id"] = created_order_id
    if context is not None:
        values["context_json"] = json.dumps(context)

    with engine.begin() as conn:
        result = conn.execute(
            chat_sessions_table.update()
            .where(chat_sessions_table.c.session_id == session_id)
            .values(**values)
        )
        return result.rowcount > 0


def reset_chat_session(session_id: str) -> dict:
    """Resets the cart and context for a session while retaining session ID."""
    empty_cart = {"items": [], "total": 0}
    empty_context = {}
    with engine.begin() as conn:
        conn.execute(
            chat_sessions_table.update()
            .where(chat_sessions_table.c.session_id == session_id)
            .values(
                cart_json=json.dumps(empty_cart),
                pending_confirmation=False,
                created_order_id=None,
                context_json=json.dumps(empty_context),
                updated_at=datetime.datetime.utcnow(),
            )
        )
    return {
        "session_id": session_id,
        "cart": empty_cart,
        "pending_confirmation": False,
        "created_order_id": None,
        "context": empty_context,
    }


def save_chat_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> int:
    """Appends a customer or assistant message to session history."""
    with engine.begin() as conn:
        result = conn.execute(
            chat_messages_table.insert().values(
                session_id=session_id,
                role=role,
                content=content,
                metadata_json=json.dumps(metadata) if metadata else None,
            ).returning(chat_messages_table.c.id)
        )
        return result.scalar_one()


def get_chat_messages(session_id: str, limit: int = 50) -> list[dict]:
    """Retrieves chronological message history for a session."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(chat_messages_table)
            .where(chat_messages_table.c.session_id == session_id)
            .order_by(chat_messages_table.c.id.asc())
            .limit(limit)
        ).mappings().all()

        messages = []
        for r in rows:
            m = dict(r)
            m["metadata"] = json.loads(m.pop("metadata_json")) if m.get("metadata_json") else None
            if m.get("created_at") and hasattr(m["created_at"], "isoformat"):
                m["created_at"] = m["created_at"].isoformat()
            messages.append(m)
        return messages
