from pydantic import BaseModel, Field
from typing import Literal

class OrderItem(BaseModel):
    product: str
    quantity: float | None = Field(default=None, gt=0)
    unit: Literal["packet","kg","g"] | None = Field(default=None)

class OrderChange(BaseModel):
    action: Literal["add", "set_quantity", "remove"]
    product: str
    quantity: float | None = None
    unit: Literal["packet", "kg", "g"] | None = None

class OrderExtraction(BaseModel):
    intent: Literal["new_order","modify_order","product_enquiry","cancel_order","unclear"]
    items: list[OrderItem]=Field(default_factory=list)
    needs_clarification: bool=False
    clarification_question: str | None=None
    changes: list[OrderChange] = Field(default_factory=list)


