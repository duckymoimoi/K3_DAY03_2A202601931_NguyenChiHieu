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
