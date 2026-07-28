from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))

from src.chatbot import BaselineChatbot
from src.core.ollama_provider import OllamaProvider


PROMPT = (
    "Toi muon mua 2 iPhone, dung ma WINNER va giao toi Ha Noi. "
    "Tong tien la bao nhieu?"
)


def main() -> None:
    provider = OllamaProvider(model_name="qwen2.5:3b")
    chatbot = BaselineChatbot(provider)
    result = chatbot.chat(PROMPT)

    artifact = {
        "provider": "ollama",
        "model": provider.model_name,
        "runs_local": True,
        "prompt": PROMPT,
        "result": result,
        "note": "Live local smoke test only. Deterministic grading artifacts still use ScriptedLLM.",
    }
    out = ROOT / "artifacts/live/ollama_smoke.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(artifact, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
