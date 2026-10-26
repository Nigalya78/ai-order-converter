from app.catalog import PRODUCT_CATALOG
from app.product_matcher import match_product_name

def process_order(items: list[dict]) -> dict:
    validated_items = []
    errors = []
    total = 0
    for item in items:
        raw_product_name = item.get("product")
        if not raw_product_name:
            errors.append("Product name is required")
            continue

        product_name = match_product_name(raw_product_name)

        if product_name is None:
            errors.append(f"Unknown product: {raw_product_name}")
            continue
        quantity = item["quantity"]
        if item["unit"] is None:
            errors.append(f"Unit is required for {product_name}")
            continue
        unit = item["unit"].lower().strip()
        if quantity is None:
            errors.append(f"Quantity is required for {product_name}")
            continue
        if quantity <= 0:
            errors.append(
                f"Invalid quantity for {product_name}: {quantity}"
            )
            continue
        if unit not in ["packet", "kg", "g"]:
            accept = ["kg", "g", "packet"]
            errors.append(
                f"There is no variant for {product_name} in {unit}. "
                f"Accepted units are: {', '.join(accept)}"
            )
            continue
        if unit == "packet":
            errors.append(
                f"Packet pricing is not configured for {product_name}"
            )
            continue
        product = PRODUCT_CATALOG[product_name]
        if unit == "kg":
            quantity_in_grams = quantity * 1000
        else:
            quantity_in_grams = quantity
        if quantity_in_grams >= 1000:
            variant = f"{quantity_in_grams / 1000:g}kg"
        else:
            variant = f"{quantity_in_grams:g}g"
        variants = product["variants"]
        if variant in variants:
            price = variants[variant]
        else:
            one_kg_price = variants.get("1kg")
            if one_kg_price is None:
                errors.append(
                    f"Cannot calculate a price for {product_name}: "
                    "1kg pricing is not configured."
                )
                continue
            price = round(quantity_in_grams / 1000 * one_kg_price)
        validated_items.append({
            "product": product_name,
            "variant": variant,
            "quantity": quantity,
            "unit": unit,
            "price": price,
        })
        total += price
    return {
        "items": validated_items,
        "errors": errors,
        "total": total,
        "valid": len(errors) == 0 and len(validated_items) > 0,
    }