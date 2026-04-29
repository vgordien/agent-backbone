# src/server/app.py
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from src.graph.builder import build_graph
from src.observability.tracker import log_trace
import uuid

app = FastAPI(title="Bank AI Agent")
graph = build_graph()

class ChatReq(BaseModel):
    user_input: str
    thread_id: str | None = None

@app.post("/chat")
async def chat(req: ChatReq):
    tid = req.thread_id or str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": tid}}
    
    try:
        # ⬇️ Конвертируем строку в HumanMessage — это ключевая фиксация
        res = graph.invoke(
            {
                "messages": [HumanMessage(content=req.user_input)],
                "adaptation_log": []
            },
            config=cfg
        )
        
        # Безопасное извлечение ответа
        last_msg = res["messages"][-1] if res.get("messages") else None
        answer = getattr(last_msg, "content", str(last_msg)) if last_msg else "Нет ответа"
        
        log_trace(res.get("metrics", {}), res.get("messages", []))
        
        return {
            "response": answer,
            "thread_id": tid,
            "metrics": res.get("metrics", {})
        }
    except Exception as e:
        # Логирование ошибки для дебага
        import logging
        logging.error(f"Agent error: {e}", exc_info=True)
        return {"error": str(e)}