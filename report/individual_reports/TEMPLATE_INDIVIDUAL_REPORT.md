# Báo cáo cá nhân: Lab 3 - Chatbot vs ReAct Agent

- **Họ tên**: [Tên của bạn]
- **Mã sinh viên**: [Mã sinh viên]
- **Ngày hoàn thiện**: [YYYY-MM-DD]

## I. Đóng góp kỹ thuật

Liệt kê phần code, Tool, test hoặc tài liệu bạn trực tiếp thực hiện.

- **Module đã làm**: [ví dụ: `src/tools/search_tool.py`]
- **Điểm đáng chú ý**: [mô tả ngắn]
- **Liên kết với ReAct loop**: [phần này hỗ trợ Agent như thế nào]

## II. Debugging case study

Phân tích một lỗi thật dựa trên trace hoặc log.

- **Vấn đề**: [ví dụ: Agent lặp `Action: search(None)`]
- **Log / Trace Source**: [đường dẫn artifact hoặc log]
- **Chẩn đoán**: [lỗi do Prompt, parser, model hay Tool spec]
- **Cách sửa**: [thay đổi đã thực hiện]
- **Bằng chứng kiểm thử**: [lệnh test]

## III. Bài học cá nhân: Chatbot vs ReAct Agent

1. **Reasoning**: `Thought` giúp Agent khác gì so với chatbot trả lời trực tiếp?
2. **Reliability**: Trường hợp nào Agent tệ hơn hoặc đắt hơn chatbot?
3. **Observation**: Feedback từ Tool ảnh hưởng thế nào đến bước tiếp theo?

## IV. Cải tiến tương lai

Đề xuất một cải tiến để đưa hệ thống gần production hơn.

- **Khả năng mở rộng**: [ví dụ: queue bất đồng bộ cho Tool call]
- **An toàn**: [ví dụ: Supervisor LLM kiểm tra hành động]
- **Hiệu năng**: [ví dụ: Tool retrieval bằng vector database]

> Nộp file này bằng cách đổi tên thành `REPORT_[YOUR_NAME].md`.
