from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.graph.state import AgentState
from src.graph.nodes import rag_node, llm_node, tool_node
from src.evolution.reflector import reflect_node

def build_graph():
    w = StateGraph(AgentState)
    w.add_node("rag", rag_node)
    w.add_node("agent", llm_node)
    w.add_node("tools", tool_node)
    w.add_node("reflect", reflect_node)
    
    w.set_entry_point("rag")
    w.add_edge("rag", "agent")
    
    def route(s):
        m = s["messages"]
        last = m[-1] if m else None
        if last and hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        if len(m) > 2:  # после 2 ходов запускаем рефлексию
            return "reflect"
        return END
        
    w.add_conditional_edges("agent", route, {"tools": "tools", "reflect": "reflect", END: END})
    w.add_edge("tools", "agent")
    w.add_edge("reflect", END)
    
    return w.compile(checkpointer=MemorySaver())