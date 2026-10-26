from app.product_matcher import match_product_name


def test_product_matching():
    assert match_product_name("murukku") == "murukku"
    assert match_product_name("muruku") == "murukku"
    assert match_product_name("laddu") == "laddu"
    assert match_product_name("chocolate") is None


if __name__ == "__main__":
    test_product_matching()
    print("All product matching tests passed!")