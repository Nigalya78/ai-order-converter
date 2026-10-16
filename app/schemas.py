from pydantic import BaseModel, Field
from typing import Literal

class OrderItem(BaseModel):
    product: str
    quantity: float=Field(gt=0)
    unit: Literal["Packet","kg","g"]

class OrderExtraction(BaseModel):
    intent: Literal["new_order","modify_order","product_enquiry","cancel_order","unclear"]
    items: list[OrderItem]=Field(default_factory=list)
    needs_clarification: bool=False
    clarification_question: str | None=None