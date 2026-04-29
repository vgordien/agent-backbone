from typing import TypedDict, Annotated, List
from operator import add
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # LangGraph корректно работает только с List, а не Sequence
    messages: Annotated[List[BaseMessage], add]
    rag_context: str | None
    adaptation_log: list[str]
    metrics: dict
    error: str | None