from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, List


CATALOG = {
    "iphone": {"item_name": "iPhone", "price": 25_000_000, "stock": 15, "weight_kg": 0.4},
    "ipad": {"item_name": "iPad", "price": 18_000_000, "stock": 8, "weight_kg": 0.5},
    "macbook": {"item_name": "MacBook", "price": 35_000_000, "stock": 0, "weight_kg": 2.0},
}

COUPONS = {
    "WINNER": {"discount_percent": 10, "valid": True},
    "LEGACY": {"discount_percent": 15, "valid": False},
}

SHIPPING_TABLE = {
    "hanoi": {"base_cost": 30_000, "per_kg": 10_000, "estimated_days": 1},
    "ha noi": {"base_cost": 30_000, "per_kg": 10_000, "estimated_days": 1},
    "saigon": {"base_cost": 35_000, "per_kg": 20_000, "estimated_days": 2},
    "ho chi minh": {"base_cost": 35_000, "per_kg": 20_000, "estimated_days": 2},
}


def _error(error: str, message: str, **extra: Any) -> Dict[str, Any]:
    payload = {"ok": False, "error": error, "message": message}
    payload.update(extra)
    return payload


def _normalize_item(item_name: str | None) -> str | None:
    if not item_name or not isinstance(item_name, str):
        return None
    name = item_name.strip().lower()
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

    return {"ok": True, "coupon_code": code, "valid": True, "discount_percent": coupon["discount_percent"]}


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


def _tool(name: str, description: str, func: Callable[..., Dict[str, Any]], input_example: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_example": input_example,
        "function": func,
    }


TOOL_REGISTRY: List[Dict[str, Any]] = [
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
]
