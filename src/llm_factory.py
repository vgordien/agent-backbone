from src.config import AppConfig
from src.tools.banking import tools


def create_llm(config: AppConfig):
    provider = config.llm.provider
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        c = config.llm.ollama
        return ChatOllama(model=c.model, temperature=c.temperature, num_predict=c.num_predict).bind_tools(tools)
    if provider == "gigachat":
        if config.llm.gigachat is None:
            raise ValueError("Секция [llm.gigachat] отсутствует в config.toml")
        from langchain_gigachat.chat_models import GigaChat
        c = config.llm.gigachat
        return GigaChat(
            credentials=c.credentials,
            scope=c.scope,
            model=c.model,
            verify_ssl_certs=c.verify_ssl_certs,
        ).bind_tools(tools)
    raise ValueError(f"Неизвестный провайдер: {provider}")
