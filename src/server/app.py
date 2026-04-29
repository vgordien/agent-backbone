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
        res = graph.invoke(
            {"messages": [HumanMessage(content=req.user_input)], "adaptation_log": []},
            config=cfg
        )
        ans = res["messages"][-1].content if res["messages"] else "Нет ответа"
        log_trace(res.get("metrics", {}), res["messages"])
        return {"response": ans, "thread_id": tid, "metrics": res.get("metrics", {})}
    except Exception as e:
        return {"error": str(e)}