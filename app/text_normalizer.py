import re

def normalize_message(message: str) -> str:
    """
    Normalizes informal English, Tamil, and Tanglish text messages into
    standardized units and quantities.
    """
    if not message:
        return ""

    text = message
    # Spelled-out gram quantities
    text = re.sub(
        r"\b(?:five\s*hundred|500)\s*(?:grams?|gms?|gm)\b",
        "500g",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:two\s*hundred\s*(?:and\s*)?fifty|250)\s*(?:grams?|gms?|gm)\b",
        "250g",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:seven\s*hundred\s*(?:and\s*)?fifty|750)\s*(?:grams?|gms?|gm)\b",
        "750g",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:one\s*hundred|100)\s*(?:grams?|gms?|gm)\b",
        "100g",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:quarter\s*(?:kg|kilo|kilogram)?|kaal\s*(?:kg|kilo|kilogram)?|kaalkilo|1/4\s*(?:kg|kilo|kilogram))\b",
        "250g",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:half\s*(?:kg|kilo|kilogram)?|ara\s*(?:kg|kilo|kilogram)?|arai\s*(?:kg|kilo|kilogram)?|arakilo|1/2\s*(?:kg|kilo|kilogram))\b",
        "500g",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:three\s*quarter\s*(?:kg|kilo|kilogram)?|mukkaal\s*(?:kg|kilo|kilogram)?|mukkaalkilo|3/4\s*(?:kg|kilo|kilogram))\b",
        "750g",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:oru|one)\s*(?:kg|kilo|kilogram)\b", "1kg", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:rendu|two)\s*(?:kg|kilo|kilograms?)\b", "2kg", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:moonu|three)\s*(?:kg|kilo|kilograms?)\b", "3kg", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*(?:kilograms?|kgs?|kilos?)\b",
        r"\1kg",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*(?:grams?|gms?|gm)\b",
        r"\1g",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip()

    return text
