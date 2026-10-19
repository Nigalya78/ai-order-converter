
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "orders.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_message TEXT NOT NULL,
                items_json TEXT NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'payment_pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_order(customer_message: str, items: list[dict], total: float) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO orders (customer_message, items_json, total)
            VALUES (?, ?, ?)
            """,
            (customer_message, json.dumps(items), total),
        )
        return cursor.lastrowid

def get_orders():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT order_id, customer_message, items_json,
                   total, status, created_at
            FROM orders
            ORDER BY order_id DESC
        """).fetchall()

        orders = []

        for row in rows:
            order = dict(row)
            order["items"] = json.loads(order.pop("items_json"))
            orders.append(order)

        return orders

def get_order_by_id(order_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT order_id, customer_message, items_json,
                   total, status, created_at
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()

        if row is None:
            return None

        order = dict(row)
        order["items"] = json.loads(order.pop("items_json"))
        return order

def update_order_status(order_id: int, status: str):
    allowed_transitions = {
        "payment_pending": ["confirmed", "cancelled"],
        "confirmed": ["cancelled"],
        "cancelled": [],
    }

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()

        if row is None:
            return False

        current_status = row["status"]

        if status == current_status:
            return True

        if status not in allowed_transitions.get(current_status, []):
            raise ValueError(
                f"Cannot change order status from "
                f"{current_status} to {status}"
            )

        conn.execute(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            (status, order_id),
        )

        return True


def update_order_items(
    order_id: int,
    customer_message: str,
    items: list[dict],
    total: float,
):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()

        if row is None:
            return False

        if row["status"] != "payment_pending":
            raise ValueError(
                "Only payment-pending orders can be modified."
            )

        conn.execute(
            """
            UPDATE orders
            SET customer_message = ?,
                items_json = ?,
                total = ?
            WHERE order_id = ?
            """,
            (
                customer_message,
                json.dumps(items),
                total,
                order_id,
            ),
        )

        return True