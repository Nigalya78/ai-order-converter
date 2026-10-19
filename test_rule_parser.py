
from app.text_normalizer import normalize_message
from app.rule_parser import parse_simple_order

messages = [
    "500gms laddu venum",
    "1kg murukku venum",
    "250g mixture venum",
    "How much is 500g laddu?",
    "What is the price of murukku?",
    "I want laddu",
    "500g laddu",
    "500gms laddu and 1kg murukku venum",
    "250g mixture and 500g thattai venum",
]

for message in messages:
    normalized = normalize_message(message)
    result = parse_simple_order(normalized)

    print(f"\nInput: {message}")
    print(f"Parsed: {result}")
