import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage

@pytest.fixture(autouse=True)
def mock_llm_and_retriever():
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(
        content="Ответ агента",
        response_metadata={"eval_count": 15, "prompt_eval_count": 40}
    )
    
    fake_retriever = MagicMock()
    fake_retriever.invoke.return_value = []

    # Патчим ленивые функции. Тесты больше не стучатся в сеть.
    with patch("src.graph.nodes.get_llm", return_value=fake_llm), \
         patch("src.graph.nodes.get_retriever", return_value=fake_retriever):
        yield fake_llm, fake_retriever