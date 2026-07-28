from typing import Any, Dict, Optional

from src.core.llm_provider import LLMProvider


class ScriptedLLM(LLMProvider):
    def __init__(self, responses: list[str], model_name: str = "scripted-llm"):
        super().__init__(model_name)
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        content = self.responses.pop(0) if self.responses else "Final Answer: No scripted response remains."
        return {
            "content": content,
            "usage": {"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40},
            "latency_ms": 1,
            "provider": "scripted",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        yield self.generate(prompt, system_prompt)["content"]
