import json
import time
from typing import Any, Dict, Generator, Optional

import requests

from src.core.llm_provider import LLMProvider


class OllamaProvider(LLMProvider):
    """LLMProvider implementation for a local Ollama server."""

    def __init__(self, model_name: str = "qwen2.5:3b", base_url: str = "http://localhost:11434"):
        super().__init__(model_name=model_name)
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt or "",
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        latency_ms = int((time.time() - start_time) * 1000)

        prompt_tokens = payload.get("prompt_eval_count", 0)
        completion_tokens = payload.get("eval_count", 0)
        return {
            "content": payload.get("response", "").strip(),
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "latency_ms": latency_ms,
            "provider": "ollama",
            "model": self.model_name,
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        with requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt or "",
                "stream": True,
                "options": {"temperature": 0},
            },
            stream=True,
            timeout=120,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                payload = json.loads(line.decode("utf-8"))
                token = payload.get("response", "")
                if token:
                    yield token
