import pytest
from src.config import load_config, AppConfig, OllamaConfig, GigaChatConfig


def test_defaults_when_no_file():
    config = load_config("nonexistent_config.toml")
    assert config.llm.provider == "ollama"
    assert config.llm.ollama.model == "qwen2.5:7b"
    assert config.llm.ollama.temperature == 0
    assert config.llm.ollama.num_predict == 512
    assert config.llm.gigachat is None


def test_ollama_provider_from_toml(tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_bytes(b"""
[llm]
provider = "ollama"

[llm.ollama]
model = "llama3:8b"
temperature = 0.5
num_predict = 256
""")
    config = load_config(str(toml_file))
    assert config.llm.provider == "ollama"
    assert config.llm.ollama.model == "llama3:8b"
    assert config.llm.ollama.temperature == 0.5
    assert config.llm.ollama.num_predict == 256


def test_gigachat_provider_from_toml(tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_bytes(b"""
[llm]
provider = "gigachat"

[llm.gigachat]
credentials = "test_creds_base64"
scope = "GIGACHAT_API_CORP"
model = "GigaChat-Pro"
verify_ssl_certs = true
""")
    config = load_config(str(toml_file))
    assert config.llm.provider == "gigachat"
    assert config.llm.gigachat.credentials == "test_creds_base64"
    assert config.llm.gigachat.scope == "GIGACHAT_API_CORP"
    assert config.llm.gigachat.model == "GigaChat-Pro"
    assert config.llm.gigachat.verify_ssl_certs is True


def test_gigachat_section_defaults(tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_bytes(b"""
[llm]
provider = "gigachat"

[llm.gigachat]
credentials = "test_creds"
""")
    config = load_config(str(toml_file))
    assert config.llm.gigachat.scope == "GIGACHAT_API_PERS"
    assert config.llm.gigachat.model == "GigaChat"
    assert config.llm.gigachat.verify_ssl_certs is False
