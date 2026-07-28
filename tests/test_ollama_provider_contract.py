from unittest.mock import Mock, patch

from src.core.ollama_provider import OllamaProvider


def test_ollama_provider_generate_matches_llm_provider_contract():
    mock_response = Mock()
    mock_response.json.return_value = {
        "response": "Final Answer: hello",
        "prompt_eval_count": 3,
        "eval_count": 4,
    }
    mock_response.raise_for_status.return_value = None

    with patch("src.core.ollama_provider.requests.post", return_value=mock_response):
        provider = OllamaProvider(model_name="qwen2.5:3b")
        result = provider.generate("hello", system_prompt="system")

    assert result["provider"] == "ollama"
    assert result["model"] == "qwen2.5:3b"
    assert result["content"] == "Final Answer: hello"
    assert result["usage"]["total_tokens"] == 7
