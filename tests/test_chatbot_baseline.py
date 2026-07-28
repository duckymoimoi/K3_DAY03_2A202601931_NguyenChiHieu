from typing import Any, Dict, Optional

from src.chatbot import BaselineChatbot
from src.core.llm_provider import LLMProvider


class FakeLLM(LLMProvider):
    def __init__(self, responses):
        super().__init__("fake-ecommerce-llm")
        self.responses = list(responses)
        self.calls = []

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        return {
            "content": self.responses.pop(0),
            "usage": {
                "prompt_tokens": 45,
                "completion_tokens": 32,
                "total_tokens": 77,
            },
            "latency_ms": 12,
            "provider": "fake",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        yield "not used"


def test_static_policy_question_uses_one_llm_call_and_no_tools():
    llm = FakeLLM(["You can return eligible products within 7 days."])
    chatbot = BaselineChatbot(llm)

    result = chatbot.chat("What is your return policy?")

    assert len(llm.calls) == 1
    assert result["llm_calls"] == 1
    assert result["tool_calls"] == 0
    assert result["classification"] == "direct_answer"
    assert result["missing_evidence"] == []


def test_multistep_ecommerce_hook_is_safe_fallback_without_tool_evidence():
    llm = FakeLLM(
        [
            "I cannot calculate a grounded checkout total from chat alone. "
            "I would need stock and price evidence, confirmation that WINNER "
            "is still valid, and a shipping fee for Ha Noi."
        ]
    )
    chatbot = BaselineChatbot(llm)

    result = chatbot.chat(
        "Toi muon mua 2 iPhone, dung ma WINNER va giao toi Ha Noi. "
        "Tong tien la bao nhieu?"
    )

    assert len(llm.calls) == 1
    assert result["llm_calls"] == 1
    assert result["tool_calls"] == 0
    assert result["classification"] == "safe_fallback"
    assert result["grounded"] is False
    assert result["missing_evidence"] == [
        "stock_and_price",
        "coupon_validity",
        "shipping_fee",
        "final_total",
    ]
    assert "cannot calculate a grounded checkout total" in result["answer"]


def test_baseline_out_of_scope_question_stops_before_llm_call():
    llm = FakeLLM(["Final Answer: unsupported answer"])
    chatbot = BaselineChatbot(llm)

    result = chatbot.chat("Who won the football match yesterday?")

    assert result["classification"] == "out_of_scope"
    assert result["llm_calls"] == 0
    assert result["tool_calls"] == 0
    assert llm.calls == []


def test_vietnamese_accented_checkout_query_marks_total_as_missing_evidence():
    llm = FakeLLM(["Không thể tính tổng tiền có bằng chứng nếu chưa gọi Tool."])
    chatbot = BaselineChatbot(llm)

    result = chatbot.chat("Tôi muốn mua 2 iPhone, dùng mã WINNER và giao tới Hà Nội. Tổng tiền là bao nhiêu?")

    assert result["classification"] == "safe_fallback"
    assert result["missing_evidence"] == [
        "stock_and_price",
        "coupon_validity",
        "shipping_fee",
        "final_total",
    ]
