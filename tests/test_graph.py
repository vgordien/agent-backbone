import pytest
from src.graph.builder import build_graph
from langchain_core.messages import HumanMessage, AIMessage

def test_flow_success():
    app = build_graph()
    cfg = {"configurable": {"thread_id": "test-success"}}

    res = app.invoke(
        {"messages": [HumanMessage(content="Какой баланс у счёта ACC-1?")], "adaptation_log": []},
        config=cfg
    )

    assert "messages" in res
    assert "metrics" in res
    assert res["metrics"].get("latency") is not None
    
    # Проверка по типу, а не по строке роли (устойчиво к версиям LangChain)
    assert any(isinstance(m, AIMessage) for m in res["messages"])

def test_reflection_triggers():
    app = build_graph()
    cfg = {"configurable": {"thread_id": "test-reflect"}}

    app.invoke({"messages": [HumanMessage(content="Тест 1")], "adaptation_log": []}, config=cfg)
    app.invoke({"messages": [HumanMessage(content="Тест 2")], "adaptation_log": []}, config=cfg)
    res = app.invoke({"messages": [HumanMessage(content="Тест 3 с ошибкой")], "adaptation_log": []}, config=cfg)
    
    assert "adaptation_log" in res
    assert isinstance(res["adaptation_log"], list)