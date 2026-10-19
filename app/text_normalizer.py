
import re


def normalize_message(message: str) -> str:
    # Normalize kilogram variations first
    message = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*(?:kilograms?|kgs?)\b",
        r"\1kg",
        message,
        flags=re.IGNORECASE,
    )

    # Normalize gram variations
    message = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*(?:grams?|gms?|gm)\b",
        r"\1g",
        message,
        flags=re.IGNORECASE,
    )

    return message
