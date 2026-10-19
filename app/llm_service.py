import ollama
from app.schemas import OrderExtraction

MODEL_NAME="llama3.1"
def extract(message: str) -> OrderExtraction:
    response=ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role":"system",
                "content":"""
You convert customer messages into structured order data.
Understand informal and Tamil-English messages.
Extract the customer's intent,product names,quantities, and units.
Allowed intents: new_order,modify_order,product_enquiry,cancel_order,unclear
Allowed units: packet,kg,g
Never invent products or quantities.
If the message is unclear, ask for clarification.
Do not calculate prices
If a customer asks to order a product but does not specify
a quantity or package size:
- Set needs_clarification to true.
- Set quantity to null.
- Ask the customer to specify the quantity or size.
- Do not treat an incomplete order request as a product enquiry.


INTENT CLASSIFICATION RULES:

1. If the customer asks about a product's price, cost, or available sizes,
   classify the intent as "product_enquiry".

2. Examples:
   - "What is the price of murukku?"
   - "What is the price of 500g murukku?"
   - "How much does 1kg laddu cost?"
   - "Do you have 250g mixture?"
   All of these are "product_enquiry".

3. For product_enquiry:
   - Put the product name in "items".
   - Extract the requested size into quantity and unit when specified.
   - Example: "What is the price of 500g murukku?"
     items = [{"product": "murukku", "quantity": 500, "unit": "g"}]
   - If no size is specified, quantity and unit must be null.
   - Always set "changes" to [].
   - Do not ask for clarification if the product can be identified.

4. Use "changes" only when the customer wants to modify an existing order,
   not when asking about a product or its price.

INTENT RULES:
- "I want some murukku" means a new order, not a product enquiry.
- Use "new_order" when the customer expresses a desire to buy a product.
- Use "product_enquiry" only when the customer asks for information about a product.
- For intent "new_order", "items" MUST contain all requested products.
- For intent "new_order", "changes" MUST be an empty list [].
- Each item must contain product, quantity, and unit.
- If quantity or unit is missing, use null for the missing field and set needs_clarification to true.
- Never assume "packet", "kg", or "g" when the customer has not specified a unit. Set unit to null.
- Use "changes" only for modifying an existing order.

MISSING QUANTITY RULES:
- Never use "clarification" as a product name.
- Only include products explicitly mentioned by the customer.
- Allowed units are choices, not products or order items.
- If quantity or package size is missing, return only the actual requested product with missing fields set to null.
- Never guess a quantity, weight, or package size.
- If the customer wants to order a product without specifying quantity or size, set "needs_clarification" to true.
- Set the missing quantity to null.
- Ask which quantity or package size the customer wants.
- Do not treat an incomplete order as a product enquiry.

ORDER MODIFICATION RULES:
- If the customer asks to add an item to an existing order,
  classify the intent as "modify_order".
- Words and phrases such as "add", "also add", "include",
  and " சேர்த்து" indicate an order modification when referring
  to an existing order.
- For modifications, put each requested change in the "changes"
  list.
- Use action "add" for items being added.
- Example:
  Message: "Add 250g mixture also"
  Intent: "modify_order"
  Changes: [{"action": "add", "product": "mixture",
             "quantity": 250, "unit": "g"}]

For order modifications, always use the changes field.

Examples:
- "Add 250g mixture also"
  -> intent: modify_order
  -> changes: [{action: "add", product: "mixture",
                quantity: 250, unit: "g"}]

- "Remove the laddu"
  -> intent: modify_order
  -> changes: [{action: "remove", product: "laddu"}]

- "Change murukku to 500g"
  -> intent: modify_order
  -> changes: [{action: "set_quantity", product: "murukku",
                quantity: 500, unit: "g"}]

For modify_order, do not put modifications in items.
Use changes only. If the message is ambiguous, ask for clarification.
"""

            },
            {
                "role":"user",
                "content":message,
            },
        ],
        format=OrderExtraction.model_json_schema(),
    )

    import json
    data = json.loads(response["message"]["content"])
    if data.get("intent") == "new_order":
        data["changes"] = []

    message_lower = message.lower()

    price_question = any(
        phrase in message_lower
        for phrase in [
            "price",
            "how much",
            "cost",
            "rate",
        ]
    )

    if price_question and data.get("intent") in {"unclear", "product_enquiry"}:
        data["intent"] = "product_enquiry"
        data["changes"] = []
        data["needs_clarification"] = False
        data["clarification_question"] = None

        extracted_items = data.get("items", [])
        extracted_changes = data.get("changes", [])

        if not extracted_items and extracted_changes:
            data["items"] = [
                {
                    "product": extracted_changes[0]["product"],
                    "quantity": extracted_changes[0].get("quantity"),
                    "unit": extracted_changes[0].get("unit"),
                }
            ]

    for item in data.get("items", []):
        if isinstance(item.get("unit"), str):
            item["unit"] = item["unit"].lower()
    return OrderExtraction.model_validate(data)