# Bảng claim bonus

| Hạng mục bonus | Điểm tối đa | Bằng chứng trong repo | Trạng thái |
|---|---:|---|---|
| Extra Monitoring | +3 | `artifacts/bonus/monitoring_summary.json` có tokens, latency, token ratio, cost estimate | Có cơ sở claim |
| Extra Tools | +2 | `calc_total` và `search_policy` trong `src/tools/tools.py`, có tests | Có cơ sở claim |
| Failure Handling | +3 | repeated-action detector, evidence gate, `calc_total` prerequisite guardrail | Mạnh |
| Live System Demo | +5 | `artifacts/live/live_system_demo.json` chạy Ollama `qwen2.5:3b`, Agent trả final answer đúng | Mạnh nếu demo trực tiếp được |
| Ablation Experiment | +2 | `artifacts/bonus/ablation_guardrail.json` so sánh V1/V2 | Có cơ sở claim |

Tổng bonus có thể nhắm tới: 12-15 điểm, tùy instructor đánh giá live demo và mức độ xem `search_policy`/`calc_total` là Extra Tools.