
from app.text_normalizer import normalize_message

test_messages = [
    "500gms laddu venum",
    "500 gm murukku",
    "1kgs thattai",
    "500 grams mixture",
    "250g laddu",
    "500 gms laddu VENUM",
]

for message in test_messages:
    print(f"{message} -> {normalize_message(message)}")
