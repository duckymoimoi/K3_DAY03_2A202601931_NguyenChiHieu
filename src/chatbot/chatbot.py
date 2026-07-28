import unicodedata
from typing import Any, Dict, Optional

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


ECOMMERCE_BASELINE_PROMPT = """
You are the baseline e-commerce chatbot for the Lab 3 Chatbot vs ReAct Agent
exercise.

Rules:
- Make exactly one direct response from the LLM.
- Do not call tools, databases, APIs, inventory systems, coupon validators, or
  shipping calculators.
- If the user asks for dynamic facts such as stock, price, coupon validity,
  shipping fee, delivery availability, or final checkout total, be transparent
  that the baseline cannot verify those facts.
- You may explain what evidence would be needed, but you must not invent a
  grounded total.

For the hook question "I want to buy 2 iPhones, use code WINNER and ship to
Ha Noi. What is the total?", say that the answer needs evidence for stock and
price, coupon WINNER validity, shipping fee, and final total.
""".strip()


class BaselineChatbot:
    """One-call chatbot baseline with zero tool access."""

    def __init__(self, llm: LLMProvider, system_prompt: Optional[str] = None):
        self.llm = llm
        self.system_prompt = system_prompt or ECOMMERCE_BASELINE_PROMPT

    def chat(self, user_input: str) -> Dict[str, Any]:
        logger.log_event(
            "BASELINE_CHATBOT_START",
            {"input": user_input, "model": self.llm.model_name},
        )

        result = self.llm.generate(user_input, system_prompt=self.system_prompt)
        answer = result.get("content", "").strip()
        usage = result.get("usage", {})
        latency_ms = result.get("latency_ms", 0)
        provider = result.get("provider", "unknown")
        missing_evidence = self._missing_dynamic_evidence(user_input)

        tracker.track_request(provider, self.llm.model_name, usage, latency_ms)

        response = {
            "answer": answer,
            "llm_calls": 1,
            "tool_calls": 0,
            "grounded": False,
            "classification": "safe_fallback" if missing_evidence else "direct_answer",
            "missing_evidence": missing_evidence,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": provider,
        }

        logger.log_event(
            "BASELINE_CHATBOT_END",
            {
                "llm_calls": response["llm_calls"],
                "tool_calls": response["tool_calls"],
                "grounded": response["grounded"],
                "missing_evidence": response["missing_evidence"],
            },
        )
        return response

    def _missing_dynamic_evidence(self, user_input: str) -> list[str]:
        normalized = self._normalize_text(user_input)
        evidence = []

        if any(term in normalized for term in ["iphone", "ipad", "macbook", "stock", "ton kho", "price", "gia"]):
            evidence.append("stock_and_price")
        if any(term in normalized for term in ["winner", "coupon", "discount", "ma ", "code"]):
            evidence.append("coupon_validity")
        if any(term in normalized for term in ["ha noi", "hanoi", "saigon", "shipping", "ship", "giao"]):
            evidence.append("shipping_fee")
        if any(term in normalized for term in ["total", "tong tien", "bao nhieu", "how much"]):
            evidence.append("final_total")

        return evidence

    def _normalize_text(self, text: str) -> str:
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFD", text.lower())
            if unicodedata.category(char) != "Mn"
        )
        return without_accents
