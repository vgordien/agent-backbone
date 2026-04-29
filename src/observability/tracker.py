import logging
from rich.console import Console

logger = logging.getLogger("agent")
console = Console()

def log_trace(metrics: dict, messages: list):
    total = metrics.get("prompt_tokens", 0) + metrics.get("output_tokens", 0)
    console.print(f"\n📊 TRACE | Tokens: {total} | Latency: {metrics.get('latency', 0)}s")
    for m in messages:
        role = getattr(m, "role", "system")
        content = str(m.content)[:120]
        tools = [t["name"] for t in getattr(m, "tool_calls", [])]
        console.print(f"  ↳ {role}: {content} {'| tools:'+','.join(tools) if tools else ''}")