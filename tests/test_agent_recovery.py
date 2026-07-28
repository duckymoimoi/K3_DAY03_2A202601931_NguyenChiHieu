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


def test_v2_recovers_once_from_repeated_stock_call_when_checkout_tools_are_missing():
    repeated_stock = 'Action: check_stock({"item_name": "iPhone"})'
    agent = ReActAgentV2(
        ScriptedLLM(
            [
                repeated_stock,
                repeated_stock,
                'Action: get_discount({"coupon_code": "WINNER"})',
                'Action: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
                'Action: calc_total({"item_quantity": 2, "price_per_item": 25000000, "discount_percent": 10, "shipping_cost": 38000})',
                "Final Answer: Total = 45,038,000 VND.",
            ]
        ),
        TOOL_REGISTRY,
        max_steps=6,
    )

    result = agent.run("Tôi muốn mua 2 iPhone, dùng mã WINNER và giao tới Hà Nội. Tổng tiền là bao nhiêu?")

    assert result["status"] == "final_answer"
    assert result["tool_path"] == ["check_stock", "get_discount", "calc_shipping", "calc_total"]
    assert any(
        step.get("observation", {}).get("error") == "repeated_action_recovery"
        for step in result["trace"]
    )


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


def test_calc_total_is_blocked_until_prerequisite_evidence_exists():
    agent = ReActAgentV2(
        ScriptedLLM(
            [
                'Thought: Try total early.\nAction: calc_total({"item_quantity": 2, "price_per_item": 15000000, "discount_percent": 10, "shipping_cost": 38000})',
                'Thought: Need stock.\nAction: check_stock({"item_name": "iPhone"})',
                'Thought: Need coupon.\nAction: get_discount({"coupon_code": "WINNER"})',
                'Thought: Need shipping.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
                'Thought: Now total is grounded.\nAction: calc_total({"item_quantity": 2, "price_per_item": 25000000, "discount_percent": 10, "shipping_cost": 38000})',
                "Final Answer: Total = 45,038,000 VND.",
            ]
        ),
        TOOL_REGISTRY,
        max_steps=6,
    )

    result = agent.run("I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?")

    assert result["status"] == "final_answer"
    assert result["trace"][1]["observation"]["error"] == "missing_prerequisite_evidence"
    assert any(
        step.get("tool") == "calc_total"
        and step.get("observation", {}).get("total") == 45_038_000
        for step in result["trace"]
    )


def test_repeated_calc_total_after_success_returns_grounded_final_answer():
    action = 'Action: calc_total({"item_quantity": 2, "price_per_item": 25000000, "discount_percent": 10, "shipping_cost": 38000})'
    agent = ReActAgentV2(
        ScriptedLLM(
            [
                'Action: check_stock({"item_name": "iPhone"})',
                'Action: get_discount({"coupon_code": "WINNER"})',
                'Action: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
                action,
                action,
            ]
        ),
        TOOL_REGISTRY,
        max_steps=6,
    )

    result = agent.run("I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?")

    assert result["status"] == "final_answer"
    assert result["tool_path"] == ["check_stock", "get_discount", "calc_shipping", "calc_total"]
    assert "45,038,000 VND" in result["answer"]


def test_out_of_stock_observation_turns_repeated_stock_call_into_final_answer():
    repeated_stock = 'Action: check_stock({"item_name": "MacBook"})'
    agent = ReActAgentV2(
        ScriptedLLM(
            [
                'Action: calc_shipping({"weight": 2.0, "destination": "Saigon"})',
                repeated_stock,
                repeated_stock,
            ]
        ),
        TOOL_REGISTRY,
        max_steps=4,
    )

    result = agent.run("Can I buy 1 MacBook and ship to Saigon? How much?")

    assert result["status"] == "final_answer"
    assert result["tool_path"] == ["calc_shipping", "check_stock"]
    assert "MacBook is out of stock" in result["answer"]


def test_v2_out_of_scope_question_stops_before_llm_or_tools():
    llm = ScriptedLLM(["Final Answer: The weather is sunny."])
    agent = ReActAgentV2(llm, TOOL_REGISTRY, max_steps=4)

    result = agent.run("What is the weather in Hanoi today?")

    assert result["status"] == "out_of_scope"
    assert result["steps"] == 0
    assert result["tool_calls"] == 0
    assert result["tool_path"] == []
    assert llm.calls == []


def test_v2_lists_store_options_with_tool_evidence():
    agent = ReActAgentV2(
        ScriptedLLM(['Action: list_store_options({"include_expired": false})']),
        TOOL_REGISTRY,
        max_steps=3,
    )

    result = agent.run("Shop có những sản phẩm và mã giảm giá nào?")

    assert result["status"] == "final_answer"
    assert result["tool_path"] == ["list_store_options"]
    assert "AirPods Pro" in result["answer"]
    assert "VIP20" in result["answer"]
