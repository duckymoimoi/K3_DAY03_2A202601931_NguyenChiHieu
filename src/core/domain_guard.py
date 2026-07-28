import unicodedata
from typing import Dict


OUT_OF_SCOPE_ANSWER = (
    "Demo này chỉ có dữ liệu về catalog iPhone/iPad/MacBook, coupon WINNER/LEGACY, "
    "shipping tới Hanoi/Saigon và policy cửa hàng. Mình không có evidence cho câu hỏi "
    "ngoài phạm vi đó nên sẽ không tự bịa câu trả lời."
)


def normalize_text(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )


def classify_ecommerce_scope(query: str) -> Dict[str, object]:
    normalized = normalize_text(query)
    product_terms = [
        "iphone",
        "ipad",
        "macbook",
    ]
    coupon_terms = [
        "winner",
        "legacy",
        "coupon",
        "discount",
        "ma ",
        "code",
    ]
    shipping_terms = [
        "ship",
        "shipping",
        "giao",
        "delivery",
    ]
    destination_terms = [
        "hanoi",
        "ha noi",
        "saigon",
        "ho chi minh",
    ]
    checkout_terms = [
        "stock",
        "ton kho",
        "price",
        "gia",
        "total",
        "tong tien",
        "bao nhieu",
        "how much",
        "buy",
        "purchase",
        "checkout",
        "order",
    ]
    policy_terms = [
        "return",
        "doi tra",
        "policy",
        "warranty",
        "bao hanh",
        "working hour",
        "opening hour",
        "gio lam viec",
        "mo cua",
    ]

    matched_terms = [
        term
        for term in product_terms + coupon_terms + shipping_terms + checkout_terms + policy_terms
        if term in normalized
    ]
    matched_destinations = [term for term in destination_terms if term in normalized]
    shipping_context = bool(matched_destinations) and any(term in normalized for term in shipping_terms)
    if matched_terms or shipping_context:
        if shipping_context:
            matched_terms.extend(matched_destinations)
        return {"in_scope": True, "reason": "matched_demo_scope", "matched_terms": matched_terms}

    return {
        "in_scope": False,
        "reason": "out_of_scope",
        "matched_terms": [],
        "answer": OUT_OF_SCOPE_ANSWER,
    }
