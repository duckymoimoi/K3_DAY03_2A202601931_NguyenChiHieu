from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_dashboard_contains_chat_and_processing_flow_sections():
    index = (ROOT / "web/index.html").read_text(encoding="utf-8")
    app = (ROOT / "web/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "web/styles.css").read_text(encoding="utf-8")

    assert "Live e-commerce chatbot" in index
    assert "conversationFlow" in index
    assert "liveGraph" in index
    assert "Cloud API" not in index
    assert "providerSelect" not in index
    assert "activeProvider" not in index
    assert "Live monitoring metrics" in index
    assert "LLM calls" in index
    assert "Token ratio" in index
    assert "/api/chat/stream" in app
    assert "appendMessage" in app
    assert "appendFlowStep" in app
    assert "renderResultMessage" in app
    assert "answer-group" in app
    assert "flow-step" in app
    assert "Scope gate" in app
    assert ".workspace" in styles
    assert ".conversation-flow" in styles
    assert ".process-flow" in styles
    assert ".answer-group" in styles
    assert ".answer-kv" in styles
    assert "height: 100vh" in styles
    assert "resize: none" in styles
