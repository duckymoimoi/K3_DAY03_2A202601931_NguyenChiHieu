from src.agent.agent import ReActAgent
from src.tools import TOOL_REGISTRY
from tests.fakes import ScriptedLLM


def test_agent_runs_tool_sequence_and_appends_observations():
    llm = ScriptedLLM(
        [
            'Thought: Need price and stock.\nAction: check_stock({"item_name": "iPhone"})',
            'Thought: Need coupon evidence.\nAction: get_discount({"coupon_code": "WINNER"})',
            'Thought: Need shipping evidence.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
            "Final Answer: Total is 45,038,000 VND.",
        ]
    )
    agent = ReActAgent(llm, TOOL_REGISTRY, max_steps=5)

    result = agent.run("I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?")

    assert result["status"] == "final_answer"
    assert result["tool_path"] == ["check_stock", "get_discount", "calc_shipping"]
    assert result["tool_calls"] == 3
    assert "45,038,000 VND" in result["answer"]
    assert "Observation:" in llm.calls[1]["prompt"]
    assert '"price": 25000000' in llm.calls[1]["prompt"]


def test_agent_ignores_unexecuted_actions_after_first_action_in_prompt_history():
    llm = ScriptedLLM(
        [
            'Thought: Need all evidence.\nAction: check_stock({"item_name": "iPhone"})\nAction: get_discount({"coupon_code": "WINNER"})',
            "Final Answer: Waiting for more evidence.",
        ]
    )
    agent = ReActAgent(llm, TOOL_REGISTRY, max_steps=2)

    result = agent.run("I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?")

    assert result["tool_path"] == ["check_stock"]
    assert 'Action: get_discount({"coupon_code": "WINNER"})' not in llm.calls[1]["prompt"]
    assert "output after the first Action was ignored" in llm.calls[1]["prompt"]
