import copy
import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class ReActAgent:
    """
    ReAct-style Agent following Thought -> Action -> Observation -> Final Answer.
    """

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 5,
        version: str = "v1",
        detect_repeated_action: bool = False,
        evidence_gate: bool = False,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.version = version
        self.detect_repeated_action = detect_repeated_action
        self.evidence_gate = evidence_gate
        self.history = []

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [
                f"- {tool['name']}: {tool['description']} Example input: "
                f"{json.dumps(tool.get('input_example', {}), ensure_ascii=False)}"
                for tool in self.tools
            ]
        )
        return f"""
        You are an e-commerce ReAct agent. Use tools only when dynamic evidence is needed.

        Available tools:
        {tool_descriptions}

        Output one of these formats:
        Thought: brief reason for the next step.
        Action: tool_name({{"argument": "value"}})

        Or, when enough evidence is available:
        Final Answer: your final response.

        Rules:
        - Return exactly one Action per response, then stop.
        - Never invent tool names. Use only the listed tools.
        - Never write Observation yourself; the application will append it.
        - Never include multiple Action lines in one response.
        - Do not claim checkout success until tool evidence supports stock, price,
          coupon status, shipping fee, and final total.
        - For static policy or working-hours questions, answer directly with Final Answer.
        """

    def run(self, user_input: str, on_event: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        logger.log_event(
            "AGENT_START",
            {"input": user_input, "model": self.llm.model_name, "version": self.version},
        )

        prompt = f"Question: {user_input}"
        trace: List[Dict[str, Any]] = []
        tool_path: List[str] = []
        prompt_history: List[str] = [prompt]
        previous_action: Optional[Tuple[str, Dict[str, Any]]] = None

        for step in range(1, self.max_steps + 1):
            llm_result = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
            raw_output = llm_result.get("content", "") if isinstance(llm_result, dict) else str(llm_result)
            trace.append(
                {
                    "step": step,
                    "type": "llm",
                    "content": raw_output,
                    "usage": llm_result.get("usage", {}) if isinstance(llm_result, dict) else {},
                    "latency_ms": llm_result.get("latency_ms", 0) if isinstance(llm_result, dict) else 0,
                    "provider": llm_result.get("provider", "unknown") if isinstance(llm_result, dict) else "unknown",
                }
            )
            self._emit(on_event, trace[-1])

            final_answer = self.parse_final_answer(raw_output)
            if final_answer:
                missing_tools = self._missing_required_tools(user_input, tool_path, trace)
                if self.evidence_gate and missing_tools:
                    observation = {
                        "ok": False,
                        "error": "premature_final_missing_evidence",
                        "message": "Dynamic checkout answers require tool evidence before Final Answer.",
                        "missing_tools": missing_tools,
                    }
                    trace.append({"step": step, "type": "observation", "observation": observation})
                    self._emit(on_event, trace[-1])
                    prompt = self._append_observation(prompt, raw_output, observation)
                    prompt_history.append(prompt)
                    continue

                result = {
                    "answer": final_answer,
                    "status": "final_answer",
                    "trace": trace,
                    "steps": step,
                    "tool_calls": len(tool_path),
                    "tool_path": tool_path,
                    "prompt_history": prompt_history,
                }
                logger.log_event("AGENT_END", {"status": result["status"], "steps": step, "tool_path": tool_path})
                self._emit(on_event, {"type": "result", "result": result})
                return result

            action = self.parse_action(raw_output)
            if action is None:
                observation = {
                    "ok": False,
                    "error": "parse_error",
                    "message": "Expected Action: tool_name({...}) or Final Answer: ...",
                    "raw_output": raw_output,
                }
                trace.append({"step": step, "type": "observation", "observation": observation})
                self._emit(on_event, trace[-1])
                prompt = self._append_observation(prompt, raw_output, observation)
                prompt_history.append(prompt)
                continue

            tool_name, arguments = action
            current_action = (tool_name, arguments)
            if self.detect_repeated_action and previous_action == current_action:
                out_of_stock = self._last_out_of_stock(trace)
                if out_of_stock:
                    final_answer = self._format_out_of_stock_answer(out_of_stock)
                    result = {
                        "answer": final_answer,
                        "status": "final_answer",
                        "trace": trace,
                        "steps": step,
                        "tool_calls": len(tool_path),
                        "tool_path": tool_path,
                        "prompt_history": prompt_history,
                    }
                    logger.log_event("AGENT_END", {"status": result["status"], "steps": step, "tool_path": tool_path})
                    self._emit(on_event, {"type": "result", "result": result})
                    return result

                grounded_total = self._last_successful_total(trace)
                if tool_name == "calc_total" and grounded_total:
                    final_answer = self._format_total_answer(grounded_total)
                    result = {
                        "answer": final_answer,
                        "status": "final_answer",
                        "trace": trace,
                        "steps": step,
                        "tool_calls": len(tool_path),
                        "tool_path": tool_path,
                        "prompt_history": prompt_history,
                    }
                    logger.log_event("AGENT_END", {"status": result["status"], "steps": step, "tool_path": tool_path})
                    self._emit(on_event, {"type": "result", "result": result})
                    return result

                observation = {
                    "ok": False,
                    "error": "repeated_action",
                    "message": "The agent repeated the same tool call without new evidence.",
                    "tool": tool_name,
                    "arguments": arguments,
                }
                trace.append({"step": step, "type": "observation", "observation": observation})
                self._emit(on_event, trace[-1])
                result = {
                    "answer": "I stopped because the agent repeated the same action without progress.",
                    "status": "repeated_action",
                    "trace": trace,
                    "steps": step,
                    "tool_calls": len(tool_path),
                    "tool_path": tool_path,
                    "prompt_history": prompt_history,
                }
                logger.log_event("AGENT_END", {"status": result["status"], "steps": step, "tool_path": tool_path})
                self._emit(on_event, {"type": "result", "result": result})
                return result

            previous_action = current_action
            prerequisite_error = self._tool_prerequisite_error(tool_name, user_input, tool_path, trace)
            observation = prerequisite_error or self._execute_tool(tool_name, arguments)
            if observation.get("ok") is not False:
                tool_path.append(tool_name)
            else:
                tool_path.append(tool_name)

            trace.append(
                {
                    "step": step,
                    "type": "tool",
                    "tool": tool_name,
                    "arguments": arguments,
                    "observation": observation,
                }
            )
            self._emit(on_event, trace[-1])
            prompt = self._append_observation(prompt, self._executed_action_text(raw_output), observation)
            prompt_history.append(prompt)

        result = {
            "answer": "I could not complete the task safely within the step limit.",
            "status": "max_steps_exceeded",
            "trace": trace,
            "steps": self.max_steps,
            "tool_calls": len(tool_path),
            "tool_path": tool_path,
            "prompt_history": prompt_history,
        }
        logger.log_event("AGENT_END", {"status": result["status"], "steps": self.max_steps, "tool_path": tool_path})
        self._emit(on_event, {"type": "result", "result": result})
        return result

    def _emit(self, on_event: Optional[Callable[[Dict[str, Any]], None]], event: Dict[str, Any]) -> None:
        if on_event:
            on_event(copy.deepcopy(event))

    def parse_action(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        match = re.search(r"Action:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\((\{.*?\})\)", text, re.DOTALL)
        if not match:
            return None
        tool_name = match.group(1)
        raw_args = match.group(2)
        try:
            arguments = json.loads(raw_args)
        except json.JSONDecodeError:
            return None
        if not isinstance(arguments, dict):
            return None
        return tool_name, arguments

    def parse_final_answer(self, text: str) -> Optional[str]:
        match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
        if not match:
            return None
        answer = match.group(1).strip()
        return answer or None

    def _append_observation(self, prompt: str, raw_output: str, observation: Dict[str, Any]) -> str:
        return (
            f"{prompt}\n\n{raw_output.strip()}\n"
            f"Observation: {json.dumps(observation, ensure_ascii=False)}"
        )

    def _executed_action_text(self, text: str) -> str:
        match = re.search(r"Action:\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\(\{.*?\}\)", text, re.DOTALL)
        if not match:
            return text
        trimmed = text[: match.end()]
        if text[match.end() :].strip():
            trimmed += "\n[Application note: output after the first Action was ignored because only one Action is executed per step.]"
        return trimmed

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        available_tools = {tool["name"]: tool for tool in self.tools}
        tool = available_tools.get(tool_name)
        if tool is None:
            return {
                "ok": False,
                "error": "unknown_tool",
                "message": f"Tool '{tool_name}' is not registered.",
                "available_tools": sorted(available_tools),
            }

        try:
            return tool["function"](**arguments)
        except TypeError as exc:
            return {
                "ok": False,
                "error": "invalid_arguments",
                "message": str(exc),
                "tool": tool_name,
                "arguments": arguments,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": "tool_failure",
                "message": str(exc),
                "tool": tool_name,
                "arguments": arguments,
            }

    def _tool_prerequisite_error(
        self,
        tool_name: str,
        user_input: str,
        tool_path: List[str],
        trace: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if tool_name != "calc_total":
            return None

        missing_tools = self._missing_required_tools(user_input, tool_path, trace)
        if not missing_tools:
            return None

        return {
            "ok": False,
            "error": "missing_prerequisite_evidence",
            "message": "calc_total requires grounded stock, coupon, and shipping observations first.",
            "missing_tools": missing_tools,
        }

    def _last_successful_total(self, trace: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for step in reversed(trace):
            if step.get("type") != "tool" or step.get("tool") != "calc_total":
                continue
            observation = step.get("observation", {})
            if observation.get("ok") is True and "total" in observation:
                return observation
        return None

    def _last_out_of_stock(self, trace: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for step in reversed(trace):
            if step.get("type") != "tool" or step.get("tool") != "check_stock":
                continue
            observation = step.get("observation", {})
            if observation.get("status") == "out_of_stock":
                return observation
        return None

    def _format_out_of_stock_answer(self, stock_observation: Dict[str, Any]) -> str:
        item_name = stock_observation.get("item_name", "This item")
        return f"{item_name} is out of stock, so I cannot confirm the purchase or calculate a checkout total."

    def _format_total_answer(self, total_observation: Dict[str, Any]) -> str:
        total = int(total_observation["total"])
        subtotal = int(total_observation.get("subtotal", 0))
        discount_amount = int(total_observation.get("discount_amount", 0))
        shipping_cost = int(total_observation.get("shipping_cost", 0))
        currency = total_observation.get("currency", "VND")
        return (
            f"Total = {total:,} {currency}. "
            f"Subtotal {subtotal:,} {currency}, discount {discount_amount:,} {currency}, "
            f"shipping {shipping_cost:,} {currency}."
        )

    def _missing_required_tools(
        self,
        user_input: str,
        tool_path: List[str],
        trace: List[Dict[str, Any]],
    ) -> List[str]:
        normalized = user_input.lower()
        dynamic_item = any(term in normalized for term in ["iphone", "ipad", "macbook"])
        checkout_total = any(term in normalized for term in ["total", "how much", "bao nhieu", "tong tien"])
        if not dynamic_item or not checkout_total:
            return []

        out_of_stock = any(
            step.get("type") == "tool"
            and step.get("tool") == "check_stock"
            and step.get("observation", {}).get("status") == "out_of_stock"
            for step in trace
        )

        required = ["check_stock"]
        if out_of_stock:
            return [tool for tool in required if tool not in tool_path]

        if any(term in normalized for term in ["winner", "legacy", "coupon", "code"]):
            required.append("get_discount")
        if any(term in normalized for term in ["ship", "shipping", "hanoi", "ha noi", "saigon"]):
            required.append("calc_shipping")

        return [tool for tool in required if tool not in tool_path]
