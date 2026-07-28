from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, List


CATALOG = {
    "iphone": {"item_name": "iPhone", "price": 25_000_000, "stock": 15, "weight_kg": 0.4},
    "ipad": {"item_name": "iPad", "price": 18_000_000, "stock": 8, "weight_kg": 0.5},
    "macbook": {"item_name": "MacBook", "price": 35_000_000, "stock": 0, "weight_kg": 2.0},
    "airpod": {"item_name": "AirPods Pro", "price": 6_000_000, "stock": 20, "weight_kg": 0.2},
    "apple watch": {"item_name": "Apple Watch", "price": 10_000_000, "stock": 12, "weight_kg": 0.3},
    "magic keyboard": {"item_name": "Magic Keyboard", "price": 3_500_000, "stock": 25, "weight_kg": 0.6},
    "studio display": {"item_name": "Studio Display", "price": 42_000_000, "stock": 2, "weight_kg": 6.3},
}

COUPONS = {
    "WINNER": {"discount_percent": 10, "valid": True},
    "LEGACY": {"discount_percent": 15, "valid": False},
    "STUDENT": {"discount_percent": 8, "valid": True},
    "WELCOME5": {"discount_percent": 5, "valid": True},
    "VIP20": {"discount_percent": 20, "valid": True},
}

SHIPPING_TABLE = {
    "hanoi": {"base_cost": 30_000, "per_kg": 10_000, "estimated_days": 1},
    "ha noi": {"base_cost": 30_000, "per_kg": 10_000, "estimated_days": 1},
    "saigon": {"base_cost": 35_000, "per_kg": 20_000, "estimated_days": 2},
    "ho chi minh": {"base_cost": 35_000, "per_kg": 20_000, "estimated_days": 2},
}

POLICY_DOCS = {
    "return": "Sản phẩm đủ điều kiện có thể đổi trả trong 7 ngày nếu còn hóa đơn và chưa hư hại do người dùng.",
    "warranty": "iPhone và iPad có bảo hành demo 12 tháng; phụ kiện có bảo hành demo 6 tháng.",
    "working_hours": "Cửa hàng demo làm việc từ 8:00 đến 21:00 hằng ngày.",
}


def _error(error: str, message: str, **extra: Any) -> Dict[str, Any]:
    payload = {"ok": False, "error": error, "message": message}
    payload.update(extra)
    return payload


def _normalize_item(item_name: str | None) -> str | None:
    if not item_name or not isinstance(item_name, str):
        return None
    name = item_name.strip().lower()
    aliases = {
        "airpods": "airpod",
        "airpods pro": "airpod",
        "watch": "apple watch",
        "apple watches": "apple watch",
        "keyboard": "magic keyboard",
        "display": "studio display",
    }
    if name in aliases:
        return aliases[name]
    if name.endswith("s"):
        name = name[:-1]
    return name


def check_stock(item_name: str | None = None) -> Dict[str, Any]:
    """Return deterministic stock, price, and weight for one catalog item."""
    key = _normalize_item(item_name)
    if not key:
        return _error("missing_argument", "item_name is required.", required=["item_name"])
    if key not in CATALOG:
        return _error("item_not_found", f"Item '{item_name}' is not in the demo catalog.")

    item = deepcopy(CATALOG[key])
    status = "in_stock" if item["stock"] > 0 else "out_of_stock"
    return {"ok": True, **item, "status": status}


def get_discount(coupon_code: str | None = None) -> Dict[str, Any]:
    """Validate a coupon code and return its discount if currently usable."""
    if not coupon_code or not isinstance(coupon_code, str):
        return _error("missing_argument", "coupon_code is required.", required=["coupon_code"])

    code = coupon_code.strip().upper()
    coupon = COUPONS.get(code)
    if coupon is None:
        return _error("coupon_not_found", f"Coupon '{coupon_code}' does not exist.", coupon_code=code)
    if not coupon["valid"]:
        return _error(
            "coupon_expired",
            f"Coupon '{code}' is expired, so no discount should be applied.",
            coupon_code=code,
            valid=False,
            discount_percent=0,
        )

    return {"ok": True, "coupon_code": code, "valid": True, **coupon}


def list_store_options(include_expired: bool = False) -> Dict[str, Any]:
    """Return the demo store products, coupon codes, and shipping destinations."""
    products = []
    for item in CATALOG.values():
        products.append(
            {
                **deepcopy(item),
                "status": "in_stock" if item["stock"] > 0 else "out_of_stock",
            }
        )

    coupons = []
    for code, coupon in COUPONS.items():
        if coupon["valid"] or include_expired:
            coupons.append({"coupon_code": code, **deepcopy(coupon)})

    destinations = sorted({key.title() for key in SHIPPING_TABLE})
    return {
        "ok": True,
        "products": products,
        "coupons": coupons,
        "shipping_destinations": destinations,
    }


def calc_shipping(weight: float | int | None = None, destination: str | None = None) -> Dict[str, Any]:
    """Calculate deterministic shipping cost for a destination and package weight."""
    if weight is None:
        return _error("missing_argument", "weight is required.", required=["weight"])
    if not destination or not isinstance(destination, str):
        return _error("missing_argument", "destination is required.", required=["destination"])

    try:
        numeric_weight = float(weight)
    except (TypeError, ValueError):
        return _error("invalid_argument", "weight must be a number.", received=weight)
    if numeric_weight <= 0:
        return _error("invalid_argument", "weight must be greater than 0.", received=weight)

    destination_key = destination.strip().lower()
    rule = SHIPPING_TABLE.get(destination_key)
    if rule is None:
        return _error("unsupported_destination", f"Shipping to '{destination}' is not supported.")

    shipping_cost = int(rule["base_cost"] + numeric_weight * rule["per_kg"])
    return {
        "ok": True,
        "destination": destination,
        "weight": numeric_weight,
        "shipping_cost": shipping_cost,
        "estimated_days": rule["estimated_days"],
    }


def calc_total(
    item_quantity: int | None = None,
    price_per_item: float | int | None = None,
    discount_percent: float | int | None = 0,
    shipping_cost: float | int | None = 0,
) -> Dict[str, Any]:
    """Calculate final checkout total from grounded observations."""
    required = {
        "item_quantity": item_quantity,
        "price_per_item": price_per_item,
        "discount_percent": discount_percent,
        "shipping_cost": shipping_cost,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        return _error("missing_argument", "calc_total requires all numeric checkout fields.", required=missing)

    try:
        quantity = int(item_quantity)
        price = float(price_per_item)
        discount = float(discount_percent)
        shipping = float(shipping_cost)
    except (TypeError, ValueError):
        return _error("invalid_argument", "All calc_total inputs must be numeric.", received=required)

    if quantity <= 0 or price < 0 or not 0 <= discount <= 100 or shipping < 0:
        return _error("invalid_argument", "Quantity, price, discount, or shipping is outside the accepted range.")

    subtotal = int(quantity * price)
    discount_amount = int(subtotal * discount / 100)
    total = int(subtotal - discount_amount + shipping)
    return {
        "ok": True,
        "item_quantity": quantity,
        "price_per_item": int(price),
        "subtotal": subtotal,
        "discount_percent": discount,
        "discount_amount": discount_amount,
        "shipping_cost": int(shipping),
        "total": total,
        "currency": "VND",
        "formula": "(price_per_item * item_quantity) * (1 - discount_percent / 100) + shipping_cost",
    }


def search_policy(query: str | None = None) -> Dict[str, Any]:
    """Search the demo store policy knowledge base."""
    if not query or not isinstance(query, str):
        return _error("missing_argument", "query is required.", required=["query"])

    normalized = query.strip().lower()
    matches = []
    for key, text in POLICY_DOCS.items():
        if key in normalized or any(word in text.lower() for word in normalized.split()):
            matches.append({"id": key, "text": text})

    if not matches:
        return _error("policy_not_found", f"No policy document matched '{query}'.")

    return {"ok": True, "query": query, "matches": matches}


def _tool(name: str, description: str, func: Callable[..., Dict[str, Any]], input_example: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_example": input_example,
        "function": func,
    }


TOOL_REGISTRY: List[Dict[str, Any]] = [
    _tool(
        "list_store_options",
        "Read-only store overview. Use when users ask what products, coupon codes, or demo options are available.",
        list_store_options,
        {"include_expired": False},
    ),
    _tool(
        "check_stock",
        "Read-only catalog lookup. Input: {\"item_name\": \"iPhone\"}. Returns price, stock, weight_kg, and status.",
        check_stock,
        {"item_name": "iPhone"},
    ),
    _tool(
        "get_discount",
        "Read-only coupon validator. Input: {\"coupon_code\": \"WINNER\"}. Returns validity and discount_percent.",
        get_discount,
        {"coupon_code": "WINNER"},
    ),
    _tool(
        "calc_shipping",
        "Read-only shipping calculator. Input: {\"weight\": 0.8, \"destination\": \"Hanoi\"}. Returns shipping_cost and estimated_days.",
        calc_shipping,
        {"weight": 0.8, "destination": "Hanoi"},
    ),
    _tool(
        "calc_total",
        "Checkout calculator. Input: {\"item_quantity\": 2, \"price_per_item\": 25000000, \"discount_percent\": 10, \"shipping_cost\": 38000}. Returns final VND total.",
        calc_total,
        {"item_quantity": 2, "price_per_item": 25000000, "discount_percent": 10, "shipping_cost": 38000},
    ),
    _tool(
        "search_policy",
        "Read-only Search Tool over demo store policy docs. Input: {\"query\": \"return policy\"}. Returns matching policy passages.",
        search_policy,
        {"query": "return policy"},
    ),
]
