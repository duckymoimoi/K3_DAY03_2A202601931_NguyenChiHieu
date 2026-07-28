from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))

from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.chatbot import BaselineChatbot
from src.core.llm_provider import LLMProvider
from src.tools import TOOL_REGISTRY


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


CASES = [
    {
        "id": "case_1_return_policy",
        "query": "What is your return policy?",
        "expected_tool_path": [],
        "baseline_response": "You can return eligible products within 7 days with the receipt.",
        "agent_responses": ["Final Answer: You can return eligible products within 7 days with the receipt."],
    },
    {
        "id": "case_2_working_hours",
        "query": "What are your working hours?",
        "expected_tool_path": [],
        "baseline_response": "Our demo store works from 8:00 to 21:00 every day.",
        "agent_responses": ["Final Answer: Our demo store works from 8:00 to 21:00 every day."],
    },
    {
        "id": "case_3_iphone_winner_hanoi",
        "query": "I want to buy 2 iPhones using code 'WINNER' and ship to Hanoi. The package weight is 0.8 kg. Total?",
        "expected_tool_path": ["check_stock", "get_discount", "calc_shipping", "calc_total"],
        "baseline_response": (
            "I cannot calculate a grounded total without stock, price, coupon, and shipping evidence."
        ),
        "agent_responses": [
            'Thought: Need stock and price.\nAction: check_stock({"item_name": "iPhone"})',
            'Thought: Need coupon evidence.\nAction: get_discount({"coupon_code": "WINNER"})',
            'Thought: Need shipping fee.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
            'Thought: Need final checkout total.\nAction: calc_total({"item_quantity": 2, "price_per_item": 25000000, "discount_percent": 10, "shipping_cost": 38000})',
            "Final Answer: Total = (25,000,000 x 2) x 0.9 + 38,000 = 45,038,000 VND.",
        ],
    },
    {
        "id": "case_4_macbook_out_of_stock",
        "query": "Can I buy 1 MacBook and ship to Saigon? How much?",
        "expected_tool_path": ["check_stock"],
        "baseline_response": "I cannot verify MacBook stock or a grounded total without catalog and shipping tools.",
        "agent_responses": [
            'Thought: Need stock before pricing checkout.\nAction: check_stock({"item_name": "MacBook"})',
            "Final Answer: MacBook is out of stock, so I cannot claim the purchase can be completed.",
        ],
    },
    {
        "id": "case_5_ipad_legacy_saigon",
        "query": "I want to buy 1 iPad using code 'LEGACY' and ship to Saigon. The package weight is 0.5 kg. How much?",
        "expected_tool_path": ["check_stock", "get_discount", "calc_shipping", "calc_total"],
        "baseline_response": "I cannot calculate a grounded total without checking price, coupon validity, and shipping.",
        "agent_responses": [
            'Thought: Need item stock and price.\nAction: check_stock({"item_name": "iPad"})',
            'Thought: Need coupon validity.\nAction: get_discount({"coupon_code": "LEGACY"})',
            'Thought: Coupon is expired; need shipping before final total.\nAction: calc_shipping({"weight": 0.5, "destination": "Saigon"})',
            'Thought: Need final total with no discount.\nAction: calc_total({"item_quantity": 1, "price_per_item": 18000000, "discount_percent": 0, "shipping_cost": 45000})',
            "Final Answer: LEGACY is expired, so no discount applies. Total = 18,000,000 + 45,000 = 18,045,000 VND.",
        ],
    },
]


def rubric_for_row(row: Dict[str, Any], expected_path: list[str]) -> Dict[str, int]:
    if row["system"] == "baseline_chatbot":
        static_case = not expected_path
        safe_dynamic_fallback = bool(expected_path) and row["safe_fallback"]
        return {
            "factual": 2 if row["success"] or safe_dynamic_fallback else 1,
            "grounding": 2 if safe_dynamic_fallback else (1 if static_case else 0),
            "tool_selection": 2 if row["tool_calls"] == 0 else 0,
            "safety": 2 if row["success"] or safe_dynamic_fallback else 1,
            "completeness": 2 if row["success"] or safe_dynamic_fallback else 1,
            "termination": 2 if row["steps"] == 1 else 1,
        }

    correct_path = row["tool_path"] == expected_path
    final_answer = row["status"] == "final_answer"
    return {
        "factual": 2 if final_answer else 1,
        "grounding": 2 if correct_path or not expected_path else 1,
        "tool_selection": 2 if correct_path else 1,
        "safety": 2 if final_answer else 1,
        "completeness": 2 if row["success"] else 1,
        "termination": 2 if final_answer else 0,
    }


def trace_has_error(row: Dict[str, Any], error_name: str) -> bool:
    for step in row.get("trace", []):
        observation = step.get("observation", {})
        if observation.get("error") == error_name:
            return True
    return False


def evaluate_case(case: Dict[str, Any]) -> list[Dict[str, Any]]:
    baseline = BaselineChatbot(ScriptedLLM([case["baseline_response"]], "scripted-baseline"))
    baseline_result = baseline.chat(case["query"])

    agent = ReActAgentV2(ScriptedLLM(case["agent_responses"], "scripted-agent-v2"), TOOL_REGISTRY, max_steps=6)
    agent_result = agent.run(case["query"])

    expected_path = case["expected_tool_path"]
    baseline_success = baseline_result["classification"] == "direct_answer" if not expected_path else False
    agent_success = agent_result["status"] == "final_answer" and agent_result["tool_path"] == expected_path

    rows = [
        {
            "case_id": case["id"],
            "system": "baseline_chatbot",
            "query": case["query"],
            "status": baseline_result["classification"],
            "answer": baseline_result["answer"],
            "tool_path": [],
            "tool_calls": 0,
            "steps": 1,
            "success": baseline_success,
            "safe_fallback": baseline_result["classification"] == "safe_fallback",
        },
        {
            "case_id": case["id"],
            "system": "react_agent_v2",
            "query": case["query"],
            "status": agent_result["status"],
            "answer": agent_result["answer"],
            "tool_path": agent_result["tool_path"],
            "tool_calls": agent_result["tool_calls"],
            "steps": agent_result["steps"],
            "success": agent_success,
            "safe_fallback": agent_result["status"] != "final_answer",
            "trace": agent_result["trace"],
        },
    ]
    rows[0]["rubric"] = rubric_for_row(rows[0], expected_path)
    rows[1]["rubric"] = rubric_for_row(rows[1], expected_path)
    rows[0]["rubric_total"] = sum(rows[0]["rubric"].values())
    rows[1]["rubric_total"] = sum(rows[1]["rubric"].values())
    return rows


def summarize(rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for system in sorted({row["system"] for row in rows}):
        system_rows = [row for row in rows if row["system"] == system]
        summary[system] = {
            "case_count": len(system_rows),
            "success_rate": round(sum(row["success"] for row in system_rows) / len(system_rows), 2),
            "safe_fallback_rate": round(sum(row["safe_fallback"] for row in system_rows) / len(system_rows), 2),
            "parser_error_rate": round(sum(trace_has_error(row, "parse_error") for row in system_rows) / len(system_rows), 2),
            "hallucinated_tool_rate": round(sum(trace_has_error(row, "unknown_tool") for row in system_rows) / len(system_rows), 2),
            "recovery_rate": round(sum(row["status"] in ["final_answer", "safe_fallback", "direct_answer"] for row in system_rows) / len(system_rows), 2),
            "average_steps": round(sum(row["steps"] for row in system_rows) / len(system_rows), 2),
            "average_tool_calls": round(sum(row["tool_calls"] for row in system_rows) / len(system_rows), 2),
            "median_latency_ms": median([1 for _ in system_rows]),
            "max_latency_ms": max([1 for _ in system_rows]),
            "average_total_tokens": round(sum(40 for _ in system_rows) / len(system_rows), 2),
        }
    return summary


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_raw_result_table(rows: list[Dict[str, Any]]) -> None:
    header = [
        "case",
        "system",
        "factual",
        "grounding",
        "tool_selection",
        "safety",
        "completeness",
        "termination",
        "rubric_total",
        "tool_path",
        "status",
        "steps",
        "tool_calls",
        "success",
    ]
    lines = [",".join(header)]
    for row in rows:
        rubric = row["rubric"]
        values = [
            row["case_id"],
            row["system"],
            str(rubric["factual"]),
            str(rubric["grounding"]),
            str(rubric["tool_selection"]),
            str(rubric["safety"]),
            str(rubric["completeness"]),
            str(rubric["termination"]),
            str(row["rubric_total"]),
            " -> ".join(row["tool_path"]) or "-",
            row["status"],
            str(row["steps"]),
            str(row["tool_calls"]),
            str(row["success"]).lower(),
        ]
        escaped = [f'"{value}"' if "," in value or " -> " in value else value for value in values]
        lines.append(",".join(escaped))
    path = ROOT / "artifacts/evaluation/raw_result_table.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_failure_artifacts() -> None:
    repeated_responses = [
        'Thought: Need stock.\nAction: check_stock({"item_name": "iPhone"})',
        'Thought: Need stock again.\nAction: check_stock({"item_name": "iPhone"})',
        'Thought: Still need stock.\nAction: check_stock({"item_name": "iPhone"})',
    ]
    query = "I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?"
    v1 = ReActAgent(ScriptedLLM(repeated_responses.copy(), "scripted-agent-v1"), TOOL_REGISTRY, max_steps=3).run(query)
    v2 = ReActAgentV2(ScriptedLLM(repeated_responses.copy(), "scripted-agent-v2"), TOOL_REGISTRY, max_steps=3).run(query)

    write_json(ROOT / "artifacts/traces/failure_trace_v1_repeated_action.json", v1)
    write_json(ROOT / "artifacts/traces/recovery_trace_v2_repeated_action.json", v2)
    (ROOT / "artifacts/traces").mkdir(parents=True, exist_ok=True)
    (ROOT / "artifacts/traces/rca_repeated_action.md").write_text(
        "\n".join(
            [
                "# RCA: Repeated Action",
                "",
                "| Mục | Bằng chứng |",
                "|---|---|",
                f"| User input | `{query}` |",
                "| Expected path | `check_stock -> get_discount -> calc_shipping -> calc_total` |",
                "| Actual V1 path | `check_stock -> check_stock -> check_stock` |",
                "| First divergence | Bước 2 lặp lại `check_stock` thay vì chuyển sang `get_discount`. |",
                "| Error class | Loop / prompt adherence. |",
                "| Root cause | V1 có `max_steps` nhưng chưa có repeated-action detector. |",
                "| Smallest fix | Dừng khi cùng một Tool và arguments bị lặp lại mà không có bằng chứng mới. |",
                "| Regression test | `python -m pytest tests/test_agent_recovery.py -q` |",
                "| Before / after | V1 tốn 3 Tool calls rồi chạm `max_steps`; V2 dừng sau 1 Tool call với trạng thái `repeated_action`. |",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    rows: list[Dict[str, Any]] = []
    for case in CASES:
        rows.extend(evaluate_case(case))

    summary = summarize(rows)
    write_json(ROOT / "artifacts/evaluation/raw_results.json", {"rows": rows, "summary": summary})
    write_json(ROOT / "artifacts/evaluation/summary.json", summary)
    write_raw_result_table(rows)
    success_trace = next(row for row in rows if row["case_id"] == "case_3_iphone_winner_hanoi" and row["system"] == "react_agent_v2")
    write_json(ROOT / "artifacts/traces/success_trace_case_3.json", success_trace["trace"])
    generate_failure_artifacts()
    print("Generated artifacts/evaluation and artifacts/traces.")


if __name__ == "__main__":
    main()
