from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.agent.agent_v2 import ReActAgentV2
from src.chatbot import BaselineChatbot
from src.core.groq_provider import GroqProvider
from src.tools import TOOL_REGISTRY


BASELINE_QUERY = "Tôi muốn mua 2 iPhone, dùng mã WINNER và giao tới Hà Nội. Tổng tiền là bao nhiêu?"
AGENT_QUERY = "I want to buy 2 iPhones using code WINNER and ship to Hanoi. The package weight is 0.8 kg. Total?"


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    provider = GroqProvider()

    baseline = BaselineChatbot(provider).chat(BASELINE_QUERY)
    agent = ReActAgentV2(provider, TOOL_REGISTRY, max_steps=8).run(AGENT_QUERY)

    demo = {
        "provider": "groq",
        "model": provider.model_name,
        "runs_local": False,
        "baseline_query": BASELINE_QUERY,
        "agent_query": AGENT_QUERY,
        "baseline_result": baseline,
        "agent_result": agent,
        "demo_passed": baseline["tool_calls"] == 0
        and baseline["classification"] == "safe_fallback"
        and agent["status"] == "final_answer"
        and "45,038,000" in agent["answer"],
        "system_signals": [
            "Live System Demo bằng Groq API",
            "Failure Handling: evidence gate, repeated-action detection, calc_total prerequisite",
            "Tool mở rộng: calc_total và search_policy",
            "Monitoring: token, latency, cost estimate trong live trace",
        ],
    }

    write_json(ROOT / "artifacts/live/live_system_demo.json", demo)
    print(
        json.dumps(
            {
                "demo_passed": demo["demo_passed"],
                "model": provider.model_name,
                "baseline_status": baseline["classification"],
                "agent_status": agent["status"],
                "agent_tool_path": agent["tool_path"],
                "agent_answer": agent["answer"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
