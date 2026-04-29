# Дизайн: поддержка GigaChat + конфигурируемый LLM-провайдер

**Дата:** 2026-04-29  
**Статус:** Approved

## Цель

Добавить GigaChat как альтернативный LLM-провайдер рядом с Ollama. Провайдер выбирается через `config.toml` в корне проекта.

## Новые файлы

| Файл | Назначение |
|---|---|
| `config.toml` | Конфиг провайдера (в .gitignore — содержит credentials) |
| `config.toml.example` | Шаблон для коммита в git |
| `src/config.py` | Загрузка и Pydantic-валидация конфига |
| `src/llm_factory.py` | Фабрика: конфиг → LLM-объект с bind_tools |

## Изменяемые файлы

| Файл | Изменение |
|---|---|
| `src/graph/nodes.py` | `get_llm()` делегирует фабрике вместо прямого создания ChatOllama |
| `pyproject.toml` | Добавляется `langchain-gigachat` в зависимости |
| `.gitignore` | `config.toml` добавляется в ignore |

## Формат config.toml

```toml
[llm]
provider = "gigachat"   # "gigachat" или "ollama"

[llm.ollama]
model = "qwen2.5:7b"
temperature = 0
num_predict = 512

[llm.gigachat]
credentials = "YOUR_BASE64_CREDENTIALS_HERE"
scope = "GIGACHAT_API_PERS"   # или GIGACHAT_API_CORP
model = "GigaChat"
verify_ssl_certs = false
```

Если `config.toml` отсутствует — поведение как раньше (Ollama с дефолтными параметрами).

## src/config.py

```python
from pydantic import BaseModel
import tomllib, pathlib

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
```

## src/llm_factory.py

```python
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
        return GigaChat(credentials=c.credentials, scope=c.scope,
                        model=c.model, verify_ssl_certs=c.verify_ssl_certs).bind_tools(tools)
    raise ValueError(f"Неизвестный провайдер: {provider}")
```

## Изменения в src/graph/nodes.py

`get_llm()` заменяется на:

```python
def get_llm():
    global _llm
    if _llm is None:
        from src.config import load_config
        from src.llm_factory import create_llm
        _llm = create_llm(load_config())
    return _llm
```

## Ключевые решения

- **tomllib** — встроен в Python 3.11+, нет новой зависимости для парсинга TOML
- **Ленивые импорты** — `langchain_ollama` и `langchain_gigachat` импортируются внутри `if`-веток, поэтому отсутствие одного пакета не ломает другой
- **Дефолт без конфига** — если `config.toml` нет, поведение идентично текущему
- **credentials в .gitignore** — `config.toml` не коммитится; в git идёт только `config.toml.example`

## Тестирование

Существующие тесты используют `patch('src.graph.nodes.get_llm')` — они продолжат работать без изменений. Новые тесты покрывают `load_config()` и `create_llm()` изолированно.
