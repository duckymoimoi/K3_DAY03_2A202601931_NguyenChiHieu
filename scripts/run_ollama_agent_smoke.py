from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.agent.agent_v2 import ReActAgentV2
from src.core.ollama_provider import OllamaProvider
from src.tools import TOOL_REGISTRY


QUERY = "I want to buy 2 iPhones using code WINNER and ship to Hanoi. The package weight is 0.8 kg. Total?"


def main() -> None:
    provider = OllamaProvider(model_name="qwen3.5:4b")
    agent = ReActAgentV2(provider, TOOL_REGISTRY, max_steps=8)
    result = agent.run(QUERY)

    artifact = {
        "provider": "ollama",
        "model": provider.model_name,
        "runs_local": True,
        "query": QUERY,
        "result": result,
        "note": "Live local Agent V2 smoke test. Deterministic grading artifacts still use ScriptedLLM.",
    }
    out = ROOT / "artifacts/live/ollama_agent_smoke.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": result["status"], "tool_path": result["tool_path"], "answer": result["answer"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
