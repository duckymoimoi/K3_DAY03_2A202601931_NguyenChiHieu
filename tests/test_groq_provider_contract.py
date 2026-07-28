from unittest.mock import Mock, patch

from src.core.groq_provider import GroqProvider


def test_groq_provider_generate_uses_openai_compatible_contract():
    message = Mock()
    message.content = "Final Answer: hello"
    choice = Mock()
    choice.message = message
    usage = Mock()
    usage.prompt_tokens = 3
    usage.completion_tokens = 4
    usage.total_tokens = 7
    response = Mock()
    response.choices = [choice]
    response.usage = usage

    with patch("src.core.groq_provider.OpenAI") as client_cls:
        client_cls.return_value.chat.completions.create.return_value = response
        provider = GroqProvider(api_key="test-key", base_url="https://api.groq.com/openai/v1")
        result = provider.generate("hello", system_prompt="system")

    client_cls.assert_called_once()
    assert result["provider"] == "groq"
    assert result["content"] == "Final Answer: hello"
    assert result["usage"]["total_tokens"] == 7
