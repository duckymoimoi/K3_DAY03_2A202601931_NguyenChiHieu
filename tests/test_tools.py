from src.tools import calc_shipping, check_stock, get_discount


def test_check_stock_returns_price_stock_and_status():
    result = check_stock("iPhone")

    assert result["ok"] is True
    assert result["price"] == 25_000_000
    assert result["stock"] == 15
    assert result["status"] == "in_stock"


def test_tools_return_structured_errors_instead_of_crashing():
    assert check_stock("Pixel")["error"] == "item_not_found"
    assert get_discount("NOPE")["error"] == "coupon_not_found"
    assert calc_shipping(destination="Hanoi")["error"] == "missing_argument"


def test_coupon_and_shipping_are_deterministic():
    assert get_discount("WINNER") == get_discount("winner")
    assert calc_shipping(0.8, "Hanoi") == calc_shipping(0.8, "Hanoi")


def test_expired_coupon_returns_no_discount_signal():
    result = get_discount("LEGACY")

    assert result["ok"] is False
    assert result["error"] == "coupon_expired"
    assert result["discount_percent"] == 0
