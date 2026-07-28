import ast
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider


class ReActAgentV2(ReActAgent):
    """V2 adds the smallest guardrail from the repeated-action failed trace."""

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        super().__init__(
            llm=llm,
            tools=tools,
            max_steps=max_steps,
            version="v2",
            detect_repeated_action=True,
        )

    def get_system_prompt(self) -> str:
        return (
            super().get_system_prompt()
            + "\nV2 guardrail: if a tool call produced no new path forward, do not repeat the exact same Action. "
            "Use the observation to answer, ask for missing information, or stop safely.\n"
        )

    def parse_action(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        match = re.search(r"Action:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\((\{.*?\})\)", text, re.DOTALL)
        if not match:
            return None

        tool_name = match.group(1)
        raw_args = match.group(2)
        try:
            arguments: Any = json.loads(raw_args)
        except json.JSONDecodeError:
            try:
                arguments = ast.literal_eval(raw_args)
            except (SyntaxError, ValueError):
                return None

        if not isinstance(arguments, dict):
            return None
        return tool_name, arguments
