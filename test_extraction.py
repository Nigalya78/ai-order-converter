from app.llm_service import extract


TEST_MESSAGES = [
    "I need 500g murukku",
    "2kg laddu please",
    "What is the price of 500g murukku?",
    "Do you have mixture?",
    "I want murukku",
    "Send me some snacks",
    "Add 250g mixture also",
    "Remove the laddu",
    "Change murukku to 500g",
    "laddu 250gm podhum",
    "murukku 500g ah mathunga",
]


if __name__ == "__main__":
    for message in TEST_MESSAGES:
        print("\n" + "=" * 60)
        print("INPUT:", message)

        try:
            result = extract(message)
            print(result.model_dump_json(indent=2))
        except Exception as exc:
            print("ERROR:", type(exc).__name__, str(exc))
