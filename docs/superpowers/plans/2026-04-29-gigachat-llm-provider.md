# GigaChat LLM Provider Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GigaChat as a configurable LLM provider alongside Ollama, selected via `config.toml` in the project root.

**Architecture:** A new `src/config.py` loads `config.toml` with stdlib `tomllib` and validates it with Pydantic. A new `src/llm_factory.py` takes an `AppConfig` and returns the correct LLM bound to tools. `src/graph/nodes.py` delegates LLM creation to the factory instead of hardcoding ChatOllama. Provider-specific imports are lazy (inside `if`-branches) so missing packages don't break the other provider.

**Tech Stack:** Python 3.12, Pydantic v2, tomllib (stdlib, no extra dep), langchain-ollama (existing), langchain-gigachat (new)

---

### Task 1: Dependencies, .gitignore, config.toml.example

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `config.toml.example`

- [ ] **Step 1: Add langchain-gigachat to pyproject.toml**

Replace the `dependencies` list in `pyproject.toml`:

```toml
dependencies = [
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "langchain-ollama>=0.2.0",
    "langchain-community>=0.3.0",
    "langchain-chroma>=0.2.0",
    "langchain-gigachat>=0.3.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "pydantic>=2.9.0",
    "tenacity>=9.0.0",
    "rich>=13.0.0",
]
```

- [ ] **Step 2: Add config.toml to .gitignore**

Append to `.gitignore` (config.toml contains credentials, must not be committed):

```
# Local LLM provider config (contains credentials)
config.toml
```

- [ ] **Step 3: Create config.toml.example**

Create `config.toml.example` in the project root:

```toml
[llm]
provider = "ollama"   # "ollama" or "gigachat"

[llm.ollama]
model = "qwen2.5:7b"
temperature = 0
num_predict = 512

[llm.gigachat]
credentials = "YOUR_BASE64_CREDENTIALS_HERE"
scope = "GIGACHAT_API_PERS"   # or "GIGACHAT_API_CORP"
model = "GigaChat"
verify_ssl_certs = false
```

- [ ] **Step 4: Install new dependency**

```bash
uv sync
```

Expected: resolves and installs `langchain-gigachat` without errors, updates `uv.lock`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore config.toml.example uv.lock
git commit -m "feat: add langchain-gigachat dependency and config template"
```

---

### Task 2: src/config.py

**Files:**
- Create: `tests/test_config.py`
- Create: `src/config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'load_config' from 'src.config'` (module doesn't exist yet)

- [ ] **Step 3: Implement src/config.py**

Create `src/config.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add config module with Pydantic models for LLM provider settings"
```

---

### Task 3: src/llm_factory.py

**Files:**
- Create: `tests/test_llm_factory.py`
- Create: `src/llm_factory.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_llm_factory.py`:

```python
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
    config = AppConfig(llm=LLMConfig(provider="unknown"))
    with pytest.raises(ValueError, match="Неизвестный провайдер: unknown"):
        create_llm(config)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_llm_factory.py -v
```

Expected: `ImportError: cannot import name 'create_llm' from 'src.llm_factory'`

- [ ] **Step 3: Implement src/llm_factory.py**

Create `src/llm_factory.py`:

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
        return GigaChat(
            credentials=c.credentials,
            scope=c.scope,
            model=c.model,
            verify_ssl_certs=c.verify_ssl_certs,
        ).bind_tools(tools)
    raise ValueError(f"Неизвестный провайдер: {provider}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_llm_factory.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_factory.py tests/test_llm_factory.py
git commit -m "feat: add LLM factory supporting Ollama and GigaChat providers"
```

---

### Task 4: Update src/graph/nodes.py

**Files:**
- Modify: `src/graph/nodes.py`

- [ ] **Step 1: Replace get_llm() in nodes.py**

In `src/graph/nodes.py`, replace lines 10–14:

```python
# OLD
def get_llm():
    global _llm
    if _llm is None:
        from langchain_ollama import ChatOllama
        _llm = ChatOllama(model="qwen2.5:7b", temperature=0, num_predict=512).bind_tools(tools)
    return _llm
```

with:

```python
# NEW
def get_llm():
    global _llm
    if _llm is None:
        from src.config import load_config
        from src.llm_factory import create_llm
        _llm = create_llm(load_config())
    return _llm
```

- [ ] **Step 2: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASS. Existing graph/tools tests mock `get_llm` directly and are unaffected by this change.

- [ ] **Step 3: Commit**

```bash
git add src/graph/nodes.py
git commit -m "feat: nodes.py delegates LLM creation to llm_factory"
```

---

### Task 5: Smoke test

- [ ] **Step 1: Verify graph works with mock LLM (no Ollama required)**

```bash
uv run python -c "
from src.graph.builder import build_graph
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

fake_llm = MagicMock()
fake_llm.invoke.return_value = AIMessage(content='OK')

with patch('src.graph.nodes.get_llm', return_value=fake_llm):
    g = build_graph()
    res = g.invoke(
        {'messages': [HumanMessage(content='Тест')], 'adaptation_log': []},
        config={'configurable': {'thread_id': 'smoke-1'}}
    )
    print('Graph OK | keys:', list(res.keys()))
"
```

Expected: `Graph OK | keys: ['messages', 'rag_context', 'adaptation_log', 'metrics', 'error']`

- [ ] **Step 2: Verify config switching works**

```bash
cp config.toml.example config.toml
uv run python -c "
from src.config import load_config
cfg = load_config()
print('Provider:', cfg.llm.provider)
print('Ollama model:', cfg.llm.ollama.model)
"
```

Expected:
```
Provider: ollama
Ollama model: qwen2.5:7b
```

- [ ] **Step 3: Clean up test config**

```bash
rm config.toml
```
