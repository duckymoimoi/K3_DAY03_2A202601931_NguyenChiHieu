import copy
import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.core.domain_guard import classify_ecommerce_scope, normalize_text
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
        - For questions asking what products, coupon codes, or store demo options
          are available, call list_store_options.
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
        scope = classify_ecommerce_scope(user_input)
        if not scope["in_scope"]:
            trace = [{"step": 0, "type": "scope", "scope": scope}]
            self._emit(on_event, trace[0])
            result = {
                "answer": scope["answer"],
                "status": "out_of_scope",
                "trace": trace,
                "steps": 0,
                "tool_calls": 0,
                "tool_path": [],
                "prompt_history": [prompt],
            }
            logger.log_event("AGENT_END", {"status": result["status"], "steps": 0, "tool_path": []})
            self._emit(on_event, {"type": "result", "result": result})
            return result

        trace: List[Dict[str, Any]] = []
        tool_path: List[str] = []
        prompt_history: List[str] = [prompt]
        previous_action: Optional[Tuple[str, Dict[str, Any]]] = None
        repeated_recovery_actions: set[Tuple[str, str]] = set()

        checkout_gap = self._checkout_without_shipping_intent(user_input)
        if checkout_gap:
            result = self._answer_checkout_without_shipping(
                user_input=user_input,
                intent=checkout_gap,
                trace=trace,
                tool_path=tool_path,
                prompt_history=prompt_history,
                on_event=on_event,
            )
            logger.log_event(
                "AGENT_END",
                {"status": result["status"], "steps": result["steps"], "tool_path": result["tool_path"]},
            )
            self._emit(on_event, {"type": "result", "result": result})
            return result

        store_options_intent = self._store_options_intent(user_input)
        if store_options_intent:
            arguments = {"include_expired": False}
            observation = self._execute_tool("list_store_options", arguments)
            tool_path.append("list_store_options")
            trace.append(
                {
                    "step": 1,
                    "type": "tool",
                    "tool": "list_store_options",
                    "arguments": arguments,
                    "observation": observation,
                }
            )
            self._emit(on_event, trace[-1])
            display = self._store_options_display(observation, store_options_intent)
            result = {
                "answer": self._format_store_options_answer(observation, store_options_intent),
                "status": "final_answer",
                "trace": trace,
                "steps": 1,
                "tool_calls": 1,
                "tool_path": tool_path,
                "prompt_history": prompt_history,
                "display": display,
            }
            logger.log_event("AGENT_END", {"status": result["status"], "steps": 1, "tool_path": tool_path})
            self._emit(on_event, {"type": "result", "result": result})
            return result

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

                missing_tools = self._missing_required_tools(user_input, tool_path, trace)
                recovery_key = (tool_name, json.dumps(arguments, ensure_ascii=False, sort_keys=True))
                if missing_tools and recovery_key not in repeated_recovery_actions:
                    repeated_recovery_actions.add(recovery_key)
                    observation = {
                        "ok": False,
                        "error": "repeated_action_recovery",
                        "message": "The repeated tool call was not executed. Use the existing observation and move to the next missing tool.",
                        "tool": tool_name,
                        "arguments": arguments,
                        "missing_tools": missing_tools,
                        "next_tool_hint": missing_tools[0],
                    }
                    trace.append({"step": step, "type": "observation", "observation": observation})
                    self._emit(on_event, trace[-1])
                    prompt = self._append_observation(prompt, raw_output, observation)
                    prompt_history.append(prompt)
                    continue

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
                    "answer": "Mình đã dừng vì Agent lặp lại cùng một tool call mà không tạo thêm evidence mới.",
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

            if tool_name == "check_stock" and observation.get("status") == "out_of_stock":
                final_answer = self._format_out_of_stock_answer(observation)
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

            if tool_name == "list_store_options" and observation.get("ok") is True:
                store_options_intent = self._store_options_intent(user_input) or {
                    "products": True,
                    "coupons": True,
                    "shipping": True,
                }
                final_answer = self._format_store_options_answer(observation, store_options_intent)
                result = {
                    "answer": final_answer,
                    "status": "final_answer",
                    "trace": trace,
                    "steps": step,
                    "tool_calls": len(tool_path),
                    "tool_path": tool_path,
                    "prompt_history": prompt_history,
                    "display": self._store_options_display(observation, store_options_intent),
                }
                logger.log_event("AGENT_END", {"status": result["status"], "steps": step, "tool_path": tool_path})
                self._emit(on_event, {"type": "result", "result": result})
                return result

            if tool_name == "calc_shipping" and observation.get("ok") is False:
                final_answer = self._format_shipping_error_answer(observation)
                result = {
                    "answer": final_answer,
                    "status": "safe_fallback",
                    "trace": trace,
                    "steps": step,
                    "tool_calls": len(tool_path),
                    "tool_path": tool_path,
                    "prompt_history": prompt_history,
                }
                logger.log_event("AGENT_END", {"status": result["status"], "steps": step, "tool_path": tool_path})
                self._emit(on_event, {"type": "result", "result": result})
                return result

            if tool_name == "calc_total" and observation.get("ok") is True and "total" in observation:
                final_answer = self._format_total_answer(observation)
                result = {
                    "answer": final_answer,
                    "status": "final_answer",
                    "trace": trace,
                    "steps": step,
                    "tool_calls": len(tool_path),
                    "tool_path": tool_path,
                    "prompt_history": prompt_history,
                    "display": self._total_display(observation),
                }
                logger.log_event("AGENT_END", {"status": result["status"], "steps": step, "tool_path": tool_path})
                self._emit(on_event, {"type": "result", "result": result})
                return result

        result = {
            "answer": "Mình chưa thể hoàn tất an toàn trong giới hạn số bước của Agent.",
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
        return f"{item_name} đang hết hàng, nên mình chưa thể xác nhận đơn mua hoặc tính tổng checkout."

    def _format_total_answer(self, total_observation: Dict[str, Any]) -> str:
        total = int(total_observation["total"])
        subtotal = int(total_observation.get("subtotal", 0))
        discount_amount = int(total_observation.get("discount_amount", 0))
        shipping_cost = int(total_observation.get("shipping_cost", 0))
        currency = total_observation.get("currency", "VND")
        return (
            f"Tổng đơn hàng = {total:,} {currency}. "
            f"Tạm tính hàng {subtotal:,} {currency}, giảm giá {discount_amount:,} {currency}, "
            f"phí ship {shipping_cost:,} {currency}."
        )

    def _checkout_without_shipping_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        normalized = normalize_text(user_input)
        checkout_total = any(term in normalized for term in ["total", "how much", "bao nhieu", "tong tien", "tinh tong"])
        if not checkout_total:
            return None

        item_name = self._extract_item_name(normalized)
        if not item_name:
            return None

        has_shipping_context = any(
            term in normalized
            for term in [
                "ship",
                "shipping",
                "giao",
                "hanoi",
                "ha noi",
                "saigon",
                "ho chi minh",
                "da nang",
                "danang",
                "hai phong",
                "can tho",
                "hue",
                "nha trang",
            ]
        )
        if has_shipping_context:
            return None

        return {
            "item_name": item_name,
            "quantity": self._extract_quantity(normalized, item_name),
            "coupon_code": self._extract_coupon_code(normalized),
        }

    def _extract_item_name(self, normalized: str) -> Optional[str]:
        item_aliases = [
            ("studio display", "Studio Display"),
            ("magic keyboard", "Magic Keyboard"),
            ("apple watch", "Apple Watch"),
            ("airpods pro", "AirPods Pro"),
            ("airpods", "AirPods Pro"),
            ("airpod", "AirPods Pro"),
            ("macbook", "MacBook"),
            ("iphone", "iPhone"),
            ("ipad", "iPad"),
        ]
        for alias, item_name in item_aliases:
            if alias in normalized:
                return item_name
        return None

    def _extract_coupon_code(self, normalized: str) -> Optional[str]:
        for code in ["winner", "legacy", "student", "welcome5", "vip20"]:
            if code in normalized:
                return code.upper()
        return None

    def _extract_quantity(self, normalized: str, item_name: str) -> int:
        number_pattern = r"(\d+|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)"
        correction_patterns = [
            rf"\bkhong\s+(?:phai\s+)?{number_pattern}\s*(?:cai|chiec)?\s*(?:{normalize_text(item_name)})?\s*thoi\b",
            rf"\b(?:sua|doi|chuyen)\s+(?:lai\s+)?(?:thanh\s+)?{number_pattern}\s*(?:cai|chiec)?\b",
        ]
        for pattern in correction_patterns:
            match = re.search(pattern, normalized)
            if match:
                return self._quantity_value(match.group(1))

        item_token = normalize_text(item_name).replace("airpods pro", "airpod")
        match = re.search(rf"\b{number_pattern}\s*(?:cai|chiec)?\s*{re.escape(item_token)}s?\b", normalized)
        if match:
            return self._quantity_value(match.group(1))
        return 1

    def _quantity_value(self, raw_value: str) -> int:
        if raw_value.isdigit():
            return int(raw_value)
        number_words = {
            "mot": 1,
            "hai": 2,
            "ba": 3,
            "bon": 4,
            "nam": 5,
            "sau": 6,
            "bay": 7,
            "tam": 8,
            "chin": 9,
            "muoi": 10,
        }
        return number_words.get(raw_value, 1)

    def _answer_checkout_without_shipping(
        self,
        user_input: str,
        intent: Dict[str, Any],
        trace: List[Dict[str, Any]],
        tool_path: List[str],
        prompt_history: List[str],
        on_event: Optional[Callable[[Dict[str, Any]], None]],
    ) -> Dict[str, Any]:
        stock_args = {"item_name": intent["item_name"]}
        stock_observation = self._execute_tool("check_stock", stock_args)
        tool_path.append("check_stock")
        trace.append(
            {
                "step": 1,
                "type": "tool",
                "tool": "check_stock",
                "arguments": stock_args,
                "observation": stock_observation,
            }
        )
        self._emit(on_event, trace[-1])

        if stock_observation.get("status") == "out_of_stock":
            return {
                "answer": self._format_out_of_stock_answer(stock_observation),
                "status": "final_answer",
                "trace": trace,
                "steps": 1,
                "tool_calls": 1,
                "tool_path": tool_path,
                "prompt_history": prompt_history,
            }

        discount_percent = 0
        coupon_code = intent.get("coupon_code")
        if coupon_code:
            discount_args = {"coupon_code": coupon_code}
            discount_observation = self._execute_tool("get_discount", discount_args)
            tool_path.append("get_discount")
            trace.append(
                {
                    "step": 2,
                    "type": "tool",
                    "tool": "get_discount",
                    "arguments": discount_args,
                    "observation": discount_observation,
                }
            )
            self._emit(on_event, trace[-1])
            if discount_observation.get("ok") is True:
                discount_percent = float(discount_observation.get("discount_percent", 0))

        quantity = int(intent["quantity"])
        price = int(stock_observation.get("price", 0))
        subtotal = quantity * price
        discount_amount = int(subtotal * discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        item_name = stock_observation.get("item_name", intent["item_name"])
        answer = (
            f"Mình đã tính được phần hàng cho {quantity} {item_name}: "
            f"tạm tính trước phí ship là {subtotal_after_discount:,} VND. "
            f"Subtotal {subtotal:,} VND, giảm giá {discount_amount:,} VND. "
            "Bạn gửi thêm nơi giao hàng để mình tính phí ship và chốt tổng cuối."
        )
        return {
            "answer": answer,
            "status": "needs_shipping_destination",
            "trace": trace,
            "steps": len(trace),
            "tool_calls": len(tool_path),
            "tool_path": tool_path,
            "prompt_history": prompt_history,
            "display": self._partial_checkout_display(
                item_name=item_name,
                quantity=quantity,
                price=price,
                discount_amount=discount_amount,
                subtotal=subtotal,
                subtotal_after_discount=subtotal_after_discount,
            ),
        }

    def _partial_checkout_display(
        self,
        item_name: str,
        quantity: int,
        price: int,
        discount_amount: int,
        subtotal: int,
        subtotal_after_discount: int,
    ) -> Dict[str, Any]:
        return {
            "type": "checkout_partial",
            "sections": {
                "total": [
                    {"label": "Sản phẩm", "value": item_name},
                    {"label": "Số lượng", "value": str(quantity)},
                    {"label": "Đơn giá", "value": f"{price:,} VND"},
                    {"label": "Tạm tính hàng", "value": f"{subtotal:,} VND"},
                    {"label": "Giảm giá", "value": f"{discount_amount:,} VND"},
                    {"label": "Tạm tính trước phí ship", "value": f"{subtotal_after_discount:,} VND"},
                    {"label": "Phí ship", "value": "Cần nơi giao hàng"},
                ],
                "missing": ["Nơi giao hàng để tính phí ship và tổng cuối."],
            },
        }

    def _store_options_intent(self, user_input: str) -> Optional[Dict[str, bool]]:
        normalized = normalize_text(user_input)
        checkout_query = any(term in normalized for term in ["tong tien", "checkout", "mua ", "buy", "purchase"])
        listing_signal = any(
            term in normalized
            for term in ["hien co", "co nhung", "co cac", "danh sach", "liet ke", "nao", "bang gia", "cho toi biet", "kiem tra"]
        )
        product_signal = any(term in normalized for term in ["san pham", "mat hang", "catalog", "ban gi", "co gi"])
        coupon_signal = any(term in normalized for term in ["ma giam", "giam gia", "coupon", "voucher", "code"])
        shipping_signal = any(term in normalized for term in ["gia ship", "phi ship", "bang gia ship", "shipping", "ship"])

        if checkout_query or not listing_signal:
            return None
        if not any([product_signal, coupon_signal, shipping_signal]):
            return None

        return {
            "products": product_signal,
            "coupons": coupon_signal,
            "shipping": shipping_signal,
        }

    def _store_options_display(self, observation: Dict[str, Any], intent: Dict[str, bool]) -> Dict[str, Any]:
        sections = {}
        if intent.get("products"):
            sections["products"] = observation.get("products", [])
        if intent.get("coupons"):
            sections["coupons"] = observation.get("coupons", [])
        if intent.get("shipping"):
            sections["shipping"] = observation.get("shipping_options", [])
        return {"type": "store_options", "sections": sections}

    def _total_display(self, total_observation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "checkout_total",
            "sections": {
                "total": [
                    {"label": "Tổng cuối", "value": f"{int(total_observation['total']):,} {total_observation.get('currency', 'VND')}"},
                    {"label": "Tạm tính hàng", "value": f"{int(total_observation.get('subtotal', 0)):,} VND"},
                    {"label": "Giảm giá", "value": f"{int(total_observation.get('discount_amount', 0)):,} VND"},
                    {"label": "Phí ship", "value": f"{int(total_observation.get('shipping_cost', 0)):,} VND"},
                ]
            },
        }

    def _format_store_options_answer(self, observation: Dict[str, Any], intent: Dict[str, bool]) -> str:
        lines = []
        if intent.get("products"):
            lines.append("Sản phẩm hiện có:")
            for product in observation.get("products", []):
                status = "còn hàng" if product.get("status") == "in_stock" else "hết hàng"
                lines.append(
                    f"- {product['item_name']}: {product['price']:,} VND, {status}, "
                    f"stock {product['stock']}, weight {product['weight_kg']} kg"
                )

        if intent.get("coupons"):
            lines.append("Mã giảm giá hiện có:")
            for coupon in observation.get("coupons", []):
                lines.append(f"- {coupon['coupon_code']}: giảm {coupon['discount_percent']}%")

        if intent.get("shipping"):
            lines.append("Bảng giá ship hiện có:")
            for option in observation.get("shipping_options", []):
                lines.append(
                    f"- {option['destination']}: base {option['base_cost']:,} VND + "
                    f"{option['per_kg']:,} VND/kg, ETA {option['estimated_days']} ngày"
                )

        return "\n".join(lines)

    def _format_shipping_error_answer(self, observation: Dict[str, Any]) -> str:
        error = observation.get("error")
        if error == "unsupported_destination":
            supported = ", ".join(observation.get("supported_destinations", []))
            return (
                f"Hiện demo chưa hỗ trợ ship tới điểm đó. "
                f"Các nơi đang hỗ trợ: {supported}."
            )
        if error == "missing_argument":
            supported = ", ".join(observation.get("supported_destinations", []))
            suffix = f" Các nơi đang hỗ trợ: {supported}." if supported else ""
            return f"Mình cần nơi giao hàng trước khi tính phí ship.{suffix}"
        return observation.get("message", "Mình chưa thể tính phí ship một cách an toàn.")

    def _missing_required_tools(
        self,
        user_input: str,
        tool_path: List[str],
        trace: List[Dict[str, Any]],
    ) -> List[str]:
        normalized = normalize_text(user_input)
        dynamic_item = any(
            term in normalized
            for term in [
                "iphone",
                "ipad",
                "macbook",
                "airpod",
                "apple watch",
                "magic keyboard",
                "studio display",
            ]
        )
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
