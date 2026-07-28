# RCA: Repeated Action

| Mục | Bằng chứng |
|---|---|
| User input | `I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?` |
| Expected path | `check_stock -> get_discount -> calc_shipping` |
| Actual V1 path | `check_stock -> check_stock -> check_stock` |
| First divergence | Bước 2 lặp lại `check_stock` thay vì chuyển sang `get_discount`. |
| Error class | Loop / prompt adherence. |
| Root cause | V1 có `max_steps` nhưng chưa có repeated-action detector. |
| Smallest V2 fix | Dừng khi cùng một Tool và arguments bị lặp lại mà không có bằng chứng mới. |
| Regression test | `python -m pytest tests/test_agent_recovery.py -q` |
| Before / after | V1 tốn 3 Tool calls rồi chạm `max_steps`; V2 dừng sau 1 Tool call với trạng thái `repeated_action`. |
