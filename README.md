# Очистка кэша
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Тесты
uv run pytest tests/ -v

ollama pull qwen2.5:7b nomic-embed-text

# Локальный прогон с mock-заглушкой (если Ollama ещё не скачал модель)
uv run python -c "
from src.graph.builder import build_graph
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

fake_llm = MagicMock()
fake_llm.invoke.return_value = AIMessage(content='Моковый ответ')

with patch('src.graph.nodes.get_llm', return_value=fake_llm):
    g = build_graph()
    # ⬇️ Обязательно: config с thread_id для MemorySaver
    config = {'configurable': {'thread_id': 'test-1'}}
    res = g.invoke(
        {'messages': [HumanMessage(content='Тест')], 'adaptation_log': []},
        config=config
    )
    print('✅ Graph OK | State keys:', list(res.keys()))
"

# запуск сервера
uv run uvicorn src.server.app:app --port 8000

# тест запроса с красивым ответом
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Рассчитай платёж по кредиту 500000 на 24 месяца"}' | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'💬 Ответ: {d[\"response\"]}')
print(f'⚡ Задержка: {d[\"metrics\"][\"latency\"]}s')
print(f'🪙 Токены: {d[\"metrics\"][\"prompt_tokens\"]}→{d[\"metrics\"][\"output_tokens\"]}')
"