# Báo cáo cá nhân: Lab 3 - Chatbot vs ReAct Agent

- **Họ tên**: Nguyen Chi Hieu
- **Mã sinh viên**: 2A202601931
- **Ngày hoàn thiện**: 2026-07-28

## I. Đóng góp kỹ thuật

- Implement `Baseline Chatbot` trong `src/chatbot/chatbot.py`.
- Implement các Tool deterministic trong `src/tools/tools.py`, gồm `check_stock`, `get_discount`, `calc_shipping`, `calc_total` và `search_policy`.
- Implement `ReAct Agent V1` trong `src/agent/agent.py`.
- Implement `ReAct Agent V2` với repeated-action guardrail trong `src/agent/agent_v2.py`.
- Thêm unit tests cho chatbot baseline, Tool, ReAct loop, recovery và web UI.
- Thêm script deterministic evaluation: `scripts/run_lab_evaluation.py`.
- Thêm `OllamaProvider` và smoke scripts cho model local `qwen3.5:4b`.
- Thêm `GroqProvider` để chạy live demo nhanh qua API OpenAI-compatible.
- Thêm live system demo `scripts/run_live_demo.py`, monitoring artifact và ablation artifact.
- Xây web UI live trong `web/`: graph cập nhật realtime qua `/api/chat/stream`, có hover để xem chi tiết từng LLM/Tool event.

## II. Debugging case study

- **Vấn đề**: Agent V1 lặp lại `check_stock({"item_name": "iPhone"})` thay vì chuyển sang kiểm tra coupon.
- **Nguồn log / trace**: `artifacts/traces/failure_trace_v1_repeated_action.json`
- **First divergence**: Bước 2 lặp lại `check_stock`.
- **Chẩn đoán**: Loop có `max_steps`, nhưng chưa có repeated-action detector.
- **Cách sửa**: `ReActAgentV2` dừng an toàn khi cùng một Tool và arguments bị lặp lại mà không có bằng chứng mới.
- **Phát hiện từ live model**: model live từng cố trả lời tổng tiền khi Tool path chưa hợp lệ hoặc lặp `calc_total`, nên V2 có thêm evidence gate, `calc_total` prerequisite guardrail và cơ chế chốt answer từ Observation `calc_total` đã grounded.
- **Bằng chứng kiểm thử**: `python -m pytest tests/test_agent_recovery.py -q`

## III. Bằng chứng kỹ thuật cá nhân

- **Live system demo**: `python scripts/run_live_demo.py` gọi Groq API để tạo `artifacts/live/live_system_demo.json`, trong đó Baseline trả `safe_fallback` và Agent trả `45,038,000 VND`.
- **Tool mở rộng**: thêm `calc_total` để tính checkout total có công thức rõ ràng và `search_policy` để search policy nội bộ.
- **Failure Handling**: Agent chặn repeated-action, chặn final answer sớm và chặn `calc_total` khi chưa đủ Observation.
- **Monitoring**: `artifacts/monitoring/live_monitoring_summary.json` theo dõi tokens, latency, token ratio và cost estimate demo.
- **Ablation Experiment**: `artifacts/experiments/ablation_guardrail.json` chứng minh V2 giảm lỗi loop so với V1.

## IV. Bài học cá nhân: Chatbot vs ReAct Agent

Chatbot rẻ và nhanh hơn cho câu hỏi tĩnh như chính sách đổi trả hoặc giờ làm việc, vì không cần dữ liệu động. Với câu hỏi checkout, chatbot không nên tự bịa tổng tiền vì giá, tồn kho, coupon và shipping đều là dữ liệu cần bằng chứng.

ReAct Agent tốn nhiều bước hơn vì phải gọi Tool, nhưng đổi lại câu trả lời có `Observation` làm bằng chứng. Kết luận quan trọng nhất là Agent không phải lúc nào cũng tốt hơn; Agent đáng dùng khi bài toán cần hành động, kiểm chứng hoặc dữ liệu mới.

## V. Cải tiến tương lai

- Thêm Pydantic schema cho arguments trước khi gọi Tool.
- Dùng inventory database và coupon API thật thay vì dữ liệu hardcode.
- Thêm human confirmation trước khi thực hiện purchase/payment.
- Theo dõi cost và latency cho từng LLM call và Tool call.
- Dùng graph-based framework nếu workflow checkout có nhiều nhánh phức tạp.

