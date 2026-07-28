# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyen Chi Hieu
- **Student ID**: 2A202601931
- **Date**: 2026-07-28

## I. Technical Contribution

- Implemented baseline chatbot in `src/chatbot/chatbot.py`.
- Implemented deterministic e-commerce tools in `src/tools/tools.py`.
- Implemented ReAct V1 loop in `src/agent/agent.py`.
- Implemented V2 repeated-action guardrail in `src/agent/agent_v2.py`.
- Added unit tests for chatbot baseline, tools, ReAct loop, recovery, and web artifact.
- Added deterministic evaluation script: `scripts/run_lab_evaluation.py`.
- Built static UI dashboard in `web/`.

## II. Debugging Case Study

- **Problem**: Agent V1 repeated `check_stock({"item_name": "iPhone"})` instead of moving to coupon validation.
- **Log / Trace Source**: `artifacts/traces/failure_trace_v1_repeated_action.json`
- **First divergence**: Step 2 repeated `check_stock`.
- **Diagnosis**: The loop had `max_steps`, but no repeated-action detector.
- **Solution**: `ReActAgentV2` stops safely when the exact same tool and arguments repeat without new evidence.
- **Evidence**: `python -m pytest tests/test_agent_recovery.py -q`

## III. Personal Insights: Chatbot vs ReAct

The chatbot is cheaper and faster for static questions such as return policy and working hours because no external evidence is needed. For checkout questions, the chatbot should not invent a total because price, stock, coupon status, and shipping are dynamic facts.

The ReAct agent is more expensive because it uses multiple steps and tool calls, but it can ground the final answer in observations. The strongest insight from the 5-case evaluation is that the agent is not always better; it is better when the task requires action, validation, or fresh evidence.

## IV. Future Improvements

- Add Pydantic schemas for Action arguments before tool execution.
- Add an authenticated inventory and coupon database instead of hardcoded lab data.
- Add human confirmation before any real purchase or payment action.
- Add cost and latency monitoring per tool and per LLM call.
- Use a graph-based framework if the checkout workflow gains more branches.
