# Báo cáo nhóm: Lab 3 - Chatbot vs ReAct Agent

- **Tên nhóm**: [Tên nhóm]
- **Thành viên**: [Thành viên 1, Thành viên 2, ...]
- **Ngày hoàn thiện**: [YYYY-MM-DD]

## 1. Tóm tắt

Tóm tắt mục tiêu của Agent, tỉ lệ thành công, và điểm khác biệt so với Baseline Chatbot.

- **Tỉ lệ thành công**: [ví dụ: 85% trên 20 test cases]
- **Kết quả chính**: [ví dụ: Agent giải được nhiều câu hỏi multi-step hơn nhờ dùng Search Tool]

## 2. Kiến trúc hệ thống và Tool

### 2.1 ReAct loop

Mô tả hoặc vẽ diagram cho luồng `Thought -> Action -> Observation`.

### 2.2 Danh sách Tool

| Tool Name | Input Format | Mục đích |
| :--- | :--- | :--- |
| `calc_tax` | `json` | Tính VAT theo country code. |
| `search_api` | `string` | Lấy thông tin cập nhật từ Search API. |

### 2.3 LLM Provider

- **Primary**: [ví dụ: GPT-4o]
- **Backup**: [ví dụ: Gemini 1.5 Flash]

## 3. Telemetry và hiệu năng

Phân tích metrics thu được trong lần chạy cuối.

- **Average Latency**: [ví dụ: 1200ms]
- **Average Tokens per Task**: [ví dụ: 350 tokens]
- **Total Cost**: [ví dụ: $0.05]

## 4. Root Cause Analysis

Phân tích một lỗi thật của Agent.

### Case study: [ví dụ: Hallucinated Argument]

- **Input**: [câu hỏi]
- **Observation**: [Agent đã làm gì]
- **Root Cause**: [Prompt, parser, Tool spec, dữ liệu, hoặc loop]
- **Smallest Fix**: [thay đổi nhỏ nhất]
- **Regression Test**: [lệnh test]

## 5. Ablation và so sánh

| Case | Chatbot Result | Agent Result | Nhận xét |
| :--- | :--- | :--- | :--- |
| Simple Q&A | Correct | Correct | Chatbot đủ tốt |
| Multi-step | Hallucinated | Correct | Agent tốt hơn |

## 6. Mức sẵn sàng production

- **Bảo mật**: [ví dụ: kiểm tra input và không commit API key]
- **Guardrails**: [ví dụ: max_steps, repeated-action detector]
- **Scaling**: [ví dụ: chuyển sang LangGraph nếu workflow phức tạp]

> Nộp file này bằng cách đổi tên thành `GROUP_REPORT_[TEAM_NAME].md`.
