# Lab 3: Chatbot vs ReAct Agent

Repo này là bài làm Lab 03: so sánh **Baseline Chatbot** với **ReAct Agent** trong ngữ cảnh e-commerce. Mục tiêu chính là trả lời câu hỏi: chatbot có thể nói nghe hợp lý, nhưng câu trả lời đó có thật sự có bằng chứng từ dữ liệu hay `Tool` không?

## Cài đặt

Tạo môi trường và cài thư viện:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu cần dùng API thật, tạo `.env` từ `.env.example`. Bài làm hiện tại không yêu cầu API key để chạy bộ kiểm thử deterministic.

## Chạy kiểm thử

```bash
python -m pytest -q
```

## Sinh artifacts

```bash
python scripts/run_lab_evaluation.py
```

Kết quả được lưu tại:

- `artifacts/evaluation/`
- `artifacts/traces/`

## Chạy thử bằng Ollama local

Máy đã có Ollama và model `qwen2.5:3b`, nên có thể chạy smoke test bằng model thật local:

```bash
python scripts/run_ollama_smoke.py
python scripts/run_ollama_agent_smoke.py
python scripts/run_live_demo.py
```

Lưu ý: bộ chấm deterministic vẫn dùng `ScriptedLLM`. Ollama chỉ là live smoke test, kết quả có thể thay đổi theo model.

`scripts/run_live_demo.py` là demo end-to-end dùng Ollama local `qwen2.5:3b`: Baseline Chatbot trả `safe_fallback`, còn ReAct Agent V2 gọi Tool để lấy bằng chứng và trả tổng tiền `45,038,000 VND`.

## Thành phần đã hoàn thiện

- `Baseline Chatbot`: `src/chatbot/chatbot.py`
- `Tool` deterministic: `src/tools/tools.py`
- `ReAct Agent V1`: `src/agent/agent.py`
- `ReAct Agent V2`: `src/agent/agent_v2.py`
- `OllamaProvider`: `src/core/ollama_provider.py`
- Script evaluation: `scripts/run_lab_evaluation.py`
- Script smoke test Ollama: `scripts/run_ollama_smoke.py`, `scripts/run_ollama_agent_smoke.py`
- Artifacts evaluation: `artifacts/evaluation/`
- Success trace và failure trace: `artifacts/traces/`
- Live Ollama artifacts: `artifacts/live/`
- Bonus artifacts: `artifacts/bonus/`
- Web UI: `web/index.html`

## Web UI

Mở trực tiếp file sau trong trình duyệt:

```text
web/index.html
```

UI hiển thị 5 test cases, kết quả so sánh Baseline Chatbot và ReAct Agent V2, `Tool path`, `Observation`, và luồng xử lý.

## Kết quả chính

- Baseline Chatbot: đúng với câu hỏi tĩnh, nhưng phải `safe fallback` khi cần giá, tồn kho, coupon, shipping hoặc tổng tiền.
- ReAct Agent V2: dùng `Tool` để lấy bằng chứng trước khi trả lời các câu hỏi checkout.
- V2 có thêm guardrail:
  - chặn lặp cùng một `Action`;
  - chặn `Final Answer` sớm khi chưa đủ `Tool evidence`;
  - chặn `calc_total` nếu chưa có Observation từ `check_stock`, `get_discount` và `calc_shipping`.

## Điểm bonus có thể claim

- **Live System Demo**: `artifacts/live/live_system_demo.json`, sinh bằng `python scripts/run_live_demo.py`.
- **Extra Monitoring**: `artifacts/bonus/monitoring_summary.json` có tokens, latency, token ratio và cost estimate demo.
- **Extra Tools**: `calc_total` để tính checkout total có cấu trúc và `search_policy` để search policy nội bộ.
- **Failure Handling**: repeated-action detector, evidence gate và `calc_total` prerequisite guardrail.
- **Ablation Experiment**: `artifacts/bonus/ablation_guardrail.json` so sánh V1 chưa có guardrail với V2 đã sửa.

Sinh lại toàn bộ bonus artifacts:

```bash
python scripts/generate_bonus_artifacts.py
```
