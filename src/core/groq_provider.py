import os
import time
from typing import Any, Dict, Generator, Optional

from dotenv import load_dotenv
from openai import OpenAI

from src.core.llm_provider import LLMProvider


class GroqProvider(LLMProvider):
    """OpenAI-compatible provider for Groq-hosted chat models."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        load_dotenv()
        model = model_name or os.getenv("GROQ_MODEL") or os.getenv("OPENAI_MODEL") or "llama-3.1-8b-instant"
        key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
        url = base_url or os.getenv("GROQ_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.groq.com/openai/v1"
        super().__init__(model_name=model, api_key=key)
        self.base_url = url.rstrip("/")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0,
        )
        latency_ms = int((time.time() - start_time) * 1000)
        usage_obj = response.usage
        usage = {
            "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage_obj, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage_obj, "total_tokens", 0) or 0,
        }
        return {
            "content": response.choices[0].message.content or "",
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "groq",
            "model": self.model_name,
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0,
            stream=True,
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token
