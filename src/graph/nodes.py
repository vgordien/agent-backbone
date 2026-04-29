from langchain_core.messages import ToolMessage
from src.tools.banking import tools
from src.rag.retriever import init_retriever
from src.prompts.templates import BANKING_SYSTEM_PROMPT
import time

_llm = None
_retriever = None

def get_llm():
    global _llm
    if _llm is None:
        from src.config import load_config
        from src.llm_factory import create_llm
        _llm = create_llm(load_config())
    return _llm

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = init_retriever()
    return _retriever

def _safe_content(msg) -> str:
    return msg.content if hasattr(msg, "content") else msg.get("content", "")

def rag_node(state):
    query = _safe_content(state["messages"][-1])
    try:
        docs = get_retriever().invoke(query)
        context = "\n".join([d.page_content if hasattr(d, "page_content") else str(d) for d in docs])
    except Exception:
        context = ""
    return {"rag_context": context}

def llm_node(state):
    system_prompt = BANKING_SYSTEM_PROMPT.format(
        adaptation_log="; ".join(state["adaptation_log"]) or "Нет уроков.",
        tools=[{"name": t.name, "desc": t.description} for t in tools]
    )
    msgs = [{"role": "system", "content": system_prompt}] + list(state["messages"])
    
    start = time.time()
    response = get_llm().invoke(msgs)
    latency = time.time() - start
    
    usage = getattr(response, "usage_metadata", {}) or {}
    return {
        "messages": [response],
        "metrics": {
            "latency": round(latency, 2),
            "prompt_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0)
        }
    }

def tool_node(state):
    results = []
    last = state["messages"][-1]
    if not hasattr(last, "tool_calls") or not last.tool_calls:
        return {"messages": results}
        
    for tc in last.tool_calls:
        try:
            tool_obj = next(t for t in tools if t.name == tc["name"])
            output = tool_obj.invoke(tc["args"])
            results.append(ToolMessage(content=str(output), tool_call_id=tc["id"]))
        except Exception as e:
            results.append(ToolMessage(content=f"Ошибка {tc['name']}: {e}", tool_call_id=tc["id"]))
    return {"messages": results}