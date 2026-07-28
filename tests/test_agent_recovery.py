from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.tools import TOOL_REGISTRY
from tests.fakes import ScriptedLLM


REPEATED_RESPONSES = [
    'Thought: Need stock.\nAction: check_stock({"item_name": "iPhone"})',
    'Thought: Need stock again.\nAction: check_stock({"item_name": "iPhone"})',
    'Thought: Still need stock.\nAction: check_stock({"item_name": "iPhone"})',
]


def test_v1_reaches_max_steps_on_repeated_action_failure_trace():
    agent = ReActAgent(ScriptedLLM(REPEATED_RESPONSES.copy()), TOOL_REGISTRY, max_steps=3)

    result = agent.run("I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?")

    assert result["status"] == "max_steps_exceeded"
    assert result["tool_path"] == ["check_stock", "check_stock", "check_stock"]


def test_v2_stops_repeated_action_before_wasting_tool_calls():
    agent = ReActAgentV2(ScriptedLLM(REPEATED_RESPONSES.copy()), TOOL_REGISTRY, max_steps=3)

    result = agent.run("I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?")

    assert result["status"] == "repeated_action"
    assert result["tool_path"] == ["check_stock"]
    assert result["tool_calls"] == 1


def test_v2_blocks_premature_final_for_dynamic_checkout_until_tools_are_used():
    agent = ReActAgentV2(
        ScriptedLLM(
            [
                "Final Answer: The total is $1910.",
                'Thought: Need real stock.\nAction: check_stock({"item_name": "iPhone"})',
                'Thought: Need real coupon.\nAction: get_discount({"coupon_code": "WINNER"})',
                'Thought: Need real shipping.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
                "Final Answer: Total = 45,038,000 VND.",
            ]
        ),
        TOOL_REGISTRY,
        max_steps=5,
    )

    result = agent.run("I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?")

    assert result["status"] == "final_answer"
    assert result["tool_path"] == ["check_stock", "get_discount", "calc_shipping"]
    assert result["trace"][1]["observation"]["error"] == "premature_final_missing_evidence"
