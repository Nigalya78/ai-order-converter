
from pydantic import BaseModel, Field
from typing import Literal


class OrderItem(BaseModel):
    product: str
    quantity: float | None = Field(default=None, gt=0)
    unit: Literal["packet", "kg", "g"] | None = None


class OrderChange(BaseModel):
    action: Literal["add", "set_quantity", "remove"]
    product: str | None = None
    quantity: float | None = Field(default=None, gt=0)
    unit: Literal["packet", "kg", "g"] | None = None


class OrderExtraction(BaseModel):
    intent: Literal[
        "new_order",
        "modify_order",
        "product_enquiry",
        "cancel_order",
        "unclear"
    ]

    items: list[OrderItem] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    changes: list[OrderChange] = Field(default_factory=list)

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class CartItem(BaseModel):
    product: str
    variant: str | None = None
    quantity: float
    unit: str
    price: float


class CartState(BaseModel):
    items: list[CartItem] = Field(default_factory=list)
    total: float = 0.0


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    cart: CartState
    pending_confirmation: bool = False
    order_id: int | None = None
    status: str | None = None
