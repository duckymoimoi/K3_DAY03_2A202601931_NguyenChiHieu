# RCA: Repeated Action

| Field | Evidence |
|---|---|
| User input | `I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?` |
| Expected path | `check_stock -> get_discount -> calc_shipping` |
| Actual V1 path | `check_stock -> check_stock -> check_stock` |
| First divergence | Step 2 repeated `check_stock` instead of moving to coupon validation. |
| Error class | Loop / prompt adherence. |
| Root cause | V1 had max_steps but no repeated-action detector. |
| Smallest V2 fix | Stop when the exact same tool and arguments repeat without new evidence. |
| Regression test | `python -m pytest tests/test_agent_recovery.py -q` |
| Before / after | V1 wastes 3 tool calls and hits max steps; V2 stops after 1 tool call with `repeated_action`. |