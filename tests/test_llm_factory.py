import sys
import pytest
from unittest.mock import MagicMock, patch
from src.config import AppConfig, LLMConfig, OllamaConfig, GigaChatConfig
from src.tools.banking import tools


def test_create_llm_ollama():
    from src.llm_factory import create_llm
    config = AppConfig(llm=LLMConfig(
        provider="ollama",
        ollama=OllamaConfig(model="qwen2.5:7b", temperature=0, num_predict=512)
    ))
    mock_instance = MagicMock()
    mock_cls = MagicMock(return_value=mock_instance)

    with patch("langchain_ollama.ChatOllama", mock_cls):
        result = create_llm(config)

    mock_cls.assert_called_once_with(model="qwen2.5:7b", temperature=0, num_predict=512)
    mock_instance.bind_tools.assert_called_once_with(tools)
    assert result is mock_instance.bind_tools.return_value


def test_create_llm_gigachat():
    from src.llm_factory import create_llm
    config = AppConfig(llm=LLMConfig(
        provider="gigachat",
        gigachat=GigaChatConfig(
            credentials="test_creds",
            scope="GIGACHAT_API_PERS",
            model="GigaChat",
            verify_ssl_certs=False
        )
    ))
    mock_instance = MagicMock()
    mock_gigachat_cls = MagicMock(return_value=mock_instance)
    mock_chat_models = MagicMock()
    mock_chat_models.GigaChat = mock_gigachat_cls

    with patch.dict(sys.modules, {
        "langchain_gigachat": MagicMock(),
        "langchain_gigachat.chat_models": mock_chat_models,
    }):
        result = create_llm(config)

    mock_gigachat_cls.assert_called_once_with(
        credentials="test_creds",
        scope="GIGACHAT_API_PERS",
        model="GigaChat",
        verify_ssl_certs=False
    )
    mock_instance.bind_tools.assert_called_once_with(tools)
    assert result is mock_instance.bind_tools.return_value


def test_create_llm_gigachat_missing_section():
    from src.llm_factory import create_llm
    config = AppConfig(llm=LLMConfig(provider="gigachat", gigachat=None))
    with pytest.raises(ValueError, match="Секция \\[llm.gigachat\\] отсутствует"):
        create_llm(config)


def test_create_llm_unknown_provider():
    from src.llm_factory import create_llm
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        config = AppConfig(llm=LLMConfig(provider="unknown"))
