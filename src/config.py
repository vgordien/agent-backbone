from pydantic import BaseModel
import tomllib
import pathlib


class OllamaConfig(BaseModel):
    model: str = "qwen2.5:7b"
    temperature: float = 0
    num_predict: int = 512


class GigaChatConfig(BaseModel):
    credentials: str
    scope: str = "GIGACHAT_API_PERS"
    model: str = "GigaChat"
    verify_ssl_certs: bool = False


class LLMConfig(BaseModel):
    provider: str = "ollama"
    ollama: OllamaConfig = OllamaConfig()
    gigachat: GigaChatConfig | None = None


class AppConfig(BaseModel):
    llm: LLMConfig = LLMConfig()


def load_config(path: str = "config.toml") -> AppConfig:
    p = pathlib.Path(path)
    if not p.exists():
        return AppConfig()
    with open(p, "rb") as f:
        return AppConfig.model_validate(tomllib.load(f))
