from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_dashboard_contains_required_flow_sections():
    index = (ROOT / "web/index.html").read_text(encoding="utf-8")
    app = (ROOT / "web/app.js").read_text(encoding="utf-8")

    assert "Live Agent demo e-commerce" in index
    assert "Hỏi live Agent" in index
    assert "Groq API" in index
    assert "/api/chat/stream" in index
    assert "Dữ liệu và quy trình thực nghiệm cũ" in index
    assert "Live monitoring metrics" in index
    assert "LLM calls" in index
    assert "Cost estimate" in index
    assert "Baseline Chatbot" in index
    assert "ReAct Agent V2" in index
    assert "/api/chat/stream" in app
    assert "graph-node" in app
    assert "updateMetrics" in app
    assert "check_stock -> get_discount -> calc_shipping" in app
    assert "45,038,000 VND" in app
