from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def usage_from_agent_trace(trace: list[dict]) -> dict:
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "latency_ms": 0}
    for step in trace:
        if step.get("type") != "llm":
            continue
        step_usage = step.get("usage", {})
        usage["prompt_tokens"] += step_usage.get("prompt_tokens", 0)
        usage["completion_tokens"] += step_usage.get("completion_tokens", 0)
        usage["total_tokens"] += step_usage.get("total_tokens", 0)
        usage["latency_ms"] += step.get("latency_ms", 0)
    return usage


def enrich_usage(usage: dict) -> dict:
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", 0)
    return {
        **usage,
        "completion_to_prompt_ratio": round(completion / prompt, 4) if prompt else 0,
        "cost_estimate_usd": round((total / 1000) * 0.01, 6),
    }


def main() -> None:
    live_demo = read_json("artifacts/live/live_system_demo.json")
    eval_summary = read_json("artifacts/evaluation/summary.json")
    v1_failure = read_json("artifacts/traces/failure_trace_v1_repeated_action.json")
    v2_recovery = read_json("artifacts/traces/recovery_trace_v2_repeated_action.json")

    baseline_usage = enrich_usage(live_demo["baseline_result"].get("usage", {}))
    agent_usage = enrich_usage(usage_from_agent_trace(live_demo["agent_result"].get("trace", [])))

    monitoring = {
        "source": "artifacts/live/live_system_demo.json",
        "baseline_live": baseline_usage,
        "agent_live": agent_usage,
        "deterministic_summary": eval_summary,
        "notes": [
            "Cost estimate dùng công thức demo trong telemetry: total_tokens / 1000 * 0.01.",
            "Latency là tổng latency của các LLM calls trong live demo.",
        ],
    }
    write_json(ROOT / "artifacts/monitoring/live_monitoring_summary.json", monitoring)

    ablation = {
        "experiment": "So sánh V1 chưa có repeated-action guardrail với V2 đã có guardrail",
        "input": "I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?",
        "v1": {
            "status": v1_failure["status"],
            "tool_path": v1_failure["tool_path"],
            "tool_calls": v1_failure["tool_calls"],
        },
        "v2": {
            "status": v2_recovery["status"],
            "tool_path": v2_recovery["tool_path"],
            "tool_calls": v2_recovery["tool_calls"],
        },
        "result": "V2 dừng sau 1 Tool call với repeated_action thay vì lãng phí 3 Tool calls rồi max_steps.",
    }
    write_json(ROOT / "artifacts/experiments/ablation_guardrail.json", ablation)

    print("Generated monitoring and experiment artifacts.")


if __name__ == "__main__":
    main()

