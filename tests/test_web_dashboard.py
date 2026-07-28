from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_dashboard_contains_required_flow_sections():
    index = (ROOT / "web/index.html").read_text(encoding="utf-8")
    app = (ROOT / "web/app.js").read_text(encoding="utf-8")

    assert "Bảng theo dõi luồng xử lý e-commerce" in index
    assert "Baseline Chatbot" in index
    assert "ReAct Agent V2" in index
    assert "check_stock -> get_discount -> calc_shipping" in app
    assert "45,038,000 VND" in app
