from app.catalog import PRODUCT_CATALOG
def process_order(items: list[dict]) -> dict:
    validated_items = []
    errors = []
    total = 0
    for item in items:
        product_name = item["product"].lower().strip()
        quantity = item["quantity"]
        if item["unit"] is None:
            errors.append(f"Unit is required for {product_name}")
            continue
        unit = item["unit"].lower().strip()
        if quantity is None:
            errors.append(f"Quantity is required for {product_name}")
            continue
        if quantity<=0:
            errors.append(f"Invalid quantity for {product_name}: {quantity}")
            continue
        if product_name not in PRODUCT_CATALOG:
            errors.append(f"Unknown product: {product_name}")
            continue
        
        if unit not in ["packet", "kg", "g"]:
            accept=["kg", "g", "packet"]
            errors.append(f"There is no variant for {product_name} in {unit}. Accepted units are : {', '.join(accept)}")
            continue
        if unit == "packet":
            errors.append(
                f"Packet pricing is not configured for {product_name}"
            )
            continue
        
        # Normalize the requested quantity into a catalog variant
        if unit == "kg":
            variant = f"{quantity:g}kg"
        elif unit == "g":
            variant = f"{quantity:g}g"
        product = PRODUCT_CATALOG[product_name]
        price = product["variants"].get(variant)
        if price is None:
            available=",".join(product["variants"].keys())
            errors.append(
                f"Variant {variant} is unavailable for {product_name}. Available variants : {available}"
            )
            continue
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